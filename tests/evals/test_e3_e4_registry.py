"""Registro dos cenários do E3 e do E4 (plano dos evals E3/E4, seções 6 a 8 e 11)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from escalista.domain.contracts import LLMUnavailableError, TraceEvent
from escalista.evals import e3, e4
from escalista.evals.common import EvalContext, run_scenarios
from escalista.evals.fakes import ScriptedLLM
from escalista.ingest.tables import read_tables
from escalista.rules.header_aliases import guess_mapping
from tests.fakes import TOOL_MAPPING

DATA = Path("data/demo")

E3_IDS = [f"E3-{n:02d}" for n in (*range(1, 17), *range(21, 29))]
E4_IDS = [f"E4-{n:02d}" for n in range(1, 8)]


def _by_id(scenarios) -> dict:
    return {s.id: s for s in scenarios}


def test_e3_registry_has_every_scenario_once():
    ids = [s.id for s in e3.SCENARIOS]
    assert ids == E3_IDS
    assert all(s.suite == "e3" for s in e3.SCENARIOS)


def test_e3_model_and_tier_flags():
    by = _by_id(e3.SCENARIOS)
    with_model = {i for i, s in by.items() if s.uses_model}
    assert with_model == {"E3-21", "E3-23", "E3-24", "E3-25", "E3-26", "E3-27", "E3-28"}
    assert by["E3-22"].tier == "T1b" and not by["E3-22"].uses_model
    assert by["E3-03"].tier == "T2" and not by["E3-03"].uses_model
    assert {by[i].tier for i in ("E3-25", "E3-26", "E3-28")} == {"T2"}
    assert {by[i].tier for i in ("E3-05", "E3-06", "E3-07", "E3-10", "E3-11", "E3-12")} == {"T1a"}


def _saidas(scenario) -> set[str]:
    return {r.saida for r in scenario.requires}


def test_e3_requirements_follow_the_matrix():
    by = _by_id(e3.SCENARIOS)
    for i, s in by.items():
        if not s.uses_model or i == "E3-24":
            assert "SAIDA-AC-02" in _saidas(s), i
    for i in ("E3-13", "E3-16", *(f"E3-{n}" for n in range(21, 29))):
        assert "SAIDA-AC-05" in _saidas(by[i]), i
    for i in ("E3-15", "E3-24"):
        assert "SAIDA-AC-13" in _saidas(by[i]), i
    build = next(r for r in by["E3-01"].requires if r.saida == "SAIDA-AC-02")
    assert (build.module, build.attr) == ("escalista.api.tracker_wiring", "build_tracker")


def test_e4_registry():
    by = _by_id(e4.SCENARIOS)
    assert list(by) == E4_IDS
    assert all(s.suite == "e4" for s in e4.SCENARIOS)
    assert {i for i, s in by.items() if s.uses_model} == {"E4-01", "E4-02", "E4-03", "E4-04"}
    assert by["E4-02"].requires == () and by["E4-02"].tier == "atual"
    assert {by[i].tier for i in ("E4-03", "E4-04", "E4-07")} == {"T2"}
    for i in ("E4-03", "E4-04", "E4-07"):
        assert "SAIDA-AC-17" in _saidas(by[i]), i
    msg = next(r for r in by["E4-07"].requires if r.saida == "SAIDA-AC-17")
    assert (msg.module, msg.attr) == ("escalista.agents.tracker.flow", "Tracker.message")
    assert "SAIDA-AC-13" in _saidas(by["E4-04"])
    for i in ("E4-01", "E4-05", "E4-06"):
        assert "SAIDA-AC-05" in _saidas(by[i]), i


def test_without_c7_every_dependent_scenario_says_which_output_is_missing():
    results = run_scenarios([*e3.SCENARIOS, *e4.SCENARIOS], EvalContext())
    assert {r.status for r in results} == {"não executado"}
    by = {r.id: r for r in results}
    assert by["E3-01"].reason.startswith("falta SAIDA-AC-02 (escalista.api.tracker_wiring.build_tracker)")
    assert by["E4-02"].reason == "sem --with-model"


class _Emitting:
    """Embrulha o `ScriptedLLM` e emite um evento por chamada no sink do cenário, com o nome de modelo dado."""

    def __init__(self, inner: ScriptedLLM, sink, model: str) -> None:
        self.inner, self.sink, self.model = inner, sink, model

    def complete(self, *, size, messages, tool_schema=None, run_id, parent_id=None, kind=None):
        try:
            result = self.inner.complete(
                size=size, messages=messages, tool_schema=tool_schema, run_id=run_id, parent_id=parent_id, kind=kind
            )
        except LLMUnavailableError:
            self._emit(run_id, "exception.raised", None)
            raise
        self._emit(run_id, kind or "llm.call", Decimal("0.0001"))
        return result

    def _emit(self, run_id, kind, cost) -> None:
        self.sink.emit(
            TraceEvent(
                id=f"ev-{id(self)}-{kind}", run_id=run_id, kind=kind, at=datetime(2026, 11, 8, 10),
                model=self.model, tokens_in=10, tokens_out=5, cost_usd=cost, latency_ms=7,
            )
        )  # fmt: skip


def _heuristic_answer() -> dict:
    path = DATA / "e4" / "e4-02-injecao-escala.xlsx"
    mapping = guess_mapping(read_tables(path.name, path.read_bytes()).tables)
    assert mapping is not None
    return mapping.model_dump(mode="json")


def _run_e4_02(answers: list[dict], model: str):
    scripted = ScriptedLLM(by_tool={TOOL_MAPPING: answers})
    ctx = EvalContext(data_dir=DATA, with_model=True, client_factory=lambda sink: _Emitting(scripted, sink, model))
    (r,) = run_scenarios([s for s in e4.SCENARIOS if s.id == "E4-02"], ctx)
    return r


def test_e4_02_with_a_model_that_maps_right_passes_and_counts_as_model_executed():
    r = _run_e4_02([_heuristic_answer()], "small-model")
    assert r.status == "passou" and r.model_executed
    assert r.model is not None and r.model.calls == 1 and r.model.cost_usd == Decimal("0.0001")


def test_e4_02_fallback_to_the_heuristic_is_a_failure_with_the_reason():
    bad = {**_heuristic_answer(), "start": None, "end": None}
    r = _run_e4_02([bad] * 4, "small-model")
    assert r.status == "falhou" and r.model_executed
    assert r.reason == "modelo não produziu mapeamento válido; a reserva (heurística) salvou o fluxo"


def test_e4_02_fallback_with_the_fake_model_never_counts_as_executed():
    bad = {**_heuristic_answer(), "start": None, "end": None}
    r = _run_e4_02([bad] * 4, "fake")
    assert r.status == "não executado" and r.reason == "modelo não chamado" and not r.model_executed
