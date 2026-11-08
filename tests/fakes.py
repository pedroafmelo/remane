"""Implementações falsas das portas de `escalista.domain.ports`, para as 3 frentes."""

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, LLMUnavailableError, TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.roster import Roster

# Nomes das ferramentas forçadas de cada nó (plano da C6, seção 5.4). Ficam aqui, e não em `domain/`, porque são da
# borda `llm/`; os prompts da frente B usam os mesmos textos (`llm/prompts/justify.py:TOOL_NAME` já é o último).
TOOL_MAPPING = "registrar_mapeamento"  # nó 1: ColumnMapping
TOOL_SPEC = "registrar_especificacao"  # nó 2: SolveSpec
TOOL_JUSTIFY = "registrar_justificativa"  # justificativa


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
    """Falso do `LLMClient`, que responde por nome de ferramenta (C6) ou em fila (C5). Registra as chamadas.

    - `by_tool`: fila por nome de ferramenta (`tool_schema["function"]["name"]`); cada item é um `LLMResult` ou um
      dicionário, que vira `LLMResult(tool_args=item)`.
    - `results`: fila geral, usada quando a fila da ferramenta acaba (ou a chamada não tem ferramenta).
    - Sem nada nas filas, devolve só texto, sem ferramenta (o `call_structured` trata como recusa).
    - `fail=True` levanta RX-12 em toda chamada; `fail_tools` só nas ferramentas citadas (falha por nó).
    """

    def __init__(
        self,
        results: list[LLMResult] | None = None,
        *,
        fail: bool = False,
        by_tool: Mapping[str, Sequence[LLMResult | dict[str, Any]]] | None = None,
        fail_tools: Iterable[str] = (),
    ) -> None:
        self._results = list(results or [])
        self._fail = fail
        self._by_tool = {name: [_as_result(item) for item in items] for name, items in (by_tool or {}).items()}
        self._fail_tools = frozenset(fail_tools)
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
        name = (tool_schema or {}).get("function", {}).get("name")
        self.calls.append(
            {
                "size": size,
                "messages": messages,
                "tool_schema": tool_schema,
                "tool_name": name,
                "run_id": run_id,
                "parent_id": parent_id,
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
        return LLMResult(content="resposta falsa", model="fake", key_index=1)


def _as_result(item: LLMResult | dict[str, Any]) -> LLMResult:
    return item if isinstance(item, LLMResult) else LLMResult(tool_args=item, model="fake", key_index=1)


class InMemoryRepository:
    """`Repository` e `RosterRepository` em dicionários. Guarda cópias, para o chamador não alterar o que já foi
    salvo."""

    def __init__(self) -> None:
        self.runs: dict[str, RunState] = {}
        self.versions: dict[str, ScheduleVersion] = {}
        self.approvals: dict[str, Approval] = {}
        self.published_at: dict[str, datetime] = {}
        self.rosters: dict[int, Roster] = {}

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

    def save_roster(self, r: Roster) -> None:
        if r.version in self.rosters:
            raise ValueError(f"o quadro versão {r.version} já existe; cada confirmação acrescenta uma versão")
        self.rosters[r.version] = r.model_copy(deep=True)

    def latest_roster(self) -> Roster | None:
        return self.rosters[max(self.rosters)] if self.rosters else None

    def get_roster(self, version: int) -> Roster | None:
        return self.rosters.get(version)
