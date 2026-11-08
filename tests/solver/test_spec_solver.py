"""Solver com a `SolveSpec` (plano da C6, A5; seções 5.1 e 10).

- `spec=None`: entrada, hash e escala idênticos aos da C5 (E1 não muda).
- Restrições duras por pessoa: lidas **do cartão** (regras `execucao` que `card_with_spec` acrescenta), para o solver
  obedecer exatamente o que o verificador confere.
- Preferências e estabilidade: penalidades no objetivo, nunca acima da cobertura.

Os testes conferem a escala com o verificador mínimo de `test_model.py` e com contas feitas aqui.
"""

from __future__ import annotations

import time as wallclock
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from escalista.domain.results import SolveRequest
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift, Store
from escalista.domain.spec import (
    MaxWeeklyHoursConstraint,
    PreferredDayOffConstraint,
    PreferredWindowConstraint,
    SolveSpec,
    UnavailableConstraint,
)
from escalista.rules.spec import card_with_spec, default_spec
from escalista.solver.model import ModelStats, input_hash, solve
from tests.solver.test_model import DEMO, MONDAY, _violations, card, demand_block, emp, request

STORE = Store(id="S1", name="Loja teste", opens=time(8), closes=time(22))
EV = "pedido do gestor"


def with_spec(req: SolveRequest, spec: SolveSpec, hint: Schedule | None = None) -> SolveRequest:
    """Como o agente chama: o cartão ganha as regras `execucao` da spec e a spec vai junto."""
    return req.model_copy(update={"card": card_with_spec(req.card, spec), "spec": spec, "hint": hint})


def trio(shifts: list[Shift]) -> list[tuple[str, datetime, datetime]]:
    return [(s.employee_id, s.start, s.end) for s in shifts]


def hours_of(sched: Schedule, eid: str) -> float:
    return sum((s.end - s.start).total_seconds() / 3600 for s in sched.shifts if s.employee_id == eid)


def overlaps(sh: Shift, start: datetime, end: datetime) -> bool:
    return sh.start < end and sh.end > start


def _person_violations(sched: Schedule, rc: RuleCard) -> list[str]:
    """As duas regras `execucao` conferidas aqui, a partir do cartão (independente do solver)."""
    out = []
    for r in rc.rules:
        p = r.params
        mine = [s for s in sched.shifts if s.employee_id == p.get("employee_id")]
        if r.kind == "indisponibilidade":
            day = date.fromisoformat(p["day"])
            start = datetime.combine(day, time.fromisoformat(p["start"]) if p.get("start") else time(0))
            end = (
                datetime.combine(day, time.fromisoformat(p["end"]))
                if p.get("end")
                else datetime.combine(day + timedelta(days=1), time(0))
            )
            out += [f"{r.id} {s.start}" for s in mine if overlaps(s, start, end)]
        elif r.kind == "jornada_semanal_max_pessoa":
            if sum((s.end - s.start).total_seconds() / 3600 for s in mine) > p["hours"] + 1e-9:
                out.append(r.id)
    return out


# spec=None: nada muda --------------------------------------------------------------------------------------------


def _pinned_request() -> SolveRequest:
    employees = [emp("E1"), emp("E2", wage="11.00"), emp("E3", wage="12.00")]
    demand = demand_block("S1", MONDAY, time(8), time(20), 2) + demand_block(
        "S1", MONDAY + timedelta(days=2), time(10), time(22), 1
    )
    return request([STORE], employees, demand, seed=3)


def test_spec_none_keeps_hash_and_schedule_of_c5():
    # Hash e escala gravados com o solver da C5 (antes da A5), mesma fixture, seed 3, 1 thread.
    result = solve(_pinned_request())

    assert result.input_hash == "3a6a7c90990c48c0f8c544ca5e74313dcc46414886b8a1293df204609f83cce0"
    d0, d2 = MONDAY, MONDAY + timedelta(days=2)
    at = datetime.combine
    assert trio(result.schedule.shifts) == [
        ("E1", at(d0, time(12)), at(d0, time(20))),
        ("E1", at(d2, time(14)), at(d2, time(22))),
        ("E2", at(d0, time(8, 30)), at(d0, time(16, 30))),
        ("E2", at(d2, time(10)), at(d2, time(14))),
        ("E3", at(d0, time(8)), at(d0, time(12))),
    ]


def test_default_spec_same_schedule_but_hash_includes_spec():
    base = _pinned_request()
    none = solve(base)
    default = solve(base.model_copy(update={"spec": default_spec()}))
    heavier = base.model_copy(update={"spec": SolveSpec(shortfall_weight=200)})

    assert default.schedule == none.schedule  # sem restrições, a spec padrão é o objetivo da C5
    assert default.input_hash != none.input_hash  # a spec entra no hash quando existe
    assert input_hash(heavier) != default.input_hash


# Restrições duras por pessoa (do cartão) ---------------------------------------------------------------------------


def test_unavailable_whole_day_is_respected_even_with_symmetry_peer():
    # Mesmo salário: sem cuidado, a quebra de simetria (horas de E1 ≥ horas de E2) deixaria a faixa descoberta.
    employees = [emp("E1"), emp("E2")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    spec = SolveSpec(constraints=[UnavailableConstraint(employee_id="E1", day=MONDAY, evidence=EV)])
    req = with_spec(request([STORE], employees, demand), spec)

    result = solve(req)

    assert result.status == "optimal" and result.uncovered == []
    assert [s.employee_id for s in result.schedule.shifts] == ["E2"]
    assert _person_violations(result.schedule, req.card) == []
    assert _violations(result.schedule, req.card, [STORE], employees) == []


def test_unavailable_interval_blocks_only_overlapping_shifts():
    employees = [emp("E1"), emp("E2", wage="20.00")]
    demand = demand_block("S1", MONDAY, time(14), time(18), 1)
    spec = SolveSpec(
        constraints=[UnavailableConstraint(employee_id="E1", day=MONDAY, start=time(8), end=time(12), evidence=EV)]
    )
    req = with_spec(request([STORE], employees, demand), spec)

    result = solve(req)

    assert result.uncovered == []
    assert [s.employee_id for s in result.schedule.shifts] == ["E1"]  # fora do intervalo, a pessoa segue disponível
    assert _person_violations(result.schedule, req.card) == []


def test_unavailable_interval_also_blocks_overnight_shift_from_previous_day():
    night = Store(id="S1", name="Loja noturna", opens=time(16), closes=time(2))
    employees = [emp("E1"), emp("E2", wage="20.00")]
    demand = demand_block("S1", MONDAY, time(20), time(23, 59), 1) + demand_block(
        "S1", MONDAY + timedelta(days=1), time(0), time(1), 1
    )
    tuesday = MONDAY + timedelta(days=1)
    spec = SolveSpec(
        constraints=[UnavailableConstraint(employee_id="E1", day=tuesday, start=time(0), end=time(1), evidence=EV)]
    )
    req = with_spec(request([night], employees, demand), spec)

    result = solve(req)

    assert result.uncovered == []
    blocked = (datetime.combine(tuesday, time(0)), datetime.combine(tuesday, time(1)))
    assert not [s for s in result.schedule.shifts if s.employee_id == "E1" and overlaps(s, *blocked)]
    assert _person_violations(result.schedule, req.card) == []


def test_per_person_weekly_cap_is_respected():
    employees = [emp("E1"), emp("E2", wage="15.00")]
    demand = [s for d in range(5) for s in demand_block("S1", MONDAY + timedelta(days=d), time(9), time(17), 1)]
    free = solve(request([STORE], employees, demand))
    assert hours_of(free.schedule, "E1") == 40  # sem o teto, a mais barata faz tudo

    spec = SolveSpec(constraints=[MaxWeeklyHoursConstraint(employee_id="E1", hours=20, evidence=EV)])
    req = with_spec(request([STORE], employees, demand), spec)
    result = solve(req)

    assert result.uncovered == []
    assert 0 < hours_of(result.schedule, "E1") <= 20
    assert _person_violations(result.schedule, req.card) == []
    assert _violations(result.schedule, req.card, [STORE], employees) == []


def test_hard_rules_in_card_apply_even_without_spec():
    # O solver obedece o cartão: as regras `execucao` valem mesmo que o agente não mande a spec.
    employees = [emp("E1"), emp("E2")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    spec = SolveSpec(constraints=[UnavailableConstraint(employee_id="E1", day=MONDAY, evidence=EV)])
    req = request([STORE], employees, demand).model_copy(update={"card": card_with_spec(card(), spec)})

    result = solve(req)

    assert [s.employee_id for s in result.schedule.shifts] == ["E2"]


def test_spec_hard_constraints_without_card_rules_are_not_read_from_spec():
    # A fonte das restrições duras é o cartão; a spec sozinha não restringe (o agente chama `card_with_spec`).
    employees = [emp("E1"), emp("E2", wage="20.00")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    spec = SolveSpec(constraints=[UnavailableConstraint(employee_id="E1", day=MONDAY, evidence=EV)])

    result = solve(request([STORE], employees, demand).model_copy(update={"spec": spec}))

    assert [s.employee_id for s in result.schedule.shifts] == ["E1"]


# Preferências (suaves) ---------------------------------------------------------------------------------------------


def test_preferred_day_off_is_met_when_it_costs_no_coverage():
    employees = [emp("E1"), emp("E2")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    spec = SolveSpec(constraints=[PreferredDayOffConstraint(employee_id="E1", day=MONDAY, evidence=EV)])
    stats = ModelStats()

    result = solve(with_spec(request([STORE], employees, demand), spec), stats)

    assert result.uncovered == []
    assert [s.employee_id for s in result.schedule.shifts] == ["E2"]
    assert (stats.preferences_met, stats.preferences_total) == (1, 1)


def test_preferred_day_off_never_beats_coverage():
    employees = [emp("E1")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    spec = SolveSpec(
        preference_weight=50, constraints=[PreferredDayOffConstraint(employee_id="E1", day=MONDAY, evidence=EV)]
    )
    stats = ModelStats()

    result = solve(with_spec(request([STORE], employees, demand), spec), stats)

    assert result.uncovered == []
    assert [s.employee_id for s in result.schedule.shifts] == ["E1"]
    assert (stats.preferences_met, stats.preferences_total) == (0, 1)


def test_preferred_window_is_met_when_it_costs_no_coverage():
    employees = [emp("E1"), emp("E2")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1) + demand_block("S1", MONDAY, time(18), time(22), 1)
    spec = SolveSpec(constraints=[PreferredWindowConstraint(employee_id="E1", window="noite", evidence=EV)])
    stats = ModelStats()

    result = solve(with_spec(request([STORE], employees, demand), spec), stats)

    assert result.uncovered == []
    mine = [s for s in result.schedule.shifts if s.employee_id == "E1"]
    assert mine and all(s.start.time() >= time(18) for s in mine)
    assert (stats.preferences_met, stats.preferences_total) == (1, 1)


def test_preference_weight_zero_ignores_preferences():
    employees = [emp("E1"), emp("E2", wage="10.50")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    spec = SolveSpec(
        preference_weight=0, constraints=[PreferredDayOffConstraint(employee_id="E1", day=MONDAY, evidence=EV)]
    )

    result = solve(with_spec(request([STORE], employees, demand), spec))

    assert [s.employee_id for s in result.schedule.shifts] == ["E1"]  # a mais barata, sem penalidade


# Estabilidade ------------------------------------------------------------------------------------------------------


def _expensive_hint(start: time, end: time) -> Schedule:
    return Schedule(
        week_start=MONDAY,
        shifts=[
            Shift(
                employee_id="E2",
                store_id="S1",
                start=datetime.combine(MONDAY, start),
                end=datetime.combine(MONDAY, end),
            )
        ],
    )


def test_stability_repeats_the_hint_when_feasible():
    employees = [emp("E1"), emp("E2", wage="12.00")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    hint = _expensive_hint(time(9), time(13))
    base = request([STORE], employees, demand)

    cheap = solve(with_spec(base, SolveSpec(stability_weight=0), hint))
    stable = solve(with_spec(base, SolveSpec(stability_weight=50), hint))

    assert [s.employee_id for s in cheap.schedule.shifts] == ["E1"]  # sem peso, o custo manda
    assert trio(stable.schedule.shifts) == trio(hint.shifts)


def test_stability_uses_nearest_catalog_shift_when_hint_is_off_catalog():
    employees = [emp("E1"), emp("E2", wage="12.00")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    hint = _expensive_hint(time(9, 10), time(13, 10))  # fora do passo de 30 min; o mais próximo é 09:00–13:00

    result = solve(with_spec(request([STORE], employees, demand), SolveSpec(stability_weight=50), hint))

    assert trio(result.schedule.shifts) == [
        ("E2", datetime.combine(MONDAY, time(9)), datetime.combine(MONDAY, time(13)))
    ]


def test_hint_enters_hash_only_when_stability_weighs():
    employees = [emp("E1"), emp("E2", wage="12.00")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)
    base = request([STORE], employees, demand)
    h1, h2 = _expensive_hint(time(9), time(13)), _expensive_hint(time(8), time(13))

    assert input_hash(with_spec(base, SolveSpec(), h1)) == input_hash(with_spec(base, SolveSpec(), h2))
    assert input_hash(with_spec(base, SolveSpec(stability_weight=10), h1)) != input_hash(
        with_spec(base, SolveSpec(stability_weight=10), h2)
    )


# Faixas dos pesos (pydantic) ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("shortfall_weight", 9),
        ("shortfall_weight", 1001),
        ("stability_weight", -1),
        ("stability_weight", 51),
        ("preference_weight", -1),
        ("preference_weight", 51),
    ],
)
def test_weights_out_of_range_are_refused_by_schema(field: str, value: int):
    with pytest.raises(ValidationError):
        SolveSpec(**{field: value})


# 60 × 7 com spec ---------------------------------------------------------------------------------------------------


@pytest.mark.slow
def test_solver_60x7_with_spec_respects_person_rules():
    stores = TypeAdapter(list[Store]).validate_json((DEMO / "lojas.json").read_bytes())
    employees = TypeAdapter(list[Employee]).validate_json((DEMO / "pessoas.json").read_bytes())
    demand = TypeAdapter(list[DemandSlot]).validate_json((DEMO / "demanda.json").read_bytes())
    ids = sorted(e.id for e in employees)
    spec = SolveSpec(
        constraints=[
            UnavailableConstraint(employee_id=ids[0], day=MONDAY + timedelta(days=2), evidence=EV),
            UnavailableConstraint(
                employee_id=ids[1], day=MONDAY + timedelta(days=4), start=time(14), end=time(18), evidence=EV
            ),
            MaxWeeklyHoursConstraint(employee_id=ids[2], hours=24, evidence=EV),
            PreferredDayOffConstraint(employee_id=ids[3], day=MONDAY + timedelta(days=5), evidence=EV),
            PreferredWindowConstraint(employee_id=ids[4], window="manha", evidence=EV),
        ]
    )
    req = with_spec(request(stores, employees, demand, seed=42, workers=8, limit=30.0), spec)
    stats = ModelStats()

    t0 = wallclock.perf_counter()
    result = solve(req, stats)
    elapsed = wallclock.perf_counter() - t0

    assert result.status in ("optimal", "feasible")
    assert sum(stats.solver_wall_s.values()) <= 30.0 + 2  # limite configurado: tempo que o CP-SAT reporta
    assert elapsed <= 3 * 30.0  # parede total só contra travamento
    assert _violations(result.schedule, req.card, stores, employees) == []
    assert _person_violations(result.schedule, req.card) == []
    assert stats.preferences_total == 2
    assert all(isinstance(e.hourly_wage, Decimal) for e in employees)
