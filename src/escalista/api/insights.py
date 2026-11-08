"""Leituras do painel (FT-01 e FT-05): o cartão de regras em português e o impacto medido nas execuções gravadas.

Nada aqui estima: `impact` lê o que o agente gravou (`run_state`, `schedule_version`, `trace_event`). A comparação
antes e depois de cada execução é a da própria execução (`compare_schedules`, a mesma função de custo nas duas
escalas); custo e latência do agente são a soma do que está no rastro.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from escalista.api.simulation import LIMIT_TEXT, SIM_RUN_ID
from escalista.audit.tables import TraceEventRow
from escalista.domain.results import RunState
from escalista.domain.rules import Rule, RuleCard, RuleLayer
from escalista.store.tables import RunStateRow, ScheduleVersionRow

LAYER_TITLES = {
    RuleLayer.LEI: "Lei · EC 141/CLT",
    RuleLayer.CONVENCAO: "Convenção fictícia",
    RuleLayer.POLITICA: "Política fictícia",
}
TEXT_FIELDS = ("descricao", "regra", "texto")  # o que uma regra `info` diz, na ordem em que o YAML costuma trazer

# --- regras -------------------------------------------------------------------------------------------------------


class RuleView(BaseModel):
    id: str
    title: str
    limit: str
    status: str
    source: str
    engine: bool  # o solver e o verificador leem esta regra; `False` = só informativa
    escalates: bool  # exceção que o agente não decide sozinho (acao: escalar ou verificar_convencao)
    provisional: bool
    note: str | None = None


class RuleGroup(BaseModel):
    layer: RuleLayer
    title: str
    rules: list[RuleView]


class RulesView(BaseModel):
    reference_date: date
    groups: list[RuleGroup]


def rules_view(card: RuleCard) -> RulesView:
    groups = []
    for layer in LAYER_TITLES:  # a camada `execucao` (C6) nasce do pedido de cada execução, não do cartão em vigor
        rules = [_rule_view(r, card) for r in card.rules if r.layer is layer]
        rules.sort(key=lambda r: not r.engine)  # as que o motor usa primeiro; estável no resto
        groups.append(RuleGroup(layer=layer, title=LAYER_TITLES[layer], rules=rules))
    return RulesView(reference_date=card.reference_date, groups=groups)


def _rule_view(rule: Rule, card: RuleCard) -> RuleView:
    engine = rule.kind in LIMIT_TEXT
    if engine:
        limit = LIMIT_TEXT[rule.kind](rule.params)
    else:
        limit = next((str(rule.params[f]).strip() for f in TEXT_FIELDS if rule.params.get(f)), "") or (rule.note or "")
    return RuleView(
        id=rule.id,
        title=rule.id.replace("_", " ").capitalize(),
        limit=limit,
        status=rule.status.value,
        source=rule.source,
        engine=engine,
        escalates=rule.action is not None,
        provisional=rule.id in card.provisional,
        note=rule.note if engine else None,
    )


# --- impacto ------------------------------------------------------------------------------------------------------


class RunImpact(BaseModel):
    run_id: str
    phase: str
    started_at: datetime | None  # primeiro evento do rastro
    published_at: datetime | None
    cost_before: Decimal | None = None
    cost_after: Decimal | None = None
    savings: Decimal | None = None
    overtime_hours_avoided: Decimal | None = None
    violations_avoided: int | None = None
    coverage_after: float | None = None
    agent_cost_usd: Decimal  # soma de `cost_usd` no rastro da execução
    agent_latency_ms: int  # soma de `latency_ms` no rastro da execução
    events: int


class Impact(BaseModel):
    current: RunImpact | None  # a última versão publicada (a escala em vigor na semana da demo)
    runs_total: int
    runs_published: int
    agent_cost_usd_total: Decimal
    agent_latency_ms_avg: int | None  # por execução com rastro
    runs: list[RunImpact]  # as últimas, da mais nova para a mais velha
    provenance: dict[str, str]


PROVENANCE = {
    "comparison": "Custo, horas extras, violações e cobertura: calculados pela mesma função de custo nas duas escalas"
    " (a enviada e a otimizada) e pelo verificador independente, na execução da versão publicada em vigor.",
    "agent": "Custo e latência do agente: soma do que foi medido no rastro de cada execução (custo dos modelos;"
    " passos sem modelo contam zero).",
    "scope": "A demo tem uma semana (11 a 17/01/2027): cada publicação substitui a anterior. Por isso os números da"
    " escala são da versão em vigor, e não a soma das publicações.",
}


def impact(engine: Engine, limit: int = 10) -> Impact:
    with Session(engine) as session:
        runs = {row.run_id: RunState.model_validate(row.data) for row in session.scalars(select(RunStateRow))}
        published = {
            row.run_id: (row.publish_seq, row.published_at)
            for row in session.scalars(select(ScheduleVersionRow).where(ScheduleVersionRow.publish_seq.is_not(None)))
        }
        trace = {
            run_id: (cost or Decimal(0), int(latency or 0), count, first_seq, first_at)
            for run_id, cost, latency, count, first_seq, first_at in session.execute(
                select(
                    TraceEventRow.run_id,
                    func.sum(TraceEventRow.cost_usd),
                    func.sum(TraceEventRow.latency_ms),
                    func.count(),
                    func.min(TraceEventRow.seq),
                    func.min(TraceEventRow.at),
                )
                .where(TraceEventRow.run_id != SIM_RUN_ID)
                .group_by(TraceEventRow.run_id)
            )
        }

    rows = [_run_impact(state, trace.get(run_id), published.get(run_id)) for run_id, state in runs.items()]
    order = {run_id: (trace.get(run_id) or (0, 0, 0, 0, None))[3] for run_id in runs}
    rows.sort(key=lambda r: order[r.run_id], reverse=True)
    current_id = max(published, key=lambda run_id: published[run_id][0]) if published else None
    current = next((r for r in rows if r.run_id == current_id and r.savings is not None), None)
    traced = [r for r in rows if r.events]
    return Impact(
        current=current,
        runs_total=len(rows),
        runs_published=sum(r.phase == "published" for r in rows),
        agent_cost_usd_total=sum((r.agent_cost_usd for r in rows), Decimal(0)),
        agent_latency_ms_avg=round(sum(r.agent_latency_ms for r in traced) / len(traced)) if traced else None,
        runs=rows[:limit],
        provenance=PROVENANCE,
    )


def _run_impact(state: RunState, trace, published) -> RunImpact:  # noqa: ANN001
    cost, latency, count, _, first_at = trace or (Decimal(0), 0, 0, 0, None)
    row = RunImpact(
        run_id=state.run_id,
        phase=state.phase,
        started_at=first_at,
        published_at=published[1] if published else None,
        agent_cost_usd=cost,
        agent_latency_ms=latency,
        events=count,
    )
    c = state.comparison
    if c is None:
        return row
    return row.model_copy(
        update={
            "cost_before": c.before.total_cost,
            "cost_after": c.after.total_cost,
            "savings": c.savings,
            "overtime_hours_avoided": c.overtime_hours_avoided,
            "violations_avoided": c.violations_avoided,
            "coverage_after": c.after.coverage_pct,
        }
    )
