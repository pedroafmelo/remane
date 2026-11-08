"""Leitura do CSV da escala atual (borda; RF-04, RF-23, RX-13). Formato longo da DEC-039: um turno por linha,
cabeçalho `loja_id,pessoa_id,nome,data,inicio,fim`, linhas que começam com `#` são comentário.

Aqui só se decodifica o arquivo e se separa em linhas cruas; a validação dos dados é pura e fica em
`escalista.rules.validation`. Arquivo ilegível (não UTF-8, vazio, acima de 1 MB, sem cabeçalho reconhecível ou
CSV malformado) vira RX-13 sem `Schedule`. Arquivo legível com dado inconsistente também vira RX-13, com a lista
de problemas como evidência, e a `Schedule` traz só as linhas boas.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date

from escalista.domain.contracts import ExceptionCard, Role
from escalista.domain.schedule import CsvIssue, Employee, ReadSummary, Schedule, Store
from escalista.rules.validation import COLUMNS, RawRow, validate_schedule_rows

MAX_BYTES = 1024 * 1024  # 1 MB
_IF_NO_ANSWER = "A otimização não começa sem uma escala lida e confirmada pelo gerente."


@dataclass(frozen=True)
class CsvReadResult:
    """`exception` não nulo pede ação do gerente (RX-13). `schedule` é `None` quando o arquivo é ilegível."""

    schedule: Schedule | None
    summary: ReadSummary
    exception: ExceptionCard | None


class _Unreadable(Exception):
    pass


def read_schedule_csv(
    file_name: str,
    content: bytes,
    *,
    employees: list[Employee],
    stores: list[Store],
    week_start: date | None = None,
) -> CsvReadResult:
    try:
        header, rows = _split(content)
    except _Unreadable as exc:
        return _unreadable(file_name, str(exc), week_start)

    result = validate_schedule_rows(file_name, header, rows, employees=employees, stores=stores, week_start=week_start)
    exception = None if result.summary.ok else _inconsistent(file_name, result.summary)
    return CsvReadResult(schedule=result.schedule, summary=result.summary, exception=exception)


def _split(content: bytes) -> tuple[RawRow, list[RawRow]]:
    if len(content) > MAX_BYTES:
        raise _Unreadable(f"o arquivo tem {len(content)} bytes, acima do limite de 1 MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise _Unreadable(f"o arquivo não está em UTF-8 (byte inválido na posição {exc.start})") from None
    if "\x00" in text:
        raise _Unreadable("o arquivo não é um CSV de texto (tem bytes nulos)")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    numbered = [(n, ln) for n, ln in enumerate(lines, start=1) if ln.strip() and not ln.lstrip().startswith("#")]
    if not numbered:
        raise _Unreadable("o arquivo está vazio: não há cabeçalho nem turnos")

    header_line, header_text = numbered[0]
    delimiter = ";" if header_text.count(";") > header_text.count(",") else ","
    try:
        parsed = [(n, next(csv.reader([line], delimiter=delimiter))) for n, line in numbered]
    except csv.Error as exc:
        raise _Unreadable(f"o arquivo não é um CSV válido ({exc})") from None

    header_cells = tuple(parsed[0][1])
    if not {cell.strip().lower() for cell in header_cells} & set(COLUMNS):
        expected = ",".join(COLUMNS)
        raise _Unreadable(f"cabeçalho não reconhecido na linha {header_line}: esperado {expected}")
    return RawRow(header_line, header_cells), [RawRow(n, tuple(cells)) for n, cells in parsed[1:]]


def _unreadable(file_name: str, reason: str, week_start: date | None) -> CsvReadResult:
    summary = ReadSummary(
        file_name=file_name,
        rows=0,
        employees=0,
        stores=0,
        week_start=week_start,
        total_hours=0,
        issues=[CsvIssue(line=0, reason=reason)],
        ok=False,
    )
    card = ExceptionCard(
        code="RX-13",
        title="Não consegui ler a escala",
        reason=f"{file_name}: {reason}.",
        decider=Role.GERENTE,
        evidence=[file_name],
        recommendation=f"Exporte a escala de novo como CSV em UTF-8, com o cabeçalho {','.join(COLUMNS)}, e envie.",
        if_no_answer=_IF_NO_ANSWER,
    )
    return CsvReadResult(schedule=None, summary=summary, exception=card)


def _inconsistent(file_name: str, summary: ReadSummary) -> ExceptionCard:
    n = len(summary.issues)
    return ExceptionCard(
        code="RX-13",
        title="A escala tem dados inconsistentes",
        reason=f"{file_name}: {n} {'linha com problema' if n == 1 else 'problemas encontrados'} na leitura.",
        decider=Role.GERENTE,
        evidence=[_describe(i) for i in summary.issues],
        recommendation="Corrija as linhas indicadas e envie o arquivo de novo.",
        if_no_answer=_IF_NO_ANSWER,
    )


def _describe(issue: CsvIssue) -> str:
    field = f", {issue.field}" if issue.field else ""
    return f"linha {issue.line}{field}: {issue.reason}"
