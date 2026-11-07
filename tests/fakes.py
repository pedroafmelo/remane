"""Implementações falsas das portas de `escalista.domain.ports`, para as 3 frentes."""

from datetime import datetime

from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, LLMUnavailableError, TraceEvent


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
