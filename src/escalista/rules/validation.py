"""Validação determinística das linhas da escala lidas do CSV (RF-04, RF-23), sem custo de modelo.

Núcleo puro: recebe linhas cruas (número da linha física + campos) da borda `ingest/` e devolve a `Schedule`
com as linhas boas e o `ReadSummary` com cada problema (`CsvIssue`: linha, campo, motivo). Linha com problema
não entra na `Schedule`.

Decisões:
- Pessoa numa loja diferente da do quadro é problema (`loja_id`): a fatia não trata empréstimo entre lojas.
- Sem `week_start`, a semana é a da data mais frequente (empate: a mais antiga), começando na segunda.
- `fim` menor que `inicio` é turno que vira a noite; `fim` igual a `inicio` é problema (turno sem duração).
- `nome` é só informativo: precisa existir no cabeçalho, mas pode vir vazio e não é conferido com o quadro.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from escalista.domain.schedule import CsvIssue, Employee, ReadSummary, Schedule, Shift, Store

COLUMNS = ("loja_id", "pessoa_id", "nome", "data", "inicio", "fim")
REQUIRED = ("loja_id", "pessoa_id", "data", "inicio", "fim")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TIME = re.compile(r"(\d{1,2}):(\d{2})")
_HOURS = Decimal("0.01")


@dataclass(frozen=True)
class RawRow:
    """Uma linha do arquivo: `line` é a linha física, 1-based, contando comentários."""

    line: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class ValidationResult:
    """`schedule` é `None` quando o cabeçalho está incompleto ou a semana não pode ser determinada."""

    schedule: Schedule | None
    summary: ReadSummary


@dataclass(frozen=True)
class _Parsed:
    line: int
    store_id: str
    employee_id: str
    day: date
    start: datetime
    end: datetime


def validate_schedule_rows(
    file_name: str,
    header: RawRow,
    rows: Sequence[RawRow],
    *,
    employees: Sequence[Employee],
    stores: Sequence[Store],
    week_start: date | None = None,
) -> ValidationResult:
    if week_start is not None and week_start.weekday() != 0:
        raise ValueError("week_start deve ser uma segunda-feira")

    names = [cell.strip().lower() for cell in header.cells]
    missing = [col for col in COLUMNS if col not in names]
    if missing:
        issues = [CsvIssue(line=header.line, field=col, reason=f"coluna obrigatória ausente: {col}") for col in missing]
        return ValidationResult(None, _summary(file_name, len(rows), week_start, [], issues))
    index = {col: names.index(col) for col in COLUMNS}

    issues: list[CsvIssue] = []
    candidates: list[tuple[RawRow, dict[str, str], date | None]] = []
    for row in rows:
        if len(row.cells) != len(names):
            reason = f"linha com {len(row.cells)} campos; o cabeçalho tem {len(names)}"
            issues.append(CsvIssue(line=row.line, reason=reason))
            continue
        values = {col: row.cells[i].strip() for col, i in index.items()}
        day = _parse_date(values["data"])
        candidates.append((row, values, day))

    if week_start is None:
        week_start = _infer_week([day for _, _, day in candidates if day is not None])

    store_ids = {s.id for s in stores}
    roster = {e.id: e for e in employees}
    parsed: list[_Parsed] = []
    for row, values, day in candidates:
        row_issues = _check_row(row.line, values, day, week_start, store_ids, roster)
        if row_issues:
            issues.extend(row_issues)
            continue
        assert day is not None and week_start is not None
        start_t, end_t = _parse_time(values["inicio"]), _parse_time(values["fim"])
        assert start_t is not None and end_t is not None
        start = datetime.combine(day, start_t)
        end = datetime.combine(day + timedelta(days=1) if end_t < start_t else day, end_t)
        parsed.append(_Parsed(row.line, values["loja_id"], values["pessoa_id"], day, start, end))

    accepted = _drop_overlaps(parsed, issues)
    issues.sort(key=lambda i: i.line)
    schedule = None
    if week_start is not None:
        shifts = [Shift(employee_id=p.employee_id, store_id=p.store_id, start=p.start, end=p.end) for p in accepted]
        schedule = Schedule(week_start=week_start, shifts=shifts)
    return ValidationResult(schedule, _summary(file_name, len(rows), week_start, accepted, issues))


def _check_row(
    line: int,
    values: dict[str, str],
    day: date | None,
    week_start: date | None,
    store_ids: set[str],
    roster: dict[str, Employee],
) -> list[CsvIssue]:
    out: list[CsvIssue] = []

    def add(field: str, reason: str) -> None:
        out.append(CsvIssue(line=line, field=field, reason=reason))

    for col in REQUIRED:
        if not values[col]:
            add(col, f"campo obrigatório vazio: {col}")
    empty = {i.field for i in out}

    if "data" not in empty:
        if day is None:
            add("data", f"data inválida: '{values['data']}' (esperado AAAA-MM-DD)")
        elif week_start is not None and not week_start <= day <= week_start + timedelta(days=6):
            add("data", f"data {day.isoformat()} fora da {_week_label(week_start)}")

    times: dict[str, time] = {}
    for col in ("inicio", "fim"):
        if col in empty:
            continue
        parsed = _parse_time(values[col])
        if parsed is None:
            add(col, f"hora inválida em {col}: '{values[col]}' (esperado HH:MM)")
        else:
            times[col] = parsed
    if len(times) == 2 and times["inicio"] == times["fim"]:
        add("fim", f"turno sem duração: inicio e fim iguais ({values['fim']})")

    store_id, employee_id = values["loja_id"], values["pessoa_id"]
    store_ok = "loja_id" in empty or store_id in store_ids
    if not store_ok:
        add("loja_id", f"loja_id '{store_id}' não existe no quadro de lojas")
    if "pessoa_id" not in empty:
        employee = roster.get(employee_id)
        if employee is None:
            add("pessoa_id", f"pessoa_id '{employee_id}' não existe no quadro de pessoal")
        elif store_ok and "loja_id" not in empty and employee.store_id != store_id:
            add("loja_id", f"pessoa {employee_id} é da loja {employee.store_id} no quadro, não da {store_id}")
    return out


def _drop_overlaps(parsed: list[_Parsed], issues: list[CsvIssue]) -> list[_Parsed]:
    """Na ordem do arquivo: o turno que sobrepõe outro já aceito da mesma pessoa vira problema e sai."""
    accepted: list[_Parsed] = []
    by_employee: dict[str, list[_Parsed]] = defaultdict(list)
    for p in parsed:
        clash = next((q for q in by_employee[p.employee_id] if p.start < q.end and q.start < p.end), None)
        if clash is None:
            accepted.append(p)
            by_employee[p.employee_id].append(p)
            continue
        same = "mesma pessoa e mesma data" if clash.day == p.day else f"mesma pessoa (turno de {clash.day.isoformat()})"
        reason = f"turno sobreposto ao da linha {clash.line}, {same}"
        issues.append(CsvIssue(line=p.line, field="inicio", reason=reason))
    return accepted


def _summary(
    file_name: str, rows: int, week_start: date | None, accepted: list[_Parsed], issues: list[CsvIssue]
) -> ReadSummary:
    minutes = sum(int((p.end - p.start).total_seconds()) // 60 for p in accepted)
    return ReadSummary(
        file_name=file_name,
        rows=rows,
        employees=len({p.employee_id for p in accepted}),
        stores=len({p.store_id for p in accepted}),
        week_start=week_start,
        total_hours=(Decimal(minutes) / 60).quantize(_HOURS),
        issues=issues,
        ok=not issues,
    )


def _infer_week(days: list[date]) -> date | None:
    if not days:
        return None
    counts = Counter(days)
    top = max(counts.values())
    day = min(d for d, n in counts.items() if n == top)
    return day - timedelta(days=day.weekday())


def _week_label(week_start: date) -> str:
    end = week_start + timedelta(days=6)
    first = week_start.strftime("%d/%m" if week_start.year == end.year else "%d/%m/%Y")
    return f"semana de {first} a {end.strftime('%d/%m/%Y')}"


def _parse_date(value: str) -> date | None:
    if not _DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_time(value: str) -> time | None:
    match = _TIME.fullmatch(value)
    if match is None:
        return None
    hour, minute = int(match[1]), int(match[2])
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)
