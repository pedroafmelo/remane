"""Bytes do arquivo enviado → tabelas cruas (`RawTable`), a borda da leitura por agente (plano da C6, D2; RF-23,
RX-13).

Aqui só se detecta o formato, se decodifica e se converte cada célula em texto. Não se decide o que é cabeçalho,
comentário ou coluna (isso é o mapeamento, A1/D3/B2), nem se chama modelo.

Contrato com o mapeamento:

- A `RawTable` traz **todas** as linhas do arquivo, inclusive comentários (`#`) e linhas vazias, para que índice
  0-based + 1 seja a linha física do CSV ou a linha da planilha. Linhas vazias no fim são descartadas.
- Linha vazia do CSV é `[]`; numa aba, é uma lista de `""` (as linhas de uma aba têm a mesma largura: até a última
  coluna com valor). Campo de CSV com quebra de linha entre aspas ocupa várias linhas físicas: a linha do registro
  traz o campo inteiro e as linhas físicas seguintes do mesmo registro viram `[]`, para não deslocar a numeração.
- Células como texto aparado: data `2027-01-11` (datetime às 00:00 vira só data), datetime `2027-01-11T08:00`, hora
  `08:00` (com segundos só se houver), duração `32:00`, inteiro sem `.0`, decimal com ponto, booleano `true`/`false`,
  vazio `""`.
- Um XLSX vira uma `RawTable` por aba (nome = nome da aba); um CSV vira uma (nome = nome do arquivo); um PDF vira uma
  por tabela achada pelo `pdfplumber` ("página N, tabela K"), com a quebra de linha interna da célula trocada por
  espaço. Num XLSX, célula mesclada traz o valor só na célula superior esquerda (o modo `read_only` do openpyxl não
  propaga).

Segurança (arquitetura, seção 6): tipo pelo conteúdo (magic bytes) e pela extensão; `.xlsm`, `.xls` e ZIP com
`xl/vbaProject.bin` são recusados; antes de abrir o XLSX, soma descompactada do ZIP ≤ 20 MiB e no máximo 2000
entradas (o `zipfile` não entrega mais bytes que o `file_size` declarado, então a soma é um teto real); `openpyxl` com
`read_only=True` e `data_only=True` (fórmula nunca é avaliada; vale o valor em cache) e com `defusedxml` quando
instalado; PDF só digital (camada de texto), com `pdfplumber`, até 5 páginas e sem tabela = RX-13 ("talvez escaneado");
no máximo 5000 linhas e 60 colunas com valor por tabela. Tudo que não passa vira RX-13 com o motivo,
decidido pelo gestor.
"""

from __future__ import annotations

import csv
import io
import re
import time as _time
import warnings
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import PurePath
from typing import Literal

from escalista.domain.contracts import ExceptionCard, Role
from escalista.domain.reading import RawTable

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB, o teto da arquitetura (seção 6)
MAX_UNZIPPED_BYTES = 20 * 1024 * 1024  # 20 MiB descompactados
MAX_ZIP_ENTRIES = 2000
MAX_ROWS = 5000
MAX_COLS = 60
MAX_PDF_PAGES = 5

Format = Literal["csv", "xlsx", "pdf"]

_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_PDF_MAGIC = b"%PDF"
_MACRO_EXTENSIONS = {".xlsm", ".xltm", ".xlam"}
_OLD_EXCEL_EXTENSIONS = {".xls", ".xlt"}
_DELIMITERS = (";", ",", "\t")
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_IF_NO_ANSWER = "A otimização não começa sem uma escala lida e confirmada pelo gestor."
_SEND_CSV_OR_XLSX = "Exporte a escala como CSV (UTF-8) ou XLSX e envie de novo."


@dataclass(frozen=True)
class TablesMeta:
    """Números da leitura para o rastro `ingest.parse`. `rows` é a soma das linhas; `cols`, a maior largura."""

    bytes: int
    sheets: int = 0
    rows: int = 0
    cols: int = 0
    ms: int = 0
    encoding: str | None = None  # só CSV: "utf-8" ou "cp1252"
    delimiter: str | None = None  # só CSV

    def as_dict(self) -> dict[str, object]:
        return {
            "bytes": self.bytes,
            "sheets": self.sheets,
            "rows": self.rows,
            "cols": self.cols,
            "ms": self.ms,
            "encoding": self.encoding,
            "delimiter": self.delimiter,
        }


@dataclass(frozen=True)
class TablesResult:
    """`exception` não nulo (RX-13) significa arquivo ilegível: `tables` vem vazia. `format` é `None` se nem o formato
    foi reconhecido."""

    format: Format | None
    tables: list[RawTable] = field(default_factory=list)
    exception: ExceptionCard | None = None
    meta: TablesMeta = field(default_factory=lambda: TablesMeta(bytes=0))


class _Unreadable(Exception):
    def __init__(self, reason: str, recommendation: str = _SEND_CSV_OR_XLSX) -> None:
        super().__init__(reason)
        self.reason = reason
        self.recommendation = recommendation


def read_tables(file_name: str, content: bytes) -> TablesResult:
    """Lê o arquivo enviado (CSV ou XLSX) em tabelas cruas. Nunca levanta exceção por causa do arquivo: o que não dá
    para ler volta como RX-13 em `exception`."""
    started = _time.perf_counter()
    fmt: Format | None = None
    try:
        fmt = _detect(file_name, content)
        if fmt == "pdf":
            tables = _read_pdf(content)
            meta = _meta(content, tables, started)
        elif fmt == "xlsx":
            tables = _read_xlsx(content)
            meta = _meta(content, tables, started)
        else:
            tables, encoding, delimiter = _read_csv(file_name, content)
            meta = _meta(content, tables, started, encoding=encoding, delimiter=delimiter)
    except _Unreadable as exc:
        return TablesResult(
            format=fmt,
            exception=_card(file_name, exc),
            meta=TablesMeta(bytes=len(content), ms=_elapsed_ms(started)),
        )
    return TablesResult(format=fmt, tables=tables, meta=meta)


# --- detecção ------------------------------------------------------------------------------------------------------


def _detect(file_name: str, content: bytes) -> Format:
    ext = PurePath(file_name).suffix.lower()
    if not content:
        raise _Unreadable("o arquivo está vazio")
    if len(content) > MAX_FILE_BYTES:
        raise _Unreadable(
            f"o arquivo tem {len(content)} bytes, acima do limite de {MAX_FILE_BYTES // (1024 * 1024)} MB"
        )
    if ext in _MACRO_EXTENSIONS:
        raise _Unreadable(
            f"planilha com macro ({ext}) não é aceita, por segurança",
            "Salve a planilha como XLSX comum (Pasta de Trabalho do Excel, sem macro) e envie de novo.",
        )
    if ext in _OLD_EXCEL_EXTENSIONS or content.startswith(_OLE_MAGIC):
        raise _Unreadable(
            "formato do Excel antigo (.xls) ou planilha protegida por senha não é aceito",
            "Salve a planilha como XLSX, sem senha, e envie de novo.",
        )
    if content.startswith(_PDF_MAGIC):
        return "pdf"
    if ext == ".pdf":
        raise _Unreadable("o arquivo tem extensão .pdf, mas o conteúdo não é um PDF")
    if content.startswith(_ZIP_MAGIC):
        return "xlsx"
    if ext == ".xlsx":
        raise _Unreadable("o arquivo tem extensão .xlsx, mas o conteúdo não é uma planilha XLSX (corrompido?)")
    return "csv"


# --- CSV -----------------------------------------------------------------------------------------------------------


def _read_csv(file_name: str, content: bytes) -> tuple[list[RawTable], str, str]:
    if b"\x00" in content:
        raise _Unreadable("o arquivo não é um CSV de texto (tem bytes nulos: binário ou UTF-16)")
    try:
        text, encoding = content.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        try:
            text, encoding = content.decode("cp1252"), "cp1252"
        except UnicodeDecodeError as exc:
            raise _Unreadable(f"codificação de texto não reconhecida (byte inválido na posição {exc.start})") from None

    lines = _LINE_BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()  # a quebra de linha final não abre uma linha nova
    first = next((ln for ln in lines if ln.strip() and not _is_comment(ln)), None)
    if first is None:
        raise _Unreadable("o arquivo não tem nenhuma linha de dados (só vazias ou comentários)")
    delimiter = max(_DELIMITERS, key=first.count)  # empate: a ordem de `_DELIMITERS` decide

    rows: list[list[str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            rows.append([])
            i += 1
            continue
        if _is_comment(line):
            rows.append(_parse_record(line, delimiter))
            i += 1
            continue
        start, buffer = i, line
        while buffer.count('"') % 2 == 1:  # aspas abertas: o registro continua na próxima linha física
            i += 1
            if i >= len(lines):
                raise _Unreadable(f"aspas sem fechamento a partir da linha {start + 1}")
            buffer += "\n" + lines[i]
        rows.append(_parse_record(buffer, delimiter))
        rows.extend([] for _ in range(i - start))
        i += 1

    rows = _trim_trailing_empty(rows)
    _check_limits(file_name, rows)
    return [RawTable(name=file_name, rows=rows)], encoding, delimiter


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _parse_record(text: str, delimiter: str) -> list[str]:
    try:
        record = next(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter), [])
    except csv.Error as exc:
        raise _Unreadable(f"o arquivo não é um CSV válido ({exc})") from None
    return [cell.strip() for cell in record]


# --- XLSX ----------------------------------------------------------------------------------------------------------


def _read_xlsx(content: bytes) -> list[RawTable]:
    _check_zip(content)
    import openpyxl  # importado só aqui: a borda de CSV não paga o custo

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # extensões não suportadas (validação de dados etc.) não interessam aqui
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            try:
                tables = [_read_sheet(ws) for ws in wb.worksheets]
            finally:
                wb.close()
    except _Unreadable:
        raise
    except Exception as exc:  # borda: qualquer falha da planilha vira RX-13 com o detalhe
        raise _Unreadable(f"a planilha está corrompida ou fora do padrão XLSX ({type(exc).__name__})") from None

    if not tables:
        raise _Unreadable("a planilha não tem nenhuma aba de dados")
    if not any(t.rows for t in tables):
        raise _Unreadable("a planilha está vazia")
    return tables


def _check_zip(content: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError):
        raise _Unreadable("a planilha está corrompida (o pacote ZIP do XLSX não abre)") from None
    if len(entries) > MAX_ZIP_ENTRIES:
        raise _Unreadable(f"a planilha tem {len(entries)} partes internas, acima do limite de {MAX_ZIP_ENTRIES}")
    names = {e.filename for e in entries}
    if "xl/vbaProject.bin" in names:
        raise _Unreadable(
            "a planilha contém macro (VBA), não aceita por segurança",
            "Salve a planilha como XLSX comum (Pasta de Trabalho do Excel, sem macro) e envie de novo.",
        )
    if "xl/workbook.xml" not in names:
        raise _Unreadable("o arquivo é um ZIP, mas não é uma planilha XLSX")
    unzipped = sum(e.file_size for e in entries)
    if unzipped > MAX_UNZIPPED_BYTES:
        raise _Unreadable(
            f"a planilha descompacta para {unzipped} bytes, acima do limite de "
            f"{MAX_UNZIPPED_BYTES // (1024 * 1024)} MB (possível bomba de compressão)"
        )


def _read_sheet(ws) -> RawTable:  # ws: openpyxl ReadOnlyWorksheet
    name = str(ws.title)
    ws.reset_dimensions()  # não confia na dimensão declarada: cada linha vem até a sua última célula
    rows: list[list[str]] = []
    width = 0
    for index, values in enumerate(ws.iter_rows(values_only=True)):
        row = [_cell_text(v) for v in values]
        used = _used_width(row)
        if used == 0:
            if index < MAX_ROWS:
                rows.append([])
            continue
        if index >= MAX_ROWS:
            raise _Unreadable(f"a aba '{name}' tem mais de {MAX_ROWS} linhas (limite)")
        if used > MAX_COLS:
            raise _Unreadable(f"a aba '{name}' tem {used} colunas com valor na linha {index + 1} (limite: {MAX_COLS})")
        width = max(width, used)
        rows.append(row[:used])
    rows = _trim_trailing_empty(rows)
    return RawTable(name=name, rows=[r + [""] * (width - len(r)) for r in rows])


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(Decimal(repr(value)), "f")
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        if value.time() == time(0, 0):
            return value.date().isoformat()
        return f"{value.date().isoformat()}T{_clock(value.time())}"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return _clock(value)
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        sign, total = ("-", -total) if total < 0 else ("", total)
        hours, rest = divmod(total, 3600)
        minutes, seconds = divmod(rest, 60)
        return f"{sign}{hours:02d}:{minutes:02d}" + (f":{seconds:02d}" if seconds else "")
    return str(value).strip()


def _clock(t: time) -> str:
    return t.strftime("%H:%M:%S") if t.second or t.microsecond else t.strftime("%H:%M")


# --- PDF -----------------------------------------------------------------------------------------------------------


def _read_pdf(content: bytes) -> list[RawTable]:
    """PDF digital (com camada de texto): `pdfplumber.extract_tables` em até `MAX_PDF_PAGES` páginas. Cada tabela
    achada vira uma `RawTable` ("página N, tabela K"). PDF escaneado (imagem) não tem tabela extraível: vira RX-13."""
    import pdfplumber  # importado só aqui: a borda de CSV/XLSX não paga o custo

    tables: list[RawTable] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = len(pdf.pages)
            if pages == 0:
                raise _Unreadable("o PDF não tem páginas")
            if pages > MAX_PDF_PAGES:
                raise _Unreadable(f"o PDF tem {pages} páginas, acima do limite de {MAX_PDF_PAGES}")
            for number, page in enumerate(pdf.pages, start=1):
                found = [rows for rows in page.extract_tables() if any(any(cell for cell in row) for row in rows)]
                for k, raw in enumerate(found, start=1):
                    name = f"página {number}, tabela {k}"
                    tables.append(RawTable(name=name, rows=_pdf_rows(name, raw)))
    except _Unreadable:
        raise
    except Exception as exc:  # borda: PDF corrompido, criptografado ou fora do padrão vira RX-13 com o detalhe
        raise _Unreadable(
            f"o PDF está corrompido, protegido por senha ou fora do padrão ({type(exc).__name__})"
        ) from None

    if not tables:
        raise _Unreadable("o PDF não tem tabela legível (talvez seja escaneado); envie CSV ou XLSX")
    return tables


def _pdf_rows(name: str, raw: list[list[str | None]]) -> list[list[str]]:
    rows = [[_LINE_BREAK.sub(" ", cell or "").strip() for cell in row] for row in raw]
    width = max((len(r) for r in rows), default=0)
    rows = _trim_trailing_empty([r + [""] * (width - len(r)) for r in rows])
    _check_limits(name, rows)
    return rows


# --- comum ---------------------------------------------------------------------------------------------------------


def _used_width(row: list[str]) -> int:
    for i in range(len(row) - 1, -1, -1):
        if row[i]:
            return i + 1
    return 0


def _trim_trailing_empty(rows: list[list[str]]) -> list[list[str]]:
    end = len(rows)
    while end and not any(rows[end - 1]):
        end -= 1
    return rows[:end]


def _check_limits(name: str, rows: list[list[str]]) -> None:
    if len(rows) > MAX_ROWS:
        raise _Unreadable(f"'{name}' tem mais de {MAX_ROWS} linhas (limite)")
    for index, row in enumerate(rows):
        used = _used_width(row)
        if used > MAX_COLS:
            raise _Unreadable(f"'{name}' tem {used} colunas com valor na linha {index + 1} (limite: {MAX_COLS})")


def _meta(
    content: bytes,
    tables: list[RawTable],
    started: float,
    *,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> TablesMeta:
    return TablesMeta(
        bytes=len(content),
        sheets=len(tables),
        rows=sum(len(t.rows) for t in tables),
        cols=max((len(r) for t in tables for r in t.rows), default=0),
        ms=_elapsed_ms(started),
        encoding=encoding,
        delimiter=delimiter,
    )


def _elapsed_ms(started: float) -> int:
    return round((_time.perf_counter() - started) * 1000)


def _card(file_name: str, exc: _Unreadable) -> ExceptionCard:
    return ExceptionCard(
        code="RX-13",
        title="Não consegui ler o arquivo da escala",
        reason=f"{file_name}: {exc.reason}.",
        decider=Role.GESTOR,
        evidence=[file_name, exc.reason],
        recommendation=exc.recommendation,
        if_no_answer=_IF_NO_ANSWER,
    )
