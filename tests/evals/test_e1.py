"""Evals E1 (plano da C5, D5): o runner, o placar honesto e a gravação do relatório."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from escalista.domain.results import ViolationReport
from escalista.evals import e1, suite_all
from escalista.evals.e1 import EvalContext, Outcome, Scenario

EXPECTED_IDS = [f"E1-{n:02d}" for n in range(1, 12)]
FIXED_NOW = datetime(2026, 11, 8, 3, 0, 0)


def _fast() -> list[Scenario]:
    return [s for s in e1.SCENARIOS if s.id != "E1-09"]


@pytest.fixture(scope="module")
def ctx() -> EvalContext:
    return EvalContext()


def test_suite_has_eleven_scenarios_with_expected_ids():
    assert [s.id for s in e1.SCENARIOS] == EXPECTED_IDS
    assert len({s.description for s in e1.SCENARIOS}) == 11


def test_fast_scenarios_pass_on_the_demo_data(ctx):
    results = e1.run_scenarios(_fast(), ctx)

    assert [r.id for r in results] == [i for i in EXPECTED_IDS if i != "E1-09"]
    assert [(r.id, r.obtained) for r in results if not r.passed] == []
    assert all(r.elapsed_ms >= 0 for r in results)


def _metrics(results, key):
    return [r.metrics[key] for r in results if r.metrics and key in r.metrics]


def test_e1_11_catches_every_planted_violation_with_no_false_positive(ctx):
    scenario = next(s for s in e1.SCENARIOS if s.id == "E1-11")
    outcome = scenario.run(ctx)

    assert outcome.passed, outcome.obtained
    assert outcome.metrics == {"rn04.violacoes": {"plantadas": 9, "detectadas": 9, "falsos_positivos": 0}}
    assert "9 plantadas" in outcome.obtained and "0 não detectadas" in outcome.obtained


def test_e1_11_fails_and_names_the_pairs_when_the_verifier_misses_one(ctx, monkeypatch):
    real_verify = e1.verify

    def blind(schedule, card):
        report = real_verify(schedule, card)
        kept = [v for v in report.violations if not (v.employee_id == "P004" and v.kind == "jornada_diaria_max")]
        return ViolationReport(violations=kept)

    monkeypatch.setattr(e1, "verify", blind)
    scenario = next(s for s in e1.SCENARIOS if s.id == "E1-11")
    outcome = scenario.run(ctx)

    assert not outcome.passed
    assert outcome.metrics["rn04.violacoes"] == {"plantadas": 9, "detectadas": 8, "falsos_positivos": 0}
    assert "1 não detectadas" in outcome.obtained and "P004" in outcome.obtained


def test_primitive_scenarios_report_one_planted_and_the_control_as_false_positive(ctx):
    results = e1.run_scenarios([s for s in e1.SCENARIOS if s.id in {"E1-01", "E1-02", "E1-03", "E1-04", "E1-10"}], ctx)

    assert [r.passed for r in results] == [True] * 5
    assert _metrics(results, "rn04.violacoes") == [{"plantadas": 1, "detectadas": 1, "falsos_positivos": 0}] * 5


def test_e1_06_and_e1_05_do_not_report_planted_violations(ctx):
    results = e1.run_scenarios([s for s in e1.SCENARIOS if s.id in {"E1-05", "E1-06"}], ctx)

    assert _metrics(results, "rn04.violacoes") == []


def test_fast_metrics_reach_the_rn04_block_of_the_all_report(ctx):
    rn04 = suite_all.rn04_metrics(e1.run_scenarios(_fast(), ctx))

    block = rn04["violacoes_nao_detectadas"]
    assert block["status"] == "medido"
    assert (block["plantadas"], block["detectadas"], block["nao_detectadas"], block["falsos_positivos"]) == (
        14,
        14,
        0,
        0,
    )


@pytest.mark.slow
def test_e1_09_reports_coverage_and_cost_against_the_sent_schedule(ctx):
    results = e1.run_scenarios([s for s in e1.SCENARIOS if s.id == "E1-09"], ctx)

    assert results[0].passed, results[0].obtained
    assert results[0].metrics["rn04.cobertura"] == {"escala_demo_pct": 100.0}
    rn04 = suite_all.rn04_metrics(results)
    cost = rn04["custo_contra_planilha"]
    assert cost["status"] == "medido" and cost["antes_brl"] is not None and cost["depois_brl"] is not None
    assert rn04["cobertura"]["escala_demo_pct"] == 100.0


@pytest.mark.slow
def test_full_suite_runs_eleven_results_and_writes_the_report(tmp_path: Path, ctx):
    run = e1.run_suite(tmp_path, ctx=ctx, now=lambda: FIXED_NOW)

    assert [r.id for r in run.results] == EXPECTED_IDS
    assert run.all_passed, run.table
    assert run.report["placar"] == "11/11"
    assert run.path == tmp_path / "e1-20261108T030000.json"
    assert (tmp_path / "e1-latest.json").read_text() == run.path.read_text()


def test_failing_scenario_shows_as_failure_in_the_scoreboard(tmp_path: Path):
    fake = [
        Scenario("F-01", "passa", lambda _: Outcome("1", "1", True)),
        Scenario("F-02", "cenário de mentira", lambda _: Outcome("1 violação", "0 violações", False)),
    ]

    run = e1.run_suite(tmp_path, scenarios=fake, now=lambda: FIXED_NOW)

    assert not run.all_passed
    assert e1.scoreboard(run.results) == "1/2"
    assert run.report["placar"] == "1/2" and run.report["passaram"] == 1 and run.report["total"] == 2
    assert "Placar: 1/2" in run.table
    assert "FALHOU" in run.table and "esperado: 1 violação" in run.table and "obtido:   0 violações" in run.table
    saved = json.loads((tmp_path / "e1-latest.json").read_text())
    assert [(c["id"], c["passou"]) for c in saved["cenarios"]] == [("F-01", True), ("F-02", False)]


def test_scenario_that_raises_is_a_failure_with_the_cause_and_does_not_stop_the_rest():
    def boom(_: EvalContext) -> Outcome:
        raise RuntimeError("quebrou")

    results = e1.run_scenarios(
        [Scenario("F-01", "explode", boom), Scenario("F-02", "ok", lambda _: Outcome("", "", True))]
    )

    assert [r.passed for r in results] == [False, True]
    assert "RuntimeError: quebrou" in results[0].obtained


def test_report_has_the_fields_of_each_scenario(tmp_path: Path):
    scenario = Scenario("F-01", "um", lambda _: Outcome("a", "a", True))

    run = e1.run_suite(tmp_path, scenarios=[scenario], now=lambda: FIXED_NOW)

    row = run.report["cenarios"][0]
    assert set(row) == {"id", "descricao", "esperado", "obtido", "passou", "tempo_ms"}
    assert run.report["gerado_em"] == "2026-11-08T03:00:00"
    assert "sem chamada de modelo" in run.report["modelo"]


def test_main_returns_nonzero_when_a_scenario_fails(tmp_path: Path, monkeypatch, capsys):
    failing = (Scenario("F-01", "falha", lambda _: Outcome("x", "y", False)),)
    monkeypatch.setattr(e1, "SCENARIOS", failing)
    assert e1.main(["--suite", "e1", "--out", str(tmp_path)]) == 1
    assert "Placar: 0/1" in capsys.readouterr().out
