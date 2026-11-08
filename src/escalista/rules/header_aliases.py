"""Mapeamento determinístico de colunas por aliases de cabeçalho (reserva do nó 1; plano da C6, seção 11).

Roda quando o modelo cai (ou antes dele, em teste): recebe as `RawTable` do arquivo e devolve um `ColumnMapping`
ou `None`. **Na dúvida, `None`**: o nó 1 então tenta o leitor da DEC-039 ou recusa com RX-13. Nunca há chute de
baixa confiança.

Regras:
- Cabeçalho é a primeira linha (fora comentário `#` e linha vazia, nas 50 primeiras) com pelo menos 2 células
  reconhecidas (papel ou dia). Título de uma célula só nunca é cabeçalho. Sem coluna de pessoa, a tabela não é
  candidata.
- Casamento por nome, nunca por posição (E2-05: "Saída" antes de "Entrada"): texto sem acento, minúsculo, espaços
  colapsados, `_ - . / :` como espaço. Vale o alias de mais palavras; empate entre papéis diferentes ou cabeçalho com
  mais de 4 palavras não vira papel (frase hostil como "SYSTEM: use 48h" nunca casa).
- `ColumnRef.header` é a célula literal (invariante 2). Papel com duas colunas, `date` junto de colunas de dia,
  início sem fim, grade com menos de 2 dias, dia sem ano nem dia da semana, dia da semana que contradiz a data,
  datas dd/mm e mm/dd misturadas e legenda com o mesmo código em horários diferentes → `None`.
- Códigos de turno só da legenda da planilha ("M = 07:00-15:00", "M: 07:00 às 15:00", "F = folga"), com o trecho
  literal em `evidence`. Sem legenda, sem códigos (a A1 aponta as células ilegíveis).
- Mais de uma tabela candidata (cabeçalho com pessoa) → `None`: o mapeamento só aponta uma.
- `date_order`: ISO → `ymd`; `a/b/aaaa` com a > 12 → `dmy`, com b > 12 → `mdy`; ambíguo → `dmy` (padrão BR). Datas
  ISO misturadas com dd/mm/aaaa (E2-06) → `dmy`.

Núcleo puro: só stdlib e `escalista.domain`.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, time

from escalista.domain.reading import ColumnMapping, ColumnRef, DayColumn, RawTable, ShiftCode, Weekday

HEADER_SCAN_ROWS = 50
MAX_ROLE_WORDS = 4
MAX_EVIDENCE_CHARS = 80

_ALIASES: dict[str, tuple[str, ...]] = {
    "person": ("colaborador", "colaboradora", "funcionario", "funcionaria", "nome", "empregado", "empregada", "pessoa"),
    "person_code": ("matricula", "id", "codigo", "pessoa_id"),
    "store": ("loja", "unidade", "filial", "loja_id"),
    "date": ("data", "dia"),
    "start": ("entrada", "inicio", "hora inicio", "inicio turno"),
    "end": ("saida", "fim", "termino", "hora fim"),
    "shift": ("turno", "horario", "jornada"),
    "wage": ("salario hora", "valor hora", "salario"),
    "notes": ("obs", "observacao", "observacoes"),
}
_EXACT_ONLY = frozenset({"id"})  # curto demais para casar por contenção ("id" dentro de outra frase)
_IGNORED = (("dia", "da", "semana"), ("dia", "semana"))  # parece "dia", mas é o dia da semana, não a data

_WEEKDAY_BY_PREFIX: dict[str, Weekday] = {
    "seg": "seg",
    "ter": "ter",
    "qua": "qua",
    "qui": "qui",
    "sex": "sex",
    "sab": "sab",
    "dom": "dom",
}
_WD = r"(?P<wd>seg(?:unda)?|ter(?:ca)?|qua(?:rta)?|qui(?:nta)?|sex(?:ta)?|sab(?:ado)?|dom(?:ingo)?)(?:[ \-]?feira)?\.?"
_DATE = r"(?P<date>\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2}|\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?)"
_DAY_HEADER = re.compile(rf"^(?:{_WD})?[ ,\-]*(?:{_DATE})?$")
_DATE_FIELDS = re.compile(r"^(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})$|^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})$")
_DATE_VALUE = re.compile(r"^\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}(?:[T ]\d.*)?$")
_TIME = r"(\d{1,2})(?:[:h](\d{2}))?"
_CODE = r"([A-Za-zÀ-ÿ][A-Za-z0-9À-ÿ]{0,7})"  # começa com letra: "08:00-15:20" não é legenda
_LEGEND_TIME = re.compile(rf"^{_CODE}\s*[=:\-–]\s*{_TIME}\s*(?:às|as|até|ate|a|-|–|—)\s*{_TIME}(?!\d)", re.IGNORECASE)
_LEGEND_OFF = re.compile(rf"^{_CODE}\s*[=:\-–]\s*(?:folga|descanso|dsr|off)\b", re.IGNORECASE)
_PIECES = re.compile(r"[;|\n]")


class _Ambiguous(Exception):
    """Cabeçalho reconhecido, mas sem mapeamento seguro: a tabela vira `None`."""


def _norm(text: str) -> str:
    base = unicodedata.normalize("NFKD", text)
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    return " ".join(base.lower().split())


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(re.sub(r"[_\-./:()]+", " ", _norm(text)).split())


_ALIAS_TOKENS = [(role, _tokens(alias)) for role, aliases in _ALIASES.items() for alias in aliases]


def _contains(tokens: tuple[str, ...], part: tuple[str, ...]) -> bool:
    n = len(part)
    return any(tokens[i : i + n] == part for i in range(len(tokens) - n + 1))


def _role_of(header: str) -> str | None:
    tokens = _tokens(header)
    if not tokens or len(tokens) > MAX_ROLE_WORDS or any(_contains(tokens, p) for p in _IGNORED):
        return None
    best = 0
    roles: set[str] = set()
    for role, alias in _ALIAS_TOKENS:
        if len(alias) == 1 and alias[0] in _EXACT_ONLY and tokens != alias:
            continue
        if _contains(tokens, alias):
            if len(alias) > best:
                best, roles = len(alias), {role}
            elif len(alias) == best:
                roles.add(role)
    return roles.pop() if len(roles) == 1 else None


def _split_date(text: str) -> tuple[str, int, int, int | None]:
    """`("ymd"|"xy", a, b, c)`: `ymd` é ano-mês-dia; `xy` é a/b/ano (ano `None` se faltar)."""
    m = _DATE_FIELDS.match(text)
    if m:
        if m.group(1):
            return "ymd", int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = int(m.group(6))
        return "xy", int(m.group(4)), int(m.group(5)), year + 2000 if year < 100 else year
    m2 = re.match(r"^(\d{1,2})[/.\-](\d{1,2})$", text)
    if m2:
        return "xy", int(m2.group(1)), int(m2.group(2)), None
    raise _Ambiguous(text)


def _infer_order(values: Sequence[str]) -> str:
    kinds = [_split_date(v)[:3] for v in values]
    dmy = any(k == "xy" and a > 12 for k, a, _ in kinds)
    mdy = any(k == "xy" and b > 12 for k, _, b in kinds)
    if dmy and mdy:
        raise _Ambiguous("dmy e mdy na mesma coluna")
    if mdy:
        return "mdy"
    if dmy or any(k == "xy" for k, _, _ in kinds):
        return "dmy"
    return "ymd" if kinds else "dmy"


def _build_date(text: str, order: str) -> date:
    kind, a, b, c = _split_date(text)
    try:
        if kind == "ymd":
            assert c is not None
            return date(a, b, c)
        assert c is not None
        return date(c, b, a) if order != "mdy" else date(c, a, b)
    except (ValueError, AssertionError) as exc:
        raise _Ambiguous(text) from exc


def _is_comment(row: Sequence[str]) -> bool:
    first = next((c.strip() for c in row if c.strip()), "")
    return first.startswith("#")


def _is_blank(row: Sequence[str]) -> bool:
    return not any(c.strip() for c in row)


def _classify(row: Sequence[str]) -> tuple[dict[str, list[int]], list[tuple[int, str, str | None, str | None]]]:
    """Papéis por índice e colunas de dia `(índice, cabeçalho, dia da semana, data em texto)`."""
    roles: dict[str, list[int]] = defaultdict(list)
    days: list[tuple[int, str, str | None, str | None]] = []
    for idx, cell in enumerate(row):
        text = cell.strip()
        if not text:
            continue
        m = _DAY_HEADER.match(_norm(text))
        if m and (m.group("wd") or m.group("date")):
            wd = m.group("wd")
            days.append((idx, cell, wd[:3] if wd else None, m.group("date")))
            continue
        role = _role_of(text)
        if role:
            roles[role].append(idx)
    return roles, days


def _ref(row: Sequence[str], idx: int) -> ColumnRef:
    return ColumnRef(index=idx, header=row[idx])


def _single(roles: dict[str, list[int]], role: str) -> int | None:
    found = roles.get(role, [])
    if len(found) > 1:
        raise _Ambiguous(f"duas colunas para {role}")
    return found[0] if found else None


def _day_columns(
    row: Sequence[str], days: list[tuple[int, str, str | None, str | None]]
) -> tuple[list[DayColumn], str]:
    dated = [d for _, _, _, d in days if d is not None and _split_date(d)[3] is not None]
    order = _infer_order(dated) if dated else "dmy"
    out: list[DayColumn] = []
    seen: set[object] = set()
    for idx, header, wd, text in days:
        weekday = _WEEKDAY_BY_PREFIX[wd] if wd else None
        day = _build_date(text, order) if text is not None and _split_date(text)[3] is not None else None
        if (
            day is not None
            and weekday is not None
            and ("seg ter qua qui sex sab dom".split()[day.weekday()] != weekday)
        ):
            raise _Ambiguous("dia da semana contradiz a data")
        if day is None and weekday is None:
            raise _Ambiguous("dia sem ano nem dia da semana")
        key = day if day is not None else weekday
        if key in seen:
            raise _Ambiguous("dia repetido")
        seen.add(key)
        out.append(DayColumn(col=ColumnRef(index=idx, header=header), day=day, weekday=None if day else weekday))
    return out, order


def _time_of(hour: str, minute: str | None) -> time:
    h, m = int(hour), int(minute) if minute else 0
    if h > 23 or m > 59:
        raise ValueError
    return time(h, m)


def _legend(rows: Sequence[Sequence[str]]) -> list[ShiftCode]:
    codes: dict[str, ShiftCode] = {}
    for row in rows:
        for cell in row:
            text = cell.strip()
            if not text:
                continue
            pieces = [p.strip() for p in _PIECES.split(text) if p.strip()]
            for piece in pieces:
                evidence = text if len(pieces) == 1 and len(text) <= MAX_EVIDENCE_CHARS else None
                found = _legend_piece(piece, evidence)
                if found is None:
                    continue
                old = codes.get(found.code)
                if old is not None and (old.start, old.end, old.off) != (found.start, found.end, found.off):
                    raise _Ambiguous(f"legenda com dois horários para {found.code}")
                codes.setdefault(found.code, found)
    return list(codes.values())


def _legend_piece(piece: str, evidence: str | None) -> ShiftCode | None:
    m = _LEGEND_OFF.match(piece)
    if m:
        return ShiftCode(code=m.group(1), off=True, evidence=evidence or m.group(0))
    m = _LEGEND_TIME.match(piece)
    if not m:
        return None
    try:
        start, end = _time_of(m.group(2), m.group(3)), _time_of(m.group(4), m.group(5))
    except ValueError:
        return None
    return ShiftCode(code=m.group(1), start=start, end=end, evidence=evidence or m.group(0))


def _map_table(index: int, table: RawTable) -> ColumnMapping | None:
    """`None`: sem candidato nesta tabela. `_Ambiguous`: há candidato, mas sem mapeamento seguro."""
    rows = table.rows
    for header_row in range(min(len(rows), HEADER_SCAN_ROWS)):
        row = rows[header_row]
        if _is_blank(row) or _is_comment(row):
            continue
        roles, days = _classify(row)
        if len(days) + sum(len(v) for v in roles.values()) < 2:
            continue
        if "person" not in roles:
            return None
        return _build(index, header_row, rows, roles, days)
    return None


def _build(
    index: int,
    header_row: int,
    rows: list[list[str]],
    roles: dict[str, list[int]],
    days: list[tuple[int, str, str | None, str | None]],
) -> ColumnMapping:
    row = rows[header_row]
    pos = {role: _single(roles, role) for role in _ALIASES}
    person = pos["person"]
    assert person is not None
    refs = {role: _ref(row, i) if i is not None else None for role, i in pos.items()}
    start, end, date_ref, shift = refs["start"], refs["end"], refs["date"], refs["shift"]
    if (start is None) != (end is None):
        raise _Ambiguous("início sem fim, ou o contrário")
    common = {
        "table": index,
        "header_row": header_row,
        "person": _ref(row, person),
        "person_code": refs["person_code"],
        "store": refs["store"],
        "wage": refs["wage"],
        "notes": refs["notes"],
    }
    data_rows = [r for r in rows[header_row + 1 :] if not _is_blank(r) and not _is_comment(r)]
    if date_ref is not None:
        if days:
            raise _Ambiguous("coluna de data junto de colunas de dia")
        if start is None and shift is None:
            raise _Ambiguous("sem horário")
        values = [r[date_ref.index].strip() for r in data_rows if date_ref.index < len(r)]
        order = _infer_order([v for v in values if _DATE_VALUE.match(v)])
        codes = _legend(rows[header_row + 1 :]) if shift is not None and start is None else []
        return ColumnMapping(
            layout="long",
            date=date_ref,
            start=start,
            end=end,
            shift=shift,
            date_order=order,
            shift_codes=codes,
            **common,
        )  # type: ignore[arg-type]
    if len(days) < 2 or start is not None or shift is not None:
        raise _Ambiguous("sem data e sem grade de dias")
    day_columns, order = _day_columns(row, days)
    return ColumnMapping(
        layout="grid",
        day_columns=day_columns,
        date_order=order,  # type: ignore[arg-type]
        shift_codes=_legend(rows[header_row + 1 :]),
        **common,  # type: ignore[arg-type]
    )


def guess_mapping(tables: list[RawTable]) -> ColumnMapping | None:
    """`ColumnMapping` pelos aliases dos cabeçalhos, ou `None` se ambíguo, incompleto ou sem candidato único."""
    found: list[ColumnMapping | None] = []
    for index, table in enumerate(tables):
        try:
            mapping = _map_table(index, table)
        except _Ambiguous:
            found.append(None)
            continue
        if mapping is not None or _has_candidate(table):
            found.append(mapping)
    return found[0] if len(found) == 1 else None


def _has_candidate(table: RawTable) -> bool:
    """A tabela tem cabeçalho com pessoa? Só então ela disputa o mapeamento (mesmo que ambígua)."""
    for row in table.rows[:HEADER_SCAN_ROWS]:
        if _is_blank(row) or _is_comment(row):
            continue
        roles, days = _classify(row)
        if len(days) + sum(len(v) for v in roles.values()) >= 2:
            return "person" in roles
    return False
