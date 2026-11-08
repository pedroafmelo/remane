"""Pedido de replanejamento e despachador in-process (plano da C7, seção 4.2).

O acompanhamento nunca chama a busca de cobertura direto: grava um `ReplanRequest` no caso e o despachador o entrega
à `find_cover` (só ela no v1), que devolve os candidatos aprovados pelo verificador, em ordem. Se o melhor gera hora
extra, é o gatilho `overtime_needed` (RF-28), que nasce aqui e não no varredor.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from escalista.agents.cover import CoverCandidate
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import Employee, Schedule, Shift
from escalista.domain.tracking import Case, ReplanReason, ReplanRequest

CoverFn = Callable[[Schedule, Shift, list[Employee], RuleCard], tuple[int, list[CoverCandidate]]]


@dataclass(frozen=True)
class CoverOutcome:
    evaluated: int
    candidates: list[CoverCandidate]

    @property
    def ranked(self) -> list[str]:
        return [c.employee.id for c in self.candidates]

    @property
    def overtime_needed(self) -> bool:
        """RF-28: há candidato e o primeiro da ordem gera hora extra."""
        return bool(self.candidates) and self.candidates[0].overtime_hours > 0


def request_for(case: Case, *, reason: ReplanReason, request_id: str, origin_trace_id: str | None) -> ReplanRequest:
    return ReplanRequest(
        id=request_id,
        case_id=case.id,
        window_start=case.shift.start,
        window_end=case.shift.end,
        absent_id=case.employee_id,
        reason=reason,
        origin_trace_id=origin_trace_id,
    )


def dispatch(
    request: ReplanRequest,
    *,
    cover_fn: CoverFn,
    schedule: Schedule,
    shift: Shift,
    employees: list[Employee],
    card: RuleCard,
) -> CoverOutcome:
    """Entrega o pedido à busca de cobertura. Levanta o que a busca levantar (o fluxo transforma em RX-12)."""
    assert request.absent_id == shift.employee_id, "o pedido e o turno são da mesma pessoa"
    evaluated, candidates = cover_fn(schedule, shift, employees, card)
    return CoverOutcome(evaluated=evaluated, candidates=list(candidates))
