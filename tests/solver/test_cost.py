"""Função de custo pura e `Comparison` antes e depois (plano da C5, frente A, testes 8 a 10)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift
from escalista.solver.cost import compare, compare_schedules, compute_metrics

MONDAY = date(2027, 1, 11)


def rule(kind: str, layer: RuleLayer = RuleLayer.LEI, **params) -> Rule:
    status = RuleStatus.FICTICIA if layer is not RuleLayer.LEI else RuleStatus.INTERPRETACAO
    return Rule(id=kind, kind=kind, layer=layer, params=params, status=status, source=f"fonte-{kind}")


def card(premium: int | None = 60, weekly: int = 42, daily: int = 8) -> RuleCard:
    rules = [rule("jornada_semanal_max", hours=weekly), rule("jornada_diaria_max", hours=daily)]
    if premium is not None:
        rules.append(rule("adicional_hora_extra", RuleLayer.CONVENCAO, percent=premium))
    return RuleCard(reference_date=MONDAY, rules=rules)


def emp(id_: str = "e1", wage: str = "10", store: str = "s1") -> Employee:
    return Employee(
        id=id_, name=id_, store_id=store, job="caixa", hourly_wage=Decimal(wage), contract_hours=42, sex="F"
    )


def shift(
    day_offset: int, start_h: int, hours: float, emp_id: str = "e1", store: str = "s1", start_m: int = 0
) -> Shift:
    start = datetime.combine(MONDAY + timedelta(days=day_offset), time(start_h, start_m))
    end = start + timedelta(hours=hours)
    return Shift(employee_id=emp_id, store_id=store, start=start, end=end)


def schedule(*shifts: Shift) -> Schedule:
    return Schedule(week_start=MONDAY, shifts=list(shifts))


def metrics(sched: Schedule, rc: RuleCard | None = None, employees=None, demand=None, violations: int = 0):
    return compute_metrics(sched, employees or [emp()], demand or [], rc or card(), violations)


# 8 ------------------------------------------------------------------------------------------------------


def test_cost_splits_regular_and_overtime():
    # Diário domina: 5 dias de 10h = 50h; excessos diários 5 × 2h = 10h; semanal 50 − 42 = 8h → HE = 10h.
    m = metrics(schedule(*(shift(d, 8, 10) for d in range(5))))
    assert m.overtime_hours == Decimal("10.00")
    assert m.regular_hours == Decimal("40.00")
    # 40h × 10 + 10h × 10 × 1,6 = 400 + 160
    assert m.overtime_cost == Decimal("160.00")
    assert m.total_cost == Decimal("560.00")

    # Semanal domina: 6 dias de 8h = 48h; nenhum excesso diário; semanal 48 − 42 = 6h → HE = 6h.
    m = metrics(schedule(*(shift(d, 8, 8) for d in range(6))))
    assert m.overtime_hours == Decimal("6.00")
    assert m.regular_hours == Decimal("42.00")
    assert m.total_cost == Decimal("516.00")  # 42 × 10 + 6 × 16

    # Os dois juntos, sem contar em dobro: 4 × 10h + 2 × 8h = 56h; diário 8h; semanal 14h → HE = 14h, não 22h.
    m = metrics(schedule(*(shift(d, 8, 10) for d in range(4)), shift(4, 8, 8), shift(5, 8, 8)))
    assert m.overtime_hours == Decimal("14.00")
    assert m.regular_hours == Decimal("42.00")

    # Hora extra é por pessoa: duas pessoas de 40h não somam 80h contra o limite semanal.
    two = [emp("e1"), emp("e2")]
    m = metrics(schedule(*(shift(d, 8, 8, e) for d in range(5) for e in ("e1", "e2"))), employees=two)
    assert m.overtime_hours == Decimal("0.00") and m.regular_hours == Decimal("80.00")
    assert m.total_cost == Decimal("800.00") and m.overtime_cost == Decimal("0.00")


def test_cost_uses_each_employee_wage_and_rounds_money_half_up():
    # 1h de 10,005 = 10,005 → 10,01 (ROUND_HALF_UP nos centavos, só no total)
    m = metrics(schedule(shift(0, 8, 1)), employees=[emp(wage="10.005")])
    assert m.total_cost == Decimal("10.01")
    assert m.total_cost.as_tuple().exponent == -2


# 9 ------------------------------------------------------------------------------------------------------


def test_cost_uses_convention_overtime_premium_else_law_minimum():
    one_day_10h = schedule(shift(0, 8, 10))  # 8h normais + 2h de HE

    with_convention = metrics(one_day_10h, card(premium=60))
    assert with_convention.overtime_cost == Decimal("32.00")  # 2 × 10 × 1,6
    assert with_convention.total_cost == Decimal("112.00")

    without_rule = metrics(one_day_10h, card(premium=None))
    assert without_rule.overtime_cost == Decimal("30.00")  # 2 × 10 × 1,5 (mínimo da lei)
    assert without_rule.total_cost == Decimal("110.00")


# 10 -----------------------------------------------------------------------------------------------------


def test_comparison_same_function_before_and_after():
    employees = [emp("e1"), emp("e2")]
    demand = [DemandSlot(store_id="s1", day=MONDAY, start=time(8, 0), required=1)]
    before = schedule(*(shift(d, 8, 10, "e1") for d in range(5)))  # 50h, HE 10h
    after = schedule(*(shift(d, 8, 8, "e1") for d in range(5)), shift(0, 8, 2, "e2"))  # 42h, sem HE
    rc = card()

    result = compare_schedules(before, after, employees, demand, rc, before_violations=7, after_violations=0)

    m_before = compute_metrics(before, employees, demand, rc, 7)
    m_after = compute_metrics(after, employees, demand, rc, 0)
    assert result.before == m_before and result.after == m_after
    assert result == compare(m_before, m_after)
    assert result.savings == Decimal("140.00")  # 560 − (42 × 10)
    assert result.overtime_hours_avoided == Decimal("10.00")
    assert result.violations_avoided == 7
    assert m_before.violations == 7 and m_after.violations == 0


def test_comparison_can_be_negative_when_after_is_worse():
    a = metrics(schedule(shift(0, 8, 8)))
    b = metrics(schedule(shift(0, 8, 10)), violations=1)
    result = compare(a, b)
    assert result.savings == Decimal("-32.00")
    assert result.overtime_hours_avoided == Decimal("-2.00")
    assert result.violations_avoided == -1


# Cobertura -----------------------------------------------------------------------------------------------


def slot(h: int, m: int = 0, required: int = 1, store: str = "s1", day: date = MONDAY) -> DemandSlot:
    return DemandSlot(store_id=store, day=day, start=time(h, m), required=required)


def test_coverage_counts_people_of_the_store_working_the_whole_slot():
    employees = [emp("e1"), emp("e2"), emp("e3", store="s2")]
    sched = schedule(
        shift(0, 8, 2, "e1"),  # 08:00-10:00
        shift(0, 9, 1, "e2", start_m=15),  # 09:15-10:15: não cobre 09:00-09:30 inteira
        shift(0, 8, 4, "e3", store="s2"),  # outra loja
    )
    demand = [
        slot(8, 0, required=2),  # e1 → 1 de 2
        slot(9, 0, required=1),  # e1 → 1 de 1
        slot(9, 30, required=1),  # e1 e e2 → min(1, 2) = 1
        slot(10, 0, required=1),  # ninguém inteiro (e2 sai 10:15) → 0
        slot(10, 0, required=0),  # demanda zero não pesa
    ]
    m = metrics(sched, employees=employees, demand=demand)
    assert m.uncovered_slots == 2  # 08:00 e 10:00
    assert m.coverage_pct == 60.0  # 3 de 5


def test_coverage_is_100_when_demand_is_empty():
    m = metrics(schedule(shift(0, 8, 8)), demand=[])
    assert m.coverage_pct == 100.0 and m.uncovered_slots == 0


# Turno que vira a noite ----------------------------------------------------------------------------------


def test_overnight_shift_hours_count_on_start_day():
    # Seg 20:00 a ter 06:00 (10h) e ter 08:00 a 12:00 (4h). Contando no dia de início: seg 10h (2h de HE),
    # ter 4h. Se as horas fossem divididas por dia civil, seriam seg 4h e ter 10h (2h de HE no outro dia).
    m = metrics(schedule(shift(0, 20, 10), shift(1, 8, 4)))
    assert m.overtime_hours == Decimal("2.00")
    assert m.regular_hours == Decimal("12.00")

    # Seg 22:00 a ter 04:00 (6h) não gera HE no dia de início, mesmo somando com ter 08:00 a 12:00 (4h).
    m = metrics(schedule(shift(0, 22, 6), shift(1, 8, 4)))
    assert m.overtime_hours == Decimal("0.00")


def test_overnight_shift_covers_slots_after_midnight():
    tuesday = date(2027, 1, 12)
    # Seg 22:00 a ter 02:00 cobre ter 01:00, mas não ter 02:00.
    m = metrics(schedule(shift(0, 22, 4)), demand=[slot(1, 0, day=tuesday), slot(2, 0, day=tuesday)])
    assert m.uncovered_slots == 1
    assert m.coverage_pct == 50.0
