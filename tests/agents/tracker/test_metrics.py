"""Métricas do acompanhamento a partir do rastro (SAIDA-AC-12)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from escalista.agents.tracker.metrics import summarize
from escalista.domain.contracts import Role, TraceEvent
from tests.agents.tracker.conftest import build_env

AT = datetime(2027, 1, 13, 14, 0)


def _ev(i: int, run_id: str, kind: str, payload: dict | None = None, **cols) -> TraceEvent:
    return TraceEvent(id=f"e{i}", run_id=run_id, kind=kind, at=AT, payload=payload or {}, **cols)


def test_summarize_without_model_calls_reports_cost_as_not_measured():
    m = summarize([])
    assert (m.cases, m.covered, m.coverage_rate, m.median_minutes_to_cover) == (0, 0, None, None)
    assert m.cost_usd_total is None and m.latency_ms_p50 is None and m.latency_ms_max is None
    assert m.overtime_hours_added == Decimal(0) and m.atestado_reads == 0


def test_summarize_counts_only_track_llm_read_for_cost_and_latency():
    events = [
        _ev(1, "track-a", "track.replan.requested"),
        _ev(2, "track-a", "track.llm.read_atestado", {"size": "small"}, cost_usd=Decimal("0.0010"), latency_ms=900),
        _ev(3, "track-a", "track.case.closed", {"outcome": "coberta", "minutes_to_close": 10, "new_violations": 0,
                                                 "overtime_hours_added": "1.50"}),
        _ev(4, "track-b", "track.replan.requested"),
        _ev(5, "track-b", "track.llm.read_atestado", {"size": "small"}, cost_usd=None, latency_ms=300),
        _ev(6, "track-b", "track.case.closed", {"outcome": "descoberta", "minutes_to_close": 40, "new_violations": 0,
                                                 "overtime_hours_added": "0"}),
        _ev(7, "track-c", "track.case.closed", {"outcome": "coberta", "minutes_to_close": 20, "new_violations": 0,
                                                 "overtime_hours_added": "0.00"}),
        _ev(8, "track-c", "track.llm.read_atestado", {"error": "LLMUnavailableError"}, latency_ms=5000),
        _ev(9, "run-x", "llm.justify", cost_usd=Decimal("9"), latency_ms=99999),
        _ev(10, "track-sweep", "track.channel.rejected", {"sender_hash": "abc"}),
    ]  # fmt: skip
    m = summarize(events)
    assert m.cases == 3 and m.covered == 2
    assert m.coverage_rate == 1.0  # 2 cobertos ÷ 2 casos que pediram replanejamento
    assert m.median_minutes_to_cover == 15.0
    assert m.overtime_hours_added == Decimal("1.50")
    assert m.atestado_reads == 2  # a leitura com erro não conta como leitura
    assert m.cost_usd_total == Decimal("0.0010")
    assert m.latency_ms_p50 == 900 and m.latency_ms_max == 5000
    assert m.new_violations_total == 0


def test_summarize_on_a_real_flow():
    env = build_env()
    view = env.tracker.report(employee_id="A", day=date(2027, 1, 13), kind="falta")
    view = env.tracker.respond_offer(offer_id=view.offers[0].offer_id, employee_id="C", accept=True)
    env.clock.advance(timedelta(minutes=12))
    env.tracker.on_decision(case_id=view.case_id, code="COBERTURA", option_index=0, approver_id="g", role=Role.GESTOR)
    m = summarize(env.sink.events)
    assert (m.cases, m.covered, m.coverage_rate, m.median_minutes_to_cover) == (1, 1, 1.0, 12.0)
    assert m.new_violations_total == 0 and m.cost_usd_total is None
