"""Contratos v0 (arquitetura.md, seção 8; plano da C0, seção 4). Só o que cruza frentes antes da C5.

Os contratos da frente A (`Rule`, `RuleCard`, `SolveRequest`, `SolveResult`, `ViolationReport`) nascem no TDD
da C1 e da C2. Mudança de contrato: PR pequeno, avisado às outras frentes, com o teste
`tests/domain/test_contracts_v0.py` editado junto.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class Role(StrEnum):
    """Papéis de acesso (DEC-044). `gestor` aprova e publica a escala, valida coberturas, decide exceções e aprova o
    cartão de regras; `colaborador` avisa falta, manda atestado e aceita ou recusa turno."""

    GESTOR = "gestor"
    COLABORADOR = "colaborador"

    @classmethod
    def _missing_(cls, value: object) -> Role | None:
        # linhas gravadas antes da DEC-044 (volume do Railway) ainda dizem "gerente" ou "dp"
        return cls.GESTOR if value in ("gerente", "dp") else None


class TraceEvent(BaseModel):
    """Um passo do rastro (RN-01 a RN-03).

    `cost_usd` é só o medido; `key_index` é o índice da chave (1 a 4), nunca o valor.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    run_id: str
    parent_id: str | None = None
    kind: str
    at: datetime
    rule_ref: str | None = None
    message_ref: str | None = None
    model: str | None = None
    key_index: StrictInt | None = Field(default=None, ge=1, le=4)
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: Decimal | None = None
    latency_ms: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)  # já redigido (RN-06)


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMResult(BaseModel):
    content: str | None = None
    tool_args: dict[str, Any] | None = None
    model: str
    key_index: StrictInt | None = Field(default=None, ge=1, le=4)
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: Decimal | None = None
    latency_ms: int | None = None


class ExceptionOption(BaseModel):
    label: str
    cost_usd: Decimal | None = None
    effect: str | None = None


class ExceptionCard(BaseModel):
    """Cartão de exceção (FT-04): o que o agente leva ao humano, com contexto pronto."""

    code: str  # por exemplo "RX-12"
    title: str
    reason: str
    decider: Role | None = None
    deadline: datetime | None = None
    evidence: list[str] = Field(default_factory=list)
    options: list[ExceptionOption] = Field(default_factory=list)
    recommendation: str | None = None
    if_no_answer: str | None = None
    trace_id: str | None = None


class LLMUnavailableError(Exception):
    """Falha do modelo vira exceção com contexto (RX-12), nunca erro solto (RN-05)."""

    def __init__(self, card: ExceptionCard) -> None:
        super().__init__(f"{card.code}: {card.title}")
        self.card = card
