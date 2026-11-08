"""Portas (interfaces `Protocol`) do núcleo (arquitetura.md, seção 2.1). As bordas implementam; os testes usam falsos.

`Repository` entra na fatia (plano da C5, seção 3.2; implementação SQL em `store/`, frente B) e `Channel` na C7.
`Channel`, `PunchSource`, `ExceptionQueue`, `AtestadoReader` e `TrackRepository` são do acompanhamento (plano da C7,
seção 5.2). `RosterRepository` é a extensão da C6 (plano da C6, seção 5.2): porta à parte, para o `SqlRepository`
da C5 seguir satisfazendo `Repository` até a B1 implementar o quadro; o repositório da execução implementa as duas.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Protocol, runtime_checkable

from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.roster import Roster
from escalista.domain.tracking import AtestadoReading, Case, ChannelMessage, ChatContext, ChatInterpretation, Punch


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
        size: Literal["small", "large", "vision"],
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


# --- acompanhamento (C7) -------------------------------------------------------------------------------------------


@runtime_checkable
class Channel(Protocol):
    """Canal com o colaborador (arquitetura, seção 10). `SimulatedPhone` grava em `channel_message` (RH-06)."""

    def send(self, message: ChannelMessage) -> None: ...

    def inbox(self, party: str) -> list[ChannelMessage]: ...


@runtime_checkable
class PunchSource(Protocol):
    """Ponto (simulado na demo). Levanta `PunchUnavailableError` quando fora do ar (RX-12)."""

    def punches(self, *, until: datetime) -> list[Punch]: ...


@runtime_checkable
class ExceptionQueue(Protocol):
    """Fila de exceções do gestor, vista pelo agente (sem importar `store/`). Devolve o id do item aberto."""

    def open(self, card: ExceptionCard, source: dict[str, Any]) -> str: ...


@runtime_checkable
class AtestadoReader(Protocol):
    """Leitura da comprovação (borda `ingest/atestado.py`). Levanta `LLMUnavailableError` (RX-12)."""

    def __call__(
        self, *, data: bytes, media_type: str, run_id: str, expected_day: date, employee_name: str
    ) -> AtestadoReading: ...


@runtime_checkable
class MessageInterpreter(Protocol):
    """Classifica a mensagem livre do colaborador (borda `ingest/chat.py`, C7b). Só classifica, em schema fechado;
    levanta `LLMUnavailableError` quando o modelo falha ou não entrega o schema."""

    def __call__(
        self, *, text: str, employee_name: str, context: ChatContext, run_id: str
    ) -> ChatInterpretation: ...


@runtime_checkable
class TrackRepository(Protocol):
    """Casos do acompanhamento (tabela `track_case`)."""

    def save_case(self, case: Case) -> None: ...

    def get_case(self, case_id: str) -> Case | None: ...

    def list_cases(self) -> list[Case]: ...

    def reset(self) -> None: ...
