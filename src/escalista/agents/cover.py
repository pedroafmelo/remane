"""Busca de quem cobre uma falta (FT-03 mínimo), em código e sem solver.

Candidatos: as outras pessoas da mesma loja sem turno começando no dia da falta. Para cada uma, a escala com o turno
reatribuído passa pelo verificador independente; só fica quem não cria violação nova. A ordem é: sem hora extra
primeiro, depois a mesma função de quem faltou, depois o menor custo adicional (a mesma `compute_metrics` do
antes e depois), e por fim o id, para empate determinístico. O custo adicional é o da escala coberta menos o da
escala sem o turno (o que custa cobrir em vez de deixar descoberto).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from escalista.domain.rules import RuleCard
from escalista.domain.schedule import Employee, Schedule, Shift
from escalista.solver.cost import compute_metrics
from escalista.verifier import verify


@dataclass(frozen=True)
class CoverCandidate:
    employee: Employee
    schedule: Schedule  # a escala com o turno reatribuído a `employee`
    added_cost: Decimal
    overtime_hours: Decimal  # hora extra que a cobertura acrescenta


def _keys(schedule: Schedule, card: RuleCard) -> set[tuple]:
    return {(v.rule_id, v.employee_id, v.day) for v in verify(schedule, card).violations}


def find_cover(
    schedule: Schedule, shift: Shift, employees: list[Employee], card: RuleCard
) -> tuple[int, list[CoverCandidate]]:
    """Devolve (quantos candidatos foram avaliados, os aprovados pelo verificador em ordem de preferência)."""
    by_id = {e.id: e for e in employees}
    absent = by_id[shift.employee_id]
    day = shift.start.date()
    working = {s.employee_id for s in schedule.shifts if s.start.date() == day}
    pool = sorted(
        (e for e in employees if e.store_id == shift.store_id and e.id != absent.id and e.id not in working),
        key=lambda e: e.id,
    )
    without = Schedule(week_start=schedule.week_start, shifts=[s for s in schedule.shifts if s != shift])
    base_violations = _keys(schedule, card)
    base = compute_metrics(without, employees, [], card, 0)  # demanda vazia: aqui só o custo interessa

    found: list[CoverCandidate] = []
    for person in pool:
        moved = Schedule(
            week_start=schedule.week_start,
            shifts=[*without.shifts, shift.model_copy(update={"employee_id": person.id})],
        )
        if _keys(moved, card) - base_violations:
            continue
        after = compute_metrics(moved, employees, [], card, 0)
        found.append(
            CoverCandidate(
                employee=person,
                schedule=moved,
                added_cost=after.total_cost - base.total_cost,
                overtime_hours=after.overtime_hours - base.overtime_hours,
            )
        )
    found.sort(key=lambda c: (c.overtime_hours > 0, c.employee.job != absent.job, c.added_cost, c.employee.id))
    return len(pool), found
