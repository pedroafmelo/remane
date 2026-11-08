"""Ligação do acompanhamento de escala (C7, tarefa C1; contrato SAIDA-AC-02): o `Tracker` sem HTTP.

`build_tracker` liga o fluxo às bordas: repositório e casos em SQL, fila do gestor, celular simulado, rastro em SQL,
política fictícia, leitura do atestado (`make_reader` com o cliente do modelo recebido) e ponto simulado. Na primeira
subida (sem escala publicada), publica a semana sintética do cenário (`seed_scenario`).

A escala do cenário é **dado sintético pré-carregado**, não um ato humano: é gravada e marcada publicada sem
`Approval` (não se finge aprovação) e o rastro registra `demo.seeded {version_id, synthetic: true}`. Toda mudança
posterior dessa escala passa pelo portão normal (aceite do colega e aprovação do gestor).

As mensagens de entrada do celular (o colaborador avisou, anexou, respondeu) são registradas aqui, na borda, só com
metadados (`has_text`, tipo do anexo); o texto livre nunca chega ao servidor (RN-06).
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, delete, update
from sqlalchemy.orm import Session

from escalista.agents.optimizer.tools import Tracer
from escalista.agents.tracker.flow import Tracker, World
from escalista.agents.tracker.replan import CoverFn
from escalista.domain.ports import Clock, LLMClient, PunchSource, Repository
from escalista.domain.results import ScheduleVersion
from escalista.domain.schedule import Employee, Schedule, Shift, Store
from escalista.domain.tracking import ChannelMessage
from escalista.ingest.atestado import read_atestado

read_atestado_bytes = read_atestado  # SAIDA-AC-05: a leitura do PDF em memória, reexportada para os evals

SCENARIO_RUN = "demo-acompanhamento"  # run_id das versões da escala sintética do acompanhamento (e das republicadas)
SCENARIO_DIR = "acompanhamento"
RULES_DIR = Path("data/regras")


@dataclass(frozen=True)
class Scenario:
    """A semana sintética com folga (`cenario_<nome>.json`): lojas, pessoas e turnos."""

    week_start: date
    stores: list[Store]
    employees: list[Employee]
    shifts: list[Shift]


def load_scenario(data_dir: Path = Path("data/demo"), scenario: str = "folga") -> Scenario:
    raw = json.loads((Path(data_dir) / SCENARIO_DIR / f"cenario_{scenario}.json").read_text(encoding="utf-8"))
    return Scenario(
        week_start=date.fromisoformat(raw["week_start"]),
        stores=[Store.model_validate(s) for s in raw["stores"]],
        employees=[Employee.model_validate(e) for e in raw["employees"]],
        shifts=[Shift.model_validate(s) for s in raw["shifts"]],
    )


@functools.lru_cache(maxsize=16)
def _card_for_week(rules_dir: Path, week_start: date):  # noqa: ANN202 (RuleCard; cache: o fluxo pede o cartão a cada passo)
    from escalista.rules.loader import load_rule_card_for_week

    return load_rule_card_for_week(rules_dir, week_start)


def make_world_for(
    *, repo: Repository, scenario: Scenario, data_dir: Path = Path("data/demo"), rules_dir: Path = RULES_DIR
) -> Callable[[ScheduleVersion], World]:
    """A rede de uma versão publicada. Versão do cenário sintético: as pessoas e lojas do cenário. Senão, a mesma regra
    da fila de exceções (`excecoes.published_world`: o quadro guardado pela C6 ou a rede de `data/demo`). O cartão é
    sempre o da semana da própria escala."""
    from escalista.api.excecoes import published_world
    from escalista.ingest.demo_network import load_demo_network

    scenario_stores = {s.id: s.name for s in scenario.stores}
    demo_stores, demo_employees, _ = load_demo_network(Path(data_dir))
    demo = ({s.id: s.name for s in demo_stores}, list(demo_employees))

    def world_for(version: ScheduleVersion) -> World:
        card = _card_for_week(rules_dir, version.schedule.week_start)
        if version.run_id == SCENARIO_RUN:
            return World(employees=list(scenario.employees), store_names=dict(scenario_stores), card=card)
        stores, employees = published_world(repo, version, demo)
        return World(employees=employees, store_names=stores, card=card)

    return world_for


def _tracer(engine: Engine, clock: Clock, known_secrets: Sequence[str] = ()) -> Tracer:
    from escalista.audit.sink import SqlTraceSink

    sink = SqlTraceSink(engine, known_secrets=list(known_secrets))
    return Tracer(sink, clock, new_id=lambda: uuid4().hex, list_events=sink.list_events)


def _init_tables(engine: Engine) -> None:
    """Registra as tabelas do acompanhamento no `Base` (import) antes do `init_db`."""
    import escalista.audit.tables  # noqa: F401
    import escalista.clock.tables  # noqa: F401
    import escalista.store.exceptions  # noqa: F401
    import escalista.store.sql_repository  # noqa: F401
    import escalista.store.tracking  # noqa: F401
    from escalista.db import init_db

    init_db(engine)


def seed_scenario(
    *,
    engine: Engine,
    clock: Clock,
    data_dir: Path = Path("data/demo"),
    scenario: str = "folga",
    rules_dir: Path = RULES_DIR,
    known_secrets: Sequence[str] = (),
) -> ScheduleVersion:
    """Publica a semana do cenário como uma versão nova (vira a última publicada). Sem `Approval`: é dado sintético
    pré-carregado, não decisão de ninguém; o rastro diz isso (`demo.seeded`, `synthetic: true`)."""
    from escalista.store.sql_repository import SqlRepository
    from escalista.verifier import verify

    _init_tables(engine)
    loaded = load_scenario(data_dir, scenario)
    schedule = Schedule(week_start=loaded.week_start, shifts=loaded.shifts)
    now = clock.now()
    version = ScheduleVersion(
        id=f"ver-demo-{uuid4().hex[:12]}",
        run_id=SCENARIO_RUN,
        schedule=schedule,
        status="draft",
        input_hash=f"cenario-{scenario}",
        seed=42,
        violations_total=verify(schedule, _card_for_week(rules_dir, loaded.week_start)).total,
        created_at=now,
    )
    repo = SqlRepository(engine)
    repo.save_version(version)
    repo.mark_published(version.id, now)
    _tracer(engine, clock, known_secrets).step(
        SCENARIO_RUN, "demo.seeded", payload={"version_id": version.id, "synthetic": True}
    )
    return repo.get_version(version.id) or version


def reset_demo(
    *,
    engine: Engine,
    clock: Clock,
    data_dir: Path = Path("data/demo"),
    scenario: str = "folga",
    known_secrets: Sequence[str] = (),
) -> datetime:
    """ "Reiniciar" da demo: relógio no início, casos e mensagens apagados, cartões do acompanhamento fora da fila e a
    semana do cenário publicada de novo (vira a última publicada). Devolve o instante simulado."""
    from escalista.store.exceptions import ExceptionStore
    from escalista.store.tracking import SqlTrackRepository

    _init_tables(engine)
    now = clock.reset()  # type: ignore[attr-defined] (só o `DemoClock` e o `FakeClock` dos testes reiniciam)
    SqlTrackRepository(engine).reset()
    ExceptionStore(engine).remove_by_source_kind("track")
    seed_scenario(engine=engine, clock=clock, data_dir=data_dir, scenario=scenario, known_secrets=known_secrets)
    return now


def build_tracker(
    *,
    engine: Engine,
    clock: Clock,
    llm: LLMClient,
    scenario: str = "folga",
    data_dir: Path = Path("data/demo"),
    cover_fn: CoverFn | None = None,
    punch_source: PunchSource | None = None,
    known_secrets: Sequence[str] = (),
    seed: bool = True,
) -> Tracker:
    """O `Tracker` ligado às tabelas (SAIDA-AC-02). Sem escala publicada (e com `seed`), publica a do cenário
    sintético."""
    from escalista.agents.cover import find_cover
    from escalista.api.excecoes import load_policy_exceptions
    from escalista.channel.simulated import SimulatedPhone
    from escalista.ingest.atestado import make_reader
    from escalista.ingest.chat import make_interpreter
    from escalista.rules.tracking_policy import load_track_policy
    from escalista.store.exceptions import ExceptionStore
    from escalista.store.sql_repository import SqlRepository
    from escalista.store.track_queue import ExceptionStoreQueue
    from escalista.store.tracking import SqlTrackRepository
    from escalista.synth.ponto import SimulatedPunchSource, load_deviations

    _init_tables(engine)
    repo = SqlRepository(engine)
    if seed and repo.latest_published() is None:
        seed_scenario(engine=engine, clock=clock, data_dir=data_dir, scenario=scenario, known_secrets=known_secrets)

    def published_schedule() -> Schedule | None:
        version = repo.latest_published()
        return version.schedule if version is not None else None

    punches = punch_source or SimulatedPunchSource(
        published_schedule, load_deviations(Path(data_dir) / SCENARIO_DIR / "ponto_desvios.json")
    )
    return Tracker(
        repo=repo,
        cases=SqlTrackRepository(engine),
        queue=ExceptionStoreQueue(ExceptionStore(engine), clock),
        channel=SimulatedPhone(engine),
        tracer=_tracer(engine, clock, known_secrets),
        clock=clock,
        policy=load_track_policy(),
        policy_cards=load_policy_exceptions(),
        world=make_world_for(repo=repo, scenario=load_scenario(data_dir, scenario), data_dir=data_dir),
        reader=make_reader(llm),
        punches=punches,
        cover_fn=cover_fn or find_cover,
        interpreter=make_interpreter(llm),
    )


# --- mensagens de entrada do celular simulado (só metadados; RN-06) ---------------------------------------------------


class InboundLog:
    """Registra o que o colaborador fez no celular (avisou, anexou, respondeu) **antes** de o agente responder, para a
    conversa sair na ordem certa. Se o fluxo recusar o ato, a mensagem é desfeita; o aviso ganha o `case_id` depois."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        from escalista.channel.simulated import SimulatedPhone

        self._engine = engine
        self._clock = clock
        self._phone = SimulatedPhone(engine)

    def record(
        self,
        *,
        party: str,
        template: str,
        case_id: str | None = None,
        has_text: bool = False,
        media_type: str | None = None,
    ) -> str:
        message = ChannelMessage(
            id=f"in-{uuid4().hex}",
            case_id=case_id,
            direction="in",
            party=party,
            template=template,
            body=None,
            has_text=has_text,
            attachment_media_type=media_type,
            at=self._clock.now(),
        )
        self._phone.send(message)
        return message.id

    def link(self, message_id: str, case_id: str) -> None:
        from escalista.store.tracking import ChannelMessageRow

        with Session(self._engine) as session, session.begin():
            session.execute(update(ChannelMessageRow).where(ChannelMessageRow.id == message_id).values(case_id=case_id))

    def drop(self, message_id: str) -> None:
        from escalista.store.tracking import ChannelMessageRow

        with Session(self._engine) as session, session.begin():
            session.execute(delete(ChannelMessageRow).where(ChannelMessageRow.id == message_id))
