"""Validação pura das linhas do CSV da escala (plano da C5, D3; RF-04). As linhas cruas são montadas aqui,
sem passar pela borda `ingest/`."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from escalista.domain.schedule import Employee, Store
from escalista.rules.validation import RawRow, validate_schedule_rows

HEADER = "loja_id,pessoa_id,nome,data,inicio,fim"
STORES = [
    Store(id="L1", name="Loja Sintética A", opens=time(8), closes=time(22)),
    Store(id="L2", name="Loja Sintética B", opens=time(8), closes=time(22)),
]
EMPLOYEES = [
    Employee(
        id=pid,
        name=f"Pessoa {pid} (sintético)",
        store_id=store,
        job="Atendente",
        hourly_wage=Decimal("12.00"),
        contract_hours=44,
        sex="F",
    )
    for pid, store in (("P001", "L1"), ("P002", "L1"), ("P003", "L2"))
]
MONDAY = date(2027, 1, 11)


def _validate(text: str, week_start: date | None = MONDAY):
    """Linha física 1-based; `#` é comentário; a 1ª linha não comentada é o cabeçalho."""
    lines = [(n, line) for n, line in enumerate(text.strip("\n").split("\n"), start=1)]
    lines = [(n, line) for n, line in lines if line.strip() and not line.startswith("#")]
    (hn, hline), *rest = lines
    header = RawRow(hn, tuple(hline.split(",")))
    rows = [RawRow(n, tuple(line.split(","))) for n, line in rest]
    return validate_schedule_rows("teste.csv", header, rows, employees=EMPLOYEES, stores=STORES, week_start=week_start)


def _issues(result) -> list[tuple[int, str | None]]:
    return [(i.line, i.field) for i in result.summary.issues]


def test_missing_column_issue_at_line_1():
    result = _validate("loja_id,pessoa_id,nome,data,inicio\nL1,P001,Ana,2027-01-11,08:00\n")

    assert _issues(result) == [(1, "fim")]
    assert "fim" in result.summary.issues[0].reason
    assert result.summary.ok is False
    assert result.schedule is None


def test_bad_time_format_issue_with_line():
    result = _validate(f"# marca\n{HEADER}\nL1,P001,Ana,2027-01-11,08:00,15:00\nL1,P002,Bia,2027-01-12,25:70,17:00\n")

    assert _issues(result) == [(4, "inicio")]
    assert "25:70" in result.summary.issues[0].reason
    assert [s.employee_id for s in result.schedule.shifts] == ["P001"]  # a linha com problema não entra


def test_unknown_employee_issue():
    result = _validate(f"{HEADER}\nL1,P999,Zé,2027-01-11,08:00,15:00\nL1,P001,Ana,2027-01-11,08:00,15:00\n")

    assert _issues(result) == [(2, "pessoa_id")]
    assert "P999" in result.summary.issues[0].reason


def test_store_unknown_or_different_from_roster_is_issue():
    result = _validate(f"{HEADER}\nL9,P001,Ana,2027-01-11,08:00,15:00\nL2,P002,Bia,2027-01-11,08:00,15:00\n")

    assert _issues(result) == [(2, "loja_id"), (3, "loja_id")]
    assert result.schedule.shifts == []


def test_empty_required_field_issue():
    result = _validate(f"{HEADER}\nL1,P001,Ana,2027-01-11,09:00,\n")

    assert _issues(result) == [(2, "fim")]
    assert result.summary.issues[0].reason == "campo obrigatório vazio: fim"


def test_invalid_date_issue():
    result = _validate(f"{HEADER}\nL1,P001,Ana,2027-13-01,09:00,17:00\nL1,P002,Bia,11/01/2027,09:00,17:00\n")

    assert _issues(result) == [(2, "data"), (3, "data")]


def test_wrong_number_of_fields_issue():
    result = _validate(f"{HEADER}\nL1,P001,Ana,Souza,2027-01-11,09:00,17:00\n")

    assert _issues(result) == [(2, None)]


def test_overlapping_shifts_issue():
    result = _validate(
        f"{HEADER}\nL1,P001,Ana,2027-01-11,08:00,15:00\nL1,P001,Ana,2027-01-11,10:00,16:00\n"
        "L1,P001,Ana,2027-01-12,08:00,15:00\n"
    )

    assert _issues(result) == [(3, "inicio")]
    assert result.summary.issues[0].reason == "turno sobreposto ao da linha 2, mesma pessoa e mesma data"
    assert len(result.schedule.shifts) == 2  # o 1º turno fica; o sobreposto sai


def test_overnight_overlap_with_next_day_is_issue():
    result = _validate(f"{HEADER}\nL1,P001,Ana,2027-01-13,18:00,02:00\nL1,P001,Ana,2027-01-14,01:00,08:00\n")

    assert _issues(result) == [(3, "inicio")]


def test_date_outside_week_issue():
    result = _validate(f"{HEADER}\nL1,P001,Ana,2027-01-25,09:00,17:00\nL1,P002,Bia,2027-01-17,09:00,17:00\n")

    assert _issues(result) == [(2, "data")]
    assert result.summary.issues[0].reason == "data 2027-01-25 fora da semana de 11/01 a 17/01/2027"


def test_week_is_inferred_from_most_frequent_date():
    result = _validate(
        f"{HEADER}\nL1,P001,Ana,2027-01-13,09:00,17:00\nL1,P002,Bia,2027-01-13,09:00,17:00\n"
        "L2,P003,Caio,2027-01-25,09:00,17:00\n",
        week_start=None,
    )

    assert result.summary.week_start == MONDAY
    assert result.schedule.week_start == MONDAY
    assert _issues(result) == [(4, "data")]


def test_overnight_shift_ends_next_day():
    result = _validate(f"{HEADER}\nL1,P001,Ana,2027-01-13,16:00,00:00\nL1,P002,Bia,2027-01-17,22:00,06:00\n")

    assert result.summary.ok is True
    first, second = result.schedule.shifts
    assert (first.start, first.end) == (datetime(2027, 1, 13, 16), datetime(2027, 1, 14, 0))
    assert second.end == datetime(2027, 1, 18, 6)  # domingo que vira a noite continua na semana
    assert result.summary.total_hours == Decimal("16.00")


def test_equal_start_and_end_is_issue():
    result = _validate(f"{HEADER}\nL1,P001,Ana,2027-01-13,09:00,09:00\n")

    assert _issues(result) == [(2, "fim")]


def test_summary_counts_valid_shifts():
    result = _validate(
        f"{HEADER}\nL1,P001,Ana,2027-01-11,08:00,15:20\nL1,P002,Bia,2027-01-11,08:00,16:00\n"
        "L2,P003,Caio,2027-01-12,08:00,16:00\n"
    )

    s = result.summary
    assert (s.file_name, s.rows, s.employees, s.stores, s.ok) == ("teste.csv", 3, 3, 2, True)
    assert s.total_hours == Decimal("23.33")


def test_week_start_must_be_monday():
    with pytest.raises(ValueError):
        _validate(f"{HEADER}\nL1,P001,Ana,2027-01-13,09:00,17:00\n", week_start=date(2027, 1, 12))
