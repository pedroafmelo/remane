"""Contratos das regras (plano da C5, seção 3.1). Só forma: carregar, fundir e validar é da `rules/` (A1)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from escalista.domain.contracts import ExceptionCard


class RuleStatus(StrEnum):
    """`ficticia` vale só para `convencao/` e `politica/` (DEC-039); a regra é do carregador."""

    CONFERIDA = "conferida"
    INTERPRETACAO = "interpretacao"
    PENDENTE = "pendente"
    FICTICIA = "ficticia"
    PEDIDO = "pedido"  # restrição dura pedida pelo gestor (camada `execucao`, C6)


class RuleLayer(StrEnum):
    """`execucao` (C6) guarda as restrições duras da `SolveSpec` de uma execução: só acrescenta, nunca afrouxa as
    outras camadas, e não vem de YAML."""

    LEI = "lei"
    CONVENCAO = "convencao"
    POLITICA = "politica"
    EXECUCAO = "execucao"


class Rule(BaseModel):
    """Uma regra de uma camada. `kind` é o tipo de primitiva, ou `"info"` para regra fora da fatia."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    layer: RuleLayer
    params: dict[str, Any] = Field(default_factory=dict)
    valid_from: date | None = None
    valid_to: date | None = None
    status: RuleStatus
    source: str
    action: Literal["escalar", "verificar_convencao"] | None = None
    note: str | None = None


class RuleCard(BaseModel):
    """Regras já fundidas e vigentes na data de referência, com o que ficou provisório e os conflitos ao gestor."""

    reference_date: date
    rules: list[Rule]
    provisional: list[str] = Field(default_factory=list)  # ids aplicados como "mais restritiva provisória"
    exceptions: list[ExceptionCard] = Field(default_factory=list)
