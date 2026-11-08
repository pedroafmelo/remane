"""Métricas do acompanhamento, derivadas só do rastro (SAIDA-AC-12).

Tempos em minutos **simulados** (relógio de demo). Custo e latência vêm só dos eventos `track.llm.read_atestado`
(a única chamada de modelo do T1); sem nenhum custo medido, o total é `None`, nunca 0 inventado.
"""

from __future__ import annotations

from decimal import Decimal
from statistics import median, median_low

from escalista.domain.contracts import TraceEvent
from escalista.domain.tracking import TrackMetrics

READ_KIND = "track.llm.read_atestado"
SWEEP_RUN = "track-sweep"


def summarize(events: list[TraceEvent]) -> TrackMetrics:
    """`cases`: execuções `track-<case_id>`; `coverage_rate`: cobertos ÷ casos que pediram replanejamento."""
    case_runs = {e.run_id for e in events if e.run_id.startswith("track-") and e.run_id != SWEEP_RUN}
    replanned = {e.run_id for e in events if e.kind == "track.replan.requested"}
    closed = [e.payload for e in events if e.kind == "track.case.closed"]
    covered = [p for p in closed if p.get("outcome") == "coberta"]
    reads = [e for e in events if e.kind == READ_KIND and not e.payload.get("error")]
    costs = [e.cost_usd for e in events if e.kind == READ_KIND and e.cost_usd is not None]
    latencies = [e.latency_ms for e in events if e.kind == READ_KIND and e.latency_ms is not None]
    minutes = [p["minutes_to_close"] for p in covered if p.get("minutes_to_close") is not None]
    return TrackMetrics(
        cases=len(case_runs),
        covered=len(covered),
        coverage_rate=len(covered) / len(replanned) if replanned else None,
        median_minutes_to_cover=float(median(minutes)) if minutes else None,
        new_violations_total=sum(int(p.get("new_violations", 0)) for p in closed),
        overtime_hours_added=sum((Decimal(str(p.get("overtime_hours_added", "0"))) for p in covered), Decimal(0)),
        atestado_reads=len(reads),
        cost_usd_total=sum(costs, Decimal(0)) if costs else None,
        latency_ms_p50=int(median_low(latencies)) if latencies else None,
        latency_ms_max=max(latencies) if latencies else None,
    )
