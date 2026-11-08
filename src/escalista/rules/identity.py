"""Identidade das pessoas lidas do arquivo (plano da C6, A2; seção 7). Nunca há fusão automática por parecença.

- **Id estável:** matrícula → `m-<matrícula normalizada>`; senão `n-<slug do nome>` (NFKD sem acento, minúsculo,
  pontuação removida, tokens unidos por `-`; o conteúdo entre parênteses entra no slug). Só o slug idêntico funde.
- **Homônimo:** o mesmo id por nome com turnos sobrepostos, ou em duas lojas na mesma semana, vira cartão `homonimo`.
  Sem resposta, `pending=True` e os ids ficam sem sufixo; "distintas" põe o sufixo da loja; "mesma" mantém uma pessoa
  e a sobreposição volta como problema da leitura. Com matrícula não há homônimo: sobreposição é problema direto.
- **Grafia parecida:** comparação por token (sem o conteúdo entre parênteses e sem preposições), não pelo nome inteiro:
  `SequenceMatcher` no nome inteiro dá cartão falso entre "Carla Nogueira" e "Iara Nogueira". Vira cartão
  `grafia_parecida`; sugestão "mesma" só sem turno sobreposto entre as duas grafias.
- **Quadro guardado:** slug igual a uma pessoa do quadro → id do quadro; parecido → `grafia_parecida`; sem par →
  `sem_par_no_quadro` ("pessoa nova?").

Salário, cargo e horário da loja não são preenchidos aqui (B4a, D7, A3).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from escalista.domain.reading import CellRef, IdentityAnswer, IdentityCard
from escalista.domain.roster import Roster
from escalista.domain.schedule import CsvIssue, Employee, Shift

from .mapping import MappedShift

DEFAULT_STORE_ID = "l-loja-1"
DEFAULT_STORE_NAME = "Loja 1"
SIMILARITY = 0.88
_PREPOSITIONS = frozenset({"de", "da", "do", "das", "dos", "e"})
_SHORT_STORE = re.compile(r"^[A-Za-z]{1,3}\d{1,3}$")
_PARENS = re.compile(r"\([^)]*\)")
_MIN_FIRST = 4  # regra (d): primeiro nome com pelo menos 4 letras
_MIN_TYPO = 5  # um erro de digitação (distância 1) só conta em token de 5 letras ou mais ("Souza" × "Sousa")


@dataclass(frozen=True)
class PersonDraft:
    id: str
    name: str
    store_id: str
    code: str | None
    wage: str | None


@dataclass(frozen=True)
class StoreDraft:
    id: str
    name: str


@dataclass(frozen=True)
class MergedNames:
    """Grafias diferentes que o slug juntou numa pessoa só (ex.: "Ana Souza" e "ANA  SOUZA")."""

    person_id: str
    names: list[str]


@dataclass(frozen=True)
class IdentityResult:
    """`shifts[i]` corresponde a `shifts[i]` da entrada (mesma ordem, para a evidência continuar valendo)."""

    people: list[PersonDraft]
    stores: list[StoreDraft]
    shifts: list[Shift]
    cards: list[IdentityCard]
    pending: bool  # há cartão `homonimo` sem resposta: a leitura não confirma
    issues: list[CsvIssue]
    merged: list[MergedNames] = field(default_factory=list)


# --- normalização -----------------------------------------------------------------------------------------------


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def _tokens(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", _plain(text)).split()


def name_slug(name: str) -> str:
    return "-".join(_tokens(name))


def person_id(name: str, code: str | None) -> str:
    code_slug = name_slug(code or "")
    return f"m-{code_slug}" if code_slug else f"n-{name_slug(name)}"


def store_id_for(text: str) -> str:
    text = text.strip()
    return text if _SHORT_STORE.match(text) else f"l-{name_slug(text)}"


# --- grafia parecida --------------------------------------------------------------------------------------------


def _significant(name: str) -> list[str]:
    return [t for t in _tokens(_PARENS.sub(" ", name)) if t not in _PREPOSITIONS]


def _one_edit(a: str, b: str) -> bool:
    """Distância de edição até 1 (troca, inserção ou remoção de uma letra)."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) <= 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))


def _close(a: str, b: str) -> bool:
    if SequenceMatcher(None, a, b).ratio() >= SIMILARITY:
        return True
    return min(len(a), len(b)) >= _MIN_TYPO and _one_edit(a, b)


def _close_rest(a: list[str], b: list[str]) -> bool:
    if len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True)):
        return True
    return SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() >= SIMILARITY


def similar_names(a: str, b: str) -> bool:
    """Par candidato a cartão `grafia_parecida`. Slug idêntico não é par (é a mesma pessoa)."""
    if name_slug(a) == name_slug(b):
        return False
    ta, tb = _significant(a), _significant(b)
    if not ta or not tb:
        return False
    sa, sb = set(ta), set(tb)
    if sa == sb:  # (a) "Ana Souza" × "Ana de Souza"
        return True
    if ta[0] == tb[0] and ta[-1] == tb[-1] and (sa <= sb or sb <= sa):  # (b) "Maria Silva" × "Maria Clara Silva"
        return True
    if ta[0] == tb[0] and ta[1:] and tb[1:] and _close_rest(ta[1:], tb[1:]):  # (c) "Souza" × "Sousa"
        return True
    return (  # (d) "Thiago" × "Tiago"
        ta[1:] == tb[1:] and bool(ta[1:]) and min(len(ta[0]), len(tb[0])) >= _MIN_FIRST and _close(ta[0], tb[0])
    )


# --- grupos -----------------------------------------------------------------------------------------------------


@dataclass
class _Group:
    base_id: str
    names: list[str] = field(default_factory=list)  # grafias distintas, na ordem em que aparecem
    indexes: list[int] = field(default_factory=list)
    code: str | None = None

    @property
    def name(self) -> str:
        return self.names[0]

    @property
    def by_name(self) -> bool:
        return self.base_id.startswith("n-")


def _overlaps(a: MappedShift, b: MappedShift) -> bool:
    return a.start < b.end and b.start < a.end


def _overlapping_pairs(indexes: Sequence[int], shifts: Sequence[MappedShift]) -> list[tuple[int, int]]:
    ordered = sorted(indexes, key=lambda i: (shifts[i].start, i))
    return [(i, j) for k, i in enumerate(ordered) for j in ordered[k + 1 :] if _overlaps(shifts[i], shifts[j])]


def _any_overlap(a: Iterable[int], b: Iterable[int], shifts: Sequence[MappedShift]) -> bool:
    bs = list(b)
    return any(_overlaps(shifts[i], shifts[j]) for i in a for j in bs)


def _person_cell(s: MappedShift) -> CellRef:
    for cell, raw in zip(s.evidence.cells, s.evidence.raw, strict=False):
        if raw.strip() == s.person_name.strip():
            return cell
    return s.evidence.cells[0]


def _rows(shifts: Sequence[MappedShift], indexes: Iterable[int]) -> list[CellRef]:
    """Célula do nome de cada turno, sem repetir (`CellRef` não é hashable)."""
    seen: dict[tuple[int, int, int], CellRef] = {}
    for i in indexes:
        cell = _person_cell(shifts[i])
        seen.setdefault((cell.table, cell.row, cell.col), cell)
    return list(seen.values())


def _card_id(kind: str, names: Iterable[str], stores: Iterable[str] = ()) -> str:
    key = "|".join([kind, *sorted(name_slug(n) for n in names), *sorted(stores)])
    return "idc-" + hashlib.sha1(key.encode()).hexdigest()[:10]


def _main_store(indexes: Sequence[int], store_of: Sequence[str]) -> str:
    counts = Counter(store_of[i] for i in indexes)
    best = max(counts.values())
    return next(store_of[i] for i in indexes if counts[store_of[i]] == best)


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        while self.parent.get(x, x) != x:
            x = self.parent[x]
        return x

    def union(self, keep: str, other: str) -> None:
        a, b = self.find(keep), self.find(other)
        if a != b:
            self.parent[b] = a


# --- API --------------------------------------------------------------------------------------------------------


def resolve_identities(
    shifts: list[MappedShift],
    *,
    roster: Roster | None = None,
    answers: Sequence[IdentityAnswer] = (),
) -> IdentityResult:
    """Resolve pessoa e loja de cada turno lido. Cartões ao gestor para toda dúvida; nada é fundido sem resposta."""
    answered = {a.card_id: a.same for a in answers}

    stores, store_of, store_names = _resolve_stores(shifts, roster)

    groups: dict[str, _Group] = {}
    for i, s in enumerate(shifts):
        base = person_id(s.person_name, s.person_code)
        g = groups.setdefault(base, _Group(base_id=base))
        name = s.person_name.strip()
        if name not in g.names:
            g.names.append(name)
        g.indexes.append(i)
        g.code = g.code or (s.person_code.strip() if s.person_code and s.person_code.strip() else None)
    order = list(groups)

    cards: list[IdentityCard] = []
    pending = False

    # Homônimo: mesmo id por nome, sobreposto ou em duas lojas.
    split: set[str] = set()
    on_hold: set[int] = set()  # turnos de homônimo sem resposta: a sobreposição é o cartão, não problema
    for base in order:
        g = groups[base]
        if not g.by_name:
            continue
        g_stores = list(dict.fromkeys(store_of[i] for i in g.indexes))
        overlap = _overlapping_pairs(g.indexes, shifts)
        if len(g_stores) < 2 and not overlap:
            continue
        card_id = _card_id("homonimo", [g.name], g_stores)
        where = ", ".join(store_names[s] for s in g_stores)
        reason = (
            f"'{g.name}' aparece em {len(g_stores)} loja(s) ({where})"
            + (" com turnos sobrepostos no mesmo horário" if overlap else " na mesma semana")
            + ": pode ser mais de uma pessoa com o mesmo nome."
        )
        cards.append(
            IdentityCard(
                id=card_id,
                kind="homonimo",
                names=[g.name],
                rows=_rows(shifts, g.indexes),
                suggestion="distintas" if overlap else "mesma",
                reason=reason,
            )
        )
        if card_id not in answered:
            pending = True
            on_hold.update(g.indexes)
        elif answered[card_id] is False:
            split.add(base)

    # Quadro guardado: slug igual → id do quadro.
    roster_match: dict[str, Employee] = {}
    roster_people = roster.employees if roster else []
    if roster is not None:
        for base in order:
            match = _exact_roster_match(groups[base], roster_people, store_of)
            if match is not None:
                roster_match[base] = match

    # Grafia parecida no arquivo.
    uf = _UnionFind()
    named = [b for b in order if groups[b].by_name]
    covered: set[tuple[str, str]] = set()  # (grupo, pessoa do quadro) já tratados por cartão do arquivo
    for k, a in enumerate(named):
        for b in named[k + 1 :]:
            ga, gb = groups[a], groups[b]
            if a in roster_match and b in roster_match and roster_match[a].id != roster_match[b].id:
                continue  # o quadro já diz que são duas pessoas
            if not similar_names(ga.name, gb.name):
                continue
            card_id = _similar_card(ga, gb, shifts, cards)
            for x, y in ((a, b), (b, a)):
                if y in roster_match:
                    covered.add((x, roster_match[y].id))
            if answered.get(card_id) is True:
                uf.union(a, b)

    # Quadro guardado: parecido → cartão; sem par → "pessoa nova?".
    roster_link: dict[str, Employee] = dict(roster_match)
    if roster is not None:
        for base in order:
            g = groups[base]
            if base in roster_match:
                continue
            similar = [e for e in roster_people if similar_names(g.name, e.name) and (base, e.id) not in covered]
            for e in similar:
                card_id = _card_id("grafia_parecida", [g.name, e.name], [f"quadro:{e.id}"])
                cards.append(
                    IdentityCard(
                        id=card_id,
                        kind="grafia_parecida",
                        names=[g.name, e.name],
                        rows=_rows(shifts, g.indexes),
                        suggestion="mesma",
                        reason=f"'{g.name}' (arquivo) parece '{e.name}' (quadro guardado, id {e.id}).",
                    )
                )
                if answered.get(card_id) is True and base not in roster_link:
                    roster_link[base] = e
            if not similar and not any(g_id == base for g_id, _ in covered):
                cards.append(
                    IdentityCard(
                        id=_card_id("sem_par_no_quadro", [g.name]),
                        kind="sem_par_no_quadro",
                        names=[g.name],
                        rows=_rows(shifts, g.indexes),
                        suggestion="distintas",
                        reason=f"'{g.name}' não está no quadro guardado: pessoa nova?",
                    )
                )

    # Ids finais.
    clusters: dict[str, list[str]] = defaultdict(list)
    for base in order:
        clusters[uf.find(base)].append(base)
    final_of = [""] * len(shifts)
    people: list[PersonDraft] = []
    merged: list[MergedNames] = []
    for root in order:
        if root not in clusters:
            continue
        members = clusters[root]
        indexes = sorted(i for b in members for i in groups[b].indexes)
        linked = next((roster_link[b] for b in members if b in roster_link), None)
        head = groups[root]
        names = list(dict.fromkeys(n for b in members for n in groups[b].names))
        pieces: list[tuple[str, list[int]]]
        if any(b in split for b in members):
            by_store: dict[str, list[int]] = defaultdict(list)
            for i in indexes:
                by_store[store_of[i]].append(i)
            pieces = []
            for st, idx in by_store.items():
                pid = linked.id if linked and linked.store_id == st else f"{root}-{name_slug(st)}"
                pieces.append((pid, idx))
        else:
            pieces = [(linked.id if linked else root, indexes)]
        for pid, idx in pieces:
            for i in idx:
                final_of[i] = pid
            people.append(
                PersonDraft(
                    id=pid,
                    name=head.name,
                    store_id=_main_store(idx, store_of),
                    code=next((groups[b].code for b in members if groups[b].code), None),
                    wage=next((shifts[i].wage.strip() for i in idx if shifts[i].wage and shifts[i].wage.strip()), None),
                )
            )
        if len(names) > 1:
            merged.append(MergedNames(person_id=pieces[0][0], names=names))

    issues = _overlap_issues(final_of, shifts, on_hold)
    resolved = [
        Shift(employee_id=final_of[i], store_id=store_of[i], start=s.start, end=s.end) for i, s in enumerate(shifts)
    ]
    return IdentityResult(
        people=people,
        stores=stores,
        shifts=resolved,
        cards=cards,
        pending=pending,
        issues=issues,
        merged=merged,
    )


def _resolve_stores(
    shifts: Sequence[MappedShift], roster: Roster | None
) -> tuple[list[StoreDraft], list[str], dict[str, str]]:
    known = {}
    if roster is not None:
        for st in roster.stores:
            known[st.id.lower()] = st
            known[f"l-{name_slug(st.name)}"] = st
    stores: dict[str, StoreDraft] = {}
    store_of: list[str] = []
    for s in shifts:
        text = (s.store or "").strip()
        if not text:
            sid, name = DEFAULT_STORE_ID, DEFAULT_STORE_NAME
        else:
            sid, name = store_id_for(text), text
            hit = known.get(sid.lower()) or known.get(f"l-{name_slug(text)}")
            if hit is not None:
                sid = hit.id
        stores.setdefault(sid, StoreDraft(id=sid, name=name))
        store_of.append(sid)
    return list(stores.values()), store_of, {sid: st.name for sid, st in stores.items()}


def _exact_roster_match(g: _Group, employees: Sequence[Employee], store_of: Sequence[str]) -> Employee | None:
    if g.code:
        code_id = person_id("", g.code)
        for e in employees:
            if e.id.lower() == g.code.lower() or e.id == code_id:
                return e
    slug = name_slug(g.name)
    same = [e for e in employees if name_slug(e.name) == slug]
    if not same:
        return None
    main = _main_store(g.indexes, store_of)
    return next((e for e in same if e.store_id == main), same[0])


def _similar_card(ga: _Group, gb: _Group, shifts: Sequence[MappedShift], cards: list[IdentityCard]) -> str:
    overlap = _any_overlap(ga.indexes, gb.indexes, shifts)
    card_id = _card_id("grafia_parecida", [ga.name, gb.name])
    reason = f"'{ga.name}' e '{gb.name}' têm grafia parecida" + (
        "; há turnos sobrepostos entre as duas, então devem ser pessoas distintas."
        if overlap
        else "; sem turno sobreposto entre as duas, podem ser a mesma pessoa."
    )
    cards.append(
        IdentityCard(
            id=card_id,
            kind="grafia_parecida",
            names=[ga.name, gb.name],
            rows=_rows(shifts, sorted(ga.indexes + gb.indexes)),
            suggestion="distintas" if overlap else "mesma",
            reason=reason,
        )
    )
    return card_id


def _overlap_issues(final_of: Sequence[str], shifts: Sequence[MappedShift], on_hold: set[int]) -> list[CsvIssue]:
    by_person: dict[str, list[int]] = defaultdict(list)
    for i, pid in enumerate(final_of):
        by_person[pid].append(i)
    issues: list[CsvIssue] = []
    for pid, indexes in by_person.items():
        for i, j in _overlapping_pairs(indexes, shifts):
            if i in on_hold and j in on_hold:
                continue
            later = shifts[j]
            cell = _person_cell(later)
            issues.append(
                CsvIssue(
                    line=cell.row + 1,
                    field="pessoa",
                    reason=(
                        f"turno de '{later.person_name.strip()}' ({pid}) sobreposto a outro da mesma pessoa "
                        f"(linha {_person_cell(shifts[i]).row + 1})"
                    ),
                    col=cell.col,
                )
            )
    issues.sort(key=lambda x: (x.line, x.col if x.col is not None else -1))
    return issues
