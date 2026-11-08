"""Mundo pequeno e sintético do acompanhamento: a rede do teste da cobertura, publicada num `InMemoryRepository`, com
relógio, canal, fila e casos falsos (tests/fakes.py)."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from escalista.agents.optimizer.tools import Tracer
from escalista.agents.tracker.flow import Tracker, World
from escalista.domain.results import ScheduleVersion
from escalista.domain.schedule import Employee, Schedule
from escalista.domain.tracking import TrackPolicy
from escalista.verifier import verify
from tests.agents.support import rule_card
from tests.agents.test_cover import EMPLOYEES, SCHEDULE
from tests.fakes import (
    FakeChannel,
    FakeClock,
    InMemoryRepository,
    InMemoryTrackRepository,
    ListExceptionQueue,
    ListTraceSink,
)

NOW = datetime(2027, 1, 13, 13, 55)  # qua da semana da demo (tempo simulado)
STORES = {"L1": "Loja Sintética 1", "L2": "Loja Sintética 2"}
POLICY = TrackPolicy(
    late_tolerance_min=10,
    answer_deadline_min=15,
    offer_deadline_min=20,
    max_candidates=3,
    overtime_weekly_limit_h=Decimal(6),
    overtime_warn_pct=80,
)


def _raw(code: str, titulo: str, rotulos: list[str]) -> dict[str, Any]:
    return {
        "code": code,
        "titulo": titulo,
        "motivo": f"motivo {code}",
        "decisor": "gestor",
        "prazo_min": 30,
        "opcoes": [{"rotulo": r, "efeito": f"efeito {r}"} for r in rotulos],
        "recomendacao": "recomendação",
        "sem_resposta": "sem resposta",
        "fonte": "Política fictícia (teste)",
    }


POLICY_CARDS = {
    "RX-05": _raw("RX-05", "Falta sem substituto", ["Hora extra", "Remanejar", "Deixar o turno descoberto"]),
    "RX-06": _raw("RX-06", "Ninguém aceitou", ["Hora extra", "Remanejar", "Deixar o turno descoberto"]),
    "RX-08": _raw("RX-08", "Atestado inconsistente", ["Manter provisório", "Pedir nova foto ou PDF"]),
    "RX-09": _raw("RX-09", "Sem resposta", ["Tratar como falta", "Aguardar mais 15 min", "Registrar atraso"]),
}


@dataclass
class Env:
    tracker: Tracker
    repo: InMemoryRepository
    cases: InMemoryTrackRepository
    queue: ListExceptionQueue
    channel: FakeChannel
    sink: ListTraceSink
    clock: FakeClock
    version: ScheduleVersion

    def kinds(self, run_id: str | None = None) -> list[str]:
        return [e.kind for e in self.sink.events if run_id is None or e.run_id == run_id]

    def events(self, kind: str) -> list:
        return [e for e in self.sink.events if e.kind == kind]


def build_env(*, employees: list[Employee] = EMPLOYEES, schedule: Schedule = SCHEDULE, **kwargs: Any) -> Env:
    repo = InMemoryRepository()
    card = rule_card()
    version = ScheduleVersion(
        id="ver-base",
        run_id="run-base",
        schedule=schedule,
        status="draft",
        input_hash="h",
        seed=42,
        violations_total=verify(schedule, card).total,
        created_at=NOW,
    )
    repo.save_version(version)
    repo.mark_published(version.id, NOW)
    clock = FakeClock(NOW)
    sink = ListTraceSink()
    counter = itertools.count(1)
    new_id = lambda: f"id{next(counter):04d}"  # noqa: E731
    tracer = Tracer(
        sink, clock, new_id=new_id, list_events=lambda run_id: [e for e in sink.events if e.run_id == run_id]
    )
    cases, queue, channel = InMemoryTrackRepository(), ListExceptionQueue(), FakeChannel()
    world = World(employees=list(employees), store_names=dict(STORES), card=card)
    tracker = Tracker(
        repo=repo,
        cases=cases,
        queue=queue,
        channel=channel,
        tracer=tracer,
        clock=clock,
        world=lambda _version: world,
        new_id=new_id,
        **{"policy": POLICY, "policy_cards": POLICY_CARDS, **kwargs},
    )
    return Env(tracker, repo, cases, queue, channel, sink, clock, repo.get_version(version.id))


@pytest.fixture
def env() -> Env:
    return build_env()
