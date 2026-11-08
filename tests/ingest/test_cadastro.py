"""Cadastro simulado (plano da C6, D7; RE-11): casamento por nome, salário-hora e regressão do custo do exemplo."""

from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from escalista.domain.results import SolveRequest
from escalista.domain.schedule import DemandSlot, Employee, Schedule
from escalista.ingest.cadastro import (
    NOT_INFORMED_JOB,
    Cadastro,
    enrich,
    load_cadastro,
    parse_wage,
    reference_wage,
)
from escalista.ingest.tables import read_tables
from escalista.rules.header_aliases import guess_mapping
from escalista.rules.identity import IdentityResult, PersonDraft, StoreDraft, resolve_identities
from escalista.rules.loader import load_rule_card
from escalista.rules.mapping import apply_mapping
from escalista.solver.cost import compute_metrics
from escalista.solver.model import solve
from escalista.verifier import verify

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "data" / "demo"
WEEK = date(2027, 1, 11)


def read_example() -> IdentityResult:
    path = DEMO / "escala_exemplo_grade.xlsx"
    tables = read_tables(path.name, path.read_bytes()).tables
    mapping = guess_mapping(tables)
    assert mapping is not None
    return resolve_identities(apply_mapping(tables, mapping).shifts)


@pytest.fixture(scope="module")
def cadastro() -> Cadastro:
    return load_cadastro(DEMO)


@pytest.fixture(scope="module")
def example() -> IdentityResult:
    return read_example()


def draft(id_: str, name: str, wage: str | None = None, store: str = "l-x") -> PersonDraft:
    return PersonDraft(id=id_, name=name, store_id=store, code=None, wage=wage)


def test_load_cadastro_reads_demo_json(cadastro):
    assert len(cadastro.people) == 60
    assert {s.id for s in cadastro.stores} == {"L1", "L2", "L3"}


def test_example_matches_every_person_and_store(cadastro, example):
    result = enrich(example.people, example.stores, cadastro=cadastro, default_wage=None, default_contract_hours=44)
    assert len(example.people) == 60 and len(example.stores) == 3
    assert result.matched_people == 60
    assert result.matched_stores == 3
    assert result.reference_wage is None
    assert any(
        "cadastro simulado" in a and "integração simulada" in a and "60 pessoas" in a for a in result.assumptions
    )
    assert not any("referência" in a for a in result.assumptions)


def test_employees_keep_draft_ids_and_never_copy_sex(cadastro, example):
    result = enrich(example.people, example.stores, cadastro=cadastro, default_wage=None, default_contract_hours=44)
    assert [e.id for e in result.employees] == [p.id for p in example.people]
    assert not {e.id for e in result.employees} & {e.id for e in cadastro.people}
    assert all(e.sex is None for e in result.employees)
    assert any(c.sex is not None for c in cadastro.people)
    by_name = {c.name: c for c in cadastro.people}
    for e in result.employees:
        assert e.hourly_wage == by_name[e.name].hourly_wage
        assert e.job == by_name[e.name].job


def test_store_hours_come_from_cadastro_only_for_matched_stores(cadastro):
    stores = [
        StoreDraft(id="l-loja-sintetica-norte", name="Loja Sintética Norte"),
        StoreDraft(id="L3", name="Qualquer"),  # id igual
        StoreDraft(id="l-outra", name="Outra Loja"),
    ]
    result = enrich([], stores, cadastro=cadastro, default_wage=None, default_contract_hours=44)
    assert result.matched_stores == 2
    assert set(result.store_hours) == {"l-loja-sintetica-norte", "L3"}
    assert result.store_hours["L3"] == (time(8), time(22))
    assert result.stores is not None and [s.id for s in result.stores] == ["l-loja-sintetica-norte", "L3"]
    assert "l-outra" not in result.store_hours


def test_no_store_match_gives_none(cadastro):
    result = enrich(
        [], [StoreDraft(id="l-z", name="Z")], cadastro=cadastro, default_wage=None, default_contract_hours=44
    )
    assert result.stores is None and result.store_hours == {} and result.matched_stores == 0


def test_no_match_uses_reference_wage_and_says_so(cadastro):
    result = enrich(
        [draft("n-fulano", "Fulano de Tal")], [], cadastro=cadastro, default_wage=None, default_contract_hours=40
    )
    ref = reference_wage(cadastro)
    (e,) = result.employees
    assert e.hourly_wage == ref and e.job == NOT_INFORMED_JOB and e.contract_hours == 40 and e.profile == "padrao"
    assert result.matched_people == 0 and result.reference_wage == ref
    (phrase,) = result.assumptions
    assert "referência" in phrase and "sintético" in phrase and "1 pessoa " in phrase and "informe o real" in phrase
    assert f"{ref:.2f}".replace(".", ",") in phrase


def test_reference_wage_is_the_median():
    people = [
        Employee(id=str(i), name=str(i), store_id="L1", job="x", hourly_wage=Decimal(w), contract_hours=44)
        for i, w in enumerate(["10", "11", "20", "30"])
    ]
    assert reference_wage(Cadastro(people=people, stores=[])) == Decimal("15.50")


def test_wage_precedence_cadastro_then_file_then_default_then_reference(cadastro):
    known = cadastro.people[0]
    people = [
        draft("n-a", known.name, wage="99,00"),  # cadastro vence o arquivo
        draft("n-b", "Sem Cadastro B", wage="13,25"),  # arquivo vence o padrão
        draft("n-c", "Sem Cadastro C", wage="abc"),  # ilegível → padrão da confirmação
        draft("n-d", "Sem Cadastro D"),
    ]
    result = enrich(people, [], cadastro=cadastro, default_wage=Decimal("14.00"), default_contract_hours=44)
    wages = [e.hourly_wage for e in result.employees]
    assert wages == [known.hourly_wage, Decimal("13.25"), Decimal("14.00"), Decimal("14.00")]
    assert result.reference_wage is None
    by_text = {a for a in result.assumptions}
    assert "Salário-hora de 1 pessoa veio do arquivo enviado." in by_text
    (ref,) = [a for a in result.assumptions if "R$ 14,00" in a]
    assert "2 pessoas sem cadastro" in ref and "sintético" not in ref  # o valor é do gestor, não a referência


def test_matching_is_exact_slug_not_similarity(cadastro):
    known = cadastro.people[0]
    typo = known.name.replace("a", "e", 1)
    result = enrich([draft("n-t", typo)], [], cadastro=cadastro, default_wage=Decimal("9"), default_contract_hours=44)
    assert result.matched_people == 0
    # caixa, acento e pontuação não contam (mesmo slug)
    result = enrich(
        [draft("n-u", known.name.upper())], [], cadastro=cadastro, default_wage=Decimal("9"), default_contract_hours=44
    )
    assert result.matched_people == 1


def test_without_cadastro_needs_a_default_wage():
    result = enrich([draft("n-a", "A")], [], cadastro=None, default_wage=Decimal("12"), default_contract_hours=44)
    assert result.employees[0].hourly_wage == Decimal("12") and result.stores is None
    with pytest.raises(ValueError, match="salário-hora"):
        enrich([draft("n-a", "A")], [], cadastro=None, default_wage=None, default_contract_hours=44)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12,40", "12.40"),
        ("12.40", "12.40"),
        ("R$ 12,4", "12.40"),
        ("1.234,50", "1234.50"),
        ("", None),
        (None, None),
        ("abc", None),
        ("0", None),
        ("-3", None),
    ],
)
def test_parse_wage(text, expected):
    assert parse_wage(text) == (Decimal(expected) if expected else None)


def matched_network(cadastro, example):
    """Quadro casado (ids do rascunho) e `demanda.json` com os `store_id` remapeados para os ids do rascunho."""
    result = enrich(example.people, example.stores, cadastro=cadastro, default_wage=None, default_contract_hours=44)
    assert result.stores is not None
    store_of = {s.id: sd.id for s in cadastro.stores for sd in result.stores if sd.name == s.name}
    demand = [
        d.model_copy(update={"store_id": store_of[d.store_id]})
        for d in TypeAdapter(list[DemandSlot]).validate_json((DEMO / "demanda.json").read_bytes())
    ]
    return result, demand, load_rule_card(ROOT / "data" / "regras", WEEK)


def test_regression_before_cost_of_the_example(cadastro, example):
    """Quadro casado + `demanda.json` (não a inferida): o "antes" do exemplo custa R$ 33.989,15."""
    result, demand, card = matched_network(cadastro, example)
    before = Schedule(week_start=WEEK, shifts=example.shifts)
    metrics = compute_metrics(before, result.employees, demand, card, verify(before, card).total)
    assert metrics.total_cost == Decimal("33989.15")


@pytest.mark.slow
def test_regression_after_cost_of_the_example(cadastro, example):
    """O "depois" (solver, seed 42, 1 thread, como no E1) com o quadro casado repete R$ 20.014,00.

    Ótimo provado: custo exato e 0 violações. Se a máquina carregada estourar o limite de tempo (status `feasible` ou
    `timeout`), a solução viável ainda precisa ter 0 violações e custo até 0,5% acima do ótimo.
    """
    result, demand, card = matched_network(cadastro, example)
    assert result.stores is not None
    solved = solve(
        SolveRequest(
            card=card,
            stores=result.stores,
            employees=result.employees,
            demand=demand,
            week_start=WEEK,
            seed=42,
            time_limit_s=60.0,
            num_workers=1,
        )
    )
    assert solved.schedule is not None
    after = compute_metrics(solved.schedule, result.employees, demand, card, verify(solved.schedule, card).total)
    optimal_cost = Decimal("20014.00")
    detail = f"status={solved.status}, custo={after.total_cost}, violações={after.violations}"
    assert after.violations == 0, detail
    if solved.status == "optimal":
        assert after.total_cost == optimal_cost, detail
    else:  # limite de tempo com solução viável (máquina carregada): não é regressão do custo
        assert solved.status in ("feasible", "timeout"), detail
        assert after.total_cost <= optimal_cost * Decimal("1.005"), f"limite de tempo atingido: {detail}"
