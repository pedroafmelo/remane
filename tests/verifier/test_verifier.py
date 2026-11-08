"""Verificador independente (plano da C5, D4; RF-02, RN-04). Não usa o solver: confere a escala contra o cartão."""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import DemandSlot, Schedule, Shift
from escalista.ingest.csv_schedule import read_schedule_csv
from escalista.ingest.demo_network import load_demo_network
from escalista.rules.loader import load_rule_card
from escalista.verifier import coverage_gaps, verify

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "data" / "demo"
RULES = ROOT / "data" / "regras"
MONDAY = date(2027, 1, 11)


def _rule(kind: str, source: str = "fonte de teste", **params) -> Rule:
    return Rule(id=kind, kind=kind, layer=RuleLayer.LEI, params=params, status=RuleStatus.CONFERIDA, source=source)


def _card(*rules: Rule) -> RuleCard:
    return RuleCard(reference_date=MONDAY, rules=list(rules))


def _shift(day: int, start: str, hours: float, employee: str = "P001", store: str = "L1") -> Shift:
    begin = datetime.combine(MONDAY + timedelta(days=day), time.fromisoformat(start))
    return Shift(employee_id=employee, store_id=store, start=begin, end=begin + timedelta(hours=hours))


def _schedule(*shifts: Shift) -> Schedule:
    return Schedule(week_start=MONDAY, shifts=list(shifts))


def test_weekly_hours_violation_cites_source():
    card = _card(_rule("jornada_semanal_max", source="art. 7º, XIII CF", hours=42))
    over = _schedule(*[_shift(d, "08:00", 8) for d in range(5)], _shift(5, "08:00", 3))  # 43h
    exact = _schedule(*[_shift(d, "08:00", 8) for d in range(5)], _shift(5, "08:00", 2))  # 42h

    report = verify(over, card)

    assert report.total == 1
    v = report.violations[0]
    assert (v.rule_id, v.kind, v.employee_id, v.day) == ("jornada_semanal_max", "jornada_semanal_max", "P001", None)
    assert v.source == "art. 7º, XIII CF"
    assert "43,0h" in v.detail and "42h" in v.detail
    assert verify(exact, card).total == 0


def test_daily_hours_violation():
    card = _card(_rule("jornada_diaria_max", hours=8))
    schedule = _schedule(
        _shift(0, "08:00", 9),  # viola
        _shift(1, "08:00", 8),  # no limite
        _shift(2, "08:00", 4),
        _shift(2, "14:00", 5),  # 9h somadas no dia: viola
        _shift(0, "08:00", 8, employee="P002"),
    )

    report = verify(schedule, card)

    assert [(v.employee_id, v.day) for v in report.violations] == [("P001", MONDAY), ("P001", date(2027, 1, 13))]
    assert "9,0h" in report.violations[0].detail and "8h" in report.violations[0].detail


def test_rest_between_shifts_10h_violates_11h_ok():
    card = _card(_rule("interjornada_min", hours=11))
    schedule = _schedule(
        _shift(0, "08:00", 8),  # seg 16h
        _shift(1, "02:00", 6),  # ter 02h: 10h de descanso, viola
        _shift(0, "08:00", 8, employee="P002"),  # seg 16h
        _shift(1, "03:00", 6, employee="P002"),  # ter 03h: 11h, ok
    )

    report = verify(schedule, card)

    assert report.total == 1
    v = report.violations[0]
    assert (v.employee_id, v.day) == ("P001", date(2027, 1, 12))
    assert "10,0h" in v.detail and "11h" in v.detail


def test_rest_after_overnight_shift_counts_from_its_real_end():
    card = _card(_rule("interjornada_min", hours=11), _rule("jornada_diaria_max", hours=8))
    schedule = _schedule(
        _shift(2, "16:00", 8),  # qua 16h a qui 00h: conta inteiro na quarta
        _shift(3, "08:00", 8),  # qui 08h: 8h de descanso, viola a interjornada
    )

    report = verify(schedule, card)

    assert [(v.rule_id, v.day) for v in report.violations] == [("interjornada_min", date(2027, 1, 14))]
    assert "8,0h" in report.violations[0].detail


def test_two_weekly_rest_days():
    card = _card(_rule("repouso_semanal", days=2))
    one_off = _schedule(*[_shift(d, "08:00", 6) for d in range(6)])
    two_off = _schedule(*[_shift(d, "08:00", 6, employee="P002") for d in range(5)])
    overnight_sunday = _schedule(
        *[_shift(d, "08:00", 6, employee="P003") for d in range(4)], _shift(5, "22:00", 4, employee="P003")
    )

    report = verify(one_off, card)

    assert [(v.rule_id, v.employee_id, v.day) for v in report.violations] == [("repouso_semanal", "P001", None)]
    assert "1 dia" in report.violations[0].detail and "2" in report.violations[0].detail
    assert verify(two_off, card).total == 0
    assert verify(overnight_sunday, card).total == 0  # sáb 22h a dom 02h não tira a folga de domingo


def test_coverage_metric_not_violation():
    card = _card(
        _rule("jornada_semanal_max", hours=42),
        _rule("jornada_diaria_max", hours=8),
        _rule("interjornada_min", hours=11),
        _rule("repouso_semanal", days=2),
    )
    schedule = _schedule(_shift(0, "08:00", 1))  # cobre 08h00 e 08h30 na L1
    demand = [
        DemandSlot(store_id="L1", day=MONDAY, start=time(8, 0), required=2),
        DemandSlot(store_id="L1", day=MONDAY, start=time(8, 30), required=1),
        DemandSlot(store_id="L1", day=MONDAY, start=time(9, 0), required=1),
        DemandSlot(store_id="L2", day=MONDAY, start=time(8, 0), required=1),
    ]

    gaps = coverage_gaps(schedule, demand)

    assert [(g.store_id, g.start, g.required) for g in gaps] == [
        ("L1", time(8, 0), 1),
        ("L1", time(9, 0), 1),
        ("L2", time(8, 0), 1),
    ]
    assert verify(schedule, card).total == 0  # falta de cobertura não entra no relatório de violações


def test_missing_rule_is_not_checked():
    schedule = _schedule(*[_shift(d, "08:00", 10) for d in range(7)])

    assert verify(schedule, _card(_rule("adicional_hora_extra", percent=60))).total == 0


@pytest.fixture(scope="module")
def demo_card() -> RuleCard:
    return load_rule_card(RULES, date(2027, 1, 11))


def _read_demo(name: str) -> Schedule:
    stores, employees, _ = load_demo_network(DEMO)
    result = read_schedule_csv(name, (DEMO / name).read_bytes(), employees=employees, stores=stores)
    assert result.schedule is not None and result.exception is None
    return result.schedule


def test_finds_all_planted_violations(demo_card):
    planted = json.loads((DEMO / "violacoes_plantadas.json").read_text(encoding="utf-8"))
    expected = {(p["rule_id"], p["employee_id"], date.fromisoformat(p["day"]) if p["day"] else None) for p in planted}

    report = verify(_read_demo("escala_violacoes.csv"), demo_card)
    found = [(v.rule_id, v.employee_id, v.day) for v in report.violations]

    assert len(found) == len(set(found))
    assert expected - set(found) == set(), "violações plantadas não detectadas"
    assert set(found) - expected == set(), "violações a mais (falsos positivos)"
    assert all(v.source for v in report.violations)


def test_current_schedule_has_violations_under_new_rules(demo_card):
    report = verify(_read_demo("escala_atual.csv"), demo_card)

    kinds = {v.kind for v in report.violations}
    assert {"jornada_semanal_max", "repouso_semanal", "jornada_diaria_max"} <= kinds
