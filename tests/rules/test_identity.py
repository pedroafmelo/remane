"""Identidade das pessoas (plano da C6, A2; seção 7): ids estáveis, homônimo, grafia parecida e o quadro guardado.

Os casos do E2-08 são lidos pela borda (`ingest`) e pela heurística de cabeçalho: o teste pode importar a borda, o
módulo `rules/identity.py`, não.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path

import pytest

from escalista.domain.reading import CellRef, IdentityAnswer, ShiftEvidence
from escalista.domain.roster import Roster
from escalista.domain.schedule import Employee, Store
from escalista.ingest.tables import read_tables
from escalista.rules.header_aliases import guess_mapping
from escalista.rules.identity import (
    DEFAULT_STORE_ID,
    IdentityResult,
    name_slug,
    person_id,
    resolve_identities,
    similar_names,
    store_id_for,
)
from escalista.rules.mapping import MappedShift, apply_mapping

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
E2_08 = DEMO / "e2" / "e2-08-identidade.csv"


def shift(
    name: str,
    day: int,
    start: int,
    end: int,
    store: str | None = "Loja Centro",
    code: str | None = None,
    wage: str | None = None,
    row: int = 1,
) -> MappedShift:
    raw = [name, store or "", f"{day:02d}/01/2027", f"{start:02d}:00", f"{end:02d}:00"]
    return MappedShift(
        person_name=name,
        person_code=code,
        store=store,
        start=datetime(2027, 1, day, start),
        end=datetime(2027, 1, day, end),
        wage=wage,
        note=None,
        evidence=ShiftEvidence(
            shift_index=0, cells=[CellRef(table=0, row=row, col=c) for c in range(len(raw))], raw=raw
        ),
    )


def e2_08() -> list[MappedShift]:
    tables = read_tables(E2_08.name, E2_08.read_bytes()).tables
    mapping = guess_mapping(tables)
    assert mapping is not None
    result = apply_mapping(tables, mapping)
    assert result.issues == []
    return result.shifts


def roster_of(*people: tuple[str, str, str]) -> Roster:
    stores = sorted({s for _, _, s in people})
    return Roster(
        version=1,
        stores=[Store(id=s, name=f"Loja {s}", opens=time(8), closes=time(22)) for s in stores],
        employees=[
            Employee(id=i, name=n, store_id=s, job="Atendente", hourly_wage=Decimal("12"), contract_hours=44)
            for i, n, s in people
        ],
        demand=[],
        source_run_id="run-1",
        confirmed_by="u-1",
        confirmed_at=datetime(2027, 1, 8, tzinfo=UTC),
    )


def ids_of(result: IdentityResult) -> set[str]:
    return {p.id for p in result.people}


# --- ids --------------------------------------------------------------------------------------------------------


def test_name_slug_strips_accents_case_punctuation_and_keeps_parenthetical():
    assert name_slug("ANA  SOUZA (sintético)") == "ana-souza-sintetico"
    assert name_slug("Quitéria  Horta") == "quiteria-horta"
    assert name_slug(" João D'Ávila-Neto ") == "joao-d-avila-neto"


def test_person_id_prefers_code_then_name():
    assert person_id("Ana Souza", " 00123 ") == "m-00123"
    assert person_id("Ana Souza", "AB-12") == "m-ab-12"
    assert person_id("ANA  SOUZA (sintético)", None) == "n-ana-souza-sintetico"
    assert person_id("Ana Souza", "  ") == "n-ana-souza"


def test_store_id_short_code_or_slug():
    assert store_id_for("L1") == "L1"
    assert store_id_for(" abc123 ") == "abc123"
    assert store_id_for("Loja Sintética Centro") == "l-loja-sintetica-centro"
    assert store_id_for("L1234") == "l-l1234"


def test_no_store_column_uses_default_store():
    result = resolve_identities([shift("Ana", 11, 8, 16, store=None)])
    assert [(s.id, s.name) for s in result.stores] == [(DEFAULT_STORE_ID, "Loja 1")]
    assert result.shifts[0].store_id == "l-loja-1"
    assert result.people[0].store_id == "l-loja-1"


def test_shifts_keep_input_order_and_resolved_ids():
    shifts = [shift("Ana Souza", 11, 8, 16), shift("Bia Reis", 11, 10, 18, store="L2"), shift("ANA SOUZA", 12, 8, 16)]
    result = resolve_identities(shifts)
    assert [(s.employee_id, s.store_id) for s in result.shifts] == [
        ("n-ana-souza", "l-loja-centro"),
        ("n-bia-reis", "L2"),
        ("n-ana-souza", "l-loja-centro"),
    ]
    assert result.shifts[1].start == datetime(2027, 1, 11, 10)
    assert result.cards == [] and result.issues == [] and not result.pending


def test_person_draft_fields_first_name_code_wage_and_main_store():
    shifts = [
        shift("Ana", 11, 8, 16, code="7", wage=None),
        shift("Ana (outra grafia)", 12, 8, 16, code="7", wage="12,50", store="L2"),
        shift("Ana", 13, 8, 16, code="7", store="L2"),
    ]
    result = resolve_identities(shifts)
    (person,) = result.people
    assert (person.id, person.name, person.code, person.wage, person.store_id) == ("m-7", "Ana", "7", "12,50", "L2")
    assert result.cards == []  # matrícula identifica: duas lojas não é homônimo


def test_code_overlap_is_an_issue_not_a_card():
    result = resolve_identities([shift("Ana", 11, 8, 16, code="7"), shift("Ana", 11, 12, 18, code="7", store="L2")])
    assert result.cards == []
    assert len(result.issues) == 1 and "sobrepost" in result.issues[0].reason


# --- homônimo ---------------------------------------------------------------------------------------------------


def two_store_bruno() -> list[MappedShift]:
    return [
        shift("Bruno Lima", 11, 12, 20, store="L1", row=1),
        shift("Bruno Lima", 12, 12, 20, store="L1", row=2),
        shift("Bruno Lima", 12, 14, 22, store="L2", row=3),
    ]


def test_homonym_card_is_pending_and_ids_stay_unsuffixed():
    result = resolve_identities(two_store_bruno())
    (card,) = result.cards
    assert card.kind == "homonimo" and card.names == ["Bruno Lima"]
    assert card.suggestion == "distintas"
    assert card.rows == [CellRef(table=0, row=r, col=0) for r in (1, 2, 3)]
    assert result.pending
    assert ids_of(result) == {"n-bruno-lima"}
    assert {s.employee_id for s in result.shifts} == {"n-bruno-lima"}
    assert result.issues == []  # a sobreposição é o conteúdo do cartão, ainda sem resposta


def test_homonym_answered_distinct_suffixes_store():
    card_id = resolve_identities(two_store_bruno()).cards[0].id
    result = resolve_identities(two_store_bruno(), answers=[IdentityAnswer(card_id=card_id, same=False)])
    assert not result.pending
    assert ids_of(result) == {"n-bruno-lima-l1", "n-bruno-lima-l2"}
    assert [s.employee_id for s in result.shifts] == ["n-bruno-lima-l1", "n-bruno-lima-l1", "n-bruno-lima-l2"]
    assert {p.id: p.store_id for p in result.people} == {"n-bruno-lima-l1": "L1", "n-bruno-lima-l2": "L2"}
    assert result.issues == []


def test_homonym_answered_same_keeps_one_person_and_reports_overlap():
    card_id = resolve_identities(two_store_bruno()).cards[0].id
    result = resolve_identities(two_store_bruno(), answers=[IdentityAnswer(card_id=card_id, same=True)])
    assert not result.pending
    assert ids_of(result) == {"n-bruno-lima"}
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.line == 4 and issue.field == "pessoa" and issue.col == 0 and "sobrepost" in issue.reason


def test_two_stores_without_overlap_is_homonym_suggesting_same():
    result = resolve_identities([shift("Bruno", 11, 8, 12, store="L1"), shift("Bruno", 13, 8, 12, store="L2")])
    (card,) = result.cards
    assert card.kind == "homonimo" and card.suggestion == "mesma" and result.pending


def test_unknown_answer_is_ignored():
    result = resolve_identities(two_store_bruno(), answers=[IdentityAnswer(card_id="idc-nao-existe", same=False)])
    assert result.pending


# --- grafia parecida --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Ana Souza", "Ana de Souza"),
        ("Maria Silva", "Maria Clara Silva"),
        ("Ana Souza", "Ana Sousa"),
        ("Thiago Reis", "Tiago Reis"),
        ("Ana Souza (sintético)", "Ana de Souza (sintético)"),
    ],
)
def test_similar_names(a, b):
    assert similar_names(a, b) and similar_names(b, a)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Carla Nogueira", "Iara Nogueira"),
        ("Ana Souza", "Ana Souza"),  # mesmo slug: é fusão, não cartão
        ("ANA  SOUZA", "Ana Souza"),
        ("Ana Lima", "Ana Lira"),
        ("Tiago Ivo", "Paulo Ivo"),
        ("Ana Nogueira", "Ana Siqueira"),
        ("Zé Lacerda", "Zá Lacerda"),
    ],
)
def test_not_similar_names(a, b):
    assert not similar_names(a, b)


def test_roster_people_produce_no_similarity_card():
    people = json.loads((DEMO / "pessoas.json").read_text(encoding="utf-8"))
    assert len(people) == 60
    shifts = [shift(p["name"], 11, 8, 16, store=p["store_id"], row=i + 1) for i, p in enumerate(people)]
    result = resolve_identities(shifts)
    assert result.cards == []
    assert len(result.people) == 60 and not result.pending


def test_similar_spelling_card_suggests_distinct_when_overlapping():
    result = resolve_identities([shift("Ana Souza", 11, 8, 16), shift("Ana de Souza", 11, 12, 18)])
    (card,) = result.cards
    assert card.kind == "grafia_parecida" and card.suggestion == "distintas"
    assert not result.pending
    assert ids_of(result) == {"n-ana-souza", "n-ana-de-souza"}  # nunca funde sem resposta


def test_similar_spelling_answered_same_merges_into_first():
    shifts = [shift("Ana Souza", 11, 8, 16), shift("Ana de Souza", 12, 8, 16)]
    card_id = resolve_identities(shifts).cards[0].id
    result = resolve_identities(shifts, answers=[IdentityAnswer(card_id=card_id, same=True)])
    assert ids_of(result) == {"n-ana-souza"}
    assert [s.employee_id for s in result.shifts] == ["n-ana-souza", "n-ana-souza"]
    assert [m.names for m in result.merged] == [["Ana Souza", "Ana de Souza"]]


def test_card_ids_are_stable_across_order():
    a = resolve_identities([shift("Ana Souza", 11, 8, 16), shift("Ana de Souza", 12, 8, 16)]).cards[0].id
    b = resolve_identities([shift("Ana de Souza", 12, 8, 16), shift("Ana Souza", 11, 8, 16)]).cards[0].id
    assert a == b and a.startswith("idc-")


# --- E2-08 ------------------------------------------------------------------------------------------------------


def test_e2_08_matches_expected_identity():
    expected = json.loads(E2_08.with_suffix(".esperado.json").read_text(encoding="utf-8"))["identity"]
    result = resolve_identities(e2_08())

    merges = [{"names": m.names, "person_id": m.person_id} for m in result.merged]
    assert merges == [{"names": e["names"], "person_id": e["person_id"]} for e in expected["merged_by_normalization"]]

    got = sorted((c.kind, c.names, c.suggestion) for c in result.cards)
    assert got == [
        ("grafia_parecida", ["Ana Souza (sintético)", "Ana de Souza (sintético)"], "mesma"),
        ("homonimo", ["Bruno Lima (sintético)"], "distintas"),
    ]
    homonym = next(c for c in result.cards if c.kind == "homonimo")
    assert expected["cards"][1]["stores"] == ["Loja Sintética Centro", "Loja Sintética Norte"]
    assert all(store in homonym.reason for store in expected["cards"][1]["stores"])

    flagged = {n for c in result.cards for n in c.names}
    assert not flagged & set(expected["distinct_people_without_card"])
    assert expected["auto_merge_by_similarity"] == 0
    assert "n-ana-de-souza-sintetico" in ids_of(result)  # sem fusão por parecença
    assert result.pending
    assert {(s.id, s.name) for s in result.stores} == {
        ("l-loja-sintetica-centro", "Loja Sintética Centro"),
        ("l-loja-sintetica-norte", "Loja Sintética Norte"),
    }
    assert len(result.shifts) == 21


def test_e2_08_after_answers():
    first = resolve_identities(e2_08())
    answers = [IdentityAnswer(card_id=c.id, same=c.kind == "grafia_parecida") for c in first.cards]
    result = resolve_identities(e2_08(), answers=answers)
    assert not result.pending and result.issues == []
    assert ids_of(result) == {
        "n-ana-souza-sintetico",
        "n-bruno-lima-sintetico-l-loja-sintetica-centro",
        "n-bruno-lima-sintetico-l-loja-sintetica-norte",
        "n-diego-prado-sintetico",
        "n-elisa-mota-sintetico",
    }


# --- quadro guardado --------------------------------------------------------------------------------------------


def test_roster_exact_slug_reuses_roster_id_and_store():
    roster = roster_of(("P001", "Ana Souza", "L1"), ("P002", "Bia Reis", "L1"))
    result = resolve_identities([shift("ANA  SOUZA", 11, 8, 16, store="L1")], roster=roster)
    assert result.cards == []
    assert ids_of(result) == {"P001"}
    assert result.shifts[0].employee_id == "P001"


def test_roster_store_matched_by_name():
    roster = roster_of(("P001", "Ana Souza", "L1"))
    result = resolve_identities([shift("Ana Souza", 11, 8, 16, store="Loja L1")], roster=roster)
    assert result.shifts[0].store_id == "L1"


def test_roster_similar_name_card_and_answer():
    roster = roster_of(("P001", "Ana Souza", "L1"))
    shifts = [shift("Ana de Souza", 11, 8, 16, store="L1")]
    first = resolve_identities(shifts, roster=roster)
    (card,) = first.cards
    assert card.kind == "grafia_parecida" and card.names == ["Ana de Souza", "Ana Souza"]
    assert ids_of(first) == {"n-ana-de-souza"}
    same = resolve_identities(shifts, roster=roster, answers=[IdentityAnswer(card_id=card.id, same=True)])
    assert ids_of(same) == {"P001"}


def test_roster_without_match_is_new_person_card():
    roster = roster_of(("P001", "Ana Souza", "L1"))
    result = resolve_identities([shift("Caio Prates", 11, 8, 16, store="L1")], roster=roster)
    (card,) = result.cards
    assert card.kind == "sem_par_no_quadro" and card.names == ["Caio Prates"]
    assert ids_of(result) == {"n-caio-prates"} and not result.pending


def test_roster_with_full_pessoas_json_reads_back_without_cards():
    people = json.loads((DEMO / "pessoas.json").read_text(encoding="utf-8"))
    roster = roster_of(*[(p["id"], p["name"], p["store_id"]) for p in people])
    shifts = [shift(p["name"], 11, 8, 16, store=p["store_id"], row=i + 1) for i, p in enumerate(people)]
    result = resolve_identities(shifts, roster=roster)
    assert result.cards == []
    assert ids_of(result) == {p["id"] for p in people}
    assert date(2027, 1, 11) == result.shifts[0].start.date()


def test_pending_homonym_does_not_hide_other_overlaps():
    shifts = [*two_store_bruno(), shift("Caio", 11, 8, 16, code="9", row=4), shift("Caio", 11, 10, 18, code="9", row=5)]
    result = resolve_identities(shifts)
    assert result.pending
    assert [(i.line, i.field) for i in result.issues] == [(6, "pessoa")]


def test_roster_unknown_code_is_new_person_card():
    roster = roster_of(("P001", "Ana Souza", "L1"))
    result = resolve_identities([shift("Caio Prates", 11, 8, 16, store="L1", code="77")], roster=roster)
    assert [c.kind for c in result.cards] == ["sem_par_no_quadro"]
    assert ids_of(result) == {"m-77"}


def test_roster_known_code_reuses_roster_id():
    roster = roster_of(("m-77", "Caio Prates", "L1"))
    result = resolve_identities([shift("Caio P.", 11, 8, 16, store="L1", code="77")], roster=roster)
    assert result.cards == [] and ids_of(result) == {"m-77"}
