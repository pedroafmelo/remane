"""Adaptador fino entre a API e o agente LangGraph (plano da C5, seção 4, C4; plano da C6, seção 14, C1).

`OptimizerAgent` (`agents/optimizer/graph.py`) levanta os erros de `agents/optimizer/errors.py`, de outra hierarquia
(`agents` não importa a borda). Aqui cada erro vira o seu equivalente de `api/wiring.py`, que `routes_runs.install_runs`
traduz em 404, 409 e 403.

C6: o `SliceAgent` ganhou `confirm(run_id, data)`, e o `SliceAgentC6`, `start_next_week()` e `roster()`. O agente da
frente B só os terá na B4a, com essas mesmas assinaturas. Até lá o adaptador encaminha quando o agente tiver o método
(ou o parâmetro) e, quando não tiver, degrada sem quebrar a fatia da C5: `confirm` ignora o corpo (com aviso no log),
`start_next_week` responde 409 e `roster` devolve `None` (a rota responde 404).
"""

from __future__ import annotations

import inspect
import logging
from typing import Any

from escalista.agents.optimizer import errors as agent_errors
from escalista.agents.optimizer.graph import OptimizerAgent
from escalista.api import wiring
from escalista.domain.contracts import TraceEvent
from escalista.domain.reading import ConfirmInput
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.roster import Roster
from escalista.domain.schedule import EmployeePublic, Schedule

log = logging.getLogger("escalista")

NEXT_WEEK_UNAVAILABLE = "planejar a próxima semana ainda não está disponível"


class OptimizerSliceAgent:
    """Implementa o `SliceAgentC6` envolvendo o `OptimizerAgent` e traduzindo as exceções."""

    def __init__(self, agent: OptimizerAgent) -> None:
        self._agent = agent

    def start_run(self, file_name: str, content: bytes) -> RunState:
        return self._translated(self._agent.start_run, file_name, content)

    def confirm(self, run_id: str, data: ConfirmInput | None = None) -> RunState:
        if _accepts_second_argument(self._agent.confirm):
            return self._translated(self._agent.confirm, run_id, data)
        if data is not None:
            log.warning("confirm de %s: o agente ainda não recebe ConfirmInput; correções do gestor ignoradas", run_id)
        return self._translated(self._agent.confirm, run_id)

    def start_next_week(self) -> RunState:
        call = getattr(self._agent, "start_next_week", None)
        if call is None:
            raise wiring.RunPhaseError(NEXT_WEEK_UNAVAILABLE)
        return self._translated(call)

    def roster(self) -> Roster | None:
        call = getattr(self._agent, "roster", None)
        return call() if call is not None else None

    def get_run(self, run_id: str) -> RunState | None:
        return self._agent.get_run(run_id)

    def get_schedule(self, run_id: str) -> Schedule | None:
        return self._agent.get_schedule(run_id)

    def employees(self, run_id: str) -> list[EmployeePublic]:
        return self._agent.employees(run_id)

    def approve(self, run_id: str, approval: Approval) -> RunState:
        return self._translated(self._agent.approve, run_id, approval)

    def published(self) -> ScheduleVersion | None:
        return self._agent.published()

    def trace(self, run_id: str) -> list[TraceEvent]:
        return self._agent.trace(run_id)

    @staticmethod
    def _translated(call, *args):  # noqa: ANN001, ANN205 (repasse com a tradução dos erros)
        try:
            return call(*args)
        except agent_errors.RunNotFoundError as exc:
            raise wiring.RunNotFoundError(str(exc)) from exc
        except agent_errors.RunPhaseError as exc:
            raise wiring.RunPhaseError(str(exc)) from exc
        except agent_errors.PublishRefusedError as exc:
            raise wiring.PublishRefusedError(exc.reason, exc.card) from exc


def _accepts_second_argument(call: Any) -> bool:
    """O método ligado aceita um segundo argumento posicional (o `ConfirmInput`)?"""
    try:
        params = list(inspect.signature(call).parameters.values())
    except (TypeError, ValueError):
        return False
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 2 or any(p.kind is p.VAR_POSITIONAL for p in params)
