"""Rotas do painel do gestor: regras em vigor (FT-01), simulação de vigência (FT-07) e impacto medido (FT-05).

Todas exigem o papel `gestor` e têm linha na matriz de `tests/api/test_access.py`. Nenhuma muda escala: a simulação
calcula e recomenda; quem decide é o gestor.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool

from escalista.api.deps import require_role
from escalista.api.insights import Impact, RulesView, impact, rules_view
from escalista.api.simulation import VigenciaSimulation, VigenciaSimulator
from escalista.api.wiring import DEFAULT_DEMO_FILES_DIR, DEFAULT_RULES_DIR, DEMO_WEEK_START
from escalista.audit.sink import SqlTraceSink
from escalista.config import Settings
from escalista.domain.contracts import Role
from escalista.ingest.demo_network import load_demo_network
from escalista.rules.loader import load_rule_card

router = APIRouter(prefix="/api", dependencies=[Depends(require_role(Role.GESTOR))])


def install_insights(app: FastAPI, settings: Settings) -> None:
    """Liga as rotas e monta o simulador sobre a mesma entrada do solver da fatia (quadro e demanda de `data/demo`)."""
    stores, employees, demand = load_demo_network(Path(DEFAULT_DEMO_FILES_DIR))
    sink = SqlTraceSink(app.state.engine, known_secrets=[key for _, key in settings.featherless_keys])
    app.state.simulator = VigenciaSimulator(
        Path(DEFAULT_RULES_DIR), stores, employees, demand, DEMO_WEEK_START, sink=sink
    )
    app.include_router(router)


# --- dependências (os testes trocam por `app.dependency_overrides`) ---


def get_simulator(request: Request) -> VigenciaSimulator:
    return request.app.state.simulator


@router.get("/rules", response_model=RulesView)
def rules() -> RulesView:
    """O cartão em vigor na semana da demo, por camada, como o motor o monta (carregador + fusão)."""
    return rules_view(load_rule_card(Path(DEFAULT_RULES_DIR), DEMO_WEEK_START))


@router.post("/simulate/vigencia", response_model=VigenciaSimulation)
async def simulate_vigencia(sim: VigenciaSimulator = Depends(get_simulator)) -> VigenciaSimulation:  # noqa: B008
    """Resolve a mesma semana sob 44 h (antes da EC 141) e 42 h (atual). A primeira vez leva o tempo de dois solves."""
    return await run_in_threadpool(sim.run)


@router.get("/impact", response_model=Impact)
def get_impact(request: Request) -> Impact:
    return impact(request.app.state.engine)
