"""`SimulatedPhone` (C7, tarefa B1): grava em `channel_message`; a entrada nunca guarda o texto (RN-06)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from escalista.channel.simulated import SimulatedPhone
from escalista.db import init_db, make_engine
from escalista.domain.ports import Channel
from escalista.domain.tracking import ChannelMessage
from escalista.store.tracking import ChannelMessageRow

T0 = datetime(2027, 1, 13, 14, 0)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    init_db(eng)
    return eng


def msg(msg_id: str, party: str, *, direction="out", body: str | None = "oi", minutes: int = 0, **extra):
    return ChannelMessage(
        id=msg_id,
        direction=direction,
        party=party,
        template="t",
        body=body,
        at=T0 + timedelta(minutes=minutes),
        **extra,
    )


def test_implements_port(engine):
    assert isinstance(SimulatedPhone(engine), Channel)


def test_inbox_filters_by_party_and_keeps_write_order(engine):
    phone = SimulatedPhone(engine)
    # `at` fora de ordem de propósito: vale a ordem de gravação, não o relógio
    phone.send(msg("m1", "e1", minutes=30))
    phone.send(msg("m2", "gestor", minutes=20))
    phone.send(msg("m3", "e1", minutes=10))
    phone.send(msg("m4", "e2"))
    assert [m.id for m in phone.inbox("e1")] == ["m1", "m3"]
    assert [m.id for m in phone.inbox("gestor")] == ["m2"]
    assert phone.inbox("ninguem") == []
    assert [m.id for m in phone.all_messages()] == ["m1", "m2", "m3", "m4"]


def test_round_trip_preserves_every_field(engine):
    phone = SimulatedPhone(engine)
    message = msg(
        "m1",
        "e1",
        direction="in",
        body=None,
        case_id="c1",
        has_text=True,
        attachment_media_type="application/pdf",
        decision_ref="ev-9",
    )
    phone.send(message)
    assert phone.inbox("e1") == [message]


def test_inbound_with_body_is_refused_and_not_stored(engine):
    phone = SimulatedPhone(engine)
    with pytest.raises(ValueError, match="RN-06"):
        phone.send(msg("m1", "e1", direction="in", body="tenho CID J11"))
    assert phone.all_messages() == []
    with Session(engine) as session:
        assert session.scalars(select(ChannelMessageRow)).all() == []


def test_order_survives_new_instance_and_resumes_seq(engine):
    SimulatedPhone(engine).send(msg("m1", "e1"))
    later = SimulatedPhone(engine)
    later.send(msg("m2", "e1"))
    assert [m.id for m in later.inbox("e1")] == ["m1", "m2"]
