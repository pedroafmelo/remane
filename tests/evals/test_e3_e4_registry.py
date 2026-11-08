"""Registro dos cenários do E3 e do E4 (plano dos evals E3/E4, seções 6 a 8 e 11)."""

from __future__ import annotations

from escalista.evals import e3, e4
from escalista.evals.common import EvalContext, run_scenarios

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


def test_e4_02_with_a_model_client_is_not_yet_written():
    (r,) = run_scenarios([s for s in e4.SCENARIOS if s.id == "E4-02"], EvalContext(with_model=True, llm=object()))  # type: ignore[arg-type]
    assert r.status == "não executado" and "tarefa E2" in (r.reason or "")
