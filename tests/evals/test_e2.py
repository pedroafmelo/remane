"""Evals E2 (plano da C6, D5): suíte sem modelo, modo com modelo (cliente falso) e reserva se o modelo falha."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from escalista.domain.contracts import LLMUnavailableError, TraceEvent
from escalista.domain.ports import TraceSink
from escalista.evals import __main__ as evals_cli
from escalista.evals import e2
from escalista.ingest.tables import read_tables
from escalista.rules.header_aliases import guess_mapping
from tests.fakes import TOOL_MAPPING, FakeLLMClient

DATA = Path("data/demo")
FIXED_NOW = datetime(2026, 11, 8, 4, 0, 0)
EXPECTED_IDS = [
    *(f"E2-{n:02d}" for n in range(1, 11)),
    "E2-11a",
    "E2-11b",
    "E2-11c",
    "E2-11d",
    "EXEMPLO",
]


class _Emitting:
    """Como o cliente real: um `TraceEvent` por chamada no `TraceSink`, com `kind`, tokens, custo e latência."""

    def __init__(self, inner: FakeLLMClient, sink: TraceSink) -> None:
        self._inner = inner
        self._sink = sink

    def complete(self, *, size, messages, tool_schema=None, run_id, parent_id=None, kind=None):
        try:
            result = self._inner.complete(
                size=size, messages=messages, tool_schema=tool_schema, run_id=run_id, parent_id=parent_id
            )
        except LLMUnavailableError:
            self._emit(run_id, "exception.raised", None, None, None, None, 3)
            raise
        self._emit(run_id, kind or "llm.call", "fake-model", 10, 5, Decimal("0.0001"), 7)
        return result

    def _emit(self, run_id, kind, model, tokens_in, tokens_out, cost, latency) -> None:
        self._sink.emit(
            TraceEvent(
                id=f"ev-{run_id}-{kind}",
                run_id=run_id,
                kind=kind,
                at=FIXED_NOW,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                latency_ms=latency,
            )
        )


def _heuristic_answers() -> list[dict]:
    """O falso devolve o `guess_mapping` de cada arquivo legível, na ordem em que a suíte os lê."""
    answers = []
    for gabarito in e2.discover(DATA):
        gold = json.loads(gabarito.read_text(encoding="utf-8"))
        path = DATA / gold["file"]
        tables = read_tables(path.name, path.read_bytes())
        if tables.exception is None and tables.tables:
            mapping = guess_mapping(tables.tables)
            assert mapping is not None
            answers.append(mapping.model_dump(mode="json"))
    return answers


def test_suite_without_model_scores_every_file_with_no_invented_shift(tmp_path: Path):
    run = e2.run_suite(tmp_path, data_dir=DATA, now=lambda: FIXED_NOW)

    assert [r.id for r in run.results] == EXPECTED_IDS
    assert [(r.id, r.failures) for r in run.results if not r.passed] == []
    totals = run.report["totais"]
    assert totals["inventados"] == 0
    assert totals["turnos_esperados"] == totals["corretos"] == 747
    assert totals["perdidos"] == 0
    assert totals["rx13_certos"] == "4/4"
    assert run.report["placar"] == "15/15" == e2.scoreboard(run.results)
    assert run.all_passed
    assert {r.source for r in run.results if r.expect == "shifts"} == {e2.SOURCE_HEURISTIC}
    assert all(r.model is None for r in run.results)
    assert run.path == tmp_path / "e2-20261108T040000.json"
    assert (tmp_path / "e2-latest.json").read_text() == run.path.read_text()


def test_suite_reports_the_planted_cases(tmp_path: Path):
    by_id = {r.id: r for r in e2.run_suite(tmp_path, data_dir=DATA, now=lambda: FIXED_NOW).results}

    assert (by_id["E2-07"].issues_expected, by_id["E2-07"].issues_found, by_id["E2-07"].issues_extra) == (6, 6, 0)
    assert by_id["E2-08"].identity is not None and by_id["E2-08"].identity["bate_com_gabarito"]
    assert by_id["E2-08"].identity["fusao_por_parecenca"] == 0
    assert by_id["E2-09"].same_as is not None and by_id["E2-09"].same_as["igual"]
    assert all(by_id[i].rx13_ok for i in ("E2-11a", "E2-11b", "E2-11c", "E2-11d"))
    assert all(r.evidence_problems == 0 for r in by_id.values())


def test_with_model_uses_the_fake_and_records_model_cost_and_latency(tmp_path: Path):
    shared = FakeLLMClient(by_tool={TOOL_MAPPING: _heuristic_answers()})

    run = e2.run_suite(
        tmp_path, data_dir=DATA, client_factory=lambda sink: _Emitting(shared, sink), now=lambda: FIXED_NOW
    )

    assert run.all_passed, run.table
    assert run.report["modo"] == "com_modelo"
    readable = [r for r in run.results if r.model is not None]
    assert len(readable) == 11  # os 4 RX-13 não chegam ao modelo
    assert len(shared.calls) == 11
    assert {r.source for r in readable} == {e2.SOURCE_MODEL}
    for r in readable:
        m = r.model
        assert m is not None
        assert (m.calls, m.models, m.tokens_in, m.tokens_out, m.cost_usd, m.latency_ms) == (
            1,
            ["fake-model"],
            10,
            5,
            Decimal("0.0001"),
            7,
        )
        assert not m.fell_back and m.same_as_heuristic is True
    assert run.report["modelo"] == {
        "chamadas": 11,
        "arquivos_com_reserva": 0,
        "tokens_entrada": 110,
        "tokens_saida": 55,
        "cost_usd": "0.0011",
        "latencia_ms": 77,
    }
    saved = json.loads((tmp_path / "e2-latest.json").read_text())
    assert saved["arquivos"][0]["modelo"]["cost_usd"] == "0.0001"


def test_with_model_that_fails_falls_back_to_the_heuristic_and_records_why(tmp_path: Path):
    shared = FakeLLMClient(fail=True)

    run = e2.run_suite(
        tmp_path, data_dir=DATA, client_factory=lambda sink: _Emitting(shared, sink), now=lambda: FIXED_NOW
    )

    readable = [r for r in run.results if r.model is not None]
    assert len(readable) == 11
    for r in readable:
        m = r.model
        assert m is not None and m.fell_back
        assert r.source == e2.SOURCE_FALLBACK
        assert m.fallback_reason is not None and m.fallback_reason.startswith("RX-12")
        assert m.calls == 1  # falha do cliente propaga sem reenvio
    assert run.all_passed, run.table  # a reserva leu tudo
    assert run.report["modelo"]["arquivos_com_reserva"] == 11
    assert "RESERVA: RX-12" in run.table


def test_a_model_that_poisons_the_mapping_is_not_trusted(tmp_path: Path):
    """Mapeamento válido mas errado (início e fim trocados) rende turnos errados: a suíte acusa, não esconde."""
    swapped = []
    for answer in _heuristic_answers():
        if answer["layout"] == "long" and answer["start"] and answer["end"]:
            answer = {**answer, "start": answer["end"], "end": answer["start"]}
        swapped.append(answer)
    shared = FakeLLMClient(by_tool={TOOL_MAPPING: swapped})

    run = e2.run_suite(
        tmp_path, data_dir=DATA, client_factory=lambda sink: _Emitting(shared, sink), now=lambda: FIXED_NOW
    )

    assert not run.all_passed
    assert run.report["totais"]["inventados"] == run.invented


@pytest.mark.parametrize(("drop_shift", "expected_exit"), [(False, 0), (True, 1)])
def test_cli_exit_code_is_nonzero_when_a_shift_is_invented(tmp_path: Path, drop_shift: bool, expected_exit: int):
    data = tmp_path / "demo"
    (data / "e2").mkdir(parents=True)
    shutil.copy(DATA / "e2" / "e2-01-csv-cp1252.csv", data / "e2")
    gold = json.loads((DATA / "e2" / "e2-01-csv-cp1252.esperado.json").read_text(encoding="utf-8"))
    if drop_shift:
        gold["shifts"].pop()  # o gabarito "esquece" um turno: o que o leitor devolve a mais é inventado
    (data / "e2" / "e2-01-csv-cp1252.esperado.json").write_text(json.dumps(gold), encoding="utf-8")

    code = evals_cli.main(["--suite", "e2", "--data", str(data), "--out", str(tmp_path / "out")])

    assert code == expected_exit
    report = json.loads((tmp_path / "out" / "e2-latest.json").read_text())
    assert report["totais"]["inventados"] == (1 if drop_shift else 0)
    assert report["placar"] == ("0/1" if drop_shift else "1/1")
