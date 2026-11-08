"""`BudgetedClient`: teto de orçamento e de tempo da rodada com modelo (plano dos evals E3/E4, seções 4 e 9)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from escalista.domain.contracts import LLMMessage, LLMResult, TraceEvent
from escalista.evals.common import BudgetedClient, MemorySink, NotRun

NOW = datetime(2026, 11, 8, 10, 0, 0)
PRICE_IN = Decimal("0.17")
PRICE_OUT = Decimal("0.25")


class _Inner:
    """Como o cliente real: um evento por chamada no sink, com custo medido ou sem ele (`cost=None`)."""

    def __init__(self, sink: MemorySink, costs: list[str | None], tokens: tuple[int, int] = (1000, 100)) -> None:
        self.sink = sink
        self.costs = list(costs)
        self.tokens = tokens
        self.kinds: list[str | None] = []

    def complete(self, *, size, messages, tool_schema=None, run_id, parent_id=None, kind=None):
        self.kinds.append(kind)
        cost = self.costs.pop(0)
        self.sink.emit(
            TraceEvent(
                id=f"ev{len(self.kinds)}",
                run_id=run_id,
                kind=kind or "llm.call",
                at=NOW,
                model="small-model",
                tokens_in=self.tokens[0],
                tokens_out=self.tokens[1],
                cost_usd=None if cost is None else Decimal(cost),
            )
        )
        return LLMResult(content="ok", model="small-model", key_index=1)


def _budgeted(inner: _Inner, sink: MemorySink, ceiling: str, **kw) -> BudgetedClient:
    return BudgetedClient(
        inner,
        sink,
        Decimal(ceiling),
        price_in_per_m=PRICE_IN,
        price_out_per_m=PRICE_OUT,
        max_seconds=kw.pop("max_seconds", None),
        **kw,
    )


def _call(client: BudgetedClient, **kw) -> LLMResult:
    return client.complete(size="small", messages=[LLMMessage(role="user", content="x")], run_id="r", **kw)


def test_passes_calls_through_and_forwards_kind_until_the_measured_cost_reaches_the_ceiling():
    sink = MemorySink()
    inner = _Inner(sink, ["0.4", "0.6", "0.1"])
    client = _budgeted(inner, sink, "1.00")

    _call(client, kind="track.llm.read_atestado")
    _call(client)  # gasto medido 0,4 < 1,00: passa; depois dela, 1,0
    with pytest.raises(NotRun, match="teto de orçamento"):
        _call(client)
    assert inner.kinds == ["track.llm.read_atestado", None]
    assert client.spent_usd() == Decimal("1.0")


def test_event_without_cost_uses_tokens_times_declared_price_only_for_the_guard():
    sink = MemorySink()
    # 1M de entrada e 1M de saída sem custo medido: 0,17 + 0,25 = 0,42 pela premissa da guarda.
    inner = _Inner(sink, [None, None, None], tokens=(1_000_000, 1_000_000))
    client = _budgeted(inner, sink, "0.80")

    _call(client)
    assert client.spent_usd() == Decimal("0.42")
    _call(client)
    with pytest.raises(NotRun, match="teto de orçamento"):
        _call(client)
    assert all(e.cost_usd is None for e in sink.events)  # o rastro continua "não medido"


def test_time_ceiling():
    ticks = iter([0.0, 1.0, 10.0])
    sink = MemorySink()
    inner = _Inner(sink, ["0", "0"])
    client = _budgeted(inner, sink, "1.00", max_seconds=5.0, clock=lambda: next(ticks))

    _call(client)
    with pytest.raises(NotRun, match="tempo esgotado"):
        _call(client)
