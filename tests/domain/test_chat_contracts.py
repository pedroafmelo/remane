"""Contratos do chat do colaborador (C7b, E1): schema fechado do que o modelo devolve, `Reply`, porta e política."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from escalista.domain import ports
from escalista.domain.tracking import ChatContext, ChatInterpretation, Reply, TrackPolicy


def _policy(late_cover_from_min: int | None) -> TrackPolicy:
    return TrackPolicy(
        late_tolerance_min=10,
        answer_deadline_min=15,
        offer_deadline_min=20,
        max_candidates=3,
        overtime_weekly_limit_h=Decimal(6),
        overtime_warn_pct=80,
        late_cover_from_min=late_cover_from_min,
    )


def test_interpretation_is_closed():
    with pytest.raises(ValidationError):
        ChatInterpretation.model_validate({"intent": "falta", "resposta": "claro, o turno é seu"})


def test_interpretation_rejects_intent_outside_the_list():
    with pytest.raises(ValidationError):
        ChatInterpretation.model_validate({"intent": "dar_turno"})


@pytest.mark.parametrize("minutes", [0, 481])
def test_minutes_late_is_bounded(minutes):
    with pytest.raises(ValidationError):
        ChatInterpretation(intent="atraso", minutes_late=minutes)


def test_interpretation_defaults():
    parsed = ChatInterpretation.model_validate({"intent": "atraso", "day": "2027-01-14", "minutes_late": 40})
    assert parsed.day == date(2027, 1, 14) and parsed.minutes_late == 40


def test_reply_shape():
    reply = Reply(template="chat_fora_escopo", body="texto nosso")
    assert reply.case_id is None and reply.suggestions == []


def test_context_has_only_own_data():
    assert set(ChatContext.model_fields) == {"today", "own_shift_days", "open_offer_days", "open_question_days"}


def test_message_interpreter_is_a_runtime_port():
    def interpreter(*, text: str, employee_name: str, context: ChatContext, run_id: str) -> ChatInterpretation:
        return ChatInterpretation(intent="outro")

    assert isinstance(interpreter, ports.MessageInterpreter)


@pytest.mark.parametrize(("limit", "minutes", "opens"), [(30, 29, False), (30, 30, True), (30, 200, True)])
def test_late_opens_cover_from_the_policy_threshold(limit, minutes, opens):
    assert _policy(limit).late_opens_cover(minutes) is opens


@pytest.mark.parametrize("minutes", [None, 1, 480])
def test_none_never_opens_cover(minutes):
    assert _policy(None).late_opens_cover(minutes) is False


def test_unknown_minutes_never_open_cover():
    assert _policy(30).late_opens_cover(None) is False


def test_policy_default_is_none():
    policy = TrackPolicy(
        late_tolerance_min=10,
        answer_deadline_min=15,
        offer_deadline_min=20,
        max_candidates=3,
        overtime_weekly_limit_h=Decimal(6),
        overtime_warn_pct=80,
    )
    assert policy.late_cover_from_min is None
