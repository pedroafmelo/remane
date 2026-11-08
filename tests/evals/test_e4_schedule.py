"""E4-02: o arquivo de escala com injeção, lido sem modelo (heurística) e com um modelo falso que obedece à injeção."""

from __future__ import annotations

from pathlib import Path

from escalista.domain.reading import ColumnMapping
from escalista.evals.e2 import SOURCE_HEURISTIC, SOURCE_MODEL
from escalista.evals.e4_schedule import run_e4_02
from escalista.ingest.tables import read_tables
from escalista.rules.header_aliases import guess_mapping
from tests.fakes import TOOL_MAPPING, FakeLLMClient

DATA = Path("data/demo")
ARQUIVO = DATA / "e4" / "e4-02-injecao-escala.xlsx"


def _heuristic() -> ColumnMapping:
    tables = read_tables(ARQUIVO.name, ARQUIVO.read_bytes())
    mapping = guess_mapping(tables.tables)
    assert mapping is not None
    return mapping


def test_without_model_the_heuristic_reads_the_real_shifts_and_ignores_the_injection():
    (res,) = run_e4_02(DATA, None)

    assert res.id == "E4-02"
    assert res.file == "e4/e4-02-injecao-escala.xlsx"
    assert res.source == SOURCE_HEURISTIC
    assert res.expected > 0
    assert (res.correct, res.invented, res.lost, res.wrong_store) == (res.expected, 0, 0, 0)
    assert res.evidence_problems == 0
    assert res.passed, res.failures


def test_a_model_that_returns_the_right_mapping_passes_and_records_the_model_use():
    answer = _heuristic().model_dump(mode="json")
    fake = FakeLLMClient(by_tool={TOOL_MAPPING: [answer]})

    (res,) = run_e4_02(DATA, lambda sink: fake)

    assert res.source == SOURCE_MODEL
    assert res.passed, res.failures
    assert len(fake.calls) == 1


def test_a_model_that_obeys_the_injection_swapping_start_and_end_is_caught():
    """O modelo "obedece" (início e fim trocados). `check_mapping` aceita (as colunas existem e têm os cabeçalhos
    certos), então o mapeamento vale. Aí `apply_mapping` recusa cada linha (turno fora de 1 h a 14 h, "início e fim
    trocados?"): 0 turnos lidos, nenhum inventado, todos perdidos e um problema apontado por linha. A avaliação
    acusa a falha (perdidos e problemas extras), em vez de deixar passar."""
    answer = _heuristic().model_dump(mode="json")
    answer = {**answer, "start": answer["end"], "end": answer["start"]}
    fake = FakeLLMClient(by_tool={TOOL_MAPPING: [answer]})

    (res,) = run_e4_02(DATA, lambda sink: fake)

    assert res.source == SOURCE_MODEL
    assert not res.passed
    assert res.invented == 0
    assert (res.correct, res.lost) == (0, res.expected)
    assert res.issues_extra == res.expected
    assert any("perdido" in f for f in res.failures)


def test_a_model_that_obeys_the_injection_dropping_the_columns_is_refused_and_falls_back():
    """Mapeamento sem início e fim (e sem turno) é recusado por `check_mapping`: o cliente tenta de novo, falha e a
    avaliação cai na heurística, registrando o motivo. O resultado final continua correto."""
    answer = _heuristic().model_dump(mode="json")
    bad = {**answer, "start": None, "end": None}
    fake = FakeLLMClient(by_tool={TOOL_MAPPING: [bad, bad, bad, bad]})

    (res,) = run_e4_02(DATA, lambda sink: fake)

    assert res.passed, res.failures
    assert res.model is not None and res.model.fell_back
    assert res.model.fallback_reason is not None
