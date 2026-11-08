"""Aplicação do `ColumnMapping` a todas as linhas (plano da C6, A1; invariantes 1, 2, 3 e 6).

As `RawTable` seguem o contrato da D2: todas as linhas do arquivo (comentário `#` e linhas vazias inclusive), células
já em texto. Os arquivos E2 são relidos aqui por um leitor de teste mínimo (csv da stdlib e openpyxl), sem `ingest/`.
"""

from __future__ import annotations

import csv
import io
import json
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

import openpyxl
import pytest

from escalista.domain.reading import CellRef, ColumnMapping, ColumnRef, DayColumn, RawTable, ShiftCode
from escalista.rules.mapping import MappedShift, MappingResult, apply_mapping, check_mapping, verify_evidence

E2 = Path(__file__).resolve().parents[2] / "data" / "demo" / "e2"
MONDAY = date(2027, 1, 11)


# --- leitor de teste (imita o contrato da D2) ---------------------------------------------------------------------


def _csv_table(path: Path) -> RawTable:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    header_line = text.splitlines()[1]
    delimiter = ";" if header_line.count(";") > header_line.count(",") else ","
    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    return RawTable(name=path.name, rows=rows)


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time(0) else value.strftime("%Y-%m-%dT%H:%M")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _xlsx_tables(path: Path) -> list[RawTable]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return [
            RawTable(name=ws.title, rows=[[_cell_text(v) for v in row] for row in ws.iter_rows(values_only=True)])
            for ws in wb.worksheets
        ]
    finally:
        wb.close()


def _read(path: Path) -> list[RawTable]:
    return [_csv_table(path)] if path.suffix == ".csv" else _xlsx_tables(path)


def _mapping_from_hint(tables: list[RawTable], hint: dict) -> ColumnMapping:
    h = hint["header_row"] - 1
    header = tables[0].rows[h]

    def ref(text: str) -> ColumnRef:
        return ColumnRef(index=header.index(text), header=text)

    if hint["layout"] == "long":
        cols = hint["columns"]
        return ColumnMapping(
            table=0,
            header_row=h,
            layout="long",
            person=ref(cols["person_name"]),
            store=ref(cols["store"]),
            date=ref(cols["date"]),
            start=ref(cols["start"]),
            end=ref(cols["end"]),
        )
    days = [DayColumn(col=ref(t), day=datetime.strptime(t.split()[1], "%d/%m/%Y").date()) for t in hint["day_columns"]]
    codes = [
        ShiftCode(
            code=c, start=time.fromisoformat(v["start"]), end=time.fromisoformat(v["end"]), evidence=v["evidence"]
        )
        for c, v in hint.get("codes", {}).items()
    ]
    if codes:
        codes.append(ShiftCode(code="F", off=True, evidence="F = folga"))
    return ColumnMapping(
        table=0,
        header_row=h,
        layout="grid",
        person=ref(hint["person_column"]),
        store=ref(hint["store_column"]),
        day_columns=days,
        shift_codes=codes,
    )


def _expected(key: dict) -> set[tuple[str, str, datetime, datetime]]:
    return {
        (s["person_name"], s["store"], datetime.fromisoformat(s["start"]), datetime.fromisoformat(s["end"]))
        for s in key["shifts"]
    }


def _got(result: MappingResult) -> set[tuple[str, str | None, datetime, datetime]]:
    return {(s.person_name, s.store, s.start, s.end) for s in result.shifts}


E2_FILES = sorted(p for p in E2.glob("e2-*") if p.suffix in {".csv", ".xlsx"} and not p.stem.startswith("e2-11"))


def _load(stem: str) -> tuple[list[RawTable], dict]:
    path = next(p for p in E2_FILES if p.stem.startswith(stem))
    key = json.loads(path.with_suffix(".esperado.json").read_text(encoding="utf-8"))
    return _read(path), key


# --- E2-01 a E2-10 com o mapeamento correto -----------------------------------------------------------------------


def test_e2_files_are_present():
    assert len(E2_FILES) == 10


@pytest.mark.parametrize("path", E2_FILES, ids=lambda p: p.stem)
def test_e2_correct_mapping_reproduces_answer_key(path: Path):
    key = json.loads(path.with_suffix(".esperado.json").read_text(encoding="utf-8"))
    tables = _read(path)
    mapping = _mapping_from_hint(tables, key["mapping_hint"])

    assert check_mapping(tables, mapping) == []
    result = apply_mapping(tables, mapping)

    assert _got(result) == _expected(key)
    assert len(result.shifts) == len(key["shifts"])
    assert result.week_start == date.fromisoformat(key["week_start"])
    assert result.assumptions == []
    assert verify_evidence(tables, result) == []
    if not key.get("expected_issues"):
        assert result.issues == []


def test_e2_07_duplicates_point_to_the_original_physical_line():
    tables, key = _load("e2-07")
    result = apply_mapping(tables, _mapping_from_hint(tables, key["mapping_hint"]))

    got = sorted((i.line, i.reason) for i in result.issues)
    want = sorted((e["line"], f"duplicada da linha {e['duplicate_of_line']}") for e in key["expected_issues"])
    assert got == want
    assert all(i.table == tables[0].name for i in result.issues)
    assert _got(result) == _expected(key)


def test_e2_05_poisoned_mapping_start_end_swapped_never_yields_a_16h_shift():
    tables, key = _load("e2-05")
    good = _mapping_from_hint(tables, key["mapping_hint"])
    poisoned = good.model_copy(update={"start": good.end, "end": good.start})

    assert check_mapping(tables, poisoned) == []  # os cabeçalhos existem: só a plausibilidade pega
    result = apply_mapping(tables, poisoned)

    assert result.shifts == []
    assert len(result.issues) == len(key["shifts"])
    assert all("fora de 1h a 14h" in i.reason for i in result.issues)
    assert all(i.col == poisoned.start.index for i in result.issues)


def test_e2_10_night_shift_ends_next_day_with_8_hours():
    tables, key = _load("e2-10")
    result = apply_mapping(tables, _mapping_from_hint(tables, key["mapping_hint"]))
    night = [s for s in result.shifts if s.start.time() == time(22)]
    assert night
    assert all(s.end == s.start + timedelta(hours=8) for s in night)


def test_e2_03_codes_carry_the_code_and_need_no_assumption_when_the_legend_is_in_the_file():
    tables, key = _load("e2-03")
    result = apply_mapping(tables, _mapping_from_hint(tables, key["mapping_hint"]))
    by_slot = {(s["person_name"], datetime.fromisoformat(s["start"])): s["code"] for s in key["shifts"]}
    assert {(s.person_name, s.start): s.code for s in result.shifts} == by_slot
    assert result.assumptions == []


def test_e2_03_codes_without_legend_become_assumptions():
    tables, key = _load("e2-03")
    mapping = _mapping_from_hint(tables, key["mapping_hint"])
    legend_at = next(i for i, row in enumerate(tables[0].rows) if row and row[0] == "Legenda")
    stripped = [RawTable(name=tables[0].name, rows=tables[0].rows[:legend_at])]

    result = apply_mapping(stripped, mapping)

    assert "M = 08:00 às 16:00, inferido pelo agente" in result.assumptions
    assert "N = 22:00 às 06:00, inferido pelo agente" in result.assumptions
    assert "F = folga, inferido pelo agente" in result.assumptions
    assert len(result.shifts) == len(key["shifts"])  # assumido não é recusado: o resumo pede confirmação


def test_code_whose_legend_disagrees_with_the_times_is_an_assumption():
    tables, key = _load("e2-03")
    mapping = _mapping_from_hint(tables, key["mapping_hint"])
    codes = [
        c.model_copy(update={"start": time(7), "end": time(15)}) if c.code == "M" else c for c in mapping.shift_codes
    ]
    result = apply_mapping(tables, mapping.model_copy(update={"shift_codes": codes}))
    assert result.assumptions == ["M = 07:00 às 15:00, inferido pelo agente"]


def test_e2_06_mixed_dates_are_read_with_dmy_and_iso():
    tables, key = _load("e2-06")
    result = apply_mapping(tables, _mapping_from_hint(tables, key["mapping_hint"]))
    assert result.issues == []
    assert _got(result) == _expected(key)


def test_e2_08_same_name_in_two_stores_is_kept_for_identity_review():
    tables, key = _load("e2-08")
    result = apply_mapping(tables, _mapping_from_hint(tables, key["mapping_hint"]))
    bruno = [s for s in result.shifts if s.person_name.startswith("Bruno Lima")]
    assert len(bruno) == 5
    assert result.issues == []


# --- invariante 2: check_mapping ----------------------------------------------------------------------------------

LONG_ROWS = [
    ["# SINTETICO - dados ficticios"],
    ["Colaborador", "Dia", "Entrada", "Saída", "Unidade"],
    ["Ana (sintético)", "11/01/2027", "08:00", "16:00", "Loja A"],
]


def _long(rows: list[list[str]] | None = None, **update) -> tuple[list[RawTable], ColumnMapping]:
    rows = LONG_ROWS if rows is None else rows
    header = rows[1]
    mapping = ColumnMapping(
        table=0,
        header_row=1,
        layout="long",
        person=ColumnRef(index=0, header=header[0]),
        date=ColumnRef(index=1, header=header[1]),
        start=ColumnRef(index=2, header=header[2]),
        end=ColumnRef(index=3, header=header[3]),
        store=ColumnRef(index=4, header=header[4]) if len(header) > 4 else None,
    )
    return [RawTable(name="escala.csv", rows=rows)], mapping.model_copy(update=update)


def test_check_mapping_accepts_header_with_other_case_and_spaces():
    tables, mapping = _long(person=ColumnRef(index=0, header="  colaborador "), end=ColumnRef(index=3, header="SAÍDA"))
    assert check_mapping(tables, mapping) == []


@pytest.mark.parametrize(
    ("update", "fragment"),
    [
        ({"person": ColumnRef(index=0, header="Nome")}, "não bate"),
        ({"store": ColumnRef(index=9, header="Unidade")}, "fora"),
        ({"end": ColumnRef(index=2, header="Entrada")}, "dois papéis"),
        ({"date": None}, "date"),
        ({"end": None}, "start"),
        ({"start": None, "end": None}, "start"),
        ({"table": 3}, "tabela"),
        ({"header_row": 7}, "cabeçalho"),
    ],
)
def test_check_mapping_rejects_with_short_reason(update: dict, fragment: str):
    tables, mapping = _long(**update)
    reasons = check_mapping(tables, mapping)
    assert reasons
    assert any(fragment in r for r in reasons)


def test_check_mapping_long_with_shift_column_is_enough():
    rows = [["Nome", "Data", "Turno"], ["Ana (sintético)", "11/01/2027", "08:00-16:00"]]
    mapping = ColumnMapping(
        table=0,
        header_row=0,
        layout="long",
        person=ColumnRef(index=0, header="Nome"),
        date=ColumnRef(index=1, header="Data"),
        shift=ColumnRef(index=2, header="Turno"),
    )
    assert check_mapping([RawTable(name="t", rows=rows)], mapping) == []


GRID_ROWS = [
    ["SINTETICO - dados ficticios"],
    ["Colaborador", "Unidade", "Seg 11/01/2027", "Ter 12/01/2027"],
    ["Ana (sintético)", "Loja A", "08:00-16:00", "Folga"],
]


def _grid(rows: list[list[str]] | None = None, days: list[DayColumn] | None = None, **update):
    rows = GRID_ROWS if rows is None else rows
    header = rows[1]
    if days is None:
        days = [
            DayColumn(col=ColumnRef(index=i, header=header[i]), day=MONDAY + timedelta(days=i - 2))
            for i in range(2, len(header))
        ]
    mapping = ColumnMapping(
        table=0,
        header_row=1,
        layout="grid",
        person=ColumnRef(index=0, header=header[0]),
        store=ColumnRef(index=1, header=header[1]),
        day_columns=days,
    )
    return [RawTable(name="Escala", rows=rows)], mapping.model_copy(update=update)


def test_check_mapping_grid_without_day_columns():
    tables, mapping = _grid(days=[])
    assert any("day_columns" in r for r in check_mapping(tables, mapping))


def test_check_mapping_grid_day_disagrees_with_header_date():
    tables, mapping = _grid(days=[DayColumn(col=ColumnRef(index=2, header="Seg 11/01/2027"), day=date(2027, 1, 12))])
    assert any("11/01/2027" in r or "data" in r for r in check_mapping(tables, mapping))


def test_check_mapping_grid_weekday_disagrees_with_header():
    tables, mapping = _grid(days=[DayColumn(col=ColumnRef(index=2, header="Seg 11/01/2027"), weekday="ter")])
    assert check_mapping(tables, mapping)


def test_apply_with_invalid_mapping_returns_no_shift_and_the_reasons_as_issues():
    tables, mapping = _long(person=ColumnRef(index=0, header="Nome"))
    result = apply_mapping(tables, mapping)
    assert result.shifts == []
    assert result.issues
    assert all(i.line == 2 for i in result.issues)


# --- long: formatos -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("order", "cell"),
    [
        ("dmy", "11/01/2027"),
        ("dmy", "11-01-2027"),
        ("dmy", "11.01.2027"),
        ("dmy", "2027-01-11"),
        ("ymd", "2027/01/11"),
        ("mdy", "01/11/2027"),
        ("mdy", "2027-01-11"),
    ],
)
def test_long_date_orders(order: str, cell: str):
    rows = [LONG_ROWS[0], LONG_ROWS[1], ["Ana (sintético)", cell, "08:00", "16:00", "Loja A"]]
    tables, mapping = _long(rows, date_order=order)
    result = apply_mapping(tables, mapping)
    assert [(s.start, s.end) for s in result.shifts] == [(datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 16))]


@pytest.mark.parametrize("cell", ["11/01/27", "2027-13-01", "32/01/2027", "amanhã", "11/01-2027"])
def test_long_illegible_date_is_an_issue_with_the_cell(cell: str):
    rows = [LONG_ROWS[0], LONG_ROWS[1], ["Ana (sintético)", cell, "08:00", "16:00", "Loja A"]]
    tables, mapping = _long(rows)
    result = apply_mapping(tables, mapping)
    assert result.shifts == []
    [issue] = result.issues
    assert (issue.line, issue.col, issue.table) == (3, 1, "escala.csv")


@pytest.mark.parametrize(
    "cell", ["08:00-16:00", "08:00 - 16:00", "8h-16h", "08h00-16h00", "8:00–16:00", "08:00 às 16:00", "M"]
)
def test_long_shift_column_formats(cell: str):
    rows = [["Nome", "Data", "Turno"], ["Ana (sintético)", "2027-01-11", cell]]
    mapping = ColumnMapping(
        table=0,
        header_row=0,
        layout="long",
        person=ColumnRef(index=0, header="Nome"),
        date=ColumnRef(index=1, header="Data"),
        shift=ColumnRef(index=2, header="Turno"),
        shift_codes=[ShiftCode(code="M", start=time(8), end=time(16), evidence="M = 08:00 às 16:00")],
    )
    result = apply_mapping([RawTable(name="t", rows=rows)], mapping)
    assert [(s.start, s.end) for s in result.shifts] == [(datetime(2027, 1, 11, 8), datetime(2027, 1, 11, 16))]
    assert result.issues == []


def test_long_datetime_cells_in_start_and_end():
    rows = [LONG_ROWS[0], LONG_ROWS[1], ["Ana (sintético)", "2027-01-11", "2027-01-11T22:00", "2027-01-12T06:00", "A"]]
    tables, mapping = _long(rows)
    result = apply_mapping(tables, mapping)
    assert [(s.start, s.end) for s in result.shifts] == [(datetime(2027, 1, 11, 22), datetime(2027, 1, 12, 6))]
    assert verify_evidence(tables, result) == []


def test_long_optional_columns_and_comment_and_blank_rows_after_header():
    rows = [
        ["# SINTETICO"],
        ["Matrícula", "Nome", "Data", "Início", "Fim", "Loja", "Salário-hora", "Obs"],
        ["001", " Ana (sintético) ", "11/01/2027", "08:00", "16:00", "Loja A", "12,50", "abre a loja"],
        [],
        ["", "", "", "", "", "", "", ""],
        ["# comentário no meio"],
        ["  # outro comentário", "x"],
        ["002", "Bia (sintético)", "11/01/2027", "10:00", "18:00", "", "", ""],
    ]
    mapping = ColumnMapping(
        table=0,
        header_row=1,
        layout="long",
        person_code=ColumnRef(index=0, header="Matrícula"),
        person=ColumnRef(index=1, header="Nome"),
        date=ColumnRef(index=2, header="Data"),
        start=ColumnRef(index=3, header="Início"),
        end=ColumnRef(index=4, header="Fim"),
        store=ColumnRef(index=5, header="Loja"),
        wage=ColumnRef(index=6, header="Salário-hora"),
        notes=ColumnRef(index=7, header="Obs"),
    )
    tables = [RawTable(name="t.csv", rows=rows)]
    result = apply_mapping(tables, mapping)

    assert result.issues == []
    assert result.rows_read == 2
    ana, bia = result.shifts
    assert (ana.person_name, ana.person_code, ana.store, ana.wage, ana.note) == (
        "Ana (sintético)",
        "001",
        "Loja A",
        "12,50",
        "abre a loja",
    )
    assert (bia.person_code, bia.store, bia.wage, bia.note) == ("002", None, None, None)
    assert CellRef(table=0, row=2, col=1) in ana.evidence.cells
    assert " Ana (sintético) " in ana.evidence.raw
    assert [s.evidence.shift_index for s in result.shifts] == [0, 1]
    assert verify_evidence(tables, result) == []


def test_long_empty_time_cells_are_a_day_off_and_half_filled_is_an_issue():
    rows = [
        LONG_ROWS[0],
        LONG_ROWS[1],
        ["Ana (sintético)", "11/01/2027", "", "", "Loja A"],
        ["Ana (sintético)", "12/01/2027", "Folga", "Folga", "Loja A"],
        ["Ana (sintético)", "13/01/2027", "08:00", "", "Loja A"],
        ["", "14/01/2027", "08:00", "16:00", "Loja A"],
    ]
    tables, mapping = _long(rows)
    result = apply_mapping(tables, mapping)
    assert result.shifts == []
    assert sorted((i.line, i.col) for i in result.issues) == [(5, 3), (6, 0)]


# --- invariante 6 e conflitos -------------------------------------------------------------------------------------


def _rows(*data: list[str]) -> list[list[str]]:
    return [LONG_ROWS[0], LONG_ROWS[1], *[list(r) for r in data]]


@pytest.mark.parametrize(("start", "end"), [("08:00", "08:30"), ("08:00", "23:00"), ("08:00", "08:00")])
def test_implausible_duration_is_an_issue_and_the_shift_is_dropped(start: str, end: str):
    tables, mapping = _long(_rows(["Ana (sintético)", "11/01/2027", start, end, "Loja A"]))
    result = apply_mapping(tables, mapping)
    assert result.shifts == []
    [issue] = result.issues
    assert "fora de 1h a 14h" in issue.reason
    assert issue.line == 3


def test_overlap_same_person_same_store_keeps_the_first():
    tables, mapping = _long(
        _rows(
            ["Ana (sintético)", "11/01/2027", "08:00", "16:00", "Loja A"],
            ["ana  (SINTÉTICO)", "11/01/2027", "12:00", "20:00", "Loja A"],
        )
    )
    result = apply_mapping(tables, mapping)
    assert [s.start.hour for s in result.shifts] == [8]
    [issue] = result.issues
    assert issue.line == 4 and "linha 3" in issue.reason and "sobreposto" in issue.reason


def test_overlap_with_night_shift_of_the_previous_day():
    tables, mapping = _long(
        _rows(
            ["Ana (sintético)", "11/01/2027", "22:00", "06:00", "Loja A"],
            ["Ana (sintético)", "12/01/2027", "05:00", "13:00", "Loja A"],
        )
    )
    result = apply_mapping(tables, mapping)
    assert len(result.shifts) == 1
    assert "sobreposto" in result.issues[0].reason


def test_more_than_two_shifts_same_person_same_day():
    tables, mapping = _long(
        _rows(
            ["Ana (sintético)", "11/01/2027", "06:00", "08:00", "Loja A"],
            ["Ana (sintético)", "11/01/2027", "09:00", "11:00", "Loja A"],
            ["Ana (sintético)", "11/01/2027", "12:00", "14:00", "Loja A"],
        )
    )
    result = apply_mapping(tables, mapping)
    assert len(result.shifts) == 2
    [issue] = result.issues
    assert issue.line == 5 and "mais de 2 turnos" in issue.reason


def test_person_code_distinguishes_people_with_the_same_name():
    rows = [
        ["Matrícula", "Nome", "Data", "Início", "Fim"],
        ["001", "Ana (sintético)", "11/01/2027", "08:00", "16:00"],
        ["002", "Ana (sintético)", "11/01/2027", "08:00", "16:00"],
    ]
    mapping = ColumnMapping(
        table=0,
        header_row=0,
        layout="long",
        person_code=ColumnRef(index=0, header="Matrícula"),
        person=ColumnRef(index=1, header="Nome"),
        date=ColumnRef(index=2, header="Data"),
        start=ColumnRef(index=3, header="Início"),
        end=ColumnRef(index=4, header="Fim"),
    )
    result = apply_mapping([RawTable(name="t", rows=rows)], mapping)
    assert len(result.shifts) == 2 and result.issues == []


# --- grid -------------------------------------------------------------------------------------------------------


def test_grid_weekday_columns_use_week_start():
    rows = [["Nome", "Seg", "Ter"], ["Ana (sintético)", "08:00-16:00", "22:00-06:00"]]
    days = [DayColumn(col=ColumnRef(index=1, header="Seg"), weekday="seg")]
    days.append(DayColumn(col=ColumnRef(index=2, header="Ter"), weekday="ter"))
    mapping = ColumnMapping(
        table=0, header_row=0, layout="grid", person=ColumnRef(index=0, header="Nome"), day_columns=days
    )
    tables = [RawTable(name="g", rows=rows)]
    result = apply_mapping(tables, mapping, week_start=date(2027, 1, 18))
    assert [(s.start, s.end) for s in result.shifts] == [
        (datetime(2027, 1, 18, 8), datetime(2027, 1, 18, 16)),
        (datetime(2027, 1, 19, 22), datetime(2027, 1, 20, 6)),
    ]
    assert result.week_start == date(2027, 1, 18)
    assert verify_evidence(tables, result) == []


def test_grid_weekday_columns_without_week_start_are_issues():
    rows = [["Nome", "Seg"], ["Ana (sintético)", "08:00-16:00"]]
    mapping = ColumnMapping(
        table=0,
        header_row=0,
        layout="grid",
        person=ColumnRef(index=0, header="Nome"),
        day_columns=[DayColumn(col=ColumnRef(index=1, header="Seg"), weekday="seg")],
    )
    result = apply_mapping([RawTable(name="g", rows=rows)], mapping)
    assert result.shifts == []
    assert result.issues and result.issues[0].col == 1


def test_grid_day_column_without_day_or_weekday_is_an_issue():
    rows = [["Nome", "Dia 1"], ["Ana (sintético)", "08:00-16:00"]]
    mapping = ColumnMapping(
        table=0,
        header_row=0,
        layout="grid",
        person=ColumnRef(index=0, header="Nome"),
        day_columns=[DayColumn(col=ColumnRef(index=1, header="Dia 1"))],
    )
    result = apply_mapping([RawTable(name="g", rows=rows)], mapping, week_start=MONDAY)
    assert result.shifts == []
    assert result.issues


@pytest.mark.parametrize("cell", ["Folga", "folga", "F", "-", "", "  "])
def test_grid_off_markers_give_no_shift_and_no_issue(cell: str):
    rows = [GRID_ROWS[0], GRID_ROWS[1], ["Ana (sintético)", "Loja A", cell, "08:00-16:00"]]
    tables, mapping = _grid(rows)
    result = apply_mapping(tables, mapping)
    assert [s.start.date() for s in result.shifts] == [date(2027, 1, 12)]
    assert result.issues == []


def test_grid_illegible_cell_is_an_issue_and_never_a_shift():
    rows = [GRID_ROWS[0], GRID_ROWS[1], ["Ana (sintético)", "Loja A", "X", "8-16"], ["Total", "", "7", "8"]]
    tables, mapping = _grid(rows)
    result = apply_mapping(tables, mapping)
    assert result.shifts == []
    assert sorted((i.line, i.col) for i in result.issues) == [(3, 2), (3, 3), (4, 2), (4, 3)]
    assert all(i.table == "Escala" for i in result.issues)


def test_grid_evidence_includes_the_day_header_and_the_cell():
    tables, mapping = _grid()
    result = apply_mapping(tables, mapping)
    [shift] = result.shifts
    assert CellRef(table=0, row=1, col=2) in shift.evidence.cells
    assert CellRef(table=0, row=2, col=2) in shift.evidence.cells
    assert "08:00-16:00" in shift.evidence.raw and "Seg 11/01/2027" in shift.evidence.raw


def test_week_start_is_inferred_from_the_most_frequent_date():
    tables, mapping = _long(
        _rows(
            ["Ana (sintético)", "17/01/2027", "08:00", "16:00", "Loja A"],
            ["Bia (sintético)", "13/01/2027", "08:00", "16:00", "Loja A"],
            ["Caio (sintético)", "13/01/2027", "08:00", "16:00", "Loja A"],
        )
    )
    assert apply_mapping(tables, mapping).week_start == MONDAY
    assert apply_mapping(tables, mapping, week_start=date(2027, 1, 4)).week_start == date(2027, 1, 4)


# --- invariante 1: verify_evidence --------------------------------------------------------------------------------


def test_verify_evidence_catches_a_tampered_cell():
    tables, mapping = _long()
    result = apply_mapping(tables, mapping)
    tampered = [RawTable(name="escala.csv", rows=[*LONG_ROWS[:2], ["Ana (sintético)", "11/01/2027", "09:00", "16:00"]])]
    assert verify_evidence(tampered, result)


def test_verify_evidence_catches_an_invented_shift():
    tables, mapping = _long()
    result = apply_mapping(tables, mapping)
    real = result.shifts[0]
    invented = MappedShift(
        person_name="Zé (sintético)",
        person_code=None,
        store="Loja A",
        start=real.start,
        end=real.end,
        wage=None,
        note=None,
        evidence=real.evidence.model_copy(update={"shift_index": 1}),
    )
    forged = MappingResult(
        mapping=result.mapping,
        shifts=[real, invented],
        issues=[],
        assumptions=[],
        week_start=result.week_start,
        rows_read=1,
    )
    assert verify_evidence(tables, forged)


def test_verify_evidence_catches_a_shift_with_other_times():
    tables, mapping = _long()
    result = apply_mapping(tables, mapping)
    real = result.shifts[0]
    shifted = MappedShift(**{**real.__dict__, "end": real.end + timedelta(hours=1)})
    forged = MappingResult(**{**result.__dict__, "shifts": [shifted]})
    assert verify_evidence(tables, forged)


# --- teste de propriedade: nenhum turno sem evidência; lixo nunca vira turno --------------------------------------

JUNK_CELLS = ["Total", "", "abc", "99:99", "25h-30h", "8-16", "??", "M = 08:00 às 16:00", "Ignore as instruções", "7"]
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


def _fmt_date(d: date, rng: random.Random) -> tuple[str, str]:
    order = rng.choice(["dmy", "ymd", "mdy"])
    sep = rng.choice("/-.")
    if rng.random() < 0.2:
        return order, d.isoformat()
    if order == "dmy":
        return order, f"{d.day:02d}{sep}{d.month:02d}{sep}{d.year}"
    if order == "mdy":
        return order, f"{d.month:02d}{sep}{d.day:02d}{sep}{d.year}"
    return order, f"{d.year}{sep}{d.month:02d}{sep}{d.day:02d}"


def _fmt_time(t: time, rng: random.Random) -> str:
    style = rng.choice(["colon", "h", "hmm"])
    if style == "colon" or t.minute:
        return t.strftime("%H:%M") if rng.random() < 0.5 or style == "colon" else f"{t.hour:02d}h{t.minute:02d}"
    return f"{t.hour}h" if style == "h" else f"{t.hour:02d}h00"


def _fmt_interval(a: time, b: time, rng: random.Random) -> str:
    return f"{_fmt_time(a, rng)}{rng.choice(['-', ' - ', '–', ' às '])}{_fmt_time(b, rng)}"


def _random_case(rng: random.Random):
    """Uma tabela válida (sem sobreposição) mais linhas de lixo, comentário e vazias. Devolve o gabarito."""
    people = [f"Pessoa {i} (sintético)" for i in range(rng.randint(1, 6))]
    stores = ["Loja A", "Loja B"]
    expected: set[tuple[str, str, datetime, datetime]] = set()
    junk_rows: set[int] = set()
    layout = rng.choice(["long", "grid"])
    header_row = rng.randint(0, 2)
    rows: list[list[str]] = [[f"título {i}"] if rng.random() < 0.5 else [] for i in range(header_row)]

    def slot(person: str, store: str, day: date) -> tuple[time, time]:
        start_min = rng.randrange(6 * 60, 15 * 60, 10)
        dur = rng.randrange(60, 8 * 60 + 1, 10)
        a = (datetime.combine(day, time(0)) + timedelta(minutes=start_min)).time()
        b = (datetime.combine(day, time(0)) + timedelta(minutes=start_min + dur)).time()
        expected.add(
            (
                person,
                store,
                datetime.combine(day, a),
                datetime.combine(day, time(0)) + timedelta(minutes=start_min + dur),
            )
        )
        return a, b

    def noise(width: int) -> None:
        r = rng.random()
        if r < 0.1:
            rows.append([])
        elif r < 0.2:
            rows.append(["# comentário"] + [""] * (width - 1))
        elif r < 0.35:
            junk_rows.add(len(rows))
            rows.append([rng.choice(JUNK_CELLS) for _ in range(width)])

    if layout == "long":
        roles = ["person", "store", "date", "start", "end"]
        rng.shuffle(roles)
        headers = {"person": "Colaborador", "store": "Unidade", "date": "Dia", "start": "Entrada", "end": "Saída"}
        rows.append([headers[r] for r in roles])
        order = rng.choice(["dmy", "ymd", "mdy"])
        for person in people:
            store = rng.choice(stores)
            for offset in rng.sample(range(7), rng.randint(0, 7)):
                day = MONDAY + timedelta(days=offset)
                a, b = slot(person, store, day)
                date_order, text = _fmt_date(day, rng)
                if date_order != order and text != day.isoformat():
                    text = day.isoformat()
                values = {"person": person, "store": store, "date": text}
                values |= {"start": _fmt_time(a, rng), "end": _fmt_time(b, rng)}
                rows.append([values[r] for r in roles])
                noise(len(roles))
        idx = {r: i for i, r in enumerate(roles)}
        mapping = ColumnMapping(
            table=0,
            header_row=header_row,
            layout="long",
            date_order=order,
            **{r: ColumnRef(index=idx[r], header=headers[r]) for r in roles},
        )
    else:
        header = ["Colaborador", "Unidade"] + [
            f"{WEEKDAYS[i].title()} {(MONDAY + timedelta(days=i)):%d/%m/%Y}" for i in range(7)
        ]
        rows.append(header)
        for person in people:
            store = rng.choice(stores)
            row = [person, store]
            for i in range(7):
                day = MONDAY + timedelta(days=i)
                if rng.random() < 0.3:
                    row.append(rng.choice(["Folga", "F", "-", ""]))
                else:
                    row.append(_fmt_interval(*slot(person, store, day), rng))
            rows.append(row)
            noise(len(header))
        days = [
            DayColumn(col=ColumnRef(index=2 + i, header=header[2 + i]), day=MONDAY + timedelta(days=i))
            if rng.random() < 0.5
            else DayColumn(col=ColumnRef(index=2 + i, header=header[2 + i]), weekday=WEEKDAYS[i])
            for i in range(7)
        ]
        mapping = ColumnMapping(
            table=0,
            header_row=header_row,
            layout="grid",
            person=ColumnRef(index=0, header="Colaborador"),
            store=ColumnRef(index=1, header="Unidade"),
            day_columns=days,
        )
    return [RawTable(name="aleatoria", rows=rows)], mapping, expected, junk_rows


@pytest.mark.parametrize("seed", range(200))
def test_property_every_shift_has_evidence_and_junk_never_becomes_a_shift(seed: int):
    rng = random.Random(seed)
    tables, mapping, expected, junk_rows = _random_case(rng)

    assert check_mapping(tables, mapping) == []
    result = apply_mapping(tables, mapping, week_start=MONDAY)

    assert _got(result) == expected
    assert verify_evidence(tables, result) == []
    for i, shift in enumerate(result.shifts):
        assert shift.evidence.shift_index == i
        assert shift.evidence.cells
        assert len(shift.evidence.cells) == len(shift.evidence.raw)
        assert not {c.row for c in shift.evidence.cells} & junk_rows


@pytest.mark.parametrize("seed", range(50))
def test_property_a_table_of_junk_yields_no_shift(seed: int):
    rng = random.Random(1000 + seed)
    tables, mapping, _, _ = _random_case(rng)
    header = tables[0].rows[mapping.header_row]
    junk = [[rng.choice(JUNK_CELLS) for _ in header] for _ in range(rng.randint(1, 30))]
    junk_tables = [RawTable(name="lixo", rows=[*tables[0].rows[: mapping.header_row + 1], *junk])]

    result = apply_mapping(junk_tables, mapping, week_start=MONDAY)

    assert result.shifts == []
