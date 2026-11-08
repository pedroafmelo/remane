"""Aplica o `ColumnMapping` (do modelo ou da heurística) a todas as linhas da `RawTable` (plano da C6, A1).

O modelo só diz onde estão os dados; quem lê cada linha é este código. Invariantes (seção 6):

1. Nunca turno inventado: cada turno leva a `ShiftEvidence` (células e texto cru) e `verify_evidence` relê as células
   e confere que reproduzem o turno.
2. O mapeamento só aponta para o que existe: `check_mapping` confere cabeçalho literal, índices e papéis.
3. Código de turno sem legenda no arquivo não é fato: vira `assumptions`.
6. Plausibilidade: turno com menos de 1h ou mais de 14h, ou mais de 2 turnos da pessoa no dia, vira problema.

Contrato da borda (D2): a `RawTable` traz todas as linhas do arquivo; índice da linha + 1 = linha física. Depois do
cabeçalho, linhas vazias e linhas cuja primeira célula não vazia começa com `#` são ignoradas.

Identidade (A2) vem depois: aqui a pessoa é a matrícula, se houver, ou o nome com espaço e caixa normalizados, sempre
dentro da mesma loja. O mesmo nome em duas lojas, sobreposto, fica para a identidade (cartão de homônimo).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from escalista.domain.reading import CellRef, ColumnMapping, ColumnRef, DayColumn, RawTable, ShiftCode, ShiftEvidence
from escalista.domain.schedule import CsvIssue

MIN_SHIFT = timedelta(hours=1)
MAX_SHIFT = timedelta(hours=14)
MAX_SHIFTS_PER_DAY = 2
OFF_MARKERS = frozenset({"", "folga", "f", "-", "–", "—"})
_CELL_IN_REASON = 40  # texto de célula citado num motivo é truncado (RN-12)

_T = r"\d{1,2}(?::\d{2}(?::\d{2})?|[hH](?:\d{2})?)"
_TIME = re.compile(r"(\d{1,2})(?::(\d{2})(?::\d{2})?|[hH](\d{2})?)")
_TIME_IN_TEXT = re.compile(rf"(?<![\d:])({_T})(?![\d:])")
_INTERVAL = re.compile(rf"({_T})\s*(?:[-–—]|\s(?:a|às|as|até)\s)\s*({_T})", re.IGNORECASE)
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ]00:00(?::00)?)?")
_ISO_DATETIME = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{1,2}:\d{2})(?::\d{2})?")
_DM_Y = re.compile(r"(\d{1,2})([/.\-])(\d{1,2})\2(\d{4})")
_Y_MD = re.compile(r"(\d{4})([/.\-])(\d{1,2})\2(\d{1,2})")
_HEADER_DATE = re.compile(r"(?<!\d)(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{4}))?(?!\d)")
_WEEKDAY_WORDS = {
    "seg": 0,
    "segunda": 0,
    "ter": 1,
    "terca": 1,
    "qua": 2,
    "quarta": 2,
    "qui": 3,
    "quinta": 3,
    "sex": 4,
    "sexta": 4,
    "sab": 5,
    "sabado": 5,
    "dom": 6,
    "domingo": 6,
}
_WEEKDAY_INDEX = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}


@dataclass(frozen=True)
class MappedShift:
    """Um turno lido do arquivo. Textos crus (aparados); a resolução de pessoa e loja em ids é posterior (A2)."""

    person_name: str
    person_code: str | None
    store: str | None
    start: datetime
    end: datetime
    wage: str | None
    note: str | None
    evidence: ShiftEvidence
    code: str | None = None  # código de turno da célula, quando houver (escala em grade com códigos)


@dataclass(frozen=True)
class MappingResult:
    """Resultado de `apply_mapping`. `rows_read` conta as linhas de dados consideradas (sem vazias nem `#`)."""

    mapping: ColumnMapping
    shifts: list[MappedShift]
    issues: list[CsvIssue]
    assumptions: list[str]
    week_start: date | None
    rows_read: int


# --- invariante 2 -------------------------------------------------------------------------------------------------


def check_mapping(tables: list[RawTable], mapping: ColumnMapping) -> list[str]:
    """Motivos (curtos, em português) pelos quais o mapeamento não aponta para o que existe. Vazio = ok."""
    if mapping.table >= len(tables):
        return [f"tabela {mapping.table} não existe (há {len(tables)})"]
    table = tables[mapping.table]
    if mapping.header_row >= len(table.rows):
        return [f"linha de cabeçalho {mapping.header_row} fora da tabela (há {len(table.rows)} linhas)"]
    header = table.rows[mapping.header_row]
    reasons: list[str] = []

    seen: dict[int, str] = {}
    for role, ref in _roles(mapping):
        if ref.index >= len(header):
            reasons.append(f"coluna {ref.index} ({role}) fora do cabeçalho (há {len(header)} colunas)")
            continue
        if _norm(header[ref.index]) != _norm(ref.header):
            reasons.append(
                f"{role}: cabeçalho '{_clip(ref.header)}' não bate com a coluna {ref.index} "
                f"('{_clip(header[ref.index])}')"
            )
        if ref.index in seen:
            reasons.append(f"coluna {ref.index} usada em dois papéis: {seen[ref.index]} e {role}")
        else:
            seen[ref.index] = role

    if mapping.layout == "long":
        has_times = mapping.start is not None and mapping.end is not None
        if mapping.date is None or not (has_times or mapping.shift is not None):
            reasons.append("layout long precisa de date e de start+end ou shift")
    else:
        if not mapping.day_columns:
            reasons.append("layout grid precisa de day_columns")
        for dc in mapping.day_columns:
            reasons += _day_column_reasons(dc)

    for code in mapping.shift_codes:
        if not code.off and (code.start is None or code.end is None):
            reasons.append(f"código '{code.code}' sem start/end e sem off")
    return reasons


def _roles(mapping: ColumnMapping) -> list[tuple[str, ColumnRef]]:
    named = ("person", "person_code", "store", "date", "start", "end", "shift", "wage", "notes")
    roles = [(name, ref) for name in named if (ref := getattr(mapping, name)) is not None]
    roles += [(f"dia '{_clip(dc.col.header)}'", dc.col) for dc in mapping.day_columns]
    return roles


def _day_column_reasons(dc: DayColumn) -> list[str]:
    label = f"dia '{_clip(dc.col.header)}'"
    out: list[str] = []
    if dc.day is not None and dc.weekday is not None and dc.day.weekday() != _WEEKDAY_INDEX[dc.weekday]:
        out.append(f"{label}: day {dc.day.isoformat()} não é {dc.weekday}")
    wd = dc.day.weekday() if dc.day is not None else _WEEKDAY_INDEX[dc.weekday] if dc.weekday else None
    header_wd = _header_weekday(dc.col.header)
    if wd is not None and header_wd is not None and wd != header_wd:
        out.append(f"{label}: o dia da semana do cabeçalho não bate com o mapeamento")
    if dc.day is not None:
        found = _ISO_DATE.search(dc.col.header) or _HEADER_DATE.search(dc.col.header)
        if found is not None and not _header_date_matches(found, dc.day):
            out.append(f"{label}: a data do cabeçalho não é {dc.day.isoformat()}")
    return out


def _header_weekday(header: str) -> int | None:
    first = re.split(r"[\s\-/.,]+", _fold(header).strip(), maxsplit=1)[0]
    return _WEEKDAY_WORDS.get(first)


def _header_date_matches(found: re.Match[str], day: date) -> bool:
    if found.re is _ISO_DATE:
        return (int(found[1]), int(found[2]), int(found[3])) == (day.year, day.month, day.day)
    a, b, year = int(found[1]), int(found[2]), found[3]
    if year is not None and int(year) != day.year:
        return False
    return (a, b) in {(day.day, day.month), (day.month, day.day)}


# --- aplicação ------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Err:
    field: str
    col: int
    reason: str


@dataclass(frozen=True)
class _Times:
    start: datetime
    end: datetime
    code: str | None
    start_col: int  # célula que o motivo de plausibilidade cita


@dataclass
class _Candidate:
    row: int
    times: _Times
    person_name: str
    person_code: str | None
    store: str | None
    wage: str | None
    note: str | None
    cells: list[int]  # colunas da linha `row` usadas
    header_col: int | None = None  # grade: a célula do cabeçalho do dia também é evidência


def apply_mapping(tables: list[RawTable], mapping: ColumnMapping, *, week_start: date | None = None) -> MappingResult:
    """Lê todas as linhas com o mapeamento. Nunca preenche valor que não está na célula: o que não dá para ler vira
    `CsvIssue` com a célula (linha física, tabela, coluna)."""
    reasons = check_mapping(tables, mapping)
    if reasons:
        name = tables[mapping.table].name if mapping.table < len(tables) else None
        issues = [CsvIssue(line=mapping.header_row + 1, field="mapeamento", reason=r, table=name) for r in reasons]
        return MappingResult(mapping, [], issues, [], week_start, 0)

    table = tables[mapping.table]
    data_rows = _data_rows(table, mapping.header_row)
    issues: list[CsvIssue] = []

    def add(row: int, err: _Err) -> None:
        issues.append(CsvIssue(line=row + 1, field=err.field, reason=err.reason, table=table.name, col=err.col))

    candidates: list[_Candidate] = []
    if mapping.layout == "long":
        for r, row in data_rows:
            _read_long_row(r, row, mapping, candidates, add)
    else:
        if week_start is None:
            week_start = _infer_week([dc.day for dc in mapping.day_columns if dc.day is not None])
        resolved: list[tuple[int, date]] = []
        for dc in mapping.day_columns:
            day = _column_day(dc, week_start)
            if isinstance(day, str):
                add(mapping.header_row, _Err("dia", dc.col.index, day))
            else:
                resolved.append((dc.col.index, day))
        for r, row in data_rows:
            _read_grid_row(r, row, mapping, resolved, candidates, add)

    accepted = _filter(candidates, mapping, add)
    if week_start is None:
        week_start = _infer_week([c.times.start.date() for c in accepted])
    shifts = [_to_shift(i, c, mapping, table) for i, c in enumerate(accepted)]
    used = {c.times.code for c in candidates if c.times.code is not None} | _off_codes_used(data_rows, mapping)
    issues.sort(key=lambda i: (i.line, i.col if i.col is not None else -1))
    return MappingResult(
        mapping=mapping,
        shifts=shifts,
        issues=issues,
        assumptions=_assumptions(tables, mapping, used),
        week_start=week_start,
        rows_read=len(data_rows),
    )


def _data_rows(table: RawTable, header_row: int) -> list[tuple[int, list[str]]]:
    out = []
    for r in range(header_row + 1, len(table.rows)):
        row = table.rows[r]
        first = next((c.strip() for c in row if c.strip()), None)
        if first is None or first.startswith("#"):
            continue
        out.append((r, row))
    return out


def _cell(row: list[str], ref: ColumnRef | None) -> str:
    if ref is None or ref.index >= len(row):
        return ""
    return row[ref.index]


def _opt(text: str) -> str | None:
    return text.strip() or None


def _read_long_row(
    r: int, row: list[str], m: ColumnMapping, out: list[_Candidate], add: Callable[[int, _Err], None]
) -> None:
    def get(col: int) -> str:
        return row[col] if col < len(row) else ""

    times = _long_times(get, m)
    if times is None:
        return
    person = _cell(row, m.person).strip()
    if isinstance(times, _Err):
        add(r, times)
        return
    if not person:
        add(r, _Err("pessoa", m.person.index, "linha com turno e sem pessoa"))
        return
    cols = [ref.index for ref in (m.person, m.person_code, m.store, m.date) if ref is not None]
    cols += [ref.index for ref in ((m.start, m.end) if _uses_start_end(m) else (m.shift,)) if ref is not None]
    cols += [ref.index for ref in (m.wage, m.notes) if ref is not None and _cell(row, ref).strip()]
    out.append(
        _Candidate(
            row=r,
            times=times,
            person_name=person,
            person_code=_opt(_cell(row, m.person_code)),
            store=_opt(_cell(row, m.store)),
            wage=_opt(_cell(row, m.wage)),
            note=_opt(_cell(row, m.notes)),
            cells=cols,
        )
    )


def _long_times(get: Callable[[int], str], m: ColumnMapping) -> _Times | _Err | None:
    """Turno de uma linha `long`. `None` = linha sem turno (folga ou só rótulo); `_Err` = célula ilegível."""
    assert m.date is not None
    use_times = _uses_start_end(m)
    time_refs = [m.start, m.end] if use_times else [m.shift]
    texts = [get(ref.index).strip() for ref in time_refs if ref is not None]
    date_text = get(m.date.index).strip()
    if all(_is_off(t, m.shift_codes) for t in texts):
        return None  # folga, ou linha só com rótulo
    day = parse_date(date_text, m.date_order)
    if day is None:
        return _Err("data", m.date.index, f"data ilegível: '{_clip(date_text)}' (ordem {m.date_order})")
    if use_times:
        assert m.start is not None and m.end is not None
        return _start_end(day, texts[0], texts[1], m.start.index, m.end.index)
    assert m.shift is not None
    return _shift_cell(day, texts[0], m.shift.index, m.shift_codes)


def _uses_start_end(m: ColumnMapping) -> bool:
    return m.layout == "long" and m.start is not None and m.end is not None


def _start_end(day: date, a: str, b: str, a_col: int, b_col: int) -> _Times | _Err:
    if _fold(a) in OFF_MARKERS:
        return _Err("inicio", a_col, "início vazio com fim preenchido")
    if _fold(b) in OFF_MARKERS:
        return _Err("fim", b_col, "fim vazio com início preenchido")
    start: datetime | None
    if dt := _ISO_DATETIME.fullmatch(a):
        start = _combine(dt[1], dt[2])
        if start is not None and start.date() != day:
            return _Err("inicio", a_col, f"início '{_clip(a)}' em outra data que a da linha")
    else:
        t = parse_time(a)
        start = datetime.combine(day, t) if t is not None else None
    if start is None:
        return _Err("inicio", a_col, f"hora de início ilegível: '{_clip(a)}'")
    if dt := _ISO_DATETIME.fullmatch(b):
        end = _combine(dt[1], dt[2])
        if end is None:
            return _Err("fim", b_col, f"hora de fim ilegível: '{_clip(b)}'")
        if end <= start:
            return _Err("fim", b_col, f"fim '{_clip(b)}' não é depois do início")
        return _Times(start, end, None, a_col)
    t = parse_time(b, allow_24=True)
    if t is None:
        return _Err("fim", b_col, f"hora de fim ilegível: '{_clip(b)}'")
    return _Times(start, _end_after(start, t), None, a_col)


def _shift_cell(day: date, text: str, col: int, codes: list[ShiftCode]) -> _Times | _Err | None:
    """Célula com intervalo, código ou folga. `None` = folga."""
    code = _match_code(text, codes)
    if code is not None:
        if code.off:
            return None
        assert code.start is not None and code.end is not None  # check_mapping garante
        start = datetime.combine(day, code.start)
        return _Times(start, _end_after(start, code.end), code.code, col)
    if _fold(text) in OFF_MARKERS:
        return None
    interval = _INTERVAL.fullmatch(text.strip())
    if interval is not None:
        a, b = parse_time(interval[1]), parse_time(interval[2], allow_24=True)
        if a is not None and b is not None:
            start = datetime.combine(day, a)
            return _Times(start, _end_after(start, b), None, col)
    return _Err("turno", col, f"turno ilegível: '{_clip(text)}'")


def _is_off(text: str, codes: list[ShiftCode]) -> bool:
    code = _match_code(text, codes)
    return code.off if code is not None else _fold(text) in OFF_MARKERS


def _match_code(text: str, codes: list[ShiftCode]) -> ShiftCode | None:
    stripped = text.strip()
    if not stripped:
        return None
    for code in codes:
        if code.code.strip() == stripped:
            return code
    folded = stripped.casefold()
    return next((c for c in codes if c.code.strip().casefold() == folded), None)


def _column_day(dc: DayColumn, week_start: date | None) -> date | str:
    if dc.day is not None:
        return dc.day
    if dc.weekday is None:
        return f"coluna '{_clip(dc.col.header)}' sem data nem dia da semana"
    if week_start is None:
        return f"coluna '{_clip(dc.col.header)}' só tem o dia da semana e a semana não é conhecida"
    return week_start + timedelta(days=(_WEEKDAY_INDEX[dc.weekday] - week_start.weekday()) % 7)


def _read_grid_row(
    r: int,
    row: list[str],
    m: ColumnMapping,
    days: list[tuple[int, date]],
    out: list[_Candidate],
    add: Callable[[int, _Err], None],
) -> None:
    person = _cell(row, m.person).strip()
    found: list[tuple[int, _Times]] = []
    for col, day in days:
        text = row[col] if col < len(row) else ""
        times = _shift_cell(day, text, col, m.shift_codes)
        if isinstance(times, _Err):
            add(r, times)
        elif times is not None:
            found.append((col, times))
    if found and not person:
        add(r, _Err("pessoa", m.person.index, "linha com turno e sem pessoa"))
        return
    base = [ref.index for ref in (m.person, m.person_code, m.store) if ref is not None]
    extra = [ref.index for ref in (m.wage, m.notes) if ref is not None and _cell(row, ref).strip()]
    for col, times in found:
        out.append(
            _Candidate(
                row=r,
                times=times,
                person_name=person,
                person_code=_opt(_cell(row, m.person_code)),
                store=_opt(_cell(row, m.store)),
                wage=_opt(_cell(row, m.wage)),
                note=_opt(_cell(row, m.notes)),
                cells=[*base, col, *extra],
                header_col=col,
            )
        )


def _filter(candidates: list[_Candidate], m: ColumnMapping, add: Callable[[int, _Err], None]) -> list[_Candidate]:
    """Na ordem do arquivo: plausibilidade, duplicata exata, sobreposição e limite de turnos por dia."""
    accepted: list[_Candidate] = []
    by_person: dict[tuple[str, str], list[_Candidate]] = defaultdict(list)
    for c in candidates:
        t = c.times
        length = t.end - t.start
        if length < MIN_SHIFT or length > MAX_SHIFT:
            add(c.row, _Err("inicio" if _uses_start_end(m) else "turno", t.start_col, _implausible(t)))
            continue
        key = (_norm(c.person_code) if c.person_code else _norm(c.person_name), _norm(c.store or ""))
        mine = by_person[key]
        dup = next((o for o in mine if (o.times.start, o.times.end) == (t.start, t.end)), None)
        if dup is not None:
            add(c.row, _Err("turno", t.start_col, f"duplicada da linha {dup.row + 1}"))
            continue
        clash = next((o for o in mine if t.start < o.times.end and o.times.start < t.end), None)
        if clash is not None:
            add(c.row, _Err("turno", t.start_col, f"turno sobreposto ao da linha {clash.row + 1}, mesma pessoa"))
            continue
        if sum(o.times.start.date() == t.start.date() for o in mine) >= MAX_SHIFTS_PER_DAY:
            reason = f"mais de 2 turnos de {_clip(c.person_name)} em {t.start:%d/%m/%Y}"
            add(c.row, _Err("turno", t.start_col, reason))
            continue
        accepted.append(c)
        mine.append(c)
    return accepted


def _implausible(t: _Times) -> str:
    minutes = int((t.end - t.start).total_seconds()) // 60
    next_day = " do dia seguinte" if t.end.date() > t.start.date() else ""
    return (
        f"turno de {minutes // 60}h{minutes % 60:02d} ({t.start:%H:%M} às {t.end:%H:%M}{next_day}): "
        "fora de 1h a 14h; início e fim trocados?"
    )


def _to_shift(index: int, c: _Candidate, m: ColumnMapping, table: RawTable) -> MappedShift:
    refs = [CellRef(table=m.table, row=c.row, col=col) for col in c.cells]
    if c.header_col is not None:
        refs.append(CellRef(table=m.table, row=m.header_row, col=c.header_col))
    raw = [_raw_at(table, ref) for ref in refs]
    return MappedShift(
        person_name=c.person_name,
        person_code=c.person_code,
        store=c.store,
        start=c.times.start,
        end=c.times.end,
        wage=c.wage,
        note=c.note,
        evidence=ShiftEvidence(shift_index=index, cells=refs, raw=raw),
        code=c.times.code,
    )


def _raw_at(table: RawTable, ref: CellRef) -> str:
    row = table.rows[ref.row]
    return row[ref.col] if ref.col < len(row) else ""


# --- invariante 3 -------------------------------------------------------------------------------------------------


def _off_codes_used(data_rows: list[tuple[int, list[str]]], m: ColumnMapping) -> set[str]:
    off = [c for c in m.shift_codes if c.off]
    if not off:
        return set()
    cols = [dc.col.index for dc in m.day_columns] if m.layout == "grid" else [m.shift.index] if m.shift else []
    used: set[str] = set()
    for _, row in data_rows:
        for col in cols:
            code = _match_code(row[col] if col < len(row) else "", off)
            if code is not None:
                used.add(code.code)
    return used


def _assumptions(tables: list[RawTable], m: ColumnMapping, used: set[str]) -> list[str]:
    """Códigos usados cuja legenda (`evidence`) não está no arquivo, ou não traz os horários do código."""
    text = _norm(" ".join(cell for t in tables for row in t.rows for cell in row))
    out: list[str] = []
    for code in m.shift_codes:
        if code.code not in used or _legend_confirms(code, text):
            continue
        if code.off:
            out.append(f"{code.code} = folga, inferido pelo agente")
        else:
            assert code.start is not None and code.end is not None
            out.append(f"{code.code} = {code.start:%H:%M} às {code.end:%H:%M}, inferido pelo agente")
    return out


def _legend_confirms(code: ShiftCode, file_text: str) -> bool:
    if not code.evidence or _norm(code.evidence) not in file_text:
        return False
    if code.off:
        return True
    times = {t for m in _TIME_IN_TEXT.finditer(code.evidence) if (t := parse_time(m[1], allow_24=True)) is not None}
    return code.start in times and code.end in times


# --- invariante 1 -------------------------------------------------------------------------------------------------


def verify_evidence(tables: list[RawTable], result: MappingResult) -> list[str]:
    """Relê as células de cada `ShiftEvidence` e confere que reproduzem o turno. Vazio = nenhum turno inventado."""
    m = result.mapping
    problems: list[str] = []
    for i, shift in enumerate(result.shifts):
        problem = _verify_one(tables, m, result.week_start, i, shift)
        if problem is not None:
            problems.append(f"turno {i} ({_clip(shift.person_name)}, {shift.start:%d/%m %H:%M}): {problem}")
    return problems


def _verify_one(
    tables: list[RawTable], m: ColumnMapping, week_start: date | None, index: int, shift: MappedShift
) -> str | None:
    ev = shift.evidence
    if ev.shift_index != index:
        return f"evidência aponta para o turno {ev.shift_index}"
    if not ev.cells or len(ev.cells) != len(ev.raw):
        return "evidência sem células ou com texto faltando"
    if m.table >= len(tables):
        return "tabela do mapeamento não existe"
    table = tables[m.table]
    for cell, raw in zip(ev.cells, ev.raw, strict=True):
        if cell.table != m.table or cell.row >= len(table.rows):
            return f"célula fora da tabela: {cell}"
        if _raw_at(table, cell) != raw:
            return f"célula linha {cell.row + 1}, coluna {cell.col} não tem mais '{_clip(raw)}'"
    data_rows = {c.row for c in ev.cells if c.row != m.header_row}
    if len(data_rows) != 1:
        return "evidência espalhada por mais de uma linha"
    (row,) = data_rows
    if row <= m.header_row or row not in {r for r, _ in _data_rows(table, m.header_row)}:
        return "evidência fora das linhas de dados"
    by_col = {c.col: raw for c, raw in zip(ev.cells, ev.raw, strict=True) if c.row == row}

    def get(col: int) -> str:
        if col not in by_col:
            raise KeyError(col)
        return by_col[col]

    try:
        if get(m.person.index).strip() != shift.person_name:
            return "nome não bate com a célula"
        if m.layout == "long":
            times = _long_times(get, m)
        else:
            header_cols = {c.col for c in ev.cells if c.row == m.header_row}
            dcs = [dc for dc in m.day_columns if dc.col.index in header_cols]
            if len(dcs) != 1:
                return "evidência sem a coluna do dia"
            day = _column_day(dcs[0], week_start)
            if isinstance(day, str):
                return day
            times = _shift_cell(day, get(dcs[0].col.index), dcs[0].col.index, m.shift_codes)
    except KeyError as missing:
        return f"evidência sem a célula da coluna {missing.args[0]}"
    if not isinstance(times, _Times):
        return "as células não produzem turno"
    if (times.start, times.end, times.code) != (shift.start, shift.end, shift.code):
        return f"as células dão {times.start:%d/%m %H:%M}–{times.end:%d/%m %H:%M}, não o turno"
    return None


# --- leitura de datas e horas ---------------------------------------------------------------------------------------


def parse_date(text: str, order: str = "dmy") -> date | None:
    """Data pela ordem do mapeamento (`dmy`, `ymd`, `mdy`; separador `/`, `-` ou `.`; ano com 4 dígitos).
    ISO (`2027-01-11`, também com `T00:00`) é sempre aceito."""
    s = text.strip()
    try:
        if found := _ISO_DATE.fullmatch(s):
            return date(int(found[1]), int(found[2]), int(found[3]))
        if order in ("dmy", "mdy") and (found := _DM_Y.fullmatch(s)):
            a, b, year = int(found[1]), int(found[3]), int(found[4])
            return date(year, b, a) if order == "dmy" else date(year, a, b)
        if order == "ymd" and (found := _Y_MD.fullmatch(s)):
            return date(int(found[1]), int(found[3]), int(found[4]))
    except ValueError:
        return None
    return None


def parse_time(text: str, *, allow_24: bool = False) -> time | None:
    """Hora em `08:00`, `8:00`, `08:00:00`, `8h`, `08h00`. `24:00` só quando `allow_24` (fim do turno)."""
    found = _TIME.fullmatch(text.strip())
    if found is None:
        return None
    hour = int(found[1])
    minute = int(found[2] or found[3] or 0)
    if allow_24 and hour == 24 and minute == 0:
        return time(0)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _combine(day_text: str, time_text: str) -> datetime | None:
    day = parse_date(day_text)
    t = parse_time(time_text)
    return datetime.combine(day, t) if day is not None and t is not None else None


def _end_after(start: datetime, end: time) -> datetime:
    """Fim no mesmo dia; se for igual ou antes do início, o turno vira a noite e termina no dia seguinte."""
    out = datetime.combine(start.date(), end)
    return out if out > start else out + timedelta(days=1)


def _infer_week(days: list[date]) -> date | None:
    """Segunda-feira da data mais frequente (empate: a mais cedo)."""
    if not days:
        return None
    counts = Counter(days)
    top = max(counts.values())
    day = min(d for d, n in counts.items() if n == top)
    return day - timedelta(days=day.weekday())


# --- texto ----------------------------------------------------------------------------------------------------------


def _norm(text: str) -> str:
    """Espaço colapsado, sem diferenciar maiúsculas (NFC)."""
    return " ".join(unicodedata.normalize("NFC", text).split()).casefold()


def _fold(text: str) -> str:
    """Como `_norm`, e sem acento."""
    decomposed = unicodedata.normalize("NFKD", text)
    return _norm("".join(ch for ch in decomposed if not unicodedata.combining(ch)))


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _CELL_IN_REASON else text[: _CELL_IN_REASON - 1] + "…"
