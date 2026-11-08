"""Simulação de vigência (FT-07, "e se 44h → 42h"): a mesma entrada do solver resolvida sob o regime anterior à
EC 141 e sob o atual, medida pela mesma função de custo e pelo mesmo verificador. O agente calcula e recomenda; o
gestor decide. Nada aqui publica ou muda escala.

Regimes (os dois cartões saem de `data/regras/` pelo carregador, sem valor escrito à mão):
- **42h (atual):** o cartão vigente na semana da demo (EC 141: 42 h por semana, 2 dias de repouso).
- **44h (anterior):** o cartão vigente em 15/12/2026, véspera da etapa de 42h (`jornada_semanal_max` vale 44 h até
  lá). O repouso de 2 dias só vale a partir de 16/12/2026, e o solver não decide sem um repouso: entra o descanso da
  CLT (`descanso_semanal_clt`, art. 67, 24 h consecutivas), lido como 1 dia sem turno na semana. Essa leitura é
  nossa e vai na tela.

Cache em memória por `input_hash` do pedido ao solver (o hash já inclui o cartão, ou seja, o regime).
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from escalista.domain.contracts import ExceptionCard, TraceEvent
from escalista.domain.ports import TraceSink
from escalista.domain.results import ScheduleMetrics, SolveRequest
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Store
from escalista.rules.loader import load_rule_card
from escalista.solver.cost import compute_metrics
from escalista.solver.model import input_hash, solve
from escalista.verifier import verify

PRE_EC_DATE = date(2026, 12, 15)  # véspera da etapa de 42h (ec141.yaml: marcos.etapa_42h, que herda pendência)
CLT_REST_ID = "descanso_semanal_clt"
SIM_RUN_ID = "sim-vigencia"
Regime = Literal["44h", "42h"]


class RegimeResult(BaseModel):
    regime: Regime
    label: str
    reference_date: date
    limits: list[str]  # as primitivas que o motor usou, em português
    status: str
    solve_ms: int  # medido nesta máquina, na primeira vez (o cache não refaz)
    metrics: ScheduleMetrics  # `compute_metrics` com o cartão do próprio regime; violações do verificador
    uncovered_person_hours: float
    violations_under_ec141: int  # a mesma escala conferida contra o cartão atual
    hiring: ExceptionCard | None = None  # RX-02 do solver, com a conta mínima de contratação, se faltar cobertura


class VigenciaSimulation(BaseModel):
    simulated: Literal[True] = True  # vigência simulada, dados sintéticos
    week_start: date
    cached: bool
    before: RegimeResult
    after: RegimeResult
    cost_of_ec141: Decimal  # custo no regime atual − custo no anterior, na mesma semana
    coverage_change_pct: float  # cobertura atual − anterior, em pontos percentuais
    notes: list[str]


def pre_ec_card(rules_dir: Path) -> RuleCard:
    """Cartão de 15/12/2026; sem `repouso_semanal` vigente, o descanso da CLT vira 1 dia (ceil(24 h / 24))."""
    card = load_rule_card(rules_dir, PRE_EC_DATE)
    if any(r.kind == "repouso_semanal" for r in card.rules):
        return card
    rules = []
    for rule in card.rules:
        if rule.id == CLT_REST_ID:
            days = math.ceil(float(rule.params["horas_consecutivas"]) / 24)
            note = f"Leitura do simulador: {rule.params['horas_consecutivas']} h consecutivas = {days} dia sem turno."
            rule = rule.model_copy(update={"kind": "repouso_semanal", "params": {"days": days}, "note": note})
        rules.append(rule)
    return card.model_copy(update={"rules": rules})


LIMIT_TEXT = {
    "jornada_semanal_max": lambda p: f"{_n(p['hours'])} h por semana",
    "jornada_diaria_max": lambda p: f"{_n(p['hours'])} h por dia",
    "interjornada_min": lambda p: f"{_n(p['hours'])} h de descanso entre jornadas",
    "repouso_semanal": lambda p: f"{_n(p['days'])} dia(s) de repouso por semana",
    "adicional_hora_extra": lambda p: f"adicional de {_n(p['percent'])}% na hora extra",
}


def describe_limits(card: RuleCard) -> list[str]:
    """As primitivas que o motor lê, em português, com a origem."""
    return [f"{LIMIT_TEXT[r.kind](r.params)} ({r.source})" for r in card.rules if r.kind in LIMIT_TEXT]


def _n(value: float) -> str:
    return f"{value:g}".replace(".", ",")


class VigenciaSimulator:
    def __init__(
        self,
        rules_dir: Path,
        stores: list[Store],
        employees: list[Employee],
        demand: list[DemandSlot],
        week_start: date,
        *,
        sink: TraceSink | None = None,
        seed: int = 42,  # os mesmos do agente da fatia (agents/optimizer/graph.py)
        time_limit_s: float = 30.0,
        num_workers: int = 1,
    ) -> None:
        self._cards: dict[Regime, RuleCard] = {
            "44h": pre_ec_card(rules_dir),
            "42h": load_rule_card(rules_dir, week_start),
        }
        self._stores, self._employees, self._demand = stores, employees, demand
        self._week_start = week_start
        self._sink = sink
        self._seed, self._time_limit_s, self._num_workers = seed, time_limit_s, num_workers
        # shortcut: cache em memória (some no restart do contêiner); se o primeiro clique pós-deploy doer, gravar em SQL
        self._cache: dict[str, RegimeResult] = {}
        self._lock = threading.Lock()  # dois cliques seguidos esperam a mesma conta em vez de abrir outra

    def _request(self, regime: Regime) -> SolveRequest:
        return SolveRequest(
            card=self._cards[regime],
            stores=self._stores,
            employees=self._employees,
            demand=self._demand,
            week_start=self._week_start,
            seed=self._seed,
            time_limit_s=self._time_limit_s,
            num_workers=self._num_workers,
        )

    def _solve(self, regime: Regime, req: SolveRequest) -> RegimeResult:
        card, current = self._cards[regime], self._cards["42h"]
        result = solve(req)
        if result.schedule is None:
            raise RuntimeError(f"o solver não devolveu escala no regime {regime} (status {result.status})")
        own = verify(result.schedule, card).total
        metrics = compute_metrics(result.schedule, self._employees, self._demand, card, violations=own)
        return RegimeResult(
            regime=regime,
            label="Antes da EC 141 (44 h)" if regime == "44h" else "EC 141 em vigor (42 h)",
            reference_date=card.reference_date,
            limits=describe_limits(card),
            status=result.status,
            solve_ms=result.wall_ms,
            metrics=metrics,
            uncovered_person_hours=sum(u.required for u in result.uncovered) / 2,  # faixas de 30 min
            violations_under_ec141=verify(result.schedule, current).total,
            hiring=result.exception,
        )

    def run(self) -> VigenciaSimulation:
        with self._lock:
            started = time.perf_counter()
            reqs = {regime: self._request(regime) for regime in ("44h", "42h")}
            keys = {regime: input_hash(req) for regime, req in reqs.items()}
            missing = [r for r in reqs if keys[r] not in self._cache]
            with ThreadPoolExecutor(max_workers=2) as pool:  # o CP-SAT solta o GIL: as duas versões rodam juntas
                for regime, res in zip(missing, pool.map(lambda r: self._solve(r, reqs[r]), missing), strict=True):
                    self._cache[keys[regime]] = res
            before, after = self._cache[keys["44h"]], self._cache[keys["42h"]]
            if missing:
                self._trace(before, after, keys, started)
        return VigenciaSimulation(
            week_start=self._week_start,
            cached=not missing,
            before=before,
            after=after,
            cost_of_ec141=after.metrics.total_cost - before.metrics.total_cost,
            coverage_change_pct=round(after.metrics.coverage_pct - before.metrics.coverage_pct, 2),
            notes=_notes(before, after),
        )

    def _trace(self, before: RegimeResult, after: RegimeResult, keys: dict[str, str], started: float) -> None:
        if self._sink is None:
            return
        payload = {
            "cost_basis": "sem modelo de linguagem: só solver, verificador e função de custo",
            "regimes": {
                r.regime: {"input_hash": keys[r.regime], "status": r.status, "solve_ms": r.solve_ms}
                for r in (before, after)
            },
        }
        self._sink.emit(
            TraceEvent(
                id=f"evt-{uuid.uuid4().hex[:12]}",
                run_id=SIM_RUN_ID,
                kind="simulation.vigencia",
                at=datetime.now(),
                rule_ref="jornada_semanal_max",
                cost_usd=Decimal(0),
                latency_ms=round((time.perf_counter() - started) * 1000),
                payload=payload,
            )
        )


def _notes(before: RegimeResult, after: RegimeResult) -> list[str]:
    notes = [
        "Vigência simulada com dados sintéticos: a semana real da demo já está sob a EC 141.",
        "As duas escalas saem do mesmo solver, com o mesmo quadro, a mesma demanda e a mesma semente; custo pela mesma"
        " função de custo, violações pelo mesmo verificador.",
        "O solver não escala hora extra: as horas extras ficam em zero nas duas versões.",
        "O repouso de 1 dia no regime anterior é leitura nossa do descanso de 24 h da CLT (art. 67).",
    ]
    if after.metrics.coverage_pct < before.metrics.coverage_pct:
        notes.append(
            "A cobertura cai no regime atual: a diferença de custo não inclui o que ficou sem gente."
            " A conta de contratação abaixo é um piso (cálculo do próprio solver)."
        )
    return notes
