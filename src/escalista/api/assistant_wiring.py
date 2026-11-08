"""Ligação do assistente do gestor (C7b N2): `AssistantData` sobre um banco aberto **somente leitura**.

`readonly_engine(url)`: um engine à parte para o mesmo banco, em que toda conexão nasce sem permissão de escrita
(SQLite: `PRAGMA query_only=ON`; Postgres: `default_transaction_read_only`). Qualquer `INSERT`, `UPDATE` ou `DELETE`
por ele falha no próprio banco, então nem um erro de código no assistente consegue escrever. Limite conhecido: SQLite
em memória (`sqlite://`, só nos testes) não tem como abrir uma segunda conexão ao mesmo banco; nesse caso o assistente
lê pelo engine do app, e a defesa fica só na porta (que não tem método de escrita).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url

from escalista.domain.ports import Clock
from escalista.domain.results import ScheduleVersion
from escalista.domain.rules import Rule
from escalista.domain.tracking import Case


def readonly_engine(database_url: str) -> Engine | None:
    """Engine somente leitura para `database_url`; `None` para SQLite em memória (ver o docstring do módulo)."""
    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend == "sqlite":
        if not url.database or url.database == ":memory:":
            return None
        engine = create_engine(url)

        @event.listens_for(engine, "connect")
        def _query_only(dbapi_connection, _record) -> None:  # pragma: no cover - chamado pelo driver
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA query_only=ON")
            cursor.close()

        return engine
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def _read_only(dbapi_connection, _record) -> None:  # pragma: no cover - só com Postgres
        cursor = dbapi_connection.cursor()
        cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
        cursor.close()

    return engine


class ReadOnlyAssistantData:
    """Satisfaz `AssistantData` lendo do engine somente leitura. Pessoas só pelo nome; casos sem CID."""

    def __init__(self, engine: Engine, clock: Clock, data_dir: Path = Path("data/demo")) -> None:
        from escalista.api.tracker_wiring import load_scenario, make_world_for
        from escalista.rules.tracking_policy import load_track_policy
        from escalista.store.sql_repository import SqlRepository

        self._engine = engine
        self._clock = clock
        self._data_dir = Path(data_dir)
        self._repo = SqlRepository(engine)
        self._world = make_world_for(repo=self._repo, scenario=load_scenario(data_dir), data_dir=data_dir)
        self._policy = load_track_policy()

    def published(self) -> ScheduleVersion | None:
        return self._repo.latest_published()

    def people(self) -> dict[str, str]:
        version = self.published()
        return {e.id: e.name for e in self._world(version).employees} if version else {}

    def store_names(self) -> dict[str, str]:
        version = self.published()
        return dict(self._world(version).store_names) if version else {}

    def open_exceptions(self) -> list[tuple[str, str]]:
        from escalista.store.exceptions import ExceptionStore

        return [(i.card.code, i.card.title) for i in ExceptionStore(self._engine).list() if i.status == "open"]

    def overtime(self) -> list[tuple[str, int]]:
        from escalista.agents.tracker.sweep import overtime_minutes, week_of
        from escalista.synth.ponto import SimulatedPunchSource, load_deviations

        version = self.published()
        if version is None:
            return []
        now: datetime = self._clock.now()
        deviations = load_deviations(self._data_dir / "acompanhamento" / "ponto_desvios.json")
        punches = SimulatedPunchSource(lambda: version.schedule, deviations).punches(until=now)
        monday = week_of(now.date())
        people = {s.employee_id for s in version.schedule.shifts}
        rows = [(e, overtime_minutes(version.schedule, punches, e, monday, now)) for e in sorted(people)]
        return [(e, m) for e, m in rows if m > 0]

    def overtime_limit_h(self) -> str:
        return f"{self._policy.overtime_weekly_limit_h.normalize():f}"

    def rules(self) -> list[Rule]:
        version = self.published()
        return list(self._world(version).card.rules) if version else []

    def last_case(self) -> tuple[Case, list[str]] | None:
        from escalista.audit.sink import SqlTraceSink
        from escalista.store.tracking import SqlTrackRepository

        cases = SqlTrackRepository(self._engine).list_cases()
        if not cases:
            return None
        case = max(cases, key=lambda c: (c.created_at, c.id))
        kinds = [e.kind for e in SqlTraceSink(self._engine).list_events(case.run_id)]
        return case, kinds


def build_assistant(*, engine: Engine, database_url: str, clock: Clock, llm, known_secrets=()):  # noqa: ANN001, ANN201
    """O `Assistant` com o escolhedor do modelo, a leitura somente leitura e o rastro no banco do app."""
    from uuid import uuid4

    from escalista.agents.assistant.assistant import Assistant
    from escalista.agents.optimizer.tools import Tracer
    from escalista.audit.sink import SqlTraceSink
    from escalista.ingest.assistant import make_chooser

    reader = readonly_engine(database_url) or engine
    sink = SqlTraceSink(engine, known_secrets=list(known_secrets))
    tracer = Tracer(sink, clock, new_id=lambda: uuid4().hex, list_events=sink.list_events)
    return Assistant(data=ReadOnlyAssistantData(reader, clock), chooser=make_chooser(llm), tracer=tracer, clock=clock)
