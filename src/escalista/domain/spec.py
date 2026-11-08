"""Especificação do problema formulada pelo modelo (nó 2; plano da C6, seções 5.1 e 10).

Só forma, com lista fechada de restrições e `extra="forbid"` em tudo: a spec não tem campo para regra do cartão, então
o modelo não tem como afrouxar lei nem convenção (invariante 4). Validar ids, dias, horas abaixo do cartão e evidência
é da `rules/spec.py` (A4).
"""

from __future__ import annotations

from datetime import date, time
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Evidence = Annotated[str, Field(min_length=1)]  # trecho literal do pedido do gestor ou de uma célula de `notes`


def _type_is_required(schema: dict[str, Any]) -> None:
    """`type` tem padrão (comodidade no código), mas o modelo precisa mandá-lo: a união é discriminada por ele."""
    required = schema.setdefault("required", [])
    if "type" not in required:
        required.insert(0, "type")


def _without_discriminator_mapping(schema: dict[str, Any]) -> None:
    """O `mapping` do discriminador aponta para `$defs`, que o schema da ferramenta resolve no lugar; sem ele, o
    `oneOf` com `type` constante basta (e não sobra referência solta)."""
    schema.get("properties", {}).get("constraints", {}).get("items", {}).pop("discriminator", None)


class _Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_type_is_required)

    employee_id: str
    evidence: Evidence


class UnavailableConstraint(_Constraint):
    """Dura: a pessoa não pode trabalhar no dia (ou no intervalo `start`–`end` do dia)."""

    type: Literal["indisponivel"] = "indisponivel"
    day: date
    start: time | None = None
    end: time | None = None


class MaxWeeklyHoursConstraint(_Constraint):
    """Dura: limite semanal da pessoa, só abaixo do limite do cartão."""

    type: Literal["max_horas_semana"] = "max_horas_semana"
    hours: int = Field(ge=1)


class PreferredDayOffConstraint(_Constraint):
    """Suave: folga preferida no dia."""

    type: Literal["folga_preferida"] = "folga_preferida"
    day: date


class PreferredWindowConstraint(_Constraint):
    """Suave: janela do dia preferida."""

    type: Literal["janela_preferida"] = "janela_preferida"
    window: Literal["manha", "tarde", "noite"]


SpecConstraint = Annotated[
    UnavailableConstraint | MaxWeeklyHoursConstraint | PreferredDayOffConstraint | PreferredWindowConstraint,
    Field(discriminator="type"),
]


class SolveSpec(BaseModel):
    """Pesos e restrições por pessoa. Os padrões reproduzem o comportamento da C5 (`shortfall_weight` = 100)."""

    model_config = ConfigDict(extra="forbid", json_schema_extra=_without_discriminator_mapping)

    shortfall_weight: int = Field(default=100, ge=10, le=1000)
    stability_weight: int = Field(default=0, ge=0, le=50)
    preference_weight: int = Field(default=5, ge=0, le=50)
    constraints: list[SpecConstraint] = Field(default_factory=list, max_length=30)
