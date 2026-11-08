"""Contratos do solver, do verificador, do custo, da justificativa, da versão e do estado da execução
(plano da C5, seção 3.1). Só forma: a lógica nasce no TDD de cada frente. Dinheiro e horas em `Decimal`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from escalista.domain.contracts import ExceptionCard, Role
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, ReadSummary, Schedule, Store
from escalista.domain.spec import SolveSpec


class SolveRequest(BaseModel):
    card: RuleCard
    stores: list[Store]
    employees: list[Employee]
    demand: list[DemandSlot]
    week_start: date
    seed: int
    time_limit_s: float
    num_workers: int
    hint: Schedule | None = None
    spec: SolveSpec | None = None  # `None` = comportamento da C5 (E1 não muda)


class SolveResult(BaseModel):
    status: Literal["optimal", "feasible", "infeasible", "timeout"]
    schedule: Schedule | None = None
    uncovered: list[DemandSlot] = Field(default_factory=list)  # o que faltou cobrir
    wall_ms: int
    seed: int
    input_hash: str
    exception: ExceptionCard | None = None  # RX-02 ou RX-12


class Violation(BaseModel):
    rule_id: str
    kind: str
    employee_id: str | None = None
    day: date | None = None
    source: str
    detail: str


class ViolationReport(BaseModel):
    violations: list[Violation]

    @computed_field
    @property
    def total(self) -> int:
        return len(self.violations)


class ScheduleMetrics(BaseModel):
    total_cost: Decimal
    regular_hours: Decimal
    overtime_hours: Decimal
    overtime_cost: Decimal
    coverage_pct: float
    uncovered_slots: int
    violations: int


class Comparison(BaseModel):
    """Antes e depois, medidos pela mesma função de custo."""

    before: ScheduleMetrics
    after: ScheduleMetrics
    savings: Decimal
    overtime_hours_avoided: Decimal
    violations_avoided: int


class JustificationItem(BaseModel):
    text: str
    rule_refs: list[str]  # todo id precisa existir no cartão (validação da frente B)


class Justification(BaseModel):
    """Saída estruturada do modelo."""

    summary: str
    items: list[JustificationItem]


class ScheduleVersion(BaseModel):
    id: str
    run_id: str
    schedule: Schedule
    status: Literal["draft", "approved", "published"]
    input_hash: str
    seed: int
    violations_total: int
    created_at: datetime


class Approval(BaseModel):
    """Ato humano: quem aprovou a versão, com qual papel e quando."""

    id: str
    version_id: str
    approved_by: str  # id do usuário
    role: Role
    at: datetime


class RunState(BaseModel):
    run_id: str
    phase: Literal["read", "awaiting_confirm", "optimized", "awaiting_approval", "published", "failed"]
    summary: ReadSummary | None = None
    comparison: Comparison | None = None
    report: ViolationReport | None = None
    justification: Justification | None = None
    version_id: str | None = None
    exception: ExceptionCard | None = None
    # C6: todos com padrão, para o estado da C5 (só `run_id` e `phase`) seguir válido
    mode: Literal["upload", "continuidade"] = "upload"
    before: Schedule | None = None  # a escala "antes", persistida
    week_start: date | None = None
    spec: SolveSpec | None = None
    notices: list[ExceptionCard] = Field(default_factory=list)  # avisos que não bloqueiam (RX-02, RX-12)
    roster_version: int | None = None
    attempts: int = Field(default=0, ge=0)
