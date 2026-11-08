"""Contratos do acompanhamento (C7, A0): forma e invariantes que os evals usam (SAIDA-AC-03, 05, 06)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from escalista.domain import ports
from escalista.domain.schedule import Shift
from escalista.domain.tracking import (
    AtestadoFields,
    AtestadoReading,
    Attachment,
    Case,
    CaseView,
    Offer,
    Trigger,
    shift_ref,
)
from tests.fakes import (
    FakeChannel,
    FakeClock,
    FakePunchSource,
    InMemoryTrackRepository,
    ListExceptionQueue,
)

START = datetime(2027, 1, 13, 14, 0)
SHIFT = Shift(employee_id="e1", store_id="s1", start=START, end=START + timedelta(hours=8))


def _case(**kw) -> Case:
    base = dict(
        id="c1", kind="falta", origin="aviso", employee_id="e1", shift=SHIFT, status="oferta_enviada", created_at=START
    )
    return Case(**{**base, **kw})


def test_atestado_fields_have_no_cid_doctor_or_free_text():
    names = set(AtestadoReading.model_fields)
    assert not names & {"cid", "cid10", "diagnostico", "medico", "doctor", "text", "raw_text"}


def test_atestado_fields_reject_extra_keys_from_the_model():
    with pytest.raises(ValidationError):
        AtestadoFields(legible=True, cid="J11")


def test_atestado_days_are_bounded():
    with pytest.raises(ValidationError):
        AtestadoFields(legible=True, days=31)


def test_attachment_bytes_never_show_in_repr():
    att = Attachment(data=b"%PDF CID J11", media_type="application/pdf", filename="atestado-joao.pdf")
    assert "J11" not in repr(att) and "joao" not in repr(att)


def test_trigger_key_is_kind_and_ref():
    t = Trigger(
        kind="no_punch",
        employee_id="e1",
        ref=shift_ref(SHIFT),
        observed="sem batida",
        threshold="10 min",
        rule_ref="pol_atraso",
    )
    assert t.key == f"no_punch:e1@{START.isoformat()}"


def test_case_run_id_and_view():
    offer = Offer(
        id="o1",
        candidate_id="e2",
        rank=1,
        sent_at=START,
        deadline=START + timedelta(minutes=20),
        overtime_hours=Decimal(0),
        added_cost=Decimal("80.00"),
    )
    view = CaseView.of(_case(offers=[offer], abono="provisorio"))
    assert _case().run_id == "track-c1"
    assert view.day == date(2027, 1, 13) and view.offers[0].candidate_id == "e2" and view.abono == "provisorio"


def test_fakes_satisfy_the_ports():
    assert isinstance(FakeChannel(), ports.Channel)
    assert isinstance(FakePunchSource(), ports.PunchSource)
    assert isinstance(ListExceptionQueue(), ports.ExceptionQueue)
    assert isinstance(InMemoryTrackRepository(), ports.TrackRepository)
    assert isinstance(FakeClock(START), ports.Clock)


def test_fake_clock_advances():
    clock = FakeClock(START)
    assert clock.advance(timedelta(minutes=15)) == START + timedelta(minutes=15) == clock.now()
