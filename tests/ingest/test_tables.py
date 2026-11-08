"""Bytes → `RawTable` (plano da C6, D2; RF-23, RX-13). Usa os arquivos sintéticos de `data/demo/e2/` (E2-01 a E2-11) e
planilhas geradas em memória para os limites."""

import io
import json
import zipfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

import openpyxl
import pytest

from escalista.domain.contracts import Role
from escalista.ingest.tables import MAX_COLS, MAX_FILE_BYTES, MAX_PDF_PAGES, MAX_ROWS, MAX_ZIP_ENTRIES, read_tables

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
E2 = DEMO / "e2"
READABLE = sorted(p for p in E2.glob("e2-*") if p.suffix != ".json" and not p.name.startswith("e2-11"))
FORMATS = {".xlsx": "xlsx", ".csv": "csv", ".pdf": "pdf"}
UNREADABLE = sorted(p for p in E2.glob("e2-11*") if p.suffix != ".json")


def _key(path: Path) -> dict:
    return json.loads(path.with_suffix(".esperado.json").read_text(encoding="utf-8"))


def _read(path: Path):
    return read_tables(path.name, path.read_bytes())


def _xlsx(build) -> bytes:
    wb = openpyxl.Workbook()
    build(wb)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _assert_rx13(result, *fragments: str) -> None:
    card = result.exception
    assert card is not None
    assert card.code == "RX-13"
    assert card.decider == Role.GESTOR
    assert result.tables == []
    for fragment in fragments:
        assert fragment in card.reason


# --- E2-01 a E2-10: legíveis ----------------------------------------------------------------------------------------


def test_e2_files_are_all_present():
    assert len(READABLE) == 11
    assert len(UNREADABLE) == 4


@pytest.mark.parametrize("path", READABLE, ids=lambda p: p.name)
def test_e2_readable_file_yields_tables_with_header_at_the_answer_key_row(path):
    result = _read(path)
    key = _key(path)

    assert key["expect"] == "shifts"
    assert result.exception is None
    assert result.format == FORMATS[path.suffix]
    assert len(result.tables) == 1
    table = result.tables[0]
    header = table.rows[key["mapping_hint"]["header_row"] - 1]  # índice 0-based + 1 = linha do arquivo
    columns = key["mapping_hint"].get("columns", {})
    for name in columns.values():
        assert name in header
    if "person_column" in key["mapping_hint"]:
        assert key["mapping_hint"]["person_column"] in header
    assert result.meta.sheets == 1
    assert result.meta.rows == len(table.rows)
    assert result.meta.bytes == path.stat().st_size


def test_e2_01_is_decoded_from_cp1252_with_semicolon_and_keeps_the_comment_line():
    result = _read(E2 / "e2-01-csv-cp1252.csv")

    rows = result.tables[0].rows
    assert result.meta.encoding == "cp1252"
    assert result.meta.delimiter == ";"
    assert rows[0] == ["# SINTETICO - dados ficticios"]
    assert rows[1] == ["Colaborador", "Dia", "Entrada", "Saída", "Unidade"]
    assert any(cell.startswith("Quitéria") for row in rows for cell in row)
    assert result.tables[0].name == "e2-01-csv-cp1252.csv"


def test_e2_04_merged_title_stays_in_a1_and_excel_dates_become_iso():
    table = _read(E2 / "e2-04-titulo-mesclado.xlsx").tables[0]

    assert table.name == "Escala"
    assert table.rows[0][0].startswith("SINTETICO")
    assert table.rows[0][1:] == ["", "", "", ""]  # read_only não propaga o valor mesclado
    assert table.rows[2] == ["", "", "", "", ""]  # linha em branco preservada
    assert table.rows[3] == ["Nome do colaborador", "Loja", "Dia", "Início", "Término"]
    assert table.rows[4][2] == "2027-01-11"


def test_e2_03_grid_codes_and_legend_are_read_as_text():
    table = _read(E2 / "e2-03-grade-codigos.xlsx").tables[0]
    cells = {cell for row in table.rows for cell in row}

    assert {"M", "T", "N", "F"} <= cells
    for code in _key(E2 / "e2-03-grade-codigos.xlsx")["mapping_hint"]["codes"].values():
        assert any(code["evidence"] in cell for cell in cells)


def test_e2_07_duplicate_lines_of_the_answer_key_point_to_identical_rows():
    path = E2 / "e2-07-duplicatas.csv"
    rows = _read(path).tables[0].rows

    issues = _key(path)["expected_issues"]
    assert issues
    for issue in issues:
        assert rows[issue["line"] - 1] == rows[issue["duplicate_of_line"] - 1]


def test_e2_10_night_shift_cells_are_kept_literal():
    rows = _read(E2 / "e2-10-turno-noturno.csv").tables[0].rows

    assert rows[1] == ["Funcionário", "Data", "Início", "Término", "Filial"]
    assert ["22:00", "06:00"] in [row[2:4] for row in rows[2:]]


def test_demo_grid_example_is_one_table_with_title_header_and_60_people():
    result = _read(DEMO / "escala_exemplo_grade.xlsx")

    assert result.exception is None
    (table,) = result.tables
    assert len(table.rows) == 62  # título + cabeçalho + 60 pessoas
    assert table.rows[1][:2] == ["Colaborador", "Unidade"]
    assert all(row[0] for row in table.rows[2:])
    assert result.meta.cols == 9


# --- E2-11: ilegíveis -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", UNREADABLE, ids=lambda p: p.name)
def test_e2_11_unreadable_file_is_rx13_with_reason_and_no_tables(path):
    result = _read(path)

    assert _key(path)["expect"] == "RX-13"
    _assert_rx13(result, path.name)
    assert path.name in result.exception.evidence
    assert len(result.exception.evidence) == 2


@pytest.mark.parametrize(
    ("name", "fragment"),
    [
        ("e2-11a-macro.xlsm", "macro"),
        ("e2-11b-corrompido.xlsx", "corrompida"),
        ("e2-11c-zip-bomba.xlsx", "descompacta"),
        ("e2-11d-pdf-sem-tabela.pdf", "não tem tabela legível"),
    ],
)
def test_e2_11_reason_names_the_problem(name, fragment):
    _assert_rx13(_read(E2 / name), fragment)


# --- PDF ------------------------------------------------------------------------------------------------------------


def _pdf_pages(*pages: list[str]) -> bytes:
    """PDF digital mínimo de várias páginas, uma linha de texto por item (sem grade: não tem tabela)."""
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    first_page = 4
    kids = " ".join(f"{first_page + 2 * i} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, lines in enumerate(pages):
        stream = "BT /F1 12 Tf 72 760 Td 18 TL\n" + "\n".join(f"({ln}) Tj T*" for ln in lines) + "\nET"
        number = first_page + 2 * i
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {number + 1} 0 R "
            f"/Resources << /Font << /F1 3 0 R >> >> >>".encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode())
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    pdf += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return pdf


def test_pdf_with_table_yields_one_table_with_the_header_and_all_rows():
    path = E2 / "e2-12-pdf-tabela.pdf"
    result = _read(path)
    key = _key(path)

    assert result.exception is None
    assert result.format == "pdf"
    assert [t.name for t in result.tables] == ["página 1, tabela 1"]
    rows = result.tables[0].rows
    assert rows[0] == ["Colaborador", "Dia", "Entrada", "Saída", "Unidade"]
    assert len(rows) == 1 + len(key["shifts"])
    assert all(len(r) == 5 and all(c == c.strip() and "\n" not in c for c in r) for r in rows)
    first = key["shifts"][0]
    assert any(r[0] == first["person_name"] and r[4] == first["store"] for r in rows)
    assert (result.meta.sheets, result.meta.rows, result.meta.cols) == (1, len(rows), 5)
    assert result.meta.bytes == path.stat().st_size
    assert result.meta.encoding is None


def test_pdf_detected_by_content_even_with_another_extension():
    result = read_tables("escala.bin", (E2 / "e2-12-pdf-tabela.pdf").read_bytes())

    assert result.format == "pdf"
    assert result.exception is None


def test_pdf_without_table_is_rx13_maybe_scanned():
    result = read_tables("p.pdf", _pdf_pages(["Comunicado interno", "Sem tabela nenhuma"]))

    _assert_rx13(result, "não tem tabela legível", "escaneado", "CSV ou XLSX")


def test_pdf_above_page_limit_is_rx13():
    pages = [["pagina"]] * (MAX_PDF_PAGES + 1)

    _assert_rx13(read_tables("p.pdf", _pdf_pages(*pages)), f"{MAX_PDF_PAGES + 1} páginas", f"limite de {MAX_PDF_PAGES}")


def test_pdf_at_page_limit_is_opened_and_still_needs_a_table():
    result = read_tables("p.pdf", _pdf_pages(*[["pagina"]] * MAX_PDF_PAGES))

    _assert_rx13(result, "não tem tabela legível")


def test_pdf_truncated_is_rx13():
    content = (E2 / "e2-12-pdf-tabela.pdf").read_bytes()

    _assert_rx13(read_tables("p.pdf", content[:200]), "corrompido")


def test_pdf_cells_have_line_breaks_replaced_and_none_as_empty(monkeypatch):
    class FakePage:
        def extract_tables(self):
            return [[["Nome\nCompleto ", None], [" Ana ", ""]], [[None, None]]]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr("pdfplumber.open", lambda _: FakePdf())

    result = read_tables("p.pdf", b"%PDF-1.4 stub")

    assert result.exception is None
    assert [t.rows for t in result.tables] == [[["Nome Completo", ""], ["Ana", ""]]]  # tabela só de vazios é ignorada


def test_pdf_above_column_limit_is_rx13(monkeypatch):
    class FakePage:
        def extract_tables(self):
            return [[["x"] * (MAX_COLS + 1)]]

    class FakePdf:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr("pdfplumber.open", lambda _: FakePdf())

    _assert_rx13(read_tables("p.pdf", b"%PDF-1.4 stub"), f"limite: {MAX_COLS}")


# --- CSV ------------------------------------------------------------------------------------------------------------


def test_csv_utf8_bom_comma_blank_lines_and_trailing_blank_lines():
    content = "﻿# comentário, com vírgula\nnome,data\n\nAna,2027-01-11\n\n\n".encode()
    result = read_tables("x.csv", content)

    assert result.meta.encoding == "utf-8"
    assert result.meta.delimiter == ","
    assert result.tables[0].rows == [["# comentário", "com vírgula"], ["nome", "data"], [], ["Ana", "2027-01-11"]]


def test_csv_tab_delimiter_and_cells_are_trimmed():
    rows = read_tables("x.tsv", b"nome\tdata\n Ana \t 2027-01-11 \n").tables[0].rows

    assert rows == [["nome", "data"], ["Ana", "2027-01-11"]]


def test_csv_quoted_newline_keeps_physical_line_numbers():
    content = b'nome;obs\n"Ana";"linha 1\nlinha 2"\nBia;ok\n'
    rows = read_tables("x.csv", content).tables[0].rows

    assert rows == [["nome", "obs"], ["Ana", "linha 1\nlinha 2"], [], ["Bia", "ok"]]


def test_csv_quote_in_comment_does_not_swallow_the_next_lines():
    rows = read_tables("x.csv", b'# aspas " soltas\nnome;data\nAna;2027-01-11\n').tables[0].rows

    assert rows[1:] == [["nome", "data"], ["Ana", "2027-01-11"]]


@pytest.mark.parametrize(
    ("name", "content", "fragment"),
    [
        ("x.csv", b"", "vazio"),
        ("x.csv", b"# so comentario\n\n", "nenhuma linha de dados"),
        ("x.csv", "nome;data\n".encode("utf-16"), "bytes nulos"),
        ("x.csv", b'nome;obs\nAna;"sem fim\nBia;ok\n', "aspas sem fechamento"),
        ("x.csv", b"\x81\x8d\x8f", "codificação"),
    ],
)
def test_csv_unreadable_is_rx13(name, content, fragment):
    _assert_rx13(read_tables(name, content), fragment)


def test_csv_above_row_limit_is_rx13():
    content = ("nome;data\n" + "Ana;2027-01-11\n" * MAX_ROWS).encode()

    _assert_rx13(read_tables("x.csv", content), str(MAX_ROWS))


def test_csv_at_row_limit_is_read():
    content = ("nome;data\n" + "Ana;2027-01-11\n" * (MAX_ROWS - 1)).encode()

    assert len(read_tables("x.csv", content).tables[0].rows) == MAX_ROWS


def test_csv_above_column_limit_is_rx13():
    content = (";".join(f"c{i}" for i in range(MAX_COLS + 1)) + "\n").encode()

    _assert_rx13(read_tables("x.csv", content), "colunas")


def test_file_above_size_limit_is_rx13():
    _assert_rx13(read_tables("x.csv", b"a" * (MAX_FILE_BYTES + 1)), "limite")


# --- XLSX -----------------------------------------------------------------------------------------------------------


def test_xlsx_typed_cells_become_text():
    def build(wb):
        ws = wb.active
        ws.title = "Tipos"
        ws.append(
            [
                date(2027, 1, 11),
                datetime(2027, 1, 11, 0, 0),
                datetime(2027, 1, 11, 8, 0),
                time(8, 0),
                7,
                7.0,
                7.5,
                True,
                False,
                None,
                "  texto  ",
                timedelta(hours=32),
            ]
        )
        ws["M1"] = "=1+1"  # fórmula sem valor em cache: nunca é avaliada
        ws["N1"] = "fim"

    table = read_tables("t.xlsx", _xlsx(build)).tables[0]

    assert table.name == "Tipos"
    assert table.rows == [
        [
            "2027-01-11",
            "2027-01-11",
            "2027-01-11T08:00",
            "08:00",
            "7",
            "7",
            "7.5",
            "true",
            "false",
            "",
            "texto",
            "32:00",
            "",
            "fim",
        ]
    ]


def test_xlsx_one_table_per_sheet_with_gaps_preserved_and_rectangular_rows():
    def build(wb):
        a = wb.active
        a.title = "Centro"
        a["A1"] = "titulo"
        a["C4"] = "x"
        b = wb.create_sheet("Norte")
        b["A1"] = "y"
        wb.create_sheet("Vazia")

    result = read_tables("t.xlsx", _xlsx(build))

    assert result.exception is None
    assert [t.name for t in result.tables] == ["Centro", "Norte", "Vazia"]
    centro = result.tables[0].rows
    assert centro == [["titulo", "", ""], ["", "", ""], ["", "", ""], ["", "", "x"]]
    assert result.tables[1].rows == [["y"]]
    assert result.tables[2].rows == []
    assert result.meta.sheets == 3
    assert result.meta.rows == 5


def test_xlsx_above_row_limit_is_rx13():
    def build(wb):
        ws = wb.active
        for i in range(MAX_ROWS + 1):
            ws.append([i])

    _assert_rx13(read_tables("t.xlsx", _xlsx(build)), str(MAX_ROWS))


def test_xlsx_above_column_limit_is_rx13():
    def build(wb):
        wb.active.append(list(range(MAX_COLS + 1)))

    _assert_rx13(read_tables("t.xlsx", _xlsx(build)), "colunas")


def test_xlsx_empty_workbook_is_rx13():
    _assert_rx13(read_tables("t.xlsx", _xlsx(lambda wb: None)), "vazia")


def test_xlsx_with_vba_project_is_rx13_even_with_xlsx_extension():
    buffer = io.BytesIO(_xlsx(lambda wb: wb.active.append(["a"])))
    with zipfile.ZipFile(buffer, "a") as archive:
        archive.writestr("xl/vbaProject.bin", b"\x00" * 10)

    _assert_rx13(read_tables("t.xlsx", buffer.getvalue()), "macro")


def test_zip_with_too_many_entries_is_rx13():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", b"<workbook/>")
        for i in range(MAX_ZIP_ENTRIES):
            archive.writestr(f"x/{i}", b"")

    _assert_rx13(read_tables("t.xlsx", buffer.getvalue()), "partes internas")


def test_zip_that_is_not_a_workbook_is_rx13():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", b"<doc/>")

    _assert_rx13(read_tables("t.xlsx", buffer.getvalue()), "não é uma planilha")


@pytest.mark.parametrize(
    ("name", "content", "fragment"),
    [
        ("t.xls", b"qualquer coisa", ".xls"),
        ("t.xlsx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100, ".xls"),
        ("t.xlsx", b"nome;data\n", "não é uma planilha XLSX"),
        ("t.pdf", b"nome;data\n", "não é um PDF"),
    ],
)
def test_format_mismatch_is_rx13(name, content, fragment):
    _assert_rx13(read_tables(name, content), fragment)


def test_rx13_card_explains_and_has_recommendation():
    card = read_tables("e2-11a-macro.xlsm", (E2 / "e2-11a-macro.xlsm").read_bytes()).exception

    assert card.title
    assert card.recommendation and "XLSX" in card.recommendation
    assert card.if_no_answer
