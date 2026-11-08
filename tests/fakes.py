"""Implementações falsas das portas de `escalista.domain.ports`, para as 3 frentes."""

from datetime import datetime

from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, LLMUnavailableError, TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now


class ListTraceSink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


class FakeLLMClient:
    """Devolve resultados em fila (ou um padrão); `fail=True` levanta RX-12. Registra as chamadas."""

    def __init__(self, results: list[LLMResult] | None = None, *, fail: bool = False) -> None:
        self._results = list(results or [])
        self._fail = fail
        self.calls: list[dict] = []

    def complete(
        self,
        *,
        size: str,
        messages: list[LLMMessage],
        tool_schema: dict | None = None,
        run_id: str,
        parent_id: str | None = None,
    ) -> LLMResult:
        self.calls.append(
            {"size": size, "messages": messages, "tool_schema": tool_schema, "run_id": run_id, "parent_id": parent_id}
        )
        if self._fail:
            raise LLMUnavailableError(
                ExceptionCard(code="RX-12", title="Modelo indisponível", reason="falha simulada", trace_id=parent_id)
            )
        if self._results:
            return self._results.pop(0)
        return LLMResult(content="resposta falsa", model="fake", key_index=1)


class InMemoryRepository:
    """`Repository` em dicionários. Guarda cópias, para o chamador não alterar o que já foi salvo."""

    def __init__(self) -> None:
        self.runs: dict[str, RunState] = {}
        self.versions: dict[str, ScheduleVersion] = {}
        self.approvals: dict[str, Approval] = {}
        self.published_at: dict[str, datetime] = {}

    def save_run(self, state: RunState) -> None:
        self.runs[state.run_id] = state.model_copy(deep=True)

    def get_run(self, run_id: str) -> RunState | None:
        return self.runs.get(run_id)

    def save_version(self, v: ScheduleVersion) -> None:
        self.versions[v.id] = v.model_copy(deep=True)

    def get_version(self, version_id: str) -> ScheduleVersion | None:
        return self.versions.get(version_id)

    def record_approval(self, a: Approval) -> None:
        self.approvals[a.version_id] = a.model_copy(deep=True)

    def get_approval(self, version_id: str) -> Approval | None:
        return self.approvals.get(version_id)

    def mark_published(self, version_id: str, at: datetime) -> None:
        self.versions[version_id] = self.versions[version_id].model_copy(update={"status": "published"})
        self.published_at[version_id] = at

    def latest_published(self) -> ScheduleVersion | None:
        if not self.published_at:
            return None
        return self.versions[max(self.published_at, key=self.published_at.__getitem__)]
