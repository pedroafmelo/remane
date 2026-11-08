"""Erros que o agente de otimização devolve a quem o chama. Espelham os de `api/wiring.py` (mesmos nomes e
assinaturas), sem importá-los: `agents` não importa borda. A C4 só traduz um no outro."""

from __future__ import annotations

from escalista.domain.contracts import ExceptionCard


class OptimizerAgentError(Exception):
    """Base dos erros do agente de otimização."""


class RunNotFoundError(OptimizerAgentError):
    """`run_id` desconhecido."""


class RunPhaseError(OptimizerAgentError):
    """A execução não está na fase que a operação exige."""


class PublishRefusedError(OptimizerAgentError):
    """`publicar` recusou (RH-01): sem aprovação gravada, aprovação de outra versão ou papel sem permissão."""

    def __init__(self, reason: str, card: ExceptionCard | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.card = card
