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
    ImagePart,
    LLMMessage,
    LLMResult,
    LLMUnavailableError,
    Role,
    TextPart,
    TraceEvent,
)
from escalista.domain.ports import Clock, LLMClient, TraceSink
from tests.fakes import FakeLLMClient, FixedClock, ListTraceSink

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def fields(model):
    return set(model.model_fields)


def test_role_values():
    """DEC-044: dois papéis. Linhas gravadas antes dela ainda dizem `gerente` ou `dp` e leem como `gestor`."""
    assert [r.value for r in Role] == ["gestor", "colaborador"]
    assert Role("gerente") is Role.GESTOR and Role("dp") is Role.GESTOR
    with pytest.raises(ValueError):
        Role("admin")


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


def test_legacy_role_values_read_as_gestor() -> None:
    # DEC-044: rows saved before the rename still carry "gerente" or "dp"
    assert Role("gerente") is Role.GESTOR and Role("dp") is Role.GESTOR


# --- A5 (C7 T2): conteúdo em partes, para a foto do atestado ----------------------------------------------------------


def test_llm_message_content_still_accepts_plain_text():
    assert LLMMessage(role="user", content="oi").content == "oi"


def test_llm_message_content_accepts_text_and_image_parts():
    message = LLMMessage(
        role="user",
        content=[{"type": "text", "text": "leia"}, {"type": "image", "media_type": "image/png", "data": b"\x89PNG"}],
    )
    text, image = message.content
    assert isinstance(text, TextPart) and text.text == "leia"
    assert isinstance(image, ImagePart) and image.data == b"\x89PNG" and image.media_type == "image/png"


def test_image_part_accepts_only_png_and_jpeg():
    assert ImagePart(media_type="image/jpeg", data=b"\xff\xd8\xff").type == "image"
    with pytest.raises(ValidationError):
        ImagePart(media_type="image/gif", data=b"GIF89a")


def test_unknown_part_type_is_refused():
    with pytest.raises(ValidationError):
        LLMMessage(role="user", content=[{"type": "audio", "data": b"x"}])


def test_image_bytes_never_in_repr_nor_str():
    secret = b"BYTES-DA-IMAGEM-NAO-VAZAR"
    message = LLMMessage(role="user", content=[ImagePart(media_type="image/png", data=secret)])
    for shown in (repr(message), str(message), repr(message.content[0]), str(message.content[0])):
        assert "BYTES-DA-IMAGEM" not in shown
