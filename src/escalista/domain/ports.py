"""Portas (interfaces `Protocol`) do núcleo (arquitetura.md, seção 2.1). As bordas implementam; os testes usam falsos.

`Repository` entra na fatia (plano da C5, seção 3.2; implementação SQL em `store/`, frente B) e `Channel` na C7.
`RosterRepository` é a extensão da C6 (plano da C6, seção 5.2): porta à parte, para o `SqlRepository` da C5 seguir
satisfazendo `Repository` até a B1 implementar o quadro; o repositório da execução implementa as duas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from escalista.domain.contracts import LLMMessage, LLMResult, TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.roster import Roster


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


@runtime_checkable
class Repository(Protocol):
    """Persistência da execução, das versões da escala e das aprovações (plano da C5, seção 3.2)."""

    def save_run(self, state: RunState) -> None: ...

    def get_run(self, run_id: str) -> RunState | None: ...

    def save_version(self, v: ScheduleVersion) -> None: ...

    def get_version(self, version_id: str) -> ScheduleVersion | None: ...

    def record_approval(self, a: Approval) -> None: ...

    def get_approval(self, version_id: str) -> Approval | None: ...

    def mark_published(self, version_id: str, at: datetime) -> None: ...

    def latest_published(self) -> ScheduleVersion | None: ...


@runtime_checkable
class RosterRepository(Protocol):
    """Quadro guardado, versionado (plano da C6, seção 5.2). `latest_published()` de `Repository` dá a semana."""

    def save_roster(self, r: Roster) -> None:
        """Acrescenta uma versão; nunca sobrescreve (versão repetida levanta `ValueError`)."""
        ...

    def latest_roster(self) -> Roster | None: ...

    def get_roster(self, version: int) -> Roster | None: ...
