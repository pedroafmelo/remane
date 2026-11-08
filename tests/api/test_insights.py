"""Painel do gestor: regras em português (FT-01), simulação de vigência com cache (FT-07) e impacto medido (FT-05).

A simulação aqui roda numa instância de 1 loja e 2 pessoas (dados sintéticos), nunca na 60 × 7 da demo.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from escalista.api.insights import impact, rules_view
from escalista.api.simulation import VigenciaSimulator, pre_ec_card
from escalista.api.wiring import DEFAULT_RULES_DIR, DEMO_WEEK_START
from escalista.audit.sink import SqlTraceSink
from escalista.db import init_db, make_engine
from escalista.domain.contracts import Role, TraceEvent
from escalista.domain.results import Approval, Comparison, RunState, ScheduleMetrics, ScheduleVersion
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Store
from escalista.rules.loader import load_rule_card
from escalista.store.sql_repository import SqlRepository
from tests.fakes import ListTraceSink

RULES = Path(DEFAULT_RULES_DIR)


def tiny_simulator(sink=None) -> VigenciaSimulator:
    """1 loja, 2 pessoas, 4 horas de demanda na segunda (dados sintéticos de teste)."""
    store = Store(id="S1", name="Loja Teste (fictícia)", opens=time(8), closes=time(20))
    people = [
        Employee(
            id=f"E{i}",
            name=f"Pessoa {i} (fictícia)",
            store_id="S1",
            job="caixa",
            hourly_wage=Decimal("10.00"),
            contract_hours=42,
            sex="F",
        )
        for i in (1, 2)
    ]
    demand = [
        DemandSlot(store_id="S1", day=DEMO_WEEK_START, start=time(8 + h // 2, 30 * (h % 2)), required=1)
        for h in range(8)
    ]
    return VigenciaSimulator(RULES, [store], people, demand, DEMO_WEEK_START, sink=sink, time_limit_s=5)


# --- regras ---


def test_rules_view_groups_by_layer_in_plain_portuguese():
    view = rules_view(load_rule_card(RULES, DEMO_WEEK_START))
    assert [g.layer.value for g in view.groups] == ["lei", "convencao", "politica"]
    assert [g.title for g in view.groups] == ["Lei · EC 141/CLT", "Convenção fictícia", "Política fictícia"]
    flags = [r.engine for r in view.groups[0].rules]
    assert flags == sorted(flags, reverse=True)  # as que o motor usa vêm primeiro
    lei = {r.id: r for r in view.groups[0].rules}
    weekly = lei["jornada_semanal_max"]
    assert (weekly.limit, weekly.engine, weekly.status) == ("42 h por semana", True, "interpretacao")
    assert weekly.source.startswith("art. 6º")
    assert lei["repouso_semanal"].limit == "2 dia(s) de repouso por semana"
    assert lei["regime_12x36"].engine is False and lei["regime_12x36"].escalates is True
    convencao = {r.id: r for r in view.groups[1].rules}
    assert convencao["cct_adicional_hora_extra"].limit == "adicional de 60% na hora extra"
    assert convencao["cct_folgas_dominicais"].status == "pendente"
    assert {r.status for r in view.groups[2].rules} >= {"ficticia"}


# --- simulação ---


def test_pre_ec_card_is_44h_with_one_rest_day_from_clt():
    card = pre_ec_card(RULES)
    by_kind = {r.kind: r for r in card.rules}
    assert by_kind["jornada_semanal_max"].params == {"hours": 44}
    assert by_kind["repouso_semanal"].params == {"days": 1}
    assert by_kind["repouso_semanal"].source.startswith("CLT, art. 67")


def test_simulation_solves_both_regimes_and_caches_by_input_hash():
    sink = ListTraceSink()
    sim = tiny_simulator(sink)
    first = sim.run()
    assert first.cached is False and first.simulated is True
    assert (first.before.regime, first.after.regime) == ("44h", "42h")
    assert first.after.metrics.coverage_pct == 100.0 and first.after.metrics.violations == 0
    assert first.cost_of_ec141 == first.after.metrics.total_cost - first.before.metrics.total_cost
    assert any("44 h por semana" in line for line in first.before.limits)
    second = sim.run()
    assert second.cached is True
    assert second.before == first.before and second.after == first.after
    assert [e.kind for e in sink.events] == ["simulation.vigencia"]  # o cache não emite de novo


# --- impacto ---


def metrics(cost: str, overtime: str, violations: int, coverage: float = 100.0) -> ScheduleMetrics:
    return ScheduleMetrics(
        total_cost=Decimal(cost),
        regular_hours=Decimal(100),
        overtime_hours=Decimal(overtime),
        overtime_cost=Decimal(0),
        coverage_pct=coverage,
        uncovered_slots=0,
        violations=violations,
    )


def seed_run(repo: SqlRepository, sink: SqlTraceSink, run_id: str, *, publish: bool, cost_usd: str, latency: int):
    before, after = metrics("1000.00", "10", 5), metrics("900.00", "0", 0, 98.5)
    comparison = Comparison(
        before=before, after=after, savings=Decimal("100.00"), overtime_hours_avoided=Decimal(10), violations_avoided=5
    )
    at = datetime(2027, 1, 10, 9)
    sink.emit(
        TraceEvent(id=f"{run_id}-1", run_id=run_id, kind="solver.run", at=at, cost_usd=Decimal(0), latency_ms=latency)
    )
    sink.emit(
        TraceEvent(
            id=f"{run_id}-2", run_id=run_id, kind="llm.justify", at=at, cost_usd=Decimal(cost_usd), latency_ms=latency
        )
    )
    version_id = f"v-{run_id}"
    phase = "published" if publish else "awaiting_approval"
    repo.save_run(RunState(run_id=run_id, phase=phase, comparison=comparison, version_id=version_id))
    repo.save_version(
        ScheduleVersion(
            id=version_id,
            run_id=run_id,
            schedule=Schedule(week_start=DEMO_WEEK_START, shifts=[]),
            status="draft",
            input_hash="h",
            seed=42,
            violations_total=0,
            created_at=at,
        )
    )
    if publish:
        repo.record_approval(
            Approval(id=f"a-{run_id}", version_id=version_id, approved_by="g", role=Role.GESTOR, at=at)
        )
        repo.mark_published(version_id, at)


def engine_for(tmp_path):
    import escalista.audit.tables  # noqa: F401
    import escalista.store.tables  # noqa: F401

    engine = make_engine(f"sqlite:///{tmp_path}/impact.db")
    init_db(engine)
    return engine


def test_impact_is_empty_without_runs(tmp_path):
    result = impact(engine_for(tmp_path))
    assert result.current is None and result.runs == [] and result.runs_total == 0
    assert result.agent_cost_usd_total == 0 and result.agent_latency_ms_avg is None


def test_impact_sums_trace_and_uses_the_version_in_force(tmp_path):
    engine = engine_for(tmp_path)
    repo, sink = SqlRepository(engine), SqlTraceSink(engine)
    seed_run(repo, sink, "r1", publish=True, cost_usd="0.000100", latency=1000)
    seed_run(repo, sink, "r2", publish=True, cost_usd="0.000200", latency=3000)
    seed_run(repo, sink, "r3", publish=False, cost_usd="0.000300", latency=500)
    sink.emit(
        TraceEvent(id="sim", run_id="sim-vigencia", kind="simulation.vigencia", at=datetime(2027, 1, 1), latency_ms=9)
    )

    result = impact(engine)
    assert (result.runs_total, result.runs_published) == (3, 2)
    assert [r.run_id for r in result.runs] == ["r3", "r2", "r1"]  # do mais novo para o mais velho (ordem do rastro)
    assert result.current is not None and result.current.run_id == "r2"  # a última publicada, não a soma
    assert result.current.savings == Decimal("100.00") and result.current.coverage_after == 98.5
    assert result.current.agent_cost_usd == Decimal("0.000200") and result.current.agent_latency_ms == 6000
    assert result.agent_cost_usd_total == Decimal("0.000600")
    assert result.agent_latency_ms_avg == round((2000 + 6000 + 1000) / 3)  # a simulação fica fora
    assert {"comparison", "agent", "scope"} <= set(result.provenance)
    assert date(2027, 1, 10) == result.runs[0].started_at.date()
