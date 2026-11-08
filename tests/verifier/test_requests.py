"""Restrições duras pedidas pelo gestor (camada `execucao`, C6, D4). O verificador as confere sem o solver (RF-02)."""

from datetime import date, datetime, time, timedelta

import pytest

from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import Schedule, Shift
from escalista.verifier import CHECKS, verify

MONDAY = date(2027, 1, 11)
TUESDAY = date(2027, 1, 12)


def _unavailable(n: int = 1, employee: object = "P001", day: object = "2027-01-12", **window) -> Rule:
    return Rule(
        id=f"exec-indisp-{n}",
        kind="indisponibilidade",
        layer=RuleLayer.EXECUCAO,
        status=RuleStatus.PEDIDO,
        params={"employee_id": employee, "day": day, "start": window.get("start"), "end": window.get("end")},
        source="pedido do gestor: Ana não pode na terça",
    )


def _max_hours(hours: object, n: int = 1, employee: object = "P001") -> Rule:
    return Rule(
        id=f"exec-maxh-{n}",
        kind="jornada_semanal_max_pessoa",
        layer=RuleLayer.EXECUCAO,
        status=RuleStatus.PEDIDO,
        params={"employee_id": employee, "hours": hours},
        source="pedido do gestor: Bruno no máximo 30h",
    )


def _card(*rules: Rule) -> RuleCard:
    return RuleCard(reference_date=MONDAY, rules=list(rules))


def _shift(day: int, start: str, hours: float, employee: str = "P001") -> Shift:
    begin = datetime.combine(MONDAY + timedelta(days=day), time.fromisoformat(start))
    return Shift(employee_id=employee, store_id="L1", start=begin, end=begin + timedelta(hours=hours))


def _schedule(*shifts: Shift) -> Schedule:
    return Schedule(week_start=MONDAY, shifts=list(shifts))


def test_both_request_checks_are_registered():
    assert "indisponibilidade" in CHECKS
    assert "jornada_semanal_max_pessoa" in CHECKS


# --- indisponibilidade -------------------------------------------------------------------------------------------


def test_planted_shift_on_unavailable_day_is_caught():
    rule = _unavailable()
    schedule = _schedule(_shift(0, "08:00", 8), _shift(1, "08:00", 8), _shift(1, "08:00", 8, employee="P002"))

    report = verify(schedule, _card(rule))

    assert report.total == 1
    v = report.violations[0]
    assert (v.rule_id, v.kind, v.employee_id, v.day) == ("exec-indisp-1", "indisponibilidade", "P001", TUESDAY)
    assert v.source == "pedido do gestor: Ana não pode na terça"
    assert "12/01 08:00" in v.detail and "dia inteiro" in v.detail
    assert "Ana" not in v.detail


def test_overnight_shift_from_previous_day_entering_unavailable_day_violates():
    schedule = _schedule(_shift(0, "22:00", 8))  # seg 22h a ter 06h

    report = verify(schedule, _card(_unavailable()))

    assert [(v.employee_id, v.day) for v in report.violations] == [("P001", TUESDAY)]


def test_overnight_shift_ending_exactly_at_midnight_does_not_touch_next_day():
    schedule = _schedule(_shift(0, "16:00", 8))  # seg 16h a ter 00h: interseção de duração zero

    assert verify(schedule, _card(_unavailable())).total == 0


def test_overnight_shift_leaving_unavailable_day_violates():
    schedule = _schedule(_shift(1, "22:00", 8))  # ter 22h a qua 06h

    assert verify(schedule, _card(_unavailable())).total == 1


def test_partial_window_only_flags_intersecting_shifts():
    card = _card(_unavailable(start="14:00", end="18:00"))
    morning = _schedule(_shift(1, "06:00", 8))  # 06h a 14h: encosta na janela, não cruza
    evening = _schedule(_shift(1, "18:00", 6))  # 18h a 00h: começa quando a janela termina
    afternoon = _schedule(_shift(1, "10:00", 6))  # 10h a 16h: cruza

    assert verify(morning, card).total == 0
    assert verify(evening, card).total == 0
    report = verify(afternoon, card)
    assert report.total == 1
    assert "14:00" in report.violations[0].detail and "18:00" in report.violations[0].detail


def test_window_with_only_start_runs_to_end_of_day():
    card = _card(_unavailable(start="20:00"))

    assert verify(_schedule(_shift(1, "12:00", 8)), card).total == 0  # termina 20h
    assert verify(_schedule(_shift(1, "22:00", 4)), card).total == 1


def test_window_with_only_end_starts_at_midnight():
    card = _card(_unavailable(end="06:00"))

    assert verify(_schedule(_shift(1, "06:00", 8)), card).total == 0  # começa quando a janela termina
    assert verify(_schedule(_shift(0, "22:00", 4)), card).total == 1  # seg 22h a ter 02h: cruza ter 00h a 02h


def test_two_conflicting_shifts_same_rule_yield_one_violation():
    schedule = _schedule(_shift(1, "06:00", 4), _shift(1, "14:00", 4))

    report = verify(schedule, _card(_unavailable()))

    assert report.total == 1
    assert "06:00" in report.violations[0].detail and "14:00" in report.violations[0].detail


def test_window_end_24h_is_accepted():
    card = _card(_unavailable(start="18:00", end="24:00"))

    assert verify(_schedule(_shift(1, "20:00", 2)), card).total == 1
    assert verify(_schedule(_shift(2, "00:00", 2)), card).total == 0


# --- jornada_semanal_max_pessoa ----------------------------------------------------------------------------------


def test_planted_weekly_hours_per_person_is_caught_and_limit_is_inclusive():
    card = _card(_max_hours(30))
    over = _schedule(*[_shift(d, "08:00", 8) for d in range(4)])  # 32h
    exact = _schedule(*[_shift(d, "08:00", 6) for d in range(5)])  # 30h
    other = _schedule(*[_shift(d, "08:00", 8, employee="P002") for d in range(5)])  # 40h, outra pessoa

    report = verify(over, card)

    assert report.total == 1
    v = report.violations[0]
    assert (v.rule_id, v.kind, v.employee_id, v.day) == ("exec-maxh-1", "jornada_semanal_max_pessoa", "P001", None)
    assert v.source == "pedido do gestor: Bruno no máximo 30h"
    assert "32,0h" in v.detail and "30h" in v.detail
    assert "Bruno" not in v.detail
    assert verify(exact, card).total == 0
    assert verify(other, card).total == 0


def test_weekly_hours_per_person_float_limit_and_week_convention():
    card = _card(_max_hours(7.5))
    # Turno de domingo que vira a noite conta inteiro na semana; turno da semana seguinte não conta.
    schedule = _schedule(_shift(6, "20:00", 8), _shift(7, "08:00", 8))

    report = verify(schedule, card)

    assert report.total == 1
    assert "8,0h" in report.violations[0].detail and "7,5h" in report.violations[0].detail


def test_weekly_hours_per_person_without_shifts_is_not_violation():
    assert verify(_schedule(_shift(0, "08:00", 8, employee="P002")), _card(_max_hours(0))).total == 0


# --- regra de pedido malformada ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rule",
    [
        _unavailable(employee=None),
        _unavailable(employee=""),
        _unavailable(day="12/01/2027"),
        _unavailable(day=None),
        _unavailable(start="25:00"),
        _unavailable(start="18:00", end="14:00"),
        _unavailable(start="manhã"),
        _max_hours("trinta"),
        _max_hours(None),
        _max_hours(-1),
        _max_hours(True),
        _max_hours(float("nan")),
        _max_hours(30, employee=None),
    ],
)
def test_malformed_request_rule_is_reported_not_raised(rule):
    report = verify(_schedule(_shift(1, "08:00", 8)), _card(rule))

    assert report.total == 1
    v = report.violations[0]
    assert (v.rule_id, v.kind) == (rule.id, rule.kind)
    assert v.detail.startswith("regra de pedido malformada: ")
    assert v.source == rule.source


def test_malformed_rule_keeps_employee_id_when_it_is_valid():
    v = verify(_schedule(), _card(_unavailable(day="amanhã"))).violations[0]

    assert v.employee_id == "P001" and v.day is None


def test_missing_params_are_malformed():
    rule = Rule(
        id="exec-maxh-9",
        kind="jornada_semanal_max_pessoa",
        layer=RuleLayer.EXECUCAO,
        status=RuleStatus.PEDIDO,
        params={},
        source="pedido do gestor: x",
    )

    report = verify(_schedule(), _card(rule))

    assert report.total == 1 and report.violations[0].detail.startswith("regra de pedido malformada: ")
