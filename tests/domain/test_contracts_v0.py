"""Contratos v0 (plano da C0, seção 4): fixa nomes de campos e métodos.

Mudar um contrato exige editar este teste no mesmo PR, o que deixa a mudança visível às outras frentes.
"""

import inspect
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from escalista.domain.contracts import (
    ExceptionCard,
    ExceptionOption,
    LLMMessage,
    LLMResult,
    LLMUnavailableError,
    Role,
    TraceEvent,
)
from escalista.domain.ports import Clock, LLMClient, TraceSink
from tests.fakes import FakeLLMClient, FixedClock, ListTraceSink

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def fields(model):
    return set(model.model_fields)


def test_role_values():
    """DEC-044: só dois papéis, sem alias dos antigos (`gerente`, `dp`)."""
    assert [r.value for r in Role] == ["gestor", "colaborador"]
    for old in ("gerente", "dp"):
        with pytest.raises(ValueError):
            Role(old)


def test_trace_event_fields():
    assert fields(TraceEvent) == {
        "id", "run_id", "parent_id", "kind", "at", "rule_ref", "message_ref", "model", "key_index",
        "tokens_in", "tokens_out", "cost_usd", "latency_ms", "payload",
    }  # fmt: skip


def test_trace_event_is_frozen_and_cost_is_optional_decimal():
    event = TraceEvent(id="e1", run_id="r1", kind="llm_call", at=NOW)
    assert event.cost_usd is None and event.payload == {}
    with pytest.raises(ValidationError):
        event.kind = "outro"
    assert TraceEvent(id="e2", run_id="r1", kind="llm_call", at=NOW, cost_usd=Decimal("0.0001")).cost_usd == Decimal(
        "0.0001"
    )


def test_trace_event_key_index_is_an_index_not_a_value():
    with pytest.raises(ValidationError):
        TraceEvent(id="e", run_id="r", kind="k", at=NOW, key_index="rc_segredo")


def test_llm_models_fields():
    assert fields(LLMMessage) == {"role", "content"}
    assert fields(LLMResult) == {
        "content", "tool_args", "model", "key_index", "tokens_in", "tokens_out", "cost_usd", "latency_ms",
    }  # fmt: skip


def test_exception_card_fields():
    assert fields(ExceptionOption) == {"label", "cost_usd", "effect"}
    assert fields(ExceptionCard) == {
        "code", "title", "reason", "decider", "deadline", "evidence", "options", "recommendation", "if_no_answer",
        "trace_id",
    }  # fmt: skip


def test_llm_unavailable_error_carries_an_rx12_card():
    card = ExceptionCard(code="RX-12", title="Modelo indisponível", reason="503 após 3 tentativas")
    error = LLMUnavailableError(card)
    assert error.card is card and "RX-12" in str(error)


def test_ports_methods():
    assert list(inspect.signature(Clock.now).parameters) == ["self"]
    assert list(inspect.signature(TraceSink.emit).parameters) == ["self", "event"]
    params = inspect.signature(LLMClient.complete).parameters
    assert list(params) == ["self", "size", "messages", "tool_schema", "run_id", "parent_id"]
    assert all(params[n].kind is inspect.Parameter.KEYWORD_ONLY for n in list(params)[1:])


def test_fakes_satisfy_the_ports():
    assert isinstance(FixedClock(NOW), Clock)
    assert isinstance(ListTraceSink(), TraceSink)
    assert isinstance(FakeLLMClient(), LLMClient)


def test_fakes_behave():
    assert FixedClock(NOW).now() == NOW
    sink = ListTraceSink()
    event = TraceEvent(id="e1", run_id="r1", kind="k", at=NOW)
    sink.emit(event)
    assert sink.events == [event]
    llm = FakeLLMClient(results=[LLMResult(content="ok", model="m", key_index=1)])
    assert llm.complete(size="small", messages=[LLMMessage(role="user", content="oi")], run_id="r1").content == "ok"
    assert llm.calls[0]["size"] == "small"
    with pytest.raises(LLMUnavailableError):
        FakeLLMClient(fail=True).complete(size="large", messages=[], run_id="r1")
