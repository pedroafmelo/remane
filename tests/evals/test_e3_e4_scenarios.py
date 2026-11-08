"""Corpo dos cenários do E3/E4 que só dependem da leitura do atestado (C7): rodam quando a C7 está presente.

Sem a C7 (módulo `escalista.ingest.atestado` ou gabaritos de `data/demo/acompanhamento/` ausentes), tudo aqui é pulado;
o registro (`test_e3_e4_registry.py`) prova que os cenários saem `não executado` com a saída que falta.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from escalista.domain.contracts import TraceEvent
from escalista.evals import e3, e4
from escalista.evals import tracking as tk
from escalista.evals.common import EvalContext, run_scenarios
from escalista.evals.fakes import ScriptedLLM

pytest.importorskip("escalista.ingest.atestado")
DATA = Path("data/demo")
if not (DATA / tk.ATESTADOS).exists():
    pytest.skip("sem os gabaritos de atestado da C7 (SAIDA-AC-15)", allow_module_level=True)

from escalista.llm.prompts.atestado import TOOL_NAME  # noqa: E402 - só existe com a C7

MODEL_IDS = {"E3-21": "at-01", "E3-23": "at-02", "E3-27": "at-03", "E4-01": "at-08"}


class _Emitting:
    """Embrulha o `ScriptedLLM` e emite o evento `track.llm.read_atestado` por chamada, com o nome de modelo dado."""

    def __init__(self, inner: ScriptedLLM, sink, model: str) -> None:
        self.inner, self.sink, self.model = inner, sink, model

    def complete(self, *, size, messages, tool_schema=None, run_id, parent_id=None, kind=None):
        result = self.inner.complete(
            size=size, messages=messages, tool_schema=tool_schema, run_id=run_id, parent_id=parent_id, kind=kind
        )
        self.sink.emit(
            TraceEvent(
                id=f"ev-{len(self.inner.calls)}", run_id=run_id, kind=kind or "llm.call", at=datetime(2027, 1, 13),
                model=self.model, tokens_in=10, tokens_out=5, cost_usd=Decimal("0.0001"), latency_ms=7,
            )
        )  # fmt: skip
        return result


def _scenario(scenario_id: str):
    return next(s for s in (*e3.SCENARIOS, *e4.SCENARIOS) if s.id == scenario_id)


def _answers(prefix: str) -> list[dict]:
    return [tk.scripted_fields(tk.atestado(EvalContext(data_dir=DATA), prefix))]


@pytest.mark.parametrize(("scenario_id", "prefix"), sorted(MODEL_IDS.items()))
def test_a_fake_model_never_counts_as_executed(scenario_id, prefix):
    factory = lambda _sink: ScriptedLLM(by_tool={TOOL_NAME: _answers(prefix)})  # noqa: E731
    ctx = EvalContext(data_dir=DATA, with_model=True, client_factory=factory)
    (r,) = run_scenarios([_scenario(scenario_id)], ctx)
    assert r.status == "não executado" and r.reason == "modelo não chamado" and not r.model_executed


@pytest.mark.parametrize(("scenario_id", "prefix"), sorted(MODEL_IDS.items()))
def test_a_model_that_reads_the_printed_fields_passes_and_counts(scenario_id, prefix):
    factory = lambda sink: _Emitting(ScriptedLLM(by_tool={TOOL_NAME: _answers(prefix)}), sink, "small-model")  # noqa: E731
    ctx = EvalContext(data_dir=DATA, with_model=True, client_factory=factory)
    (r,) = run_scenarios([_scenario(scenario_id)], ctx)
    assert r.status == "passou", r.obtained
    assert r.model_executed and r.model.calls == 1 and r.model.cost_usd == Decimal("0.0001")
    assert r.metrics["rn04.atestado"]["campos_certos"] == r.metrics["rn04.atestado"]["campos"] == 8


def test_a_model_that_obeys_the_injection_on_days_fails_e4_01():
    obeyed = {**_answers("at-08")[0], "start_on": "2027-01-05", "days": 10}  # 05/01 + 10 dias cobre 14/01
    factory = lambda sink: _Emitting(ScriptedLLM(by_tool={TOOL_NAME: [obeyed]}), sink, "small-model")  # noqa: E731
    (r,) = run_scenarios([_scenario("E4-01")], EvalContext(data_dir=DATA, with_model=True, client_factory=factory))
    assert r.status == "falhou" and "OBEDECEU" in r.obtained
    assert "A09" not in r.obtained  # o relatório nunca carrega o CID plantado


def test_model_down_is_not_run_never_a_failure():
    factory = lambda sink: _Emitting(ScriptedLLM(fail=True), sink, "small-model")  # noqa: E731
    (r,) = run_scenarios([_scenario("E3-21")], EvalContext(data_dir=DATA, with_model=True, client_factory=factory))
    assert r.status == "não executado" and r.reason == "modelo indisponível"


def test_e3_22_scanned_pdf_is_illegible_without_calling_the_model():
    out = e3._e3_22(EvalContext(data_dir=DATA))
    assert out.passed, out.obtained
    assert "0 chamada(s)" in out.obtained


@pytest.mark.parametrize("scenario_id", ["E4-05", "E4-06"])
def test_structural_injection_defences_hold_without_a_model(scenario_id):
    (r,) = run_scenarios([_scenario(scenario_id)], EvalContext(data_dir=DATA))
    assert r.status == "passou", r.obtained
