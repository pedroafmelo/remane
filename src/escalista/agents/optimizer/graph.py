"""Agente de otimização (plano da C5, I1; plano da C6, B4a): grafo LangGraph mínimo, sem checkpointer.

Desenho: **um grafo por trecho entre paradas humanas**, invocado pela classe `OptimizerAgent`:

- `start_run` → grafo de leitura. Dois modos, escolhidos na construção:
  - **C6** (`read_tables` injetado): nó 1 `ler_e_padronizar` = tabelas cruas (`read_tables`) → mapeamento de colunas
    (`map_columns`, o modelo; reserva: `rules.header_aliases.guess_mapping`, com aviso RX-12) → `apply_mapping` com
    a conferência de evidência → identidade (`resolve_identities` contra o último quadro) → cadastro simulado
    (`enrich`) → cartão da semana (`load_card`) → demanda inferida e capacidade → resumo. RX-13 se nada servir.
  - **C5** (`read_csv`): `ler_escala` (CSV da DEC-039 → validação → resumo), com quadro, demanda e semana fixos.
- `start_next_week` (C6): sem upload; o "antes" é a última escala publicada levada 1 semana adiante, e o quadro e a
  demanda são os do último `Roster`.
- `confirm(run_id, data)` (o gestor confirmou o resumo) → na 1ª escala grava o `Roster` (lojas, pessoas, padrão de
  demanda escalado pela cobertura-alvo) e roda o grafo de otimização: `otimizar → verificar → comparar → justificar`,
  com saída antecipada se o solver não devolver escala (RX-12). Nesta camada (M1), `spec=None`: a formulação pelo
  modelo e o laço do solver são da B4b.
- `approve` grava a aprovação humana e chama a ferramenta `publicar` (`tools.py`), que relê a aprovação no
  `Repository` e recusa sem ela.

Avisos que não bloqueiam (RX-02 de cobertura, RX-12 da justificativa ou da leitura sem modelo) vão para
`RunState.notices`; `exception` fica só para o que bloqueia (`failed`).

O estado durável é o `RunState`, salvo pelo `Repository` depois de cada nó (com o "antes" em `RunState.before`); o
estado do grafo (`FlowState`) só vive durante uma invocação (arquitetura, seção 4: sem checkpointer). O contexto da
leitura (o arquivo já mapeado, a identidade, as pessoas e o padrão de demanda) fica **em memória** entre `start_run`
e `confirm`, como a C5 fazia com o CSV: se o processo reiniciar nesse intervalo, `confirm` pede o arquivo de novo
(`RunPhaseError`). A continuidade não depende de memória: o quadro e o "antes" estão no `Repository`.

Fronteira: só núcleo (`domain`, `rules`, `solver`, `verifier`), portas e `langgraph`. As bordas entram injetadas.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from escalista.agents.optimizer.errors import RunNotFoundError, RunPhaseError
from escalista.agents.optimizer.tools import (
    PUBLISHER_ROLES,
    AgentRepository,
    Enrich,
    Justifier,
    ListEvents,
    LoadCard,
    MapColumns,
    ReadCsv,
    ReadTables,
    Tracer,
    publicar,
)
from escalista.domain.contracts import ExceptionCard, LLMUnavailableError, Role, TraceEvent
from escalista.domain.ports import Clock, TraceSink
from escalista.domain.reading import ColumnMapping, ConfirmInput, DemandPattern, IdentityAnswer, RawTable
from escalista.domain.results import (
    Approval,
    RunState,
    ScheduleVersion,
    SolveRequest,
    SolveResult,
    ViolationReport,
)
from escalista.domain.roster import Roster
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import CsvIssue, DemandSlot, Employee, EmployeePublic, ReadSummary, Schedule, Store
from escalista.domain.spec import SolveSpec
from escalista.rules.demand import (
    capacity_check,
    demand_for_week,
    infer_demand_pattern,
    infer_store_hours,
    scale_pattern,
)
from escalista.rules.header_aliases import guess_mapping
from escalista.rules.identity import IdentityResult, resolve_identities
from escalista.rules.mapping import MappingResult, apply_mapping, verify_evidence
from escalista.rules.week import next_week_start, shift_schedule
from escalista.solver.cost import compare_schedules
from escalista.solver.model import solve
from escalista.verifier import CHECKS, verify

log = logging.getLogger(__name__)

EXCEPTION_KIND = "exception.raised"
LLM_JUSTIFY_KIND = "llm.justify"
# Regras que a função de custo lê do cartão (solver/cost.py): jornadas para a hora extra e o adicional.
COST_RULE_KINDS = frozenset({"jornada_diaria_max", "jornada_semanal_max", "adicional_hora_extra"})
SOURCE_MODEL = "modelo"
SOURCE_HEURISTIC = "heuristica"
CONFIRMED_BY = "gestor"  # a assinatura de `confirm` não traz a conta de quem confirmou (B4a: relatado)
MAX_EVIDENCE = 5
MAX_CARD_ISSUES = 10
MAX_LINE_EVIDENCE = 20  # linhas com problema listadas no cartão RX-13 da leitura parcial
_HOURS = Decimal("0.01")
_FORMATS = frozenset({"csv", "xlsx", "pdf"})
_IF_NO_CONFIRM = "Nada é otimizado sem a confirmação do gestor."


class FlowState(TypedDict, total=False):
    """Estado de uma invocação do grafo. Só `run` é durável (salvo a cada nó)."""

    run: RunState
    file_name: str
    content: bytes
    # problema de otimização montado na confirmação (C5: fixo na construção; C6: por execução)
    before: Schedule
    card: RuleCard
    stores: list[Store]
    employees: list[Employee]
    demand: list[DemandSlot]
    week_start: date
    hint: Schedule | None
    spec: SolveSpec | None
    note: str  # pedido em texto do gestor; guardado para a formulação (B4b), não usado nesta camada
    solved: SolveResult
    after_report: ViolationReport
    before_report: ViolationReport


Node = Callable[[FlowState], dict[str, Any]]


@dataclass(frozen=True)
class _Assembled:
    """O problema montado a partir da leitura: identidade, cartão da semana, pessoas, lojas, padrão e "antes"."""

    identity: IdentityResult
    card: RuleCard
    employees: list[Employee]
    stores: list[Store]
    hours_from_cadastro: int
    assumptions: list[str]
    pattern: list[DemandPattern]
    before: Schedule
    week_start: date  # semana planejada


@dataclass(frozen=True)
class _Reading:
    """Contexto da leitura guardado em memória entre `start_run` e `confirm` (C6)."""

    mapped: MappingResult
    roster: Roster | None  # o quadro contra o qual a identidade foi resolvida
    file_week: date
    assembled: _Assembled


class OptimizerAgent:
    """Implementa o `SliceAgentC6` da API (mesmos métodos e assinaturas; erros em `agents/optimizer/errors.py`).

    Modo C6 quando `read_tables` é passado (exige `enrich` e `load_card`); senão, o modo da C5, que exige `read_csv`,
    `card`, `stores`, `employees`, `demand` e `week_start` e segue idêntico ao da fatia."""

    def __init__(
        self,
        *,
        repo: AgentRepository,
        sink: TraceSink,
        clock: Clock,
        justify: Justifier,
        list_events: ListEvents,
        read_csv: ReadCsv | None = None,
        card: RuleCard | None = None,
        stores: list[Store] | None = None,
        employees: list[Employee] | None = None,
        demand: list[DemandSlot] | None = None,
        week_start: date | None = None,
        read_tables: ReadTables | None = None,
        map_columns: MapColumns | None = None,
        cadastro: object | None = None,
        enrich: Enrich | None = None,
        load_card: LoadCard | None = None,
        default_wage: Decimal | None = None,
        seed: int = 42,
        time_limit_s: float = 30.0,
        num_workers: int = 1,
        publisher_roles: Iterable[Role] = PUBLISHER_ROLES,
        new_id: Callable[[], str] = lambda: uuid4().hex,
    ) -> None:
        if read_tables is not None:
            if enrich is None or load_card is None:
                raise ValueError("o modo C6 (read_tables) exige enrich e load_card")
        elif None in (read_csv, card, stores, employees, demand, week_start):
            raise ValueError("sem read_tables, o modo da C5 exige read_csv, card, stores, employees, demand e semana")
        self._repo = repo
        self._clock = clock
        self._read_csv = read_csv
        self._justify = justify
        self._list_events = list_events
        self._card = card
        self._stores = list(stores or [])
        self._employees = sorted(employees or [], key=lambda e: e.id)
        self._demand = list(demand or [])
        self._week_start = week_start
        self._read_tables = read_tables
        self._map_columns = map_columns
        self._cadastro = cadastro
        self._enrich = enrich
        self._load_card = load_card
        self._default_wage = default_wage
        self._seed = seed
        self._time_limit_s = time_limit_s
        self._num_workers = num_workers
        self._publisher_roles = frozenset(publisher_roles)
        self._new_id = new_id
        self._tracer = Tracer(sink, clock, new_id=new_id, list_events=list_events)
        self._inputs: dict[str, Schedule] = {}  # C5: escala enviada, entre `start_run` e `confirm`
        self._readings: dict[str, _Reading] = {}  # C6: contexto da leitura, entre `start_run` e `confirm`
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._roster_lock = threading.Lock()  # a versão do quadro é "última + 1": uma gravação por vez
        self._read_graph = self._build_read_graph()
        self._optimize_graph = self._build_optimize_graph()

    # --- SliceAgentC6 --------------------------------------------------------------------------------------------

    def start_run(self, file_name: str, content: bytes) -> RunState:
        state = RunState(run_id=f"run-{self._new_id()}", phase="read")
        self._repo.save_run(state)
        with self._lock(state.run_id):
            return self._invoke(self._read_graph, {"run": state, "file_name": file_name, "content": content})

    def confirm(self, run_id: str, data: ConfirmInput | None = None) -> RunState:
        with self._lock(run_id):
            state = self._require(run_id, "awaiting_confirm")
            if self._read_tables is None:
                return self._confirm_c5(state)
            answer = data or ConfirmInput()
            if state.mode == "continuidade":
                inputs = self._confirm_next_week(state, answer)
            else:
                inputs = self._confirm_upload(state, answer)
            out = self._invoke(self._optimize_graph, inputs)
            self._readings.pop(run_id, None)
            return out

    def start_next_week(self) -> RunState:
        """Planeja a semana seguinte à última publicada, sem upload (modo `continuidade`)."""
        if self._load_card is None:
            raise RunPhaseError("planejar a próxima semana exige a leitura da C6 (agente sem `load_card`)")
        published = self._repo.latest_published()
        roster = self._repo.latest_roster()
        if published is None or roster is None:
            raise RunPhaseError(
                "envie a primeira escala, confirme e publique antes de planejar a próxima semana"
                + (" (não há escala publicada)" if published is None else " (não há quadro confirmado)")
            )
        source_week = published.schedule.week_start
        week = next_week_start(source_week)
        known_people = {e.id for e in roster.employees}
        known_stores = {s.id for s in roster.stores}
        moved = shift_schedule(published.schedule, 1)
        kept = [s for s in moved.shifts if s.employee_id in known_people and s.store_id in known_stores]
        before = Schedule(week_start=week, shifts=kept)
        card = self._load_card(week)
        assumptions = _provisional_notes(card, week)
        if len(kept) < len(moved.shifts):
            assumptions.append(
                f"{len(moved.shifts) - len(kept)} turnos da escala publicada são de pessoas ou lojas fora do quadro "
                'atual e ficaram fora do "antes".'
            )
        summary = ReadSummary(
            file_name=f"última escala publicada (semana de {source_week:%d/%m})",
            rows=len(before.shifts),
            employees=len(roster.employees),
            stores=len(roster.stores),
            week_start=week,
            total_hours=_total_hours(before),
            issues=[],
            ok=True,
            format="continuidade",
            mapping=None,
            mapping_source="plataforma",
            assumptions=assumptions,
            capacity=capacity_check(roster.demand, roster.employees, card),
            planned_week_start=week,
            store_ids=[s.id for s in roster.stores],
        )
        state = RunState(
            run_id=f"run-{self._new_id()}",
            phase="awaiting_confirm",
            summary=summary,
            mode="continuidade",
            before=before,
            week_start=week,
            roster_version=roster.version,
        )
        with self._lock(state.run_id):
            self._repo.save_run(state)
            self._tracer.step(
                state.run_id,
                "run.next_week",
                payload={
                    "from_version_id": published.id,
                    "from_week_start": source_week.isoformat(),
                    "week_start": week.isoformat(),
                    "roster_version": roster.version,
                    "shifts": len(before.shifts),
                    "dropped_shifts": len(moved.shifts) - len(kept),
                    "provisional": list(card.provisional),
                },
            )
        return state

    def roster(self) -> Roster | None:
        return self._repo.latest_roster()

    def get_run(self, run_id: str) -> RunState | None:
        return self._repo.get_run(run_id)

    def get_schedule(self, run_id: str) -> Schedule | None:
        state = self._repo.get_run(run_id)
        if state is None or state.version_id is None:
            return None
        version = self._repo.get_version(state.version_id)
        return version.schedule if version else None

    def employees(self, run_id: str) -> list[EmployeePublic]:
        state = self._repo.get_run(run_id)
        if state is None:
            return []
        if self._read_tables is None:
            people = self._employees
        elif state.roster_version is not None and (roster := self._repo.get_roster(state.roster_version)):
            people = roster.employees
        elif (reading := self._readings.get(run_id)) is not None:
            people = reading.assembled.employees
        else:
            people = []
        return [EmployeePublic.from_employee(e) for e in people]

    def approve(self, run_id: str, approval: Approval) -> RunState:
        """Grava a aprovação humana (se for desta versão) e chama `publicar`, que a relê e recusa sem ela."""
        with self._lock(run_id):
            state = self._require(run_id, "awaiting_approval")
            if approval.version_id == state.version_id:
                self._repo.record_approval(approval)
                self._tracer.human(
                    run_id,
                    "approval.recorded",
                    payload={
                        "approval_id": approval.id,
                        "version_id": approval.version_id,
                        "approved_by": approval.approved_by,
                        "role": approval.role.value,
                    },
                )
            else:
                log.warning("aprovação de outra versão ignorada: run_id=%s", run_id)
            publicar(
                repo=self._repo,
                tracer=self._tracer,
                run_id=run_id,
                version_id=state.version_id,
                allowed_roles=self._publisher_roles,
            )  # levanta PublishRefusedError; a execução segue em `awaiting_approval`
            state = state.model_copy(update={"phase": "published"})
            self._repo.save_run(state)
            return state

    def published(self) -> ScheduleVersion | None:
        return self._repo.latest_published()

    def trace(self, run_id: str) -> list[TraceEvent]:
        return list(self._list_events(run_id))

    # --- confirmação ------------------------------------------------------------------------------------------------

    def _confirm_c5(self, state: RunState) -> RunState:
        before = self._inputs.get(state.run_id)
        if before is None:
            raise RunPhaseError("a escala enviada não está mais em memória; envie o arquivo de novo")
        self._tracer.human(state.run_id, "read.confirmed", payload={"rows": state.summary.rows if state.summary else 0})
        assert self._card is not None and self._week_start is not None  # garantido na construção (modo C5)
        out = self._invoke(
            self._optimize_graph,
            {
                "run": state,
                "before": before,
                "card": self._card,
                "stores": self._stores,
                "employees": self._employees,
                "demand": self._demand,
                "week_start": self._week_start,
            },
        )
        self._inputs.pop(state.run_id, None)
        return out

    def _confirm_upload(self, state: RunState, answer: ConfirmInput) -> FlowState:
        """1ª escala: aplica as correções do gestor, grava o `Roster` e monta o problema de otimização."""
        run_id = state.run_id
        reading = self._readings.get(run_id)
        if reading is None:
            raise RunPhaseError("a leitura do arquivo não está mais em memória; envie o arquivo de novo")
        planned = answer.planned_week_start or reading.file_week
        wage = answer.hourly_wage_default or self._default_wage
        asm = reading.assembled
        if answer.identity or planned != asm.week_start or answer.hourly_wage_default is not None:
            try:
                asm = self._assemble(reading.mapped, reading.roster, answer.identity, reading.file_week, planned, wage)
            except ValueError as exc:  # sem salário-hora (sem cadastro e sem valor informado)
                raise RunPhaseError(f"não foi possível montar o quadro: {exc}") from exc
        if asm.identity.pending:
            answered = {a.card_id for a in answer.identity}
            open_cards = [c for c in asm.identity.cards if c.kind == "homonimo" and c.id not in answered]
            raise RunPhaseError(
                "há cartão de homônimo sem resposta: diga se os nomes iguais são a mesma pessoa ou pessoas distintas "
                f"antes de confirmar ({', '.join(c.id for c in open_cards)})"
            )
        pattern = scale_pattern(asm.pattern, answer.coverage_pct)
        self._tracer.human(
            run_id,
            "read.confirmed",
            payload={
                "mode": "upload",
                "identity_answers": len(answer.identity),
                "identity_same": sum(1 for a in answer.identity if a.same),
                "planned_week_start": planned.isoformat(),
                "week_changed": planned != reading.file_week,
                "hourly_wage_default": str(answer.hourly_wage_default) if answer.hourly_wage_default else None,
                "coverage_pct": dict(sorted(answer.coverage_pct.items())),
                "has_note": bool(answer.note.strip()),  # o texto do pedido não vai ao rastro (pode ter nome)
                "employees": len(asm.employees),
                "stores": len(asm.stores),
                "rows": len(asm.before.shifts),
            },
        )
        roster = self._save_roster(
            run_id,
            lambda version: Roster(
                version=version,
                stores=asm.stores,
                employees=asm.employees,
                demand=pattern,
                source_run_id=run_id,
                confirmed_by=CONFIRMED_BY,
                confirmed_at=self._clock.now(),
            ),
        )
        summary = state.summary
        if summary is not None:
            summary = summary.model_copy(
                update={
                    "planned_week_start": planned,
                    "identity": asm.identity.cards,
                    "capacity": capacity_check(pattern, asm.employees, asm.card),
                }
            )
        state = state.model_copy(
            update={"summary": summary, "before": asm.before, "week_start": planned, "roster_version": roster.version}
        )
        self._repo.save_run(state)
        return {
            "run": state,
            "before": asm.before,
            "card": asm.card,
            "stores": asm.stores,
            "employees": sorted(asm.employees, key=lambda e: e.id),
            "demand": demand_for_week(pattern, planned),
            "week_start": planned,
            "hint": None,
            "spec": None,
            "note": answer.note,
        }

    def _confirm_next_week(self, state: RunState, answer: ConfirmInput) -> FlowState:
        """Continuidade: o quadro e o "antes" vêm do `Repository`; só a cobertura-alvo muda o padrão (nova versão)."""
        run_id = state.run_id
        roster = self._repo.get_roster(state.roster_version) if state.roster_version is not None else None
        if roster is None or state.before is None or state.week_start is None:
            raise RunPhaseError("o quadro desta execução não foi encontrado; planeje a próxima semana de novo")
        assert self._load_card is not None
        week = state.week_start
        card = self._load_card(week)
        coverage = {k: v for k, v in answer.coverage_pct.items() if v != 100}
        ignored = [
            name
            for name, given in (
                ("planned_week_start", answer.planned_week_start is not None),
                ("hourly_wage_default", answer.hourly_wage_default is not None),
                ("identity", bool(answer.identity)),
            )
            if given
        ]
        self._tracer.human(
            run_id,
            "read.confirmed",
            payload={
                "mode": "continuidade",
                "week_start": week.isoformat(),
                "coverage_pct": dict(sorted(answer.coverage_pct.items())),
                "ignored": ignored,  # só valem na 1ª escala
                "has_note": bool(answer.note.strip()),
            },
        )
        pattern = roster.demand
        if coverage:
            pattern = scale_pattern(roster.demand, coverage)
            base = roster
            roster = self._save_roster(
                run_id,
                lambda version: base.model_copy(
                    update={
                        "version": version,
                        "demand": pattern,
                        "source_run_id": run_id,
                        "confirmed_by": CONFIRMED_BY,
                        "confirmed_at": self._clock.now(),
                    }
                ),
            )
            state = state.model_copy(update={"roster_version": roster.version})
            self._repo.save_run(state)
        return {
            "run": state,
            "before": state.before,
            "card": card,
            "stores": roster.stores,
            "employees": sorted(roster.employees, key=lambda e: e.id),
            "demand": demand_for_week(pattern, week),
            "week_start": week,
            "hint": state.before,
            "spec": None,
            "note": answer.note,
        }

    def _save_roster(self, run_id: str, build: Callable[[int], Roster]) -> Roster:
        with self._roster_lock:
            latest = self._repo.latest_roster()
            roster = build((latest.version if latest else 0) + 1)
            self._repo.save_roster(roster)
        self._tracer.step(
            run_id,
            "roster.saved",
            payload={
                "version": roster.version,
                "employees": len(roster.employees),
                "stores": len(roster.stores),
                "demand_slots": len(roster.demand),
                "demand_person_hours": str(Decimal(sum(p.required for p in roster.demand)) / 2),
                "source_run_id": roster.source_run_id,
                "confirmed_by": roster.confirmed_by,
            },
        )
        return roster

    # --- grafos ----------------------------------------------------------------------------------------------------

    def _build_read_graph(self):  # noqa: ANN202 (grafo compilado do LangGraph)
        g = StateGraph(FlowState)
        if self._read_tables is not None:
            g.add_node("ler_e_padronizar", self._saving(self._ler_e_padronizar))
            g.add_edge(START, "ler_e_padronizar")
            g.add_edge("ler_e_padronizar", END)
        else:
            g.add_node("ler_escala", self._saving(self._ler_escala))
            g.add_edge(START, "ler_escala")
            g.add_edge("ler_escala", END)
        return g.compile()

    def _build_optimize_graph(self):  # noqa: ANN202 (grafo compilado do LangGraph)
        g = StateGraph(FlowState)
        g.add_node("otimizar", self._saving(self._otimizar))
        g.add_node("verificar", self._saving(self._verificar))
        g.add_node("comparar", self._saving(self._comparar))
        g.add_node("justificar", self._saving(self._justificar))
        g.add_edge(START, "otimizar")
        g.add_conditional_edges(
            "otimizar", lambda s: "verificar" if s["run"].phase != "failed" else END, ["verificar", END]
        )
        g.add_edge("verificar", "comparar")
        g.add_edge("comparar", "justificar")
        g.add_edge("justificar", END)
        return g.compile()

    def _saving(self, node: Node) -> Node:
        """Salva o `RunState` depois do nó (sem checkpointer: o `Repository` é o estado durável)."""

        def run(state: FlowState) -> dict[str, Any]:
            update = node(state)
            if "run" in update:
                self._repo.save_run(update["run"])
            return update

        return run

    def _invoke(self, graph: Any, inputs: FlowState) -> RunState:
        """Roda o grafo. Erro inesperado num nó não derruba o fluxo: vira RX-12 e fase `failed` (RN-05)."""
        run_id = inputs["run"].run_id
        try:
            return graph.invoke(inputs)["run"]
        except Exception as exc:  # noqa: BLE001 (RN-05: toda falha vira cartão)
            log.exception("falha inesperada no agente de otimização: run_id=%s", run_id)
            card = ExceptionCard(
                code="RX-12",
                title="Falha inesperada no agente",
                reason=f"Um passo do fluxo falhou ({type(exc).__name__}). Nada foi publicado.",
                decider=Role.GESTOR,
                recommendation="Tentar de novo com o mesmo arquivo; se persistir, abrir o rastro desta execução.",
                if_no_answer="A escala atual continua valendo; nenhuma versão nova é publicada.",
            )
            state = (self._repo.get_run(run_id) or inputs["run"]).model_copy(
                update={"phase": "failed", "exception": self._raise_card(run_id, card, step="inesperado")}
            )
            self._repo.save_run(state)
            return state

    # --- nó 1 (C6): ler e padronizar ---------------------------------------------------------------------------------

    def _ler_e_padronizar(self, state: FlowState) -> dict[str, Any]:
        run, name = state["run"], state["file_name"]
        run_id = run.run_id
        assert self._read_tables is not None
        started = time.perf_counter()
        read = self._read_tables(name, state["content"])
        self._tracer.step(
            run_id,
            "ingest.parse",
            started=started,
            payload={"format": read.format, "ok": read.exception is None, "tables": len(read.tables),
                     **read.meta.as_dict()},
        )  # fmt: skip
        if read.exception is not None:
            return self._fail_read(run, read.exception)
        tables = list(read.tables)
        notices: list[ExceptionCard] = []
        mapped, source, assumed_week = self._map(run_id, tables, notices)
        if mapped is None or not mapped.shifts:
            reason = (
                "não consegui entender as colunas do arquivo (nem pelo modelo, nem pelos nomes dos cabeçalhos)"
                if mapped is None
                else "nenhum turno pôde ser lido com o mapeamento das colunas"
            )
            issues = mapped.issues if mapped else []
            summary = None
            if mapped is not None:
                summary = ReadSummary(
                    file_name=name, rows=0, employees=0, stores=0, week_start=mapped.week_start,
                    total_hours=Decimal(0), issues=issues, ok=False, format=_format(read.format),
                    mapping=mapped.mapping, mapping_source=source or SOURCE_HEURISTIC,
                )  # fmt: skip
            card = _rx13(name, reason, [_issue_text(i) for i in issues[:MAX_CARD_ISSUES]])
            return self._fail_read(run, card, summary=summary, notices=notices)
        invented = verify_evidence(tables, mapped)
        if invented:  # invariante 1: nunca turno sem célula de origem (defeito do código, não do arquivo)
            card = _rx13(name, f"{len(invented)} turnos lidos não batem com as células de origem", [])
            return self._fail_read(run, card, notices=notices)
        assert mapped.week_start is not None and source is not None  # há turnos: a semana foi inferida
        file_week = mapped.week_start
        roster = self._repo.latest_roster()
        try:
            asm = self._assemble(mapped, roster, (), file_week, file_week, self._default_wage)
        except ValueError as exc:  # sem salário-hora: sem cadastro e sem `default_wage`
            card = _rx13(name, f"não há salário-hora para as pessoas lidas ({exc})", [])
            return self._fail_read(run, card, notices=notices)
        identity = asm.identity
        self._tracer.step(
            run_id,
            "identity.cards",
            payload={
                "cards": len(identity.cards),
                "by_kind": dict(sorted(Counter(c.kind for c in identity.cards).items())),
                "pending": identity.pending,
                "people": len(identity.people),
                "stores": len(identity.stores),
                "merged": len(identity.merged),
                "issues": len(identity.issues),
                "roster_version": roster.version if roster else None,
            },
        )
        capacity = capacity_check(asm.pattern, asm.employees, asm.card)
        self._tracer.step(
            run_id,
            "demand.inferred",
            payload={
                "demand_person_hours": str(capacity.demand_person_hours),
                "capacity_person_hours": str(capacity.capacity_person_hours),
                "fits": capacity.fits,
                "max_fitting_pct": capacity.max_fitting_pct,
                "slots": len(asm.pattern),
                "stores": len(asm.stores),
                "store_hours_from_cadastro": asm.hours_from_cadastro,
                "week_start": file_week.isoformat(),
                "card_reference_date": asm.card.reference_date.isoformat(),
                "provisional": list(asm.card.provisional),
            },
        )
        assumptions = list(mapped.assumptions)
        if assumed_week:
            assumptions.append(
                f"O arquivo só traz o dia da semana: assumi a semana de {file_week:%d/%m/%Y}; confirme a semana."
            )
        assumptions += asm.assumptions + _provisional_notes(asm.card, file_week)
        issues = [*mapped.issues, *identity.issues]
        if issues:  # RX-13 com as linhas, como aviso: o gestor pode confirmar só com as linhas válidas
            names = {s.person_name.strip() for s in mapped.shifts if s.person_name.strip()}
            card = _rx13_lines(name, issues, names)
            notices.append(self._raise_card(run_id, card, step="ler_e_padronizar"))
        summary = ReadSummary(
            file_name=name,
            rows=len(identity.shifts),
            employees=len(asm.employees),
            stores=len(asm.stores),
            week_start=file_week,
            total_hours=_total_hours(asm.before),
            issues=issues,
            ok=True,
            format=_format(read.format),
            mapping=mapped.mapping,
            mapping_source=source,
            assumptions=assumptions,
            identity=identity.cards,
            capacity=capacity,
            planned_week_start=file_week,
            store_ids=[s.id for s in asm.stores],
            evidence_sample=[s.evidence for s in mapped.shifts[:MAX_EVIDENCE]],
        )
        self._tracer.step(
            run_id,
            "read.summary",
            payload={
                "ok": True,
                "rows": summary.rows,
                "employees": summary.employees,
                "stores": summary.stores,
                "week_start": file_week.isoformat(),
                "total_hours": str(summary.total_hours),
                "format": summary.format,
                "mapping_source": source,
                "issues": len(summary.issues),
                "assumptions": len(assumptions),
                "identity_cards": len(identity.cards),
                "pending": identity.pending,
                "notices": [n.code for n in notices],
            },
        )
        self._readings[run_id] = _Reading(mapped=mapped, roster=roster, file_week=file_week, assembled=asm)
        return {
            "run": run.model_copy(
                update={
                    "phase": "awaiting_confirm",
                    "summary": summary,
                    "notices": notices,
                    "mode": "upload",
                    "before": asm.before,
                    "week_start": file_week,
                }
            )
        }

    def _map(
        self, run_id: str, tables: list[RawTable], notices: list[ExceptionCard]
    ) -> tuple[MappingResult | None, str | None, bool]:
        """Mapeamento pelo modelo; reserva pela heurística de cabeçalhos, com aviso RX-12 (seção 11).

        Devolve `(resultado, fonte, semana_assumida)`. `None` quando nem a heurística entende as colunas."""
        failure: str
        notice_reason: str
        trace_id: str | None = None
        last: tuple[MappingResult, bool] | None = None
        if self._map_columns is None:
            failure = "modelo não configurado"
            notice_reason = (
                "O modelo de leitura não está configurado nesta instalação: as colunas foram entendidas pelos nomes "
                "dos cabeçalhos, sem modelo."
            )
        else:
            try:
                mapping = self._map_columns(tables, run_id, self._tracer.parent(run_id))
            except LLMUnavailableError as exc:
                self._follow_latest(run_id)
                failure = "o modelo falhou ou insistiu em mapeamento recusado"
                trace_id = exc.card.trace_id
            except Exception as exc:  # noqa: BLE001 (seção 11: o modelo nunca bloqueia a leitura)
                log.exception("falha inesperada no mapeamento pelo modelo: run_id=%s", run_id)
                self._follow_latest(run_id)
                failure = f"falha inesperada ao chamar o modelo ({type(exc).__name__})"
            else:
                self._follow_latest(run_id)  # o evento `llm.map_columns` (custo medido) é do cliente do modelo
                last = self._apply(run_id, tables, mapping, SOURCE_MODEL)
                if last[0].shifts:
                    return last[0], SOURCE_MODEL, last[1]
                failure = "o mapeamento do modelo não produziu turnos"
            notice_reason = (
                f"O modelo não conseguiu mapear as colunas ({failure}): li o arquivo pelos nomes dos cabeçalhos, "
                "sem modelo."
            )
        self._tracer.step(
            run_id, "ingest.fallback", payload={"from": SOURCE_MODEL, "to": SOURCE_HEURISTIC, "reason": failure}
        )
        notice = ExceptionCard(
            code="RX-12",
            title="Li a escala sem o modelo: confira o mapeamento",
            reason=notice_reason,
            decider=Role.GESTOR,
            recommendation="Confira no resumo como cada coluna foi entendida antes de confirmar.",
            if_no_answer=_IF_NO_CONFIRM,
            trace_id=trace_id,
        )
        notices.append(self._raise_card(run_id, notice, step="ler_e_padronizar"))
        guessed = guess_mapping(tables)
        if guessed is None:
            self._tracer.step(
                run_id,
                "ingest.fallback",
                payload={"from": SOURCE_HEURISTIC, "to": None, "reason": "nenhum cabeçalho reconhecido"},
            )
            return (last[0], SOURCE_MODEL, last[1]) if last else (None, None, False)
        result, assumed = self._apply(run_id, tables, guessed, SOURCE_HEURISTIC)
        return result, SOURCE_HEURISTIC, assumed

    def _apply(
        self, run_id: str, tables: list[RawTable], mapping: ColumnMapping, source: str
    ) -> tuple[MappingResult, bool]:
        """`apply_mapping` com o rastro. Grade só com dia da semana: assume a próxima semana (o gestor confirma)."""
        started = time.perf_counter()
        result = apply_mapping(tables, mapping)
        assumed = False
        weekday_only = bool(mapping.day_columns) and all(dc.day is None for dc in mapping.day_columns)
        if not result.shifts and result.week_start is None and mapping.layout == "grid" and weekday_only:
            assumed = True
            result = apply_mapping(tables, mapping, week_start=next_week_start(self._clock.now().date()))
        self._tracer.step(
            run_id,
            "ingest.apply_mapping",
            started=started,
            payload={
                "source": source,
                "layout": mapping.layout,
                "table": mapping.table,
                "header_row": mapping.header_row,
                "shifts": len(result.shifts),
                "issues": len(result.issues),
                "rows_read": result.rows_read,
                "invented": len(verify_evidence(tables, result)),
                "assumptions": len(result.assumptions),
                "week_start": result.week_start.isoformat() if result.week_start else None,
                "week_assumed": assumed,
            },
        )
        return result, assumed

    def _assemble(
        self,
        mapped: MappingResult,
        roster: Roster | None,
        answers: Sequence[IdentityAnswer],
        file_week: date,
        planned: date,
        wage: Decimal | None,
    ) -> _Assembled:
        """Identidade, cartão da semana planejada, pessoas (cadastro), lojas, padrão de demanda e o "antes"."""
        assert self._enrich is not None and self._load_card is not None
        identity = resolve_identities(mapped.shifts, roster=roster, answers=answers)
        card = self._load_card(planned)
        enriched = self._enrich(
            identity.people,
            identity.stores,
            cadastro=self._cadastro,
            default_wage=wage,
            default_contract_hours=_weekly_hours(card),
        )
        inferred = {s.id: s for s in infer_store_hours(identity.shifts, identity.stores)}
        stores: list[Store] = []
        for draft in identity.stores:
            hours = enriched.store_hours.get(draft.id)
            if hours is not None:  # horário do cadastro simulado
                stores.append(Store(id=draft.id, name=draft.name, opens=hours[0], closes=hours[1]))
            elif draft.id in inferred:  # horário inferido dos turnos do arquivo
                stores.append(inferred[draft.id])
        file_schedule = Schedule(week_start=file_week, shifts=identity.shifts)
        weeks = (planned - file_week).days // 7
        return _Assembled(
            identity=identity,
            card=card,
            employees=list(enriched.employees),
            stores=stores,
            hours_from_cadastro=sum(1 for s in stores if s.id in enriched.store_hours),
            assumptions=list(enriched.assumptions),
            pattern=infer_demand_pattern(file_schedule, stores),
            before=shift_schedule(file_schedule, weeks) if weeks else file_schedule,
            week_start=planned,
        )

    def _fail_read(
        self,
        run: RunState,
        card: ExceptionCard,
        *,
        summary: ReadSummary | None = None,
        notices: Sequence[ExceptionCard] = (),
    ) -> dict[str, Any]:
        card = self._raise_card(run.run_id, card, step="ler_e_padronizar")
        update = {"phase": "failed", "exception": card, "summary": summary, "notices": list(notices)}
        return {"run": run.model_copy(update=update)}

    # --- leitura (C5) ------------------------------------------------------------------------------------------------

    def _ler_escala(self, state: FlowState) -> dict[str, Any]:
        run = state["run"]
        assert self._read_csv is not None and self._week_start is not None
        started = time.perf_counter()
        result = self._read_csv(state["file_name"], state["content"])
        summary, schedule, card = result.summary, result.schedule, result.exception
        if card is None and (not summary.ok or schedule is None):
            card = _rx13(state["file_name"], "a leitura não produziu uma escala", [])
        if card is None and schedule is not None and schedule.week_start != self._week_start:
            card = _rx13(
                state["file_name"],
                f"o arquivo é da semana de {schedule.week_start:%d/%m/%Y}, "
                f"e a semana planejada começa em {self._week_start:%d/%m/%Y}",
                [],
            )
        ok = card is None
        self._tracer.step(
            run.run_id,
            "csv.validate",
            started=started,
            payload={"ok": ok, "rows": summary.rows, "issues": len(summary.issues),
                     "issue_lines": [i.line for i in summary.issues][:50]},
        )  # fmt: skip
        self._tracer.step(
            run.run_id,
            "read.summary",
            payload={
                "ok": ok,
                "rows": summary.rows,
                "employees": summary.employees,
                "stores": summary.stores,
                "week_start": summary.week_start.isoformat() if summary.week_start else None,
                "total_hours": str(summary.total_hours),
            },
        )
        if card is not None:
            card = self._raise_card(run.run_id, card, step="ler_escala")
            return {"run": run.model_copy(update={"phase": "failed", "summary": summary, "exception": card})}
        assert schedule is not None
        self._inputs[run.run_id] = schedule
        return {"run": run.model_copy(update={"phase": "awaiting_confirm", "summary": summary})}

    # --- otimização --------------------------------------------------------------------------------------------------

    def _otimizar(self, state: FlowState) -> dict[str, Any]:
        run = state["run"]
        hint = state.get("hint")
        started = time.perf_counter()
        result = solve(
            SolveRequest(
                card=state["card"],
                stores=state["stores"],
                employees=state["employees"],
                demand=state["demand"],
                week_start=state["week_start"],
                seed=self._seed,
                time_limit_s=self._time_limit_s,
                num_workers=self._num_workers,
                hint=hint,
                spec=state.get("spec"),
            )
        )
        self._tracer.step(
            run.run_id,
            "solver.run",
            started=started,
            payload={
                "status": result.status,
                "seed": result.seed,
                "input_hash": result.input_hash,
                "wall_ms": result.wall_ms,
                "time_limit_s": self._time_limit_s,
                "num_workers": self._num_workers,
                "week_start": state["week_start"].isoformat(),
                "attempt": 1,
                "hint_shifts": len(hint.shifts) if hint is not None else 0,
                "shifts": len(result.schedule.shifts) if result.schedule else 0,
                "uncovered_slots": len(result.uncovered),
                "missing_person_slots": sum(s.required for s in result.uncovered),  # `required` é o que faltou
            },
        )
        if result.schedule is None:
            card = result.exception or ExceptionCard(
                code="RX-12",
                title="O solver não encontrou uma escala",
                reason=f"O solver terminou com status {result.status} sem escala em {self._time_limit_s:g} s.",
                decider=Role.GESTOR,
                recommendation="Conferir a demanda e o quadro de pessoal; tentar de novo com mais tempo de solver.",
                if_no_answer="A escala atual continua valendo; nenhuma versão nova é publicada.",
            )
            card = self._raise_card(run.run_id, card, step="otimizar")
            update = {"phase": "failed", "exception": card, "attempts": 1}
            return {"run": run.model_copy(update=update), "solved": result}
        update: dict[str, Any] = {"phase": "optimized", "attempts": 1}
        if result.exception is not None:  # RX-02: faixas descobertas; aviso, e o fluxo segue com a escala parcial
            update["notices"] = [*run.notices, self._raise_card(run.run_id, result.exception, step="otimizar")]
        return {"run": run.model_copy(update=update), "solved": result}

    def _verificar(self, state: FlowState) -> dict[str, Any]:
        run, solved, card = state["run"], state["solved"], state["card"]
        assert solved.schedule is not None
        after = self._checked(run.run_id, solved.schedule, "otimizada", card)
        before = self._checked(run.run_id, state["before"], "enviada", card)
        version = ScheduleVersion(
            id=f"ver-{self._new_id()}",
            run_id=run.run_id,
            schedule=solved.schedule,
            status="draft",
            input_hash=solved.input_hash,
            seed=solved.seed,
            violations_total=after.total,
            created_at=self._clock.now(),
        )
        self._repo.save_version(version)
        update: dict[str, Any] = {"report": after, "version_id": version.id}
        if after.total > 0:  # o verificador independente discorda do solver: `publicar` vai recusar
            exc_card = ExceptionCard(
                code="RX-12",
                title="O verificador achou violações na escala otimizada",
                reason=f"{after.total} violações na escala proposta; ela não pode ser publicada.",
                decider=Role.GESTOR,
                evidence=[f"{rule}: {n}" for rule, n in sorted(Counter(v.rule_id for v in after.violations).items())],
                recommendation="Não publicar; abrir o rastro e tentar de novo.",
                if_no_answer="A escala atual continua valendo; nenhuma versão nova é publicada.",
            )
            update["exception"] = self._raise_card(run.run_id, exc_card, step="verificar")
        return {"run": run.model_copy(update=update), "after_report": after, "before_report": before}

    def _comparar(self, state: FlowState) -> dict[str, Any]:
        run, solved, card = state["run"], state["solved"], state["card"]
        assert solved.schedule is not None
        started = time.perf_counter()
        comparison = compare_schedules(
            state["before"],
            solved.schedule,
            state["employees"],
            state["demand"],
            card,
            before_violations=state["before_report"].total,
            after_violations=state["after_report"].total,
        )
        self._tracer.step(
            run.run_id,
            "cost.compare",
            started=started,
            payload={**comparison.model_dump(mode="json"), "rules": _rules_of(card, COST_RULE_KINDS)},
        )
        return {"run": run.model_copy(update={"comparison": comparison})}

    def _justificar(self, state: FlowState) -> dict[str, Any]:
        run, solved = state["run"], state["solved"]
        assert run.comparison is not None
        try:
            justification = self._justify(
                card=state["card"],
                comparison=run.comparison,
                report=state["after_report"],
                status=solved.status,
                uncovered=list(solved.uncovered),
                run_id=run.run_id,
                parent_id=self._tracer.parent(run.run_id),
            )
        except LLMUnavailableError as exc:  # RX-12 (aviso): sem texto inventado; a escala é válida e pode ser aprovada
            card = self._raise_card(run.run_id, exc.card, step="justificar")
            update = {"phase": "awaiting_approval", "justification": None, "notices": [*run.notices, card]}
            return {"run": run.model_copy(update=update)}
        llm_events = [e for e in self._list_events(run.run_id) if e.kind == LLM_JUSTIFY_KIND]
        if llm_events:  # o evento com o custo medido é do cliente do modelo; o próximo passo se pendura nele
            self._tracer.follow(run.run_id, llm_events[-1].id)
        return {"run": run.model_copy(update={"phase": "awaiting_approval", "justification": justification})}

    # --- apoio -----------------------------------------------------------------------------------------------------

    def _checked(self, run_id: str, schedule: Schedule, target: str, card: RuleCard) -> ViolationReport:
        started = time.perf_counter()
        report = verify(schedule, card)
        self._tracer.step(
            run_id,
            "verifier.check",
            started=started,
            payload={
                "target": target,
                "total": report.total,
                "by_rule": dict(sorted(Counter(v.rule_id for v in report.violations).items())),
                "rules": _rules_of(card, CHECKS.keys()),
            },
        )
        return report

    def _follow_latest(self, run_id: str) -> None:
        """Encadeia o próximo passo no último evento gravado da execução (por exemplo o `llm.map_columns` do cliente
        do modelo, ou o `exception.raised` que ele emitiu ao falhar)."""
        events = self._list_events(run_id)
        if events:
            self._tracer.follow(run_id, events[-1].id)

    def _raise_card(self, run_id: str, card: ExceptionCard, *, step: str) -> ExceptionCard:
        """Registra `exception.raised` e devolve o cartão apontando para o evento. Se a borda que levantou já
        registrou o evento (o cliente do modelo faz isso), só encadeia nele, sem duplicar."""
        if card.trace_id and any(e.id == card.trace_id and e.kind == EXCEPTION_KIND for e in self._list_events(run_id)):
            self._tracer.follow(run_id, card.trace_id)
            return card
        event = self._tracer.step(
            run_id,
            EXCEPTION_KIND,
            payload={"code": card.code, "title": card.title, "step": step, "evidence": len(card.evidence)},
        )
        return card.model_copy(update={"trace_id": event.id})

    def _require(self, run_id: str, phase: str) -> RunState:
        state = self._repo.get_run(run_id)
        if state is None:
            raise RunNotFoundError(run_id)
        if state.phase != phase:
            raise RunPhaseError(f"execução em {state.phase}; a operação exige {phase}")
        return state

    def _lock(self, run_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(run_id, threading.Lock())


def _rules_of(card: RuleCard, kinds: Iterable[str]) -> list[dict[str, str]]:
    wanted = set(kinds)
    return [{"id": r.id, "status": r.status.value} for r in card.rules if r.kind in wanted]


def _weekly_hours(card: RuleCard) -> int:
    """Limite semanal do cartão da semana: a carga contratual padrão de quem não está no cadastro."""
    for rule in card.rules:
        if rule.kind == "jornada_semanal_max" and "hours" in rule.params:
            return int(float(rule.params["hours"]))
    raise ValueError("o cartão não tem jornada_semanal_max (hours)")


def _provisional_notes(card: RuleCard, week: date) -> list[str]:
    if not card.provisional:
        return []
    return [
        f"Uma regra muda no meio da semana de {week:%d/%m/%Y}: vale a mais restritiva na semana inteira, como "
        f"provisória ({', '.join(card.provisional)})."
    ]


def _total_hours(schedule: Schedule) -> Decimal:
    minutes = sum(int((s.end - s.start).total_seconds() // 60) for s in schedule.shifts)
    return (Decimal(minutes) / 60).quantize(_HOURS)


def _format(fmt: str | None) -> Any:
    return fmt if fmt in _FORMATS else "csv"


def _issue_text(issue: CsvIssue) -> str:
    where = f"linha {issue.line}"
    if issue.col is not None:
        where += f", coluna {issue.col + 1}"
    if issue.table:
        where += f" ({issue.table})"
    return f"{where}: {issue.reason}"


# Motivos que citam a pessoa (rules/identity.py e rules/mapping.py): o cartão diz a linha, sem nome nem id derivado.
_NAMED_OVERLAP = re.compile(r" de '[^']*' \([^)]*\)")
_TOO_MANY = re.compile(r"^(mais de \d+ turnos) de .+ (em \d{2}/\d{2}/\d{4})$")


def _line_text(issue: CsvIssue, names: Iterable[str]) -> str:
    """Formata `linha N[, campo]: motivo`, sem nome de pessoa."""
    reason = _TOO_MANY.sub(r"\1 da mesma pessoa \2", _NAMED_OVERLAP.sub("", issue.reason))
    for person in sorted(names, key=len, reverse=True):  # defesa: nenhum nome lido do arquivo vai ao cartão
        reason = reason.replace(person, "a pessoa")
    where = f"linha {issue.line}" + (f", {issue.field}" if issue.field else "")
    return f"{where}: {reason}"


def _rx13_lines(file_name: str, issues: Sequence[CsvIssue], names: Iterable[str]) -> ExceptionCard:
    """RX-13 da leitura parcial (dado inconsistente vira exceção com o motivo): vai em `notices`, não bloqueia."""
    lines = {i.line for i in issues}
    shown = sorted(issues, key=lambda i: (i.line, i.col if i.col is not None else -1))[:MAX_LINE_EVIDENCE]
    more = f" (as primeiras {MAX_LINE_EVIDENCE} na evidência)" if len(issues) > MAX_LINE_EVIDENCE else ""
    return ExceptionCard(
        code="RX-13",
        title="A escala tem linhas com problema",
        reason=(
            f"{file_name}: {len(issues)} problema(s) em {len(lines)} linha(s) do arquivo{more}. "
            "Os turnos válidos estão no resumo."
        ),
        decider=Role.GESTOR,
        evidence=[_line_text(i, names) for i in shown],
        recommendation="Corrija as linhas indicadas e envie de novo, ou confirme para seguir só com as linhas válidas.",
        if_no_answer=(
            "Nada é otimizado sem a confirmação do gestor; a escala atual continua valendo e nenhuma versão nova é "
            "publicada."
        ),
    )


def _rx13(file_name: str, reason: str, evidence: list[str]) -> ExceptionCard:
    return ExceptionCard(
        code="RX-13",
        title="A escala não pode ser usada",
        reason=f"{file_name}: {reason}.",
        decider=Role.GESTOR,
        evidence=evidence,
        recommendation="Corrija o arquivo e envie de novo.",
        if_no_answer="A otimização não começa sem uma escala lida e confirmada pelo gestor.",
    )
