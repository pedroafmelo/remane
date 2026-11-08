"""Ligação da API ao agente da fatia (plano da C5, seção 4: C2 e C4).

`SliceAgent` é o que as rotas de `routes_runs.py` consomem. A frente B o implementa na I1 (agente LangGraph); até a
C4, `build_agent` devolve o `FakeSliceAgent` (respostas fixas, dados sintéticos). A API só fala com o agente por aqui:
não importa `escalista.agents` antes da C4.

Divisão de responsabilidades:
- A API cuida do transporte: sessão e papel (`require_role`), tamanho do arquivo (413) e UTF-8 (cartão RX-13). O agente
  recebe só arquivos com até `MAX_UPLOAD_BYTES` e decodificáveis em UTF-8.
- A API monta o `Approval` (o ato humano) com o id e o papel da sessão; o agente o grava e só então chama `publicar`,
  que confere a aprovação **no código** e recusa sem ela (`PublishRefusedError` vira 403).
- Nada que o agente devolve à API carrega `sex` (RN-13): pessoas saem só como `EmployeePublic`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from fastapi import Request

from escalista.config import Settings
from escalista.domain.contracts import ExceptionCard, TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.schedule import EmployeePublic, Schedule

log = logging.getLogger("escalista")

MAX_UPLOAD_BYTES = 1024 * 1024  # 1 MB (MiB): acima disso, 413
DEFAULT_DEMO_FILES_DIR = "data/demo"
BRT = timezone(timedelta(hours=-3), "BRT")  # sem horário de verão desde 2019


@runtime_checkable
class SliceAgent(Protocol):
    """O agente da fatia (otimização: ler, confirmar, otimizar, verificar, comparar, justificar, publicar).

    Todo `run_id` desconhecido levanta `RunNotFoundError`, exceto em `get_run`, `get_schedule`, `employees` e `trace`,
    que devolvem `None` ou lista vazia. Uma chamada fora da fase esperada levanta `RunPhaseError`.
    """

    def start_run(self, file_name: str, content: bytes) -> RunState:
        """Cria a execução, valida o CSV e devolve o resumo da leitura (RF-04, RF-23).

        `content` já vem com até `MAX_UPLOAD_BYTES` e decodificável em UTF-8 (a API garante). Devolve a fase
        `awaiting_confirm` com `summary.ok`, ou `failed` com o cartão RX-13 (e `summary.issues` com a linha de
        cada erro).
        """
        ...

    def confirm(self, run_id: str) -> RunState:
        """O gerente confirmou o resumo: otimiza, verifica, compara e justifica. Fase `awaiting_approval` (com
        `comparison`, `report`, `justification` e `version_id`) ou `failed` com o cartão (RX-02, RX-12).
        Exige a fase `awaiting_confirm`."""
        ...

    def get_run(self, run_id: str) -> RunState | None: ...

    def get_schedule(self, run_id: str) -> Schedule | None:
        """A grade proposta (otimizada) da execução; `None` antes de otimizar."""
        ...

    def employees(self, run_id: str) -> list[EmployeePublic]:
        """As pessoas da escala da execução, sem `sex` (RN-13), para a grade mostrar nomes."""
        ...

    def approve(self, run_id: str, approval: Approval) -> RunState:
        """Grava a aprovação humana e publica a versão. Fase `published`.

        Exige a fase `awaiting_approval`. Se `publicar` recusar (sem aprovação gravada, versão ou papel errado),
        levanta `PublishRefusedError` e registra `schedule.publish_refused` no rastro."""
        ...

    def published(self) -> ScheduleVersion | None:
        """A última versão publicada, ou `None`."""
        ...

    def trace(self, run_id: str) -> list[TraceEvent]:
        """Os eventos do rastro da execução, em ordem; cada um com `cost_usd` (0 nos passos sem modelo)."""
        ...


class SliceAgentError(Exception):
    """Base dos erros que o agente devolve à API."""


class RunNotFoundError(SliceAgentError):
    """`run_id` desconhecido. A API responde 404."""


class RunPhaseError(SliceAgentError):
    """A execução não está na fase que a operação exige. A API responde 409."""


class PublishRefusedError(SliceAgentError):
    """`publicar` recusou (RH-01). A API responde 403 com o motivo e, se houver, o cartão."""

    def __init__(self, reason: str, card: ExceptionCard | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.card = card


def build_agent(settings: Settings) -> SliceAgent:
    """Escolhe o agente. Até a C4, sempre o falso (o agente real entra com o `wiring` da C4)."""
    from escalista.api.fake_agent import FakeSliceAgent

    log.warning("agente da fatia: FakeSliceAgent (respostas fixas, dados sintéticos); o agente real entra na C4")
    return FakeSliceAgent()


def now_brt() -> datetime:
    """Agora no horário de Brasília, sem fuso (os contratos usam datas sem fuso)."""
    return datetime.now(BRT).replace(tzinfo=None)


# --- dependências FastAPI (os testes trocam por `app.dependency_overrides`) ---


def get_agent(request: Request) -> SliceAgent:
    return request.app.state.agent


def get_demo_files_dir(request: Request) -> Path:
    return Path(request.app.state.demo_files_dir)
