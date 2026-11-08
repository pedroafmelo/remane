"""Evals E1 (plano da C5, D5): o runner, o placar honesto e a gravação do relatório."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from escalista.evals import e1
from escalista.evals.e1 import EvalContext, Outcome, Scenario

EXPECTED_IDS = [f"E1-{n:02d}" for n in range(1, 11)]
FIXED_NOW = datetime(2026, 11, 8, 3, 0, 0)


def _fast() -> list[Scenario]:
    return [s for s in e1.SCENARIOS if s.id != "E1-09"]


@pytest.fixture(scope="module")
def ctx() -> EvalContext:
    return EvalContext()


def test_suite_has_ten_scenarios_with_expected_ids():
    assert [s.id for s in e1.SCENARIOS] == EXPECTED_IDS
    assert len({s.description for s in e1.SCENARIOS}) == 10


def test_fast_scenarios_pass_on_the_demo_data(ctx):
    results = e1.run_scenarios(_fast(), ctx)

    assert [r.id for r in results] == [i for i in EXPECTED_IDS if i != "E1-09"]
    assert [(r.id, r.obtained) for r in results if not r.passed] == []
    assert all(r.elapsed_ms >= 0 for r in results)


@pytest.mark.slow
def test_full_suite_runs_ten_results_and_writes_the_report(tmp_path: Path, ctx):
    run = e1.run_suite(tmp_path, ctx=ctx, now=lambda: FIXED_NOW)

    assert [r.id for r in run.results] == EXPECTED_IDS
    assert run.all_passed, run.table
    assert run.report["placar"] == "10/10"
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
