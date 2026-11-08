"""Solver CP-SAT (plano da C5, frente A, A2; testes 11 a 14).

Os testes conferem a escala com um **verificador mínimo escrito aqui** (`_violations`), e não com o de `verifier/`
(frente D): o RF-02 pede que solver e verificador não errem juntos.
"""

from __future__ import annotations

import math
import time as wallclock
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from escalista.domain.contracts import Role
from escalista.domain.results import SolveRequest, SolveResult
from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Store
from escalista.solver.model import ModelStats, solve

MONDAY = date(2027, 1, 11)
DEMO = Path("data/demo")


def rule(kind: str, layer: RuleLayer = RuleLayer.LEI, **params) -> Rule:
    status = RuleStatus.FICTICIA if layer is not RuleLayer.LEI else RuleStatus.INTERPRETACAO
    return Rule(id=kind, kind=kind, layer=layer, params=params, status=status, source=f"fonte-{kind}")


def card(weekly: float = 42, daily: float = 8, rest_gap: float = 11, rest_days: int = 2) -> RuleCard:
    return RuleCard(
        reference_date=MONDAY,
        rules=[
            rule("jornada_semanal_max", hours=weekly),
            rule("jornada_diaria_max", hours=daily),
            rule("interjornada_min", hours=rest_gap),
            rule("repouso_semanal", days=rest_days),
            rule("adicional_hora_extra", RuleLayer.CONVENCAO, percent=60),
        ],
    )


def emp(id_: str, store: str = "S1", wage: str = "10.00") -> Employee:
    return Employee(
        id=id_, name=id_, store_id=store, job="caixa", hourly_wage=Decimal(wage), contract_hours=42, sex="F"
    )


def demand_block(store: str, day: date, start: time, end: time, required: int) -> list[DemandSlot]:
    out = []
    t = datetime.combine(day, start)
    stop = datetime.combine(day, end)
    while t < stop:
        out.append(DemandSlot(store_id=store, day=day, start=t.time(), required=required))
        t += timedelta(minutes=30)
    return out


def request(stores, employees, demand, rc=None, *, seed=7, workers=1, limit=10.0) -> SolveRequest:
    return SolveRequest(
        card=rc or card(),
        stores=stores,
        employees=employees,
        demand=demand,
        week_start=MONDAY,
        seed=seed,
        time_limit_s=limit,
        num_workers=workers,
    )


# Verificador mínimo do teste (independente do solver e do verificador da frente D) -----------------------------


def _param(rc: RuleCard, kind: str, key: str) -> float:
    return next(float(r.params[key]) for r in rc.rules if r.kind == kind)


def _violations(sched: Schedule, rc: RuleCard, stores: list[Store], employees: list[Employee]) -> list[str]:
    weekly = _param(rc, "jornada_semanal_max", "hours")
    daily = _param(rc, "jornada_diaria_max", "hours")
    gap = _param(rc, "interjornada_min", "hours")
    rest = _param(rc, "repouso_semanal", "days")
    home = {e.id: e.store_id for e in employees}
    hours_of = {s.id: (s.opens, s.closes) for s in stores}
    by_emp: dict[str, list] = defaultdict(list)
    out: list[str] = []
    for sh in sched.shifts:
        by_emp[sh.employee_id].append(sh)
        if home[sh.employee_id] != sh.store_id:
            out.append(f"loja errada {sh.employee_id}")
        opens, closes = hours_of[sh.store_id]
        if sh.start.time() < opens or sh.end > datetime.combine(sh.start.date(), closes):
            out.append(f"fora do horário {sh.employee_id} {sh.start}")
    for eid, shifts in by_emp.items():
        shifts.sort(key=lambda s: s.start)
        days = [s.start.date() for s in shifts]
        if len(set(days)) != len(days):
            out.append(f"dois turnos no dia {eid}")
        dur = [(s.end - s.start).total_seconds() / 3600 for s in shifts]
        if sum(dur) > weekly + 1e-9:
            out.append(f"jornada_semanal_max {eid}")
        out += [f"jornada_diaria_max {eid}" for h in dur if h > daily + 1e-9]
        if 7 - len(set(days)) < rest:
            out.append(f"repouso_semanal {eid}")
        for a, b in zip(shifts, shifts[1:], strict=False):
            if (b.start.date() - a.start.date()).days == 1 and (b.start - a.end).total_seconds() / 3600 < gap - 1e-9:
                out.append(f"interjornada_min {eid} {b.start.date()}")
    return out


def _shortfall(sched: Schedule, demand: list[DemandSlot]) -> dict[tuple, int]:
    out = {}
    for slot in demand:
        start = datetime.combine(slot.day, slot.start)
        end = start + timedelta(minutes=30)
        people = {
            s.employee_id for s in sched.shifts if s.store_id == slot.store_id and s.start <= start and s.end >= end
        }
        if len(people) < slot.required:
            out[(slot.store_id, slot.day, slot.start)] = slot.required - len(people)
    return out


def _check_uncovered_matches(result: SolveResult, demand: list[DemandSlot]) -> None:
    got = {(u.store_id, u.day, u.start): u.required for u in result.uncovered}
    assert got == _shortfall(result.schedule, demand)


# 11 ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rc",
    [
        card(weekly=12, daily=8, rest_gap=11, rest_days=5),  # semanal e repouso apertam
        card(weekly=42, daily=6, rest_gap=14, rest_days=6),  # diária, interjornada e repouso apertam
    ],
    ids=["semanal", "diaria-interjornada"],
)
def test_solver_tiny_instance_respects_four_primitives(rc: RuleCard):
    stores = [Store(id="S1", name="Loja teste", opens=time(6), closes=time(23))]
    employees = [emp("E1", wage="10.00"), emp("E2", wage="11.00"), emp("E3", wage="12.00")]
    demand = demand_block("S1", MONDAY, time(6), time(23), 2) + demand_block(
        "S1", MONDAY + timedelta(days=1), time(6), time(23), 2
    )

    result = solve(request(stores, employees, demand, rc))

    assert result.status == "optimal"
    assert result.schedule is not None and result.schedule.week_start == MONDAY
    assert result.schedule.shifts, "a demanda pede gente: a escala não pode vir vazia"
    assert _violations(result.schedule, rc, stores, employees) == []
    _check_uncovered_matches(result, demand)


def test_solver_covers_everything_when_capacity_allows_and_prefers_cheaper():
    stores = [Store(id="S1", name="Loja teste", opens=time(8), closes=time(22))]
    employees = [emp("E1", wage="10.00"), emp("E2", wage="20.00")]
    demand = demand_block("S1", MONDAY, time(9), time(13), 1)

    result = solve(request(stores, employees, demand))

    assert result.status == "optimal"
    assert result.uncovered == [] and result.exception is None
    assert [(s.employee_id, s.start.time(), s.end.time()) for s in result.schedule.shifts] == [
        ("E1", time(9), time(13))
    ]


# 12 ------------------------------------------------------------------------------------------------------------


def test_solver_stable_hash_for_same_input_and_seed():
    stores = [Store(id="S1", name="Loja teste", opens=time(8), closes=time(22))]
    employees = [emp("E1"), emp("E2", wage="11.00"), emp("E3", wage="12.00")]
    demand = demand_block("S1", MONDAY, time(8), time(20), 2) + demand_block(
        "S1", MONDAY + timedelta(days=2), time(10), time(22), 1
    )

    a = solve(request(stores, employees, demand, seed=3))
    b = solve(request(stores, list(reversed(employees)), list(reversed(demand)), seed=3, limit=5.0, workers=1))
    c = solve(request(stores, employees, demand, seed=4))

    assert len(a.input_hash) == 64
    assert a.input_hash == b.input_hash  # mesma entrada (a ordem das listas não muda a entrada) e mesma seed
    assert a.seed == b.seed == 3
    assert a.schedule == b.schedule  # 1 thread: a mesma escala
    assert c.input_hash != a.input_hash  # a seed faz parte da entrada


# 13 ------------------------------------------------------------------------------------------------------------


def test_demand_above_capacity_returns_rx02_with_hiring_math():
    # 2 pessoas; demanda de 3 pessoas das 08h às 16h, 7 dias = 168 pessoa-horas.
    # Capacidade: 2 × mín(42, 5 dias × 8h) = 80 → faltam 88 pessoa-horas → 88 ÷ 40 = 2,2 → contratar 3.
    stores = [Store(id="S1", name="Loja teste", opens=time(8), closes=time(22))]
    employees = [emp("E1"), emp("E2")]
    demand = [s for d in range(7) for s in demand_block("S1", MONDAY + timedelta(days=d), time(8), time(16), 3)]

    result = solve(request(stores, employees, demand))

    assert result.status == "optimal"
    assert result.schedule is not None and len(result.schedule.shifts) == 10  # a escala parcial continua
    assert _violations(result.schedule, card(), stores, employees) == []
    _check_uncovered_matches(result, demand)
    assert sum(u.required for u in result.uncovered) * 0.5 == 88

    exc = result.exception
    assert exc is not None and exc.code == "RX-02"
    assert exc.decider == Role.GESTOR
    evidence = " | ".join(exc.evidence)
    assert "S1" in evidence
    assert "88,0 pessoa-horas" in evidence
    assert "40,0 h" in evidence
    assert "contratar 3" in evidence
    assert exc.options and exc.recommendation and exc.if_no_answer
    assert math.ceil(88 / 40) == 3


# 14 ------------------------------------------------------------------------------------------------------------

TIME_LIMIT_S = 30.0


@pytest.mark.slow
def test_solver_60x7_within_time_limit():
    stores = TypeAdapter(list[Store]).validate_json((DEMO / "lojas.json").read_bytes())
    employees = TypeAdapter(list[Employee]).validate_json((DEMO / "pessoas.json").read_bytes())
    demand = TypeAdapter(list[DemandSlot]).validate_json((DEMO / "demanda.json").read_bytes())
    rc = card()

    stats = ModelStats()
    t0 = wallclock.perf_counter()
    result = solve(request(stores, employees, demand, rc, seed=42, workers=8, limit=TIME_LIMIT_S), stats)
    elapsed = wallclock.perf_counter() - t0

    assert result.status in ("optimal", "feasible")
    # O que se prova: o CP-SAT respeita o limite configurado (tempo que ele mesmo reporta, sem montar o modelo).
    # As lojas dividem o limite, então a soma por loja fica em TIME_LIMIT_S mais uma folga pequena.
    assert stats.solver_wall_s and sum(stats.solver_wall_s.values()) <= TIME_LIMIT_S + 2
    # Tempo de parede total só como rede contra travamento: não depende de a máquina estar ociosa.
    assert elapsed <= 3 * TIME_LIMIT_S
    assert result.schedule is not None and len({s.employee_id for s in result.schedule.shifts}) > 0
    assert _violations(result.schedule, rc, stores, employees) == []
    _check_uncovered_matches(result, demand)


def test_solver_accepts_hint_and_keeps_the_rules():
    stores = [Store(id="S1", name="Loja teste", opens=time(8), closes=time(22))]
    employees = [emp("E1"), emp("E2", wage="11.00")]
    demand = demand_block("S1", MONDAY, time(8), time(20), 1)
    first = solve(request(stores, employees, demand))

    hinted = solve(request(stores, employees, demand).model_copy(update={"hint": first.schedule}))

    assert hinted.status == "optimal"
    assert hinted.input_hash == first.input_hash  # o hint não muda a entrada que define a escala
    assert _violations(hinted.schedule, card(), stores, employees) == []
    _check_uncovered_matches(hinted, demand)
