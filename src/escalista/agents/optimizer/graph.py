"""Agente de otimização da fatia (plano da C5, I1): grafo LangGraph mínimo, sem checkpointer.

Desenho: **um grafo por trecho entre paradas humanas**, invocado pela classe `OptimizerAgent`:

- `start_run` → grafo de leitura: `ler_escala` (CSV → validação → resumo; RX-13 se o arquivo tem defeito).
- `confirm` (o gerente confirmou o resumo) → grafo de otimização: `otimizar → verificar → comparar → justificar`, com
  saída antecipada se o solver não devolver escala (RX-12).
- `approve` grava a aprovação humana e chama a ferramenta `publicar` (`tools.py`), que relê a aprovação no
  `Repository` e recusa sem ela.

O estado durável é o `RunState`, salvo pelo `Repository` depois de cada nó; o estado do grafo (`FlowState`) só vive
durante uma invocação (arquitetura, seção 4: sem checkpointer). A escala enviada fica em memória entre `start_run` e
`confirm`, porque a porta `Repository` não tem onde guardá-la: se o processo reiniciar nesse intervalo, `confirm` pede o
arquivo de novo (`RunPhaseError`).

Fronteira: só núcleo (`domain`, `rules`, `solver`, `verifier`), portas e `langgraph`. As bordas entram injetadas.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import date
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from escalista.agents.optimizer.errors import RunNotFoundError, RunPhaseError
from escalista.agents.optimizer.tools import PUBLISHER_ROLES, Justifier, ListEvents, ReadCsv, Tracer, publicar
from escalista.domain.contracts import ExceptionCard, LLMUnavailableError, Role, TraceEvent
from escalista.domain.ports import Clock, Repository, TraceSink
from escalista.domain.results import (
    Approval,
    RunState,
    ScheduleVersion,
    SolveRequest,
    SolveResult,
    ViolationReport,
)
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, EmployeePublic, Schedule, Store
from escalista.solver.cost import compare_schedules
from escalista.solver.model import solve
from escalista.verifier import CHECKS, verify

log = logging.getLogger(__name__)

EXCEPTION_KIND = "exception.raised"
LLM_JUSTIFY_KIND = "llm.justify"
# Regras que a função de custo lê do cartão (solver/cost.py): jornadas para a hora extra e o adicional.
COST_RULE_KINDS = frozenset({"jornada_diaria_max", "jornada_semanal_max", "adicional_hora_extra"})


class FlowState(TypedDict, total=False):
    """Estado de uma invocação do grafo. Só `run` é durável (salvo a cada nó)."""

    run: RunState
    file_name: str
    content: bytes
    before: Schedule
    solved: SolveResult
    after_report: ViolationReport
    before_report: ViolationReport


Node = Callable[[FlowState], dict[str, Any]]


class OptimizerAgent:
    """Implementa o `SliceAgent` da API (mesmos métodos e assinaturas; erros em `agents/optimizer/errors.py`)."""

    def __init__(
        self,
        *,
        repo: Repository,
        sink: TraceSink,
        clock: Clock,
        read_csv: ReadCsv,
        justify: Justifier,
        list_events: ListEvents,
        card: RuleCard,
        stores: list[Store],
        employees: list[Employee],
        demand: list[DemandSlot],
        week_start: date,
        seed: int = 42,
        time_limit_s: float = 30.0,
        num_workers: int = 1,
        publisher_roles: Iterable[Role] = PUBLISHER_ROLES,
        new_id: Callable[[], str] = lambda: uuid4().hex,
    ) -> None:
        self._repo = repo
        self._clock = clock
        self._read_csv = read_csv
        self._justify = justify
        self._list_events = list_events
        self._card = card
        self._stores = list(stores)
        self._employees = sorted(employees, key=lambda e: e.id)
        self._demand = list(demand)
        self._week_start = week_start
        self._seed = seed
        self._time_limit_s = time_limit_s
        self._num_workers = num_workers
        self._publisher_roles = frozenset(publisher_roles)
        self._new_id = new_id
        self._tracer = Tracer(sink, clock, new_id=new_id, list_events=list_events)
        self._inputs: dict[str, Schedule] = {}  # escala enviada, entre `start_run` e `confirm`
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._read_graph = self._build_read_graph()
        self._optimize_graph = self._build_optimize_graph()

    # --- SliceAgent ----------------------------------------------------------------------------------------------

    def start_run(self, file_name: str, content: bytes) -> RunState:
        state = RunState(run_id=f"run-{self._new_id()}", phase="read")
        self._repo.save_run(state)
        with self._lock(state.run_id):
            return self._invoke(self._read_graph, {"run": state, "file_name": file_name, "content": content})

    def confirm(self, run_id: str) -> RunState:
        with self._lock(run_id):
            state = self._require(run_id, "awaiting_confirm")
            before = self._inputs.get(run_id)
            if before is None:
                raise RunPhaseError("a escala enviada não está mais em memória; envie o arquivo de novo")
            self._tracer.human(run_id, "read.confirmed", payload={"rows": state.summary.rows if state.summary else 0})
            out = self._invoke(self._optimize_graph, {"run": state, "before": before})
            self._inputs.pop(run_id, None)
            return out

    def get_run(self, run_id: str) -> RunState | None:
        return self._repo.get_run(run_id)

    def get_schedule(self, run_id: str) -> Schedule | None:
        state = self._repo.get_run(run_id)
        if state is None or state.version_id is None:
            return None
        version = self._repo.get_version(state.version_id)
        return version.schedule if version else None

    def employees(self, run_id: str) -> list[EmployeePublic]:
        if self._repo.get_run(run_id) is None:
            return []
        return [EmployeePublic.from_employee(e) for e in self._employees]

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

    # --- grafos ----------------------------------------------------------------------------------------------------

    def _build_read_graph(self):  # noqa: ANN202 (grafo compilado do LangGraph)
        g = StateGraph(FlowState)
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
                decider=Role.GERENTE,
                recommendation="Tentar de novo com o mesmo arquivo; se persistir, abrir o rastro desta execução.",
                if_no_answer="A escala atual continua valendo; nenhuma versão nova é publicada.",
            )
            state = (self._repo.get_run(run_id) or inputs["run"]).model_copy(
                update={"phase": "failed", "exception": self._raise_card(run_id, card, step="inesperado")}
            )
            self._repo.save_run(state)
            return state

    # --- nós -------------------------------------------------------------------------------------------------------

    def _ler_escala(self, state: FlowState) -> dict[str, Any]:
        run = state["run"]
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

    def _otimizar(self, state: FlowState) -> dict[str, Any]:
        run = state["run"]
        started = time.perf_counter()
        result = solve(
            SolveRequest(
                card=self._card,
                stores=self._stores,
                employees=self._employees,
                demand=self._demand,
                week_start=self._week_start,
                seed=self._seed,
                time_limit_s=self._time_limit_s,
                num_workers=self._num_workers,
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
                decider=Role.GERENTE,
                recommendation="Conferir a demanda e o quadro de pessoal; tentar de novo com mais tempo de solver.",
                if_no_answer="A escala atual continua valendo; nenhuma versão nova é publicada.",
            )
            card = self._raise_card(run.run_id, card, step="otimizar")
            return {"run": run.model_copy(update={"phase": "failed", "exception": card}), "solved": result}
        update: dict[str, Any] = {"phase": "optimized"}
        if result.exception is not None:  # RX-02: faixas descobertas; o fluxo segue com a escala parcial
            update["exception"] = self._raise_card(run.run_id, result.exception, step="otimizar")
        return {"run": run.model_copy(update=update), "solved": result}

    def _verificar(self, state: FlowState) -> dict[str, Any]:
        run, solved = state["run"], state["solved"]
        assert solved.schedule is not None
        after = self._checked(run.run_id, solved.schedule, "otimizada")
        before = self._checked(run.run_id, state["before"], "enviada")
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
            card = ExceptionCard(
                code="RX-12",
                title="O verificador achou violações na escala otimizada",
                reason=f"{after.total} violações na escala proposta; ela não pode ser publicada.",
                decider=Role.GERENTE,
                evidence=[f"{rule}: {n}" for rule, n in sorted(Counter(v.rule_id for v in after.violations).items())],
                recommendation="Não publicar; abrir o rastro e tentar de novo.",
                if_no_answer="A escala atual continua valendo; nenhuma versão nova é publicada.",
            )
            update["exception"] = self._raise_card(run.run_id, card, step="verificar")
        return {"run": run.model_copy(update=update), "after_report": after, "before_report": before}

    def _comparar(self, state: FlowState) -> dict[str, Any]:
        run, solved = state["run"], state["solved"]
        assert solved.schedule is not None
        started = time.perf_counter()
        comparison = compare_schedules(
            state["before"],
            solved.schedule,
            self._employees,
            self._demand,
            self._card,
            before_violations=state["before_report"].total,
            after_violations=state["after_report"].total,
        )
        self._tracer.step(
            run.run_id,
            "cost.compare",
            started=started,
            payload={**comparison.model_dump(mode="json"), "rules": self._rules_of(COST_RULE_KINDS)},
        )
        return {"run": run.model_copy(update={"comparison": comparison})}

    def _justificar(self, state: FlowState) -> dict[str, Any]:
        run, solved = state["run"], state["solved"]
        assert run.comparison is not None
        try:
            justification = self._justify(
                card=self._card,
                comparison=run.comparison,
                report=state["after_report"],
                status=solved.status,
                uncovered=list(solved.uncovered),
                run_id=run.run_id,
                parent_id=self._tracer.parent(run.run_id),
            )
        except LLMUnavailableError as exc:  # RX-12: sem texto inventado; a escala é válida e pode ser aprovada
            card = self._raise_card(run.run_id, exc.card, step="justificar")
            return {"run": run.model_copy(update={"phase": "awaiting_approval", "justification": None,
                                                  "exception": card})}  # fmt: skip
        llm_events = [e for e in self._list_events(run.run_id) if e.kind == LLM_JUSTIFY_KIND]
        if llm_events:  # o evento com o custo medido é do cliente do modelo; o próximo passo se pendura nele
            self._tracer.follow(run.run_id, llm_events[-1].id)
        return {"run": run.model_copy(update={"phase": "awaiting_approval", "justification": justification})}

    # --- apoio -----------------------------------------------------------------------------------------------------

    def _checked(self, run_id: str, schedule: Schedule, target: str) -> ViolationReport:
        started = time.perf_counter()
        report = verify(schedule, self._card)
        self._tracer.step(
            run_id,
            "verifier.check",
            started=started,
            payload={
                "target": target,
                "total": report.total,
                "by_rule": dict(sorted(Counter(v.rule_id for v in report.violations).items())),
                "rules": self._rules_of(CHECKS.keys()),
            },
        )
        return report

    def _rules_of(self, kinds: Iterable[str]) -> list[dict[str, str]]:
        wanted = set(kinds)
        return [{"id": r.id, "status": r.status.value} for r in self._card.rules if r.kind in wanted]

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


def _rx13(file_name: str, reason: str, evidence: list[str]) -> ExceptionCard:
    return ExceptionCard(
        code="RX-13",
        title="A escala não pode ser usada",
        reason=f"{file_name}: {reason}.",
        decider=Role.GERENTE,
        evidence=evidence,
        recommendation="Corrija o arquivo e envie de novo.",
        if_no_answer="A otimização não começa sem uma escala lida e confirmada pelo gerente.",
    )
