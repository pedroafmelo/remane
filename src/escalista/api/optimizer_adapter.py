"""Adaptador fino entre a API e o agente LangGraph da I1 (plano da C5, seção 4, C4).

`OptimizerAgent` (`agents/optimizer/graph.py`) já tem os métodos e as assinaturas do `SliceAgent`, mas levanta os erros
de `agents/optimizer/errors.py`, de outra hierarquia (`agents` não importa a borda). Aqui cada erro vira o seu
equivalente de `api/wiring.py`, que `routes_runs.install_runs` traduz em 404, 409 e 403. Nenhum comportamento muda.
"""

from __future__ import annotations

from escalista.agents.optimizer import errors as agent_errors
from escalista.agents.optimizer.graph import OptimizerAgent
from escalista.api import wiring
from escalista.domain.contracts import TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.schedule import EmployeePublic, Schedule


class OptimizerSliceAgent:
    """Implementa o `SliceAgent` envolvendo o `OptimizerAgent` e traduzindo as exceções."""

    def __init__(self, agent: OptimizerAgent) -> None:
        self._agent = agent

    def start_run(self, file_name: str, content: bytes) -> RunState:
        return self._translated(self._agent.start_run, file_name, content)

    def confirm(self, run_id: str) -> RunState:
        return self._translated(self._agent.confirm, run_id)

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
