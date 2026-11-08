"""Especificação do modelo: conferência em código, padrão e cartão com a camada `execucao` (C6, invariante 4)."""

from datetime import date, time

import pytest
from pydantic import ValidationError

from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.spec import (
    MaxWeeklyHoursConstraint,
    PreferredDayOffConstraint,
    PreferredWindowConstraint,
    SolveSpec,
    UnavailableConstraint,
)
from escalista.rules.spec import card_with_spec, default_spec, make_screen, validate_spec

WEEK = date(2027, 1, 11)  # segunda
IDS = {"P001", "P002", "P003"}
REQUEST = "A Ana (P001) não pode na terça de manhã, das 08:00 às 12:00.  O Bruno quer  no máximo 30 horas."
NOTES = ["P003 prefere folga na sexta", "P002 só de manhã"]


def lei(rule_id: str, **params) -> Rule:
    return Rule(
        id=rule_id,
        kind=rule_id,
        layer=RuleLayer.LEI,
        params=params,
        status=RuleStatus.INTERPRETACAO,
        source=f"LEI-{rule_id}",
    )


def card(weekly: int = 42) -> RuleCard:
    rules = [
        lei("jornada_semanal_max", hours=weekly),
        lei("jornada_diaria_max", hours=8),
        lei("interjornada_min", hours=11),
        lei("repouso_semanal", days=2),
    ]
    return RuleCard(reference_date=WEEK, rules=rules, provisional=["jornada_semanal_max"])


def check(*constraints, weekly: int = 42, sources: list[str] | None = None):
    spec = SolveSpec(shortfall_weight=200, constraints=list(constraints))
    return validate_spec(
        spec,
        employee_ids=IDS,
        week_start=WEEK,
        card=card(weekly),
        evidence_sources=[REQUEST, *NOTES] if sources is None else sources,
    )


def maxh(hours: int, employee: str = "P002", evidence: str = "no máximo 30 horas") -> MaxWeeklyHoursConstraint:
    return MaxWeeklyHoursConstraint(employee_id=employee, hours=hours, evidence=evidence)


def unav(
    day: date = date(2027, 1, 12),
    employee: str = "P001",
    start: time | None = time(8),
    end: time | None = time(12),
    evidence: str = "não pode na terça de manhã",
) -> UnavailableConstraint:
    return UnavailableConstraint(employee_id=employee, day=day, start=start, end=end, evidence=evidence)


# invariante 4: estrutural --------------------------------------------------------------------------------


def test_spec_has_no_field_for_card_rules():
    with pytest.raises(ValidationError):
        SolveSpec.model_validate({"jornada_semanal_max": 48})


# invariante 4: limite semanal só abaixo do cartão --------------------------------------------------------


@pytest.mark.parametrize("hours", [50, 42])
def test_max_weekly_hours_at_or_above_card_is_rejected(hours):
    spec, rejected = check(maxh(hours))
    assert spec.constraints == []
    assert len(rejected) == 1
    item, reason = rejected[0]
    assert "P002" in item and f"{hours}" in item
    assert "não pode afrouxar a lei/convenção" in reason and "42" in reason


def test_max_weekly_hours_below_card_is_accepted():
    spec, rejected = check(maxh(30))
    assert rejected == []
    assert spec.constraints == [maxh(30)]


def test_weights_are_kept():
    spec, _ = check(maxh(50))
    assert spec.shortfall_weight == 200 and spec.stability_weight == 0 and spec.preference_weight == 5


# conferência de ids, dias, horários e evidência ---------------------------------------------------------


def test_unknown_employee_is_rejected():
    spec, rejected = check(unav(employee="P999"))
    assert spec.constraints == []
    assert "P999" in rejected[0][0] and "não existe" in rejected[0][1]


@pytest.mark.parametrize("day", [date(2027, 1, 10), date(2027, 1, 18)])
def test_day_outside_week_is_rejected(day):
    spec, rejected = check(unav(day=day), PreferredDayOffConstraint(employee_id="P003", day=day, evidence="folga"))
    assert spec.constraints == []
    assert len(rejected) == 2
    assert all("fora da semana" in reason for _, reason in rejected)


@pytest.mark.parametrize("day", [date(2027, 1, 11), date(2027, 1, 17)])
def test_week_bounds_are_inclusive(day):
    spec, rejected = check(unav(day=day))
    assert rejected == [] and len(spec.constraints) == 1


def test_invented_evidence_is_rejected():
    spec, rejected = check(maxh(30, evidence="o Bruno pediu 30 horas"))
    assert spec.constraints == []
    assert "evidência" in rejected[0][1]


def test_blank_evidence_is_rejected():
    spec, rejected = check(maxh(30, evidence="   "))
    assert spec.constraints == [] and len(rejected) == 1


def test_evidence_ignores_case_and_spacing():
    spec, rejected = check(maxh(30, evidence="QUER no   máximo\n30 HORAS"))
    assert rejected == [] and len(spec.constraints) == 1


def test_evidence_may_come_from_notes():
    item = PreferredDayOffConstraint(employee_id="P003", day=date(2027, 1, 15), evidence="prefere folga na sexta")
    window = PreferredWindowConstraint(employee_id="P002", window="manha", evidence="só de manhã")
    spec, rejected = check(item, window)
    assert rejected == [] and spec.constraints == [item, window]


def test_evidence_without_sources_is_rejected():
    spec, rejected = check(maxh(30), sources=[])
    assert spec.constraints == [] and len(rejected) == 1


def test_start_after_end_is_rejected():
    spec, rejected = check(unav(start=time(12), end=time(8)), unav(start=time(8), end=time(8)))
    assert spec.constraints == []
    assert len(rejected) == 2 and all("início" in reason for _, reason in rejected)


def test_open_interval_is_accepted():
    spec, rejected = check(unav(start=time(14), end=None), unav(start=None, end=None, day=date(2027, 1, 13)))
    assert rejected == [] and len(spec.constraints) == 2


def test_duplicates_collapse_to_one():
    spec, rejected = check(maxh(30), maxh(30, evidence="no máximo 30"), unav(), unav())
    assert rejected == []
    assert spec.constraints == [maxh(30), unav()]


def test_only_bad_items_leave_the_spec():
    good = maxh(30)
    spec, rejected = check(unav(employee="P999"), good, maxh(48, employee="P001"))
    assert spec.constraints == [good]
    assert len(rejected) == 2


def test_make_screen_is_validate_spec_with_bound_context():
    screen = make_screen(employee_ids=IDS, week_start=WEEK, card=card(), evidence_sources=[REQUEST])
    spec = SolveSpec(constraints=[maxh(30), maxh(50)])
    assert screen(spec) == validate_spec(
        spec, employee_ids=IDS, week_start=WEEK, card=card(), evidence_sources=[REQUEST]
    )


# default_spec ----------------------------------------------------------------------------------------


def test_default_spec_is_c5_behaviour():
    spec = default_spec()
    assert spec == SolveSpec()
    assert (spec.shortfall_weight, spec.stability_weight, spec.preference_weight) == (100, 0, 5)
    assert spec.constraints == []


def test_default_spec_with_continuity_values_stability():
    spec = default_spec(continuity=True)
    assert spec.stability_weight == 10
    assert spec.model_copy(update={"stability_weight": 0}) == SolveSpec()


# card_with_spec ------------------------------------------------------------------------------------------


def test_card_with_spec_only_appends_execution_rules():
    original = card()
    before = original.model_copy(deep=True)
    spec = SolveSpec(
        constraints=[
            unav(),
            maxh(30),
            PreferredDayOffConstraint(employee_id="P003", day=date(2027, 1, 15), evidence="prefere folga na sexta"),
            PreferredWindowConstraint(employee_id="P002", window="manha", evidence="só de manhã"),
            unav(day=date(2027, 1, 14), employee="P003", start=None, end=None, evidence="P003"),
            maxh(20, employee="P001", evidence="Ana"),
        ]
    )
    new = card_with_spec(original, spec)

    assert original == before  # não mexe no cartão recebido
    assert new is not original
    assert new.rules[: len(original.rules)] == original.rules
    assert all(rule in new.rules for rule in original.rules)  # subconjunto idêntico
    assert new.reference_date == original.reference_date
    assert new.provisional == original.provisional and new.exceptions == original.exceptions

    added = new.rules[len(original.rules) :]
    assert added == [
        Rule(
            id="exec-indisp-1",
            kind="indisponibilidade",
            layer=RuleLayer.EXECUCAO,
            status=RuleStatus.PEDIDO,
            params={"employee_id": "P001", "day": "2027-01-12", "start": "08:00", "end": "12:00"},
            source="pedido do gestor: não pode na terça de manhã",
        ),
        Rule(
            id="exec-maxh-1",
            kind="jornada_semanal_max_pessoa",
            layer=RuleLayer.EXECUCAO,
            status=RuleStatus.PEDIDO,
            params={"employee_id": "P002", "hours": 30},
            source="pedido do gestor: no máximo 30 horas",
        ),
        Rule(
            id="exec-indisp-2",
            kind="indisponibilidade",
            layer=RuleLayer.EXECUCAO,
            status=RuleStatus.PEDIDO,
            params={"employee_id": "P003", "day": "2027-01-14", "start": None, "end": None},
            source="pedido do gestor: P003",
        ),
        Rule(
            id="exec-maxh-2",
            kind="jornada_semanal_max_pessoa",
            layer=RuleLayer.EXECUCAO,
            status=RuleStatus.PEDIDO,
            params={"employee_id": "P001", "hours": 20},
            source="pedido do gestor: Ana",
        ),
    ]
    assert isinstance(added[1].params["hours"], int)


def test_card_with_default_spec_is_equal_card():
    original = card()
    new = card_with_spec(original, default_spec())
    assert new == original and new is not original
    new.provisional.append("x")
    assert original.provisional == ["jornada_semanal_max"]


def test_card_with_spec_keeps_card_limit_untouched():
    new = card_with_spec(card(42), SolveSpec(constraints=[maxh(30)]))
    weekly = [r for r in new.rules if r.kind == "jornada_semanal_max"]
    assert weekly == [lei("jornada_semanal_max", hours=42)]


def test_card_without_weekly_limit_accepts_any_per_person_limit():
    no_limit = card().model_copy(update={"rules": [r for r in card().rules if r.kind != "jornada_semanal_max"]})
    spec, rejected = validate_spec(
        SolveSpec(constraints=[maxh(30)]), employee_ids=IDS, week_start=WEEK, card=no_limit, evidence_sources=[REQUEST]
    )
    assert rejected == [] and len(spec.constraints) == 1
