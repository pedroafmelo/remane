"""Falsos para os cenários determinísticos do E3/E4 (plano dos evals E3/E4, seção 4).

Espelham `tests/fakes.py` (`FixedClock`, `FakeLLMClient`) sem importá-lo: `src/` não depende de `tests/`.
`ScriptedLLM` devolve `model="fake"`, e o runner **nunca** conta isso como execução com modelo.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, LLMUnavailableError

FAKE_MODEL = "fake"


class StepClock:
    """Relógio que só anda quando mandado (satisfaz `domain.ports.Clock`)."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        self._now = self._now + delta
        return self._now


def _as_result(item: LLMResult | dict[str, Any]) -> LLMResult:
    return item if isinstance(item, LLMResult) else LLMResult(tool_args=item, model=FAKE_MODEL, key_index=1)


class ScriptedLLM:
    """`LLMClient` roteirizado: fila por nome de ferramenta (`tool_schema["function"]["name"]`), fila geral, falha por
    ferramenta (`fail_tools`) ou sempre (`fail`). Registra cada chamada em `calls`. Aceita o `kind` fora da porta."""

    def __init__(
        self,
        results: Sequence[LLMResult] | None = None,
        *,
        fail: bool = False,
        by_tool: Mapping[str, Sequence[LLMResult | dict[str, Any]]] | None = None,
        fail_tools: Iterable[str] = (),
    ) -> None:
        self._results = list(results or [])
        self._fail = fail
        self._by_tool = {name: [_as_result(item) for item in items] for name, items in (by_tool or {}).items()}
        self._fail_tools = frozenset(fail_tools)
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        size: str,
        messages: list[LLMMessage],
        tool_schema: dict[str, Any] | None = None,
        run_id: str,
        parent_id: str | None = None,
        kind: str | None = None,
    ) -> LLMResult:
        name = (tool_schema or {}).get("function", {}).get("name")
        self.calls.append(
            {
                "size": size,
                "messages": messages,
                "tool_schema": tool_schema,
                "tool_name": name,
                "run_id": run_id,
                "parent_id": parent_id,
                "kind": kind,
            }
        )
        if self._fail or name in self._fail_tools:
            raise LLMUnavailableError(
                ExceptionCard(code="RX-12", title="Modelo indisponível", reason="falha simulada", trace_id=parent_id)
            )
        queue = self._by_tool.get(name) if name else None
        if queue:
            return queue.pop(0)
        if self._results:
            return self._results.pop(0)
        return LLMResult(content="resposta falsa", model=FAKE_MODEL, key_index=1)
