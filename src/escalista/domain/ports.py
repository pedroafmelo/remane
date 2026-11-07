"""Portas (interfaces `Protocol`) do núcleo (arquitetura.md, seção 2.1). As bordas implementam; os testes usam falsos.

`Repository` entra na C2 (frente A) e `Channel` na C7, junto com o primeiro consumidor (plano da C0, seção 4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from escalista.domain.contracts import LLMMessage, LLMResult, TraceEvent


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class TraceSink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...


@runtime_checkable
class LLMClient(Protocol):
    def complete(
        self,
        *,
        size: Literal["small", "large"],
        messages: list[LLMMessage],
        tool_schema: dict[str, Any] | None = None,
        run_id: str,
        parent_id: str | None = None,
    ) -> LLMResult:
        """Levanta `LLMUnavailableError` (cartão RX-12) quando o modelo falha."""
        ...
