"""Agente falso da fatia: `RunState` fixos e plausíveis, para a API e a SPA andarem antes do agente real (C4).

Tudo aqui é sintético e rotulado assim. Os números não vêm de solver, verificador nem modelo: são fixos. As pessoas
existem como `Employee` (com `sex`, como no agente real) e só saem como `EmployeePublic`, para o teste de RN-13 valer.

`refuse_publish=True` simula a recusa de `publicar` (aprovação não encontrada no código da ferramenta).

C6: `confirm` aceita o `ConfirmInput` (guardado em `confirm_inputs`, para os testes de rota) e, na 1ª escala, grava um
`Roster` fixo; `start_next_week` parte da última publicada e do último quadro; `roster` devolve o último. O falso imita
o leitor: XLSX e PDF (pelos bytes iniciais) dão um resumo fixo, e um CSV que não decodifica em UTF-8 vira RX-13.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from escalista.api.wiring import PublishRefusedError, RunNotFoundError, RunPhaseError, now_brt
from escalista.domain.contracts import ExceptionCard, Role, TraceEvent
from escalista.domain.reading import ConfirmInput, DemandPattern
from escalista.domain.results import (
    Approval,
    Comparison,
    Justification,
    JustificationItem,
    RunState,
    ScheduleMetrics,
    ScheduleVersion,
    ViolationReport,
)
from escalista.domain.roster import Roster
from escalista.domain.schedule import CsvIssue, Employee, EmployeePublic, ReadSummary, Schedule, Shift, Store

WEEK_START = date(2027, 1, 11)  # segunda; semana planejada da demo, já sob a EC 141
SEED = 42
SEEDED_AWAITING_CONFIRM = "run-semeada-lida"
SEEDED_AWAITING_APPROVAL = "run-semeada-pronta"
SEEDED_PUBLISHED = "run-semeada-publicada"
NO_MODEL = {"cost_basis": "sem chamada de modelo", "fonte": "agente falso"}
SEED_CSV = b"# SINTETICO - dados ficticios\nfuncionario,loja,dia,inicio,fim\nE01,L01,2027-01-11,08:00,16:00\n"
FAKE_CONFIRMER = "demo-gestor"  # a assinatura de `confirm` não traz a conta; o falso usa a do gestor de demo
NO_FIRST_SCHEDULE = "envie a primeira escala: ainda não há escala publicada e quadro confirmado"

STORES: tuple[Store, ...] = (Store(id="L01", name="Loja Fictícia Centro", opens=time(8), closes=time(22)),)

EMPLOYEES: tuple[Employee, ...] = (
    Employee(id="E01", name="Ana Fictícia", store_id="L01", job="atendente", hourly_wage=Decimal("15.00"),
             contract_hours=42, sex="F"),
    Employee(id="E02", name="Bruno Fictício", store_id="L01", job="atendente", hourly_wage=Decimal("15.00"),
             contract_hours=42, sex="M"),
    Employee(id="E03", name="Carla Fictícia", store_id="L01", job="caixa", hourly_wage=Decimal("15.00"),
             contract_hours=42, sex="F"),
    Employee(id="E04", name="Davi Fictício", store_id="L01", job="caixa", hourly_wage=Decimal("15.00"),
             contract_hours=42, sex="M"),
)  # fmt: skip


DEMAND: tuple[DemandPattern, ...] = tuple(
    DemandPattern(store_id="L01", weekday=d, start=time(h, m), required=2)
    for d in range(7)
    for h in range(8, 22)
    for m in (0, 30)
)


def _proposed_schedule(week_start: date = WEEK_START) -> Schedule:
    """5 turnos de 8h por pessoa (40h, 2 repousos): manhã de segunda a sexta ou tarde de quarta a domingo."""
    shifts: list[Shift] = []
    for i, e in enumerate(EMPLOYEES):
        first_day, start = (0, time(8)) if i % 2 == 0 else (2, time(14))
        for d in range(first_day, first_day + 5):
            begin = datetime.combine(week_start + timedelta(days=d), start)
            shifts.append(Shift(employee_id=e.id, store_id=e.store_id, start=begin, end=begin + timedelta(hours=8)))
    return Schedule(week_start=week_start, shifts=shifts)


def _shifted(schedule: Schedule, days: int) -> Schedule:
    delta = timedelta(days=days)
    shifts = [s.model_copy(update={"start": s.start + delta, "end": s.end + delta}) for s in schedule.shifts]
    return Schedule(week_start=schedule.week_start + delta, shifts=shifts)


COMPARISON = Comparison(
    before=ScheduleMetrics(total_cost=Decimal("2700.00"), regular_hours=Decimal("168"), overtime_hours=Decimal("8"),
                           overtime_cost=Decimal("180.00"), coverage_pct=96.0, uncovered_slots=4, violations=6),
    after=ScheduleMetrics(total_cost=Decimal("2400.00"), regular_hours=Decimal("160"), overtime_hours=Decimal("0"),
                          overtime_cost=Decimal("0.00"), coverage_pct=98.5, uncovered_slots=1, violations=0),
    savings=Decimal("300.00"),
    overtime_hours_avoided=Decimal("8"),
    violations_avoided=6,
)  # fmt: skip

JUSTIFICATION = Justification(
    summary="[agente falso] A escala proposta segue o limite de 42h e os 2 repousos semanais, sem hora extra.",
    items=[
        JustificationItem(text="Cada pessoa trabalha 40h na semana, abaixo do limite de 42h.",
                          rule_refs=["jornada_semanal_max"]),
        JustificationItem(text="Cada pessoa tem 2 dias de repouso na semana.", rule_refs=["repouso_semanal"]),
        JustificationItem(text="Nenhum turno passa de 8h, então não há hora extra a pagar.",
                          rule_refs=["jornada_diaria_max", "adicional_hora_extra"]),
    ],
)  # fmt: skip


def _rx13(file_name: str, reason: str, evidence: list[str]) -> ExceptionCard:
    return ExceptionCard(
        code="RX-13",
        title="Arquivo de escala com defeito",
        reason=reason,
        decider=Role.GESTOR,
        evidence=evidence,
        recommendation=f"Corrigir {file_name} e enviar de novo.",
    )


class FakeSliceAgent:
    """Implementa `SliceAgentC6` em memória, com respostas fixas."""

    def __init__(self, *, refuse_publish: bool = False, clock: Callable[[], datetime] = now_brt) -> None:
        self.refuse_publish = refuse_publish
        self._now = clock
        self._lock = threading.Lock()
        self._runs: dict[str, RunState] = {}
        self._versions: dict[str, ScheduleVersion] = {}
        self._approvals: dict[str, Approval] = {}
        self._trace: dict[str, list[TraceEvent]] = {}
        self._input_hashes: dict[str, str] = {}
        self._published: ScheduleVersion | None = None
        self._rosters: list[Roster] = []
        self.confirm_inputs: dict[str, ConfirmInput | None] = {}
        self._counter = 0

    @classmethod
    def with_seeded_runs(cls, **kwargs) -> FakeSliceAgent:
        """Agente com três execuções prontas (lida, aguardando aprovação e publicada, com o quadro já gravado), para
        testes que chamam a rota direto."""
        agent = cls(**kwargs)
        agent._create(SEEDED_PUBLISHED, "escala_atual.csv", SEED_CSV)
        published = agent.confirm(SEEDED_PUBLISHED)
        assert published.version_id is not None
        approval = Approval(id="apr-semeada", version_id=published.version_id, approved_by=FAKE_CONFIRMER,
                            role=Role.GESTOR, at=agent._now())  # fmt: skip
        agent.approve(SEEDED_PUBLISHED, approval)
        agent._create(SEEDED_AWAITING_CONFIRM, "escala_atual.csv", SEED_CSV)
        agent._create(SEEDED_AWAITING_APPROVAL, "escala_atual.csv", SEED_CSV)
        agent.confirm(SEEDED_AWAITING_APPROVAL)
        return agent

    # --- SliceAgentC6 ---

    def start_run(self, file_name: str, content: bytes) -> RunState:
        return self._create(self._next_id(), file_name, content)

    def confirm(self, run_id: str, data: ConfirmInput | None = None) -> RunState:
        with self._lock:
            state = self._require(run_id, "awaiting_confirm")
            self.confirm_inputs[run_id] = data
            changes = data or ConfirmInput()
            self._emit(
                run_id, "read.confirmed",
                payload={**NO_MODEL, "humano": True, "coverage_pct": changes.coverage_pct,
                         "identity_answers": len(changes.identity), "note": bool(changes.note)},
            )  # fmt: skip
            roster_version = state.roster_version
            if state.mode == "upload":
                roster = Roster(
                    version=len(self._rosters) + 1,
                    stores=list(STORES),
                    employees=list(EMPLOYEES),
                    demand=list(DEMAND),
                    source_run_id=run_id,
                    confirmed_by=FAKE_CONFIRMER,
                    confirmed_at=self._now(),
                )
                self._rosters.append(roster)
                roster_version = roster.version
                self._emit(run_id, "roster.saved", payload={**NO_MODEL, "version": roster.version})
            self._emit(run_id, "solver.run", latency_ms=850, payload={**NO_MODEL, "status": "optimal", "seed": SEED})
            self._emit(run_id, "verifier.check", latency_ms=12, payload={**NO_MODEL, "violations": 0})
            self._emit(run_id, "cost.compare", latency_ms=3, payload=dict(NO_MODEL))
            self._emit(
                run_id, "llm.justify", model="falso-pequeno", key_index=1, tokens_in=1200, tokens_out=180,
                cost_usd=Decimal("0.000412"), latency_ms=1400, payload={"cost_basis": "custo falso (agente falso)"},
            )  # fmt: skip
            version = ScheduleVersion(
                id=f"ver-{run_id}",
                run_id=run_id,
                schedule=_proposed_schedule(state.week_start or WEEK_START),
                status="draft",
                input_hash=self._input_hashes[run_id],
                seed=SEED,
                violations_total=0,
                created_at=self._now(),
            )
            self._versions[run_id] = version
            state = state.model_copy(
                update={
                    "phase": "awaiting_approval",
                    "comparison": COMPARISON,
                    "report": ViolationReport(violations=[]),
                    "justification": JUSTIFICATION,
                    "version_id": version.id,
                    "roster_version": roster_version,
                },
                deep=True,
            )
            self._runs[run_id] = state
            return state

    def start_next_week(self) -> RunState:
        with self._lock:
            published, roster = self._published, (self._rosters[-1] if self._rosters else None)
            if published is None or roster is None:
                raise RunPhaseError(NO_FIRST_SCHEDULE)
        run_id = self._next_id()
        before = _shifted(published.schedule, 7)
        hours = sum(((s.end - s.start).total_seconds() / 3600 for s in before.shifts), 0.0)
        summary = ReadSummary(
            file_name="(continuidade)",
            rows=len(before.shifts),
            employees=len(roster.employees),
            stores=len(roster.stores),
            week_start=before.week_start,
            total_hours=Decimal(str(hours)),
            issues=[],
            ok=True,
            format="continuidade",
            mapping_source="plataforma",
            planned_week_start=before.week_start,
        )
        with self._lock:
            self._trace[run_id] = []
            self._emit(run_id, "run.next_week", payload={**NO_MODEL, "from_version": published.id})
            self._input_hashes[run_id] = hashlib.sha256(before.model_dump_json().encode()).hexdigest()
            state = RunState(
                run_id=run_id,
                phase="awaiting_confirm",
                summary=summary,
                mode="continuidade",
                before=before,
                week_start=before.week_start,
                roster_version=roster.version,
            )
            self._runs[run_id] = state
            return state

    def roster(self) -> Roster | None:
        return self._rosters[-1] if self._rosters else None

    def get_run(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    def get_schedule(self, run_id: str) -> Schedule | None:
        version = self._versions.get(run_id)
        return version.schedule if version else None

    def employees(self, run_id: str) -> list[EmployeePublic]:
        if run_id not in self._runs:
            return []
        return [EmployeePublic.from_employee(e) for e in EMPLOYEES]

    def approve(self, run_id: str, approval: Approval) -> RunState:
        with self._lock:
            state = self._require(run_id, "awaiting_approval")
            version = self._versions[run_id]
            self._approvals[version.id] = approval
            self._emit(run_id, "approval.recorded", payload={**NO_MODEL, "humano": True, "role": approval.role.value})
            reason = self._refusal(version, approval)
            if reason:
                self._emit(run_id, "schedule.publish_refused", payload={**NO_MODEL, "reason": reason})
                raise PublishRefusedError(reason)
            published = version.model_copy(update={"status": "published"})
            self._versions[run_id] = published
            self._published = published
            self._emit(run_id, "schedule.publish", payload={**NO_MODEL, "version_id": version.id})
            state = state.model_copy(update={"phase": "published"})
            self._runs[run_id] = state
            return state

    def published(self) -> ScheduleVersion | None:
        return self._published

    def trace(self, run_id: str) -> list[TraceEvent]:
        return list(self._trace.get(run_id, []))

    # --- internos ---

    def _next_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"run-{self._counter:04d}"

    def _create(self, run_id: str, file_name: str, content: bytes) -> RunState:
        fmt = "xlsx" if content.startswith(b"PK\x03\x04") else "pdf" if content.startswith(b"%PDF") else "csv"
        undecodable: UnicodeDecodeError | None = None
        if fmt == "csv":
            try:
                lines = [ln for ln in content.decode("utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
            except UnicodeDecodeError as exc:
                undecodable, lines = exc, []
            rows = max(len(lines) - 1, 0)  # sem o cabeçalho
        else:
            rows = 3  # o falso não abre planilha nem PDF: resumo fixo
        with self._lock:
            self._trace[run_id] = []
            self._emit(run_id, "csv.validate", latency_ms=5, payload={**NO_MODEL, "rows": rows, "format": fmt})
            self._input_hashes[run_id] = hashlib.sha256(content).hexdigest()
            if undecodable is not None:
                reason = f"o arquivo não está em UTF-8 (byte inválido na posição {undecodable.start})"
                issue = CsvIssue(line=1, reason=reason)
                summary = ReadSummary(file_name=file_name, rows=0, employees=0, stores=0, week_start=None,
                                      total_hours=Decimal("0"), issues=[issue], ok=False)  # fmt: skip
                card = _rx13(file_name, reason, [f"linha 1: {reason}"])
                self._emit(run_id, "exception.raised", payload={**NO_MODEL, "code": card.code})
                state = RunState(run_id=run_id, phase="failed", summary=summary, exception=card)
            elif rows == 0:
                issue = CsvIssue(line=1, reason="arquivo sem linhas de escala")
                summary = ReadSummary(file_name=file_name, rows=0, employees=0, stores=0, week_start=None,
                                      total_hours=Decimal("0"), issues=[issue], ok=False)  # fmt: skip
                card = _rx13(file_name, "O arquivo não tem linhas de escala.", [f"linha {issue.line}: {issue.reason}"])
                self._emit(run_id, "exception.raised", payload={**NO_MODEL, "code": card.code})
                state = RunState(run_id=run_id, phase="failed", summary=summary, exception=card)
            else:
                summary = ReadSummary(
                    file_name=file_name,
                    rows=rows,
                    employees=len(EMPLOYEES),
                    stores=1,
                    week_start=WEEK_START,
                    total_hours=Decimal("176"),
                    issues=[],
                    ok=True,
                    format=fmt,
                    mapping_source="csv_dec039" if fmt == "csv" else "heuristica",
                )
                self._emit(run_id, "read.summary", payload={**NO_MODEL, "ok": True})
                state = RunState(run_id=run_id, phase="awaiting_confirm", summary=summary)
            self._runs[run_id] = state
            return state

    def _require(self, run_id: str, phase: str) -> RunState:
        state = self._runs.get(run_id)
        if state is None:
            raise RunNotFoundError(run_id)
        if state.phase != phase:
            raise RunPhaseError(f"execução em {state.phase}; a operação exige {phase}")
        return state

    def _refusal(self, version: ScheduleVersion, approval: Approval) -> str | None:
        if self.refuse_publish or self._approvals.get(version.id) is None:
            return "aprovação humana não encontrada"
        if approval.version_id != version.id:
            return "a aprovação é de outra versão"
        if approval.role != Role.GESTOR:
            return "papel sem permissão para publicar"
        return None

    def _emit(self, run_id: str, kind: str, *, cost_usd: Decimal = Decimal("0"), latency_ms: int = 1, **fields) -> None:
        events = self._trace.setdefault(run_id, [])
        events.append(
            TraceEvent(
                id=f"{run_id}-ev{len(events) + 1:02d}",
                run_id=run_id,
                parent_id=events[0].id if events else None,
                kind=kind,
                at=self._now(),
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                **fields,
            )
        )
