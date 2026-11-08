"""Piso da carga do contrato (PR #16) contra as regras por pessoa da C6, a quebra de simetria e a RX-02."""

from datetime import time, timedelta

from escalista.domain.rules import RuleLayer
from escalista.domain.schedule import Schedule, Store
from escalista.solver.model import ModelStats, solve
from tests.solver.test_model import MONDAY, _violations, card, demand_block, emp, request, rule

STORES = [Store(id="S1", name="Loja teste", opens=time(8), closes=time(22))]


def _hours(sched: Schedule) -> dict[str, float]:
    out: dict[str, float] = {}
    for s in sched.shifts:
        out[s.employee_id] = out.get(s.employee_id, 0) + (s.end - s.start).total_seconds() / 3600
    return out


def _unavailable(eid: str, offset: int):
    return rule(
        "indisponibilidade", RuleLayer.EXECUCAO, employee_id=eid, day=(MONDAY + timedelta(days=offset)).isoformat()
    )


def test_floor_is_bounded_by_unavailable_days_and_never_makes_the_model_infeasible():
    # 44 h de contrato, indisponível seg, ter e qua: sobram 4 dias, então o piso cai de 40 h para 4 × 8 h = 32 h
    rc = card(weekly=44)
    rc = rc.model_copy(update={"rules": [*rc.rules, *(_unavailable("E1", d) for d in range(3))]})
    employees = [emp("E1", contract_hours=44)]
    stats = ModelStats()

    result = solve(request(STORES, employees, demand_block("S1", MONDAY, time(9), time(13), 1), rc), stats)

    assert result.status == "optimal" and result.schedule is not None
    assert _hours(result.schedule)["E1"] >= 32
    assert all((s.start.date() - MONDAY).days >= 3 for s in result.schedule.shifts)
    assert stats.contract_floor_reduced == {"E1": 32 * 60}
    assert _violations(result.schedule, rc, STORES, employees) == []


def test_floor_is_bounded_by_the_person_weekly_cap():
    rc = card(weekly=44)
    cap = rule("jornada_semanal_max_pessoa", RuleLayer.EXECUCAO, employee_id="E1", hours=20)
    rc = rc.model_copy(update={"rules": [*rc.rules, cap]})
    stats = ModelStats()

    result = solve(request(STORES, [emp("E1", contract_hours=44)], [], rc), stats)

    assert result.status == "optimal" and result.schedule is not None
    assert _hours(result.schedule).get("E1", 0) == 20
    assert stats.contract_floor_reduced == {"E1": 20 * 60}


def test_store_is_resolved_without_floor_when_the_floor_alone_is_infeasible():
    # interjornada de 23 h com turnos de 8 h numa loja de 8h às 22h: 5 dias de trabalho não cabem na semana
    rc = card(weekly=44, rest_gap=23)
    stats = ModelStats()

    result = solve(request(STORES, [emp("E1", contract_hours=44)], [], rc), stats)

    assert result.status != "infeasible" and result.schedule is not None
    assert stats.contract_floor_dropped == ["S1"]


def test_symmetry_breaking_does_not_force_a_lower_contract_up_to_a_higher_one():
    # mesmo salário, contratos diferentes: trocar as semanas das duas não é simétrico, então não pode haver ordem
    employees = [emp("E1", contract_hours=16), emp("E2", contract_hours=40)]

    result = solve(request(STORES, employees, []))

    assert result.status == "optimal" and result.schedule is not None
    hours = _hours(result.schedule)
    assert hours == {"E1": 16, "E2": 40}


def test_rx02_still_raised_with_contract_floors():
    employees = [emp("E1", contract_hours=44), emp("E2", contract_hours=44)]
    demand = demand_block("S1", MONDAY, time(8), time(22), 3)

    result = solve(request(STORES, employees, demand))

    assert result.status in ("optimal", "feasible") and result.schedule is not None
    assert result.exception is not None and result.exception.code == "RX-02"
