"""App FastAPI: `/health` e, quando o build existir, a SPA React no mesmo contêiner (arquitetura.md, seção 2)."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text

from escalista.api.auth import install_auth
from escalista.api.excecoes import ExceptionDesk, build_desk, install_excecoes
from escalista.api.routes_assistant import install_assistant
from escalista.api.routes_insights import install_insights
from escalista.api.routes_runs import install_runs
from escalista.api.routes_tracker import install_tracker
from escalista.api.wiring import DEFAULT_DEMO_FILES_DIR, SliceAgentC6, build_agent
from escalista.clock.demo import DemoClock
from escalista.config import Settings
from escalista.db import init_db, make_engine
from escalista.domain.ports import LLMClient

log = logging.getLogger("escalista")


def create_app(
    settings: Settings | None = None,
    *,
    agent: SliceAgentC6 | None = None,
    desk: ExceptionDesk | None = None,
    tracker_llm: LLMClient | None = None,
    seed_demo: bool = True,
) -> FastAPI:
    """`tracker_llm`: cliente do modelo da leitura do atestado (os testes passam um falso; padrão: Featherless).
    `seed_demo`: na subida, sem escala publicada, publica a semana sintética do acompanhamento (dados pré-carregados
    do link público); os testes que precisam do banco vazio desligam."""
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    import escalista.clock.tables  # noqa: F401 (registra `demo_clock` antes do init_db)
    import escalista.store.tracking  # noqa: F401 (idem: `track_case` e `channel_message`)

    init_db(engine)
    log.info("escalista iniciado: %s", settings.summary())  # só índices e flags, nunca valores de chave

    app = FastAPI(title="Escalista", description="Dados sintéticos", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.engine = engine
    app.state.agent = agent or build_agent(settings, engine=engine)
    app.state.demo_files_dir = DEFAULT_DEMO_FILES_DIR
    # Um relógio de demo só, da fila de exceções e do acompanhamento; o resto do app segue no relógio do sistema.
    app.state.demo_clock = DemoClock(engine)
    app.state.desk = desk or build_desk(settings, engine, clock=app.state.demo_clock)
    _wire_tracker(app, settings, tracker_llm, seed_demo=seed_demo)

    @app.get("/health")
    def health() -> dict:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok", "version": os.environ.get("GIT_SHA", "dev"), **settings.summary()}

    install_auth(app, settings)  # antes da SPA: o fallback `/{path}` não pode engolir `/api/me`
    install_runs(app)
    install_excecoes(app)
    install_tracker(app)
    install_assistant(app)
    install_insights(app, settings)
    _serve_spa(app, Path(settings.web_dist_dir))
    return app


def _wire_tracker(app: FastAPI, settings: Settings, llm: LLMClient | None, *, seed_demo: bool) -> None:
    """Liga o acompanhamento (C7) com o relógio de demo e o mesmo cliente Featherless do agente (sem chave, o cliente
    sobe e só levanta RX-12 ao ser chamado; o `Tracker` trata como leitura indisponível)."""
    from escalista.api.tracker_wiring import build_tracker, load_scenario, make_world_for
    from escalista.audit.sink import SqlTraceSink
    from escalista.store.sql_repository import SqlRepository
    from escalista.store.tracking import SqlTrackRepository

    engine, clock = app.state.engine, app.state.demo_clock
    secrets = [key for _, key in settings.featherless_keys]
    if llm is None:
        from escalista.llm.client import FeatherlessClient

        sink = SqlTraceSink(engine, known_secrets=secrets)
        llm = FeatherlessClient.from_settings(settings, trace_sink=sink, clock=clock)
    tracker = build_tracker(engine=engine, clock=clock, llm=llm, known_secrets=secrets, seed=seed_demo)
    cases = SqlTrackRepository(engine)
    app.state.tracker = tracker
    app.state.track_cases = cases
    world = make_world_for(repo=SqlRepository(engine), scenario=load_scenario())
    app.state.desk.attach_tracker(tracker, cases=cases, world=world)
    from escalista.api.assistant_wiring import build_assistant

    app.state.assistant = build_assistant(
        engine=engine, database_url=settings.database_url, clock=clock, llm=llm, known_secrets=secrets
    )


def _serve_spa(app: FastAPI, dist: Path) -> None:
    """Serve o build do React: arquivos do `dist` e, nas demais rotas fora de `/api`, o `index.html` (rotas da SPA)."""
    index = dist / "index.html"
    if not index.is_file():
        return
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if candidate.is_dir():  # export estático do Next: /rota/ é a pasta rota/ com o próprio index.html
            candidate = candidate / "index.html"
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)
