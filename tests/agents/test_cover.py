"""Busca de cobertura para uma falta (FT-03 mínimo): candidatos filtrados pelo verificador e ordenados pelo custo."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from escalista.agents.cover import find_cover
from escalista.domain.schedule import Employee, Schedule, Shift
from tests.agents.support import WEEK, rule_card


def _emp(eid: str, job: str, wage: str, store: str = "L1") -> Employee:
    return Employee(
        id=eid, name=f"{eid} (sintético)", store_id=store, job=job, hourly_wage=Decimal(wage), contract_hours=44, sex="F"
    )


def _shifts(eid: str, days: list[int], start: int, store: str = "L1") -> list[Shift]:
    out = []
    for d in days:
        begin = datetime.combine(WEEK + timedelta(days=d), time(start))
        out.append(Shift(employee_id=eid, store_id=store, start=begin, end=begin + timedelta(hours=8)))
    return out


EMPLOYEES = [
    _emp("A", "Atendente", "11.50"),  # quem faltou
    _emp("B", "Atendente", "11.50"),  # folga na quarta, mas a interjornada de 12h quebra (qua 22h -> qui 08h)
    _emp("C", "Atendente", "12.00"),  # cobre: mesma função
    _emp("D", "Caixa", "11.00"),  # cobre: outra função, mais barata
    _emp("E", "Atendente", "11.00"),  # já tem 40h e 1 folga a mais quebraria o repouso e as 42h
    _emp("F", "Atendente", "10.00", store="L2"),  # outra loja: fora
]
SCHEDULE = Schedule(
    week_start=WEEK,
    shifts=[
        *_shifts("A", [0, 1, 2, 3, 4], 14),
        *_shifts("B", [0, 1, 3, 4], 8),
        *_shifts("C", [0, 1, 3], 14),
        *_shifts("D", [0, 1], 14),
        *_shifts("E", [0, 1, 3, 4, 5], 14),
        *_shifts("F", [0], 14, store="L2"),
    ],
)
WEDNESDAY_SHIFT = next(s for s in SCHEDULE.shifts if s.employee_id == "A" and s.start.weekday() == 2)


def test_candidates_are_filtered_by_the_verifier_and_ranked_same_job_then_cost():
    evaluated, candidates = find_cover(SCHEDULE, WEDNESDAY_SHIFT, EMPLOYEES, rule_card())
    assert evaluated == 4  # B, C, D, E (de folga na quarta, mesma loja)
    assert [c.employee.id for c in candidates] == ["C", "D"]
    assert candidates[0].added_cost == Decimal("96.00")  # 8h x 12,00, sem hora extra
    assert candidates[1].added_cost == Decimal("88.00")
    assert all(c.overtime_hours == 0 for c in candidates)


def test_candidate_schedule_moves_only_that_shift():
    _, candidates = find_cover(SCHEDULE, WEDNESDAY_SHIFT, EMPLOYEES, rule_card())
    moved = candidates[0].schedule
    assert len(moved.shifts) == len(SCHEDULE.shifts)
    assert WEDNESDAY_SHIFT not in moved.shifts
    assert WEDNESDAY_SHIFT.model_copy(update={"employee_id": "C"}) in moved.shifts


def test_no_one_eligible_returns_empty():
    only_blocked = [e for e in EMPLOYEES if e.id in {"A", "B", "E"}]
    schedule = Schedule(week_start=WEEK, shifts=[s for s in SCHEDULE.shifts if s.employee_id in {"A", "B", "E"}])
    evaluated, candidates = find_cover(schedule, WEDNESDAY_SHIFT, only_blocked, rule_card())
    assert evaluated == 2
    assert candidates == []
