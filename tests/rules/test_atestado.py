"""Julgamento da comprovação em código (C7 A2b; contrato SAIDA-AC-05): `verdict` e `reasons` nunca vêm do modelo."""

from datetime import date

import pytest

from escalista.domain.tracking import AtestadoFields, AtestadoReading
from escalista.rules.atestado import judge

DAY = date(2027, 1, 13)


def fields(**overrides) -> AtestadoFields:
    base = {
        "legible": True,
        "issued_on": DAY,
        "start_on": DAY,
        "days": 1,
        "patient_matches": True,
        "has_crm": True,
    }
    return AtestadoFields(**(base | overrides))


@pytest.mark.parametrize(
    ("overrides", "verdict", "reasons"),
    [
        pytest.param({}, "valido", [], id="tudo-certo"),
        pytest.param({"issued_on": None, "start_on": None}, "inconsistente", ["sem_data"], id="sem-data"),
        pytest.param({"start_on": date(2027, 1, 12)}, "inconsistente", ["data_nao_bate"], id="dia-anterior"),
        pytest.param({"start_on": date(2027, 1, 14)}, "inconsistente", ["data_nao_bate"], id="dia-seguinte"),
        pytest.param({"has_crm": False}, "inconsistente", ["sem_crm"], id="sem-crm"),
        pytest.param({"has_crm": None}, "valido", [], id="crm-desconhecido"),
        pytest.param({"patient_matches": False}, "inconsistente", ["nome_nao_bate"], id="nome-nao-bate"),
        pytest.param({"patient_matches": None}, "valido", [], id="nome-desconhecido"),
        pytest.param(
            {"start_on": date(2027, 1, 1), "has_crm": False, "patient_matches": False},
            "inconsistente",
            ["data_nao_bate", "sem_crm", "nome_nao_bate"],
            id="ordem-fixa",
        ),
        pytest.param(
            {"issued_on": None, "start_on": None, "has_crm": False, "patient_matches": False},
            "inconsistente",
            ["sem_data", "sem_crm", "nome_nao_bate"],
            id="sem-data-nao-julga-a-janela",
        ),
    ],
)
def test_judge_table(overrides, verdict, reasons):
    reading = judge(fields(**overrides), expected_day=DAY)
    assert (reading.verdict, reading.reasons) == (verdict, reasons)


def test_illegible_keeps_fields_and_only_reports_ilegivel():
    raw = fields(legible=False, start_on=date(2026, 1, 1), has_crm=False, patient_matches=False)
    reading = judge(raw, expected_day=DAY)
    assert reading.verdict == "ilegivel"
    assert reading.reasons == ["ilegivel"]
    assert reading.model_dump(exclude={"verdict", "reasons"}) == raw.model_dump()


def test_returns_a_reading_with_the_same_fields():
    raw = fields(days=3)
    reading = judge(raw, expected_day=DAY)
    assert isinstance(reading, AtestadoReading)
    assert reading.model_dump(exclude={"verdict", "reasons"}) == raw.model_dump()


@pytest.mark.parametrize(
    ("start_on", "days", "expected_day", "inside"),
    [
        (date(2027, 1, 11), 3, date(2027, 1, 11), True),  # primeiro dia da janela
        (date(2027, 1, 11), 3, date(2027, 1, 13), True),  # último dia da janela
        (date(2027, 1, 11), 3, date(2027, 1, 14), False),  # um dia depois
        (date(2027, 1, 11), 3, date(2027, 1, 10), False),  # um dia antes
        (date(2027, 1, 13), None, date(2027, 1, 13), True),  # sem dias: 1 dia
        (date(2027, 1, 13), None, date(2027, 1, 14), False),
        (date(2026, 12, 30), 5, date(2027, 1, 3), True),  # vira o ano
    ],
)
def test_window_edges(start_on, days, expected_day, inside):
    reading = judge(fields(issued_on=None, start_on=start_on, days=days), expected_day=expected_day)
    assert ("data_nao_bate" not in reading.reasons) is inside


def test_window_starts_at_issue_date_when_start_is_missing():
    on_issue = judge(fields(issued_on=date(2027, 1, 12), start_on=None, days=2), expected_day=DAY)
    assert on_issue.verdict == "valido"
    late = judge(fields(issued_on=date(2027, 1, 11), start_on=None, days=2), expected_day=DAY)
    assert late.reasons == ["data_nao_bate"]


def test_start_date_wins_over_issue_date():
    reading = judge(fields(issued_on=date(2027, 1, 1), start_on=DAY, days=1), expected_day=DAY)
    assert reading.verdict == "valido"


def test_judge_is_pure():
    raw = fields(has_crm=False)
    assert judge(raw, expected_day=DAY) == judge(raw, expected_day=DAY)
    assert raw == fields(has_crm=False)
