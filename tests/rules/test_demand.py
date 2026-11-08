"""Demanda inferida da escala lida e conta de capacidade (plano da C6, A3; seção 9)."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import pytest

from escalista.domain.reading import CapacityCheck, DemandPattern
from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift, Store
from escalista.rules.demand import (
    capacity_check,
    demand_for_week,
    infer_demand_pattern,
    infer_store_hours,
    scale_pattern,
)
from escalista.rules.identity import StoreDraft
from escalista.rules.loader import load_rule_card

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "data" / "demo"
RULES = ROOT / "data" / "regras"
MONDAY = date(2027, 1, 11)


def _shift(emp: str, store: str, start: datetime, end: datetime) -> Shift:
    return Shift(employee_id=emp, store_id=store, start=start, end=end)


def _demo_schedule() -> Schedule:
    text = (DEMO / "escala_atual.csv").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    shifts = []
    for row in csv.DictReader(io.StringIO("\n".join(lines))):
        day = date.fromisoformat(row["data"])
        start = datetime.combine(day, time.fromisoformat(row["inicio"]))
        end = datetime.combine(day, time.fromisoformat(row["fim"]))
        shifts.append(_shift(row["pessoa_id"], row["loja_id"], start, end))
    return Schedule(week_start=MONDAY, shifts=shifts)


def _demo_employees() -> list[Employee]:
    return [Employee(**e) for e in json.loads((DEMO / "pessoas.json").read_text(encoding="utf-8"))]


def _card(weekly: float = 42, daily: float = 8, rest: int = 2) -> RuleCard:
    def rule(kind: str, params: dict) -> Rule:
        return Rule(id=kind, kind=kind, layer=RuleLayer.LEI, params=params, status=RuleStatus.INTERPRETACAO, source="t")

    return RuleCard(
        reference_date=MONDAY,
        rules=[
            rule("jornada_semanal_max", {"hours": weekly}),
            rule("jornada_diaria_max", {"hours": daily}),
            rule("repouso_semanal", {"days": rest}),
        ],
    )


# --- horário da loja ------------------------------------------------------------------------------------------


def test_store_hours_are_first_start_and_last_end_rounded_out_to_30_min():
    shifts = [
        _shift("P1", "L1", datetime(2027, 1, 11, 8, 10), datetime(2027, 1, 11, 16)),
        _shift("P2", "L1", datetime(2027, 1, 12, 14), datetime(2027, 1, 12, 22, 10)),
        _shift("P3", "L2", datetime(2027, 1, 11, 9), datetime(2027, 1, 11, 17, 30)),
        _shift("P9", "LX", datetime(2027, 1, 11, 6), datetime(2027, 1, 11, 23)),  # loja fora da lista: ignorada
    ]
    stores = infer_store_hours(shifts, [StoreDraft("L1", "Centro"), StoreDraft("L2", "Norte")])
    assert stores == [
        Store(id="L1", name="Centro", opens=time(8), closes=time(22, 30)),
        Store(id="L2", name="Norte", opens=time(9), closes=time(17, 30)),
    ]


def test_store_without_shifts_is_left_out():
    shifts = [_shift("P1", "L1", datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 16))]
    stores = infer_store_hours(shifts, [StoreDraft("L1", "Centro"), StoreDraft("L2", "Norte")])
    assert [s.id for s in stores] == ["L1"]


def test_overnight_shift_closes_after_midnight_like_the_solver_catalog():
    # turno que vira a noite: fecha no dia seguinte (closes < opens, convenção de `solver/catalog.py`)
    shifts = [
        _shift("P1", "L1", datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 16)),
        _shift("P2", "L1", datetime(2027, 1, 11, 18), datetime(2027, 1, 12, 1, 10)),
    ]
    assert infer_store_hours(shifts, [StoreDraft("L1", "C")])[0].closes == time(1, 30)
    midnight = [*shifts[:1], _shift("P2", "L1", datetime(2027, 1, 11, 16), datetime(2027, 1, 12, 0, 0))]
    assert infer_store_hours(midnight, [StoreDraft("L1", "C")])[0].closes == time(0, 0)


def test_store_open_around_the_clock_closes_when_it_opens():
    shifts = [
        _shift("P1", "L1", datetime(2027, 1, 11, 2), datetime(2027, 1, 11, 10)),
        _shift("P2", "L1", datetime(2027, 1, 11, 22), datetime(2027, 1, 12, 6)),
    ]
    store = infer_store_hours(shifts, [StoreDraft("L1", "C")])[0]
    assert (store.opens, store.closes) == (time(2), time(2))


# --- padrão de demanda ----------------------------------------------------------------------------------------


def test_pattern_counts_people_per_slot_with_partial_slots_and_zeros_inside_store_hours():
    store = Store(id="L1", name="C", opens=time(8), closes=time(12))
    schedule = Schedule(
        week_start=MONDAY,
        shifts=[
            _shift("P1", "L1", datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 10, 10)),  # 10:00 parcial conta
            _shift("P2", "L1", datetime(2027, 1, 11, 9, 40), datetime(2027, 1, 11, 12)),  # 09:30 parcial conta
        ],
    )
    pattern = infer_demand_pattern(schedule, [store])
    assert len(pattern) == 7 * 8  # todas as faixas do horário, todos os dias (zeros inclusos)
    monday = {p.start: p.required for p in pattern if p.weekday == 0}
    assert monday == {
        time(8): 1,
        time(8, 30): 1,
        time(9): 1,
        time(9, 30): 2,
        time(10): 2,
        time(10, 30): 1,
        time(11): 1,
        time(11, 30): 1,
    }
    assert all(p.required == 0 for p in pattern if p.weekday != 0)
    assert pattern == sorted(pattern, key=lambda p: (p.weekday, p.start))


def test_pattern_counts_distinct_people_and_ignores_slots_outside_store_hours():
    store = Store(id="L1", name="C", opens=time(9), closes=time(10))
    schedule = Schedule(
        week_start=MONDAY,
        shifts=[
            _shift("P1", "L1", datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 9, 30)),
            _shift("P1", "L1", datetime(2027, 1, 11, 9, 15), datetime(2027, 1, 11, 11)),  # sobreposição: 1 pessoa
        ],
    )
    monday = {p.start: p.required for p in infer_demand_pattern(schedule, [store]) if p.weekday == 0}
    assert monday == {time(9): 1, time(9, 30): 1}


def test_pattern_puts_after_midnight_slots_on_the_next_weekday():
    store = Store(id="L1", name="C", opens=time(22), closes=time(1))
    schedule = Schedule(
        week_start=MONDAY,
        shifts=[_shift("P1", "L1", datetime(2027, 1, 11, 22), datetime(2027, 1, 12, 1))],
    )
    got = {(p.weekday, p.start) for p in infer_demand_pattern(schedule, [store]) if p.required}
    assert got == {(0, time(22)), (0, time(22, 30)), (0, time(23)), (0, time(23, 30)), (1, time(0)), (1, time(0, 30))}


# --- escala por loja ------------------------------------------------------------------------------------------


def _p(store: str, required: int, minute: int = 0) -> DemandPattern:
    return DemandPattern(store_id=store, weekday=0, start=time(8, minute), required=required)


def test_scale_pattern_rounds_up_keeps_one_and_zero_and_defaults_to_100():
    pattern = [_p("L1", 0), _p("L1", 1, 30), _p("L1", 3), _p("L1", 10), _p("L2", 3)]
    scaled = scale_pattern(pattern, {"L1": 50})
    assert [p.required for p in scaled] == [0, 1, 2, 5, 3]  # 0 → 0; 1 × 50% → 1; 3 × 50% → 2; L2 ausente = 100
    assert [p.required for p in scale_pattern(pattern, {"L1": 120})][:4] == [0, 2, 4, 12]
    assert [(p.store_id, p.weekday, p.start) for p in scaled] == [(p.store_id, p.weekday, p.start) for p in pattern]
    assert [p.required for p in pattern] == [0, 1, 3, 10, 3]  # pura


def test_scale_pattern_rounds_up_exact_products_without_float_error():
    assert scale_pattern([_p("L1", 7)], {"L1": 100})[0].required == 7
    assert scale_pattern([_p("L1", 10)], {"L1": 70})[0].required == 7


# --- demanda da semana ----------------------------------------------------------------------------------------


def test_demand_for_week_materializes_the_pattern_on_dates():
    pattern = [
        DemandPattern(store_id="L1", weekday=0, start=time(8), required=2),
        DemandPattern(store_id="L1", weekday=6, start=time(21, 30), required=1),
    ]
    assert demand_for_week(pattern, date(2027, 1, 18)) == [
        DemandSlot(store_id="L1", day=date(2027, 1, 18), start=time(8), required=2),
        DemandSlot(store_id="L1", day=date(2027, 1, 24), start=time(21, 30), required=1),
    ]
    with pytest.raises(ValueError, match="segunda"):
        demand_for_week(pattern, date(2027, 1, 19))


# --- capacidade -----------------------------------------------------------------------------------------------


def _employees(n: int) -> list[Employee]:
    return [
        Employee(id=f"P{i}", name=f"P{i}", store_id="L1", job="x", hourly_wage=Decimal("10"), contract_hours=44)
        for i in range(n)
    ]


def test_capacity_check_small_case():
    pattern = [_p("L1", 4), _p("L1", 4, 30)]  # 8 faixas × 0,5 h = 4 pessoa-hora
    check = capacity_check(pattern, _employees(1), _card(weekly=3))
    assert check == CapacityCheck(
        demand_person_hours=Decimal("4"), capacity_person_hours=Decimal("3"), fits=False, max_fitting_pct=75
    )
    assert capacity_check(pattern, _employees(1), _card()).fits is True
    assert capacity_check(pattern, _employees(1), _card()).max_fitting_pct == 100


def test_capacity_uses_days_times_daily_limit_when_lower_than_weekly():
    # 42h semanais, mas 7 − 2 = 5 dias × 8h = 40h por pessoa
    check = capacity_check([_p("L1", 1)], _employees(3), _card())
    assert check.capacity_person_hours == Decimal("120")


def test_capacity_floor_is_50_when_not_even_half_fits():
    check = capacity_check([_p("L1", 100)], _employees(1), _card(weekly=1, daily=1))
    assert (check.fits, check.max_fitting_pct) == (False, 50)


def test_capacity_check_needs_the_card_primitives():
    card = _card().model_copy(update={"rules": _card().rules[:2]})  # sem repouso_semanal
    with pytest.raises(ValueError, match="repouso_semanal"):
        capacity_check([_p("L1", 1)], _employees(1), card)


# --- o fato medido do exemplo (plano, seção 3) ----------------------------------------------------------------


def test_demo_file_needs_2777_person_hours_against_2400():
    # O plano (seção 3) cita 2.776: a conta de lá fez ceil(duração / 30 min) por turno. Por faixa alinhada, como a
    # demanda é materializada, os 2 turnos 12:40–22:10 tocam 20 faixas (12:30 e 22:00 parciais), não 19: 2.777.
    # Os picos de lá (14, 13, 13) não se reproduzem: às 14:00–15:00 os turnos 08:00–15:20 e 14:00–22:00 se somam.
    schedule = _demo_schedule()
    drafts = [StoreDraft(s["id"], s["name"]) for s in json.loads((DEMO / "lojas.json").read_text(encoding="utf-8"))]
    stores = infer_store_hours(schedule.shifts, drafts)
    assert [(s.id, s.opens, s.closes) for s in stores] == [
        ("L1", time(8), time(22)),
        ("L2", time(8), time(23, 30)),
        ("L3", time(8), time(22, 30)),
    ]
    pattern = infer_demand_pattern(schedule, stores)
    peaks = Counter()
    for p in pattern:
        peaks[p.store_id] = max(peaks[p.store_id], p.required)
    assert dict(peaks) == {"L1": 20, "L2": 20, "L3": 19}

    employees = _demo_employees()
    assert len(employees) == 60
    check = capacity_check(pattern, employees, load_rule_card(RULES, MONDAY))
    assert check.demand_person_hours == Decimal("2777")
    assert check.capacity_person_hours == Decimal("2400")
    assert check.fits is False
    pct = check.max_fitting_pct
    assert pct == 80  # 2.400 / 2.777 = 86,4% na conta linear; o arredondamento para cima por faixa leva a 80%
    fitting = sum(p.required for p in scale_pattern(pattern, dict.fromkeys(("L1", "L2", "L3"), pct))) / 2
    over = sum(p.required for p in scale_pattern(pattern, dict.fromkeys(("L1", "L2", "L3"), pct + 1))) / 2
    assert fitting <= 2400 < over

    week = demand_for_week(pattern, MONDAY)
    assert len(week) == len(pattern)
    assert sum(s.required for s in week) / 2 == 2777
