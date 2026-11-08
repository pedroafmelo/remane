"""Harness comum dos evals (plano dos evals E3/E4, seção 4): status honesto, requisitos e modelo executado de fato."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from escalista.domain.contracts import TraceEvent
from escalista.evals import common, e1, e2
from escalista.evals.common import (
    EvalContext,
    MemorySink,
    ModelUse,
    NotRun,
    Outcome,
    Requirement,
    Scenario,
    model_use,
    run_scenarios,
)

NOW = datetime(2026, 11, 8, 10, 0, 0)


def _event(run_id: str, kind: str, model: str | None, cost: str | None, latency: int = 5) -> TraceEvent:
    return TraceEvent(
        id=f"{run_id}-{kind}-{model}",
        run_id=run_id,
        kind=kind,
        at=NOW,
        model=model,
        tokens_in=10 if model else None,
        tokens_out=4 if model else None,
        cost_usd=None if cost is None else Decimal(cost),
        latency_ms=latency,
    )


def _real_use() -> ModelUse:
    sink = MemorySink()
    sink.emit(_event("r1", "track.llm.read_atestado", "small-model", "0.0002"))
    return model_use(sink, "r1", ("track.llm.read_atestado",))


def test_old_names_are_reexported_from_e1_and_e2():
    assert e1.Outcome is Outcome and e1.Scenario is Scenario and e1.EvalContext is EvalContext
    assert e2.MemorySink is MemorySink and e2.ModelUse is ModelUse


def test_scenario_defaults_keep_the_e1_style():
    s = Scenario("X-01", "desc", lambda _: Outcome("a", "a", True))
    assert (s.suite, s.uses_model, s.tier, s.requires) == ("e1", False, "atual", ())


def test_passing_failing_and_raising_scenarios_get_a_status():
    def boom(_):
        raise RuntimeError("quebrou")

    results = run_scenarios(
        [
            Scenario("X-01", "ok", lambda _: Outcome("a", "a", True)),
            Scenario("X-02", "falha", lambda _: Outcome("a", "b", False)),
            Scenario("X-03", "explode", boom),
        ]
    )
    assert [r.status for r in results] == ["passou", "falhou", "falhou"]
    assert [r.passed for r in results] == [True, False, False]
    assert "RuntimeError: quebrou" in results[2].obtained


def test_not_run_raised_by_the_scenario_is_not_a_failure():
    def cannot(_):
        raise NotRun("cenário ainda não escrito")

    (r,) = run_scenarios([Scenario("X-01", "x", cannot)])
    assert r.status == "não executado" and r.reason == "cenário ainda não escrito" and not r.passed


def test_missing_requirement_is_not_run_and_the_scenario_never_runs():
    called = []

    def run(_):
        called.append(1)
        return Outcome("a", "a", True)

    reqs = (Requirement("escalista.nao_existe.modulo", "build_tracker", "SAIDA-AC-02"),)
    (r,) = run_scenarios([Scenario("X-01", "x", run, requires=reqs)])
    assert r.status == "não executado"
    assert r.reason == "falta SAIDA-AC-02 (escalista.nao_existe.modulo.build_tracker)"
    assert called == []


def test_missing_attribute_is_detected_with_a_chained_getattr():
    reqs = (Requirement("escalista.evals.common", "Scenario.nao_existe", "SAIDA-AC-17"),)
    (r,) = run_scenarios([Scenario("X-01", "x", lambda _: Outcome("a", "a", True), requires=reqs)])
    assert r.reason == "falta SAIDA-AC-17 (escalista.evals.common.Scenario.nao_existe)"

    present = (Requirement("escalista.evals.common", "Scenario", "SAIDA-AC-17"), Requirement("json", None, "X"))
    (ok,) = run_scenarios([Scenario("X-02", "x", lambda _: Outcome("a", "a", True), requires=present)])
    assert ok.status == "passou"


def test_model_scenario_without_with_model_is_not_run():
    (r,) = run_scenarios([Scenario("X-01", "x", lambda _: Outcome("a", "a", True), uses_model=True)])
    assert r.status == "não executado" and r.reason == "sem --with-model"


def test_model_scenario_with_model_but_without_a_key_is_not_run():
    ctx = EvalContext(with_model=True, llm=None)
    (r,) = run_scenarios([Scenario("X-01", "x", lambda _: Outcome("a", "a", True), uses_model=True)], ctx)
    assert r.status == "não executado" and r.reason == "sem chave"


def test_model_scenario_that_never_called_a_real_model_is_forced_to_not_run():
    """Regra de honestidade: o falso (`model="fake"`) e nenhuma chamada nunca contam como execução com modelo."""
    ctx = EvalContext(with_model=True, llm=object())  # type: ignore[arg-type]
    fake_sink = MemorySink()
    fake_sink.emit(_event("r1", "llm.call", "fake", "0"))
    fake = model_use(fake_sink, "r1", ("llm.call",))
    scenarios = [
        Scenario("X-01", "sem modelo no outcome", lambda _: Outcome("a", "a", True), uses_model=True),
        Scenario("X-02", "falso", lambda _: Outcome("a", "a", True, model=fake), uses_model=True),
        Scenario("X-03", "falso falhando", lambda _: Outcome("a", "b", False, model=fake), uses_model=True),
        Scenario("X-04", "real", lambda _: Outcome("a", "a", True, model=_real_use()), uses_model=True),
    ]
    results = run_scenarios(scenarios, ctx)
    assert [r.status for r in results] == ["não executado", "não executado", "não executado", "passou"]
    assert all(r.reason == "modelo não chamado" for r in results[:3])
    assert [r.model_executed for r in results] == [False, False, False, True]


def test_scenario_without_model_never_counts_as_model_executed():
    (r,) = run_scenarios([Scenario("X-01", "x", lambda _: Outcome("a", "a", True, model=_real_use()))])
    assert r.status == "passou" and not r.model_executed


def test_model_use_filters_by_run_id_and_kind_and_keeps_cost_unmeasured_when_missing():
    sink = MemorySink()
    sink.emit(_event("r1", "track.llm.read_atestado", "m", "0.0001", 3))
    sink.emit(_event("r1", "exception.raised", "m", None, 2))
    sink.emit(_event("r2", "track.llm.read_atestado", "m", "0.5"))
    sink.emit(_event("r1", "llm.map_columns", "m", "0.5"))

    use = model_use(sink, "r1", ("track.llm.read_atestado",))
    assert (use.calls, use.models, use.tokens_in, use.tokens_out, use.latency_ms) == (2, ["m"], 10, 4, 5)
    assert use.cost_usd is None  # uma chamada sem custo medido: o total não é medido, nunca estimado


def test_as_json_keeps_the_e1_keys_and_adds_the_new_ones():
    (r,) = run_scenarios([Scenario("X-01", "x", lambda _: Outcome("a", "a", True, metrics={"k": 1}), tier="T1b")])
    row = r.as_json()
    assert {"id", "descricao", "esperado", "obtido", "passou", "tempo_ms"} <= set(row)
    assert {"status", "suite", "usa_modelo", "tier", "motivo"} <= set(row)
    assert row["metricas"] == {"k": 1} and "modelo" not in row
    assert row["tier"] == "T1b" and row["passou"] is True


def test_render_shows_status_and_reason_per_line():
    results = run_scenarios(
        [
            Scenario("X-01", "ok", lambda _: Outcome("a", "a", True)),
            Scenario("X-02", "falha", lambda _: Outcome("a", "b", False)),
            Scenario("X-03", "modelo", lambda _: Outcome("a", "a", True), uses_model=True),
        ]
    )
    table = common.render(results)
    assert "passou" in table and "FALHOU" in table and "não executado (sem --with-model)" in table
