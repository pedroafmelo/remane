"""App FastAPI: `/health` e, quando o build existir, a SPA React no mesmo contêiner (arquitetura.md, seção 2)."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text

from escalista.config import Settings
from escalista.db import init_db, make_engine

log = logging.getLogger("escalista")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    init_db(engine)
    log.info("escalista iniciado: %s", settings.summary())  # só índices e flags, nunca valores de chave

    app = FastAPI(title="Escalista", description="Dados sintéticos", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.engine = engine

    @app.get("/health")
    def health() -> dict:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok", "version": os.environ.get("GIT_SHA", "dev"), **settings.summary()}

    _serve_spa(app, Path(settings.web_dist_dir))
    return app


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
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)
