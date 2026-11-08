"""Varredor puro do acompanhamento (C7 A3; contrato SAIDA-AC-06): `no_punch`, `no_answer`, `offer_expired`."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from escalista.agents.tracker.sweep import detect
from escalista.domain.schedule import Schedule, Shift
from escalista.domain.tracking import Case, Offer, Punch, TrackPolicy, Trigger, shift_ref

POLICY = TrackPolicy(
    late_tolerance_min=10,
    answer_deadline_min=15,
    offer_deadline_min=20,
    max_candidates=3,
    overtime_weekly_limit_h=Decimal("6"),
    overtime_warn_pct=80,
)
START = datetime(2027, 1, 13, 14, 0)
ANA = Shift(employee_id="ana", store_id="centro", start=START, end=datetime(2027, 1, 13, 22, 0))
BRUNO = Shift(
    employee_id="bruno", store_id="centro", start=datetime(2027, 1, 13, 8, 0), end=datetime(2027, 1, 13, 14, 0)
)
CAIO = Shift(employee_id="caio", store_id="norte", start=START, end=datetime(2027, 1, 13, 20, 0))
SCHEDULE = Schedule(week_start=date(2027, 1, 11), shifts=[ANA, BRUNO, CAIO])


def punch_in(shift: Shift, at: datetime | None = None) -> Punch:
    return Punch(employee_id=shift.employee_id, shift_start=shift.start, kind="in", at=at or shift.start)


# Todos bateram o ponto menos a Ana (falta plantada).
PUNCHES = [punch_in(BRUNO), punch_in(CAIO)]


def run(*, now: datetime, punches=PUNCHES, cases=(), schedule=SCHEDULE, policy=POLICY) -> list[Trigger]:
    return detect(schedule=schedule, punches=list(punches), policy=policy, cases=list(cases), now=now)


def case(**overrides) -> Case:
    base = {
        "id": "c1",
        "kind": "falta",
        "origin": "ponto",
        "employee_id": "ana",
        "shift": ANA,
        "status": "aguardando_colaborador",
        "created_at": START + timedelta(minutes=10),
    }
    return Case(**(base | overrides))


def offer(**overrides) -> Offer:
    base = {
        "id": "o1",
        "candidate_id": "caio",
        "rank": 1,
        "sent_at": START + timedelta(minutes=20),
        "deadline": START + timedelta(minutes=40),
        "overtime_hours": Decimal("0"),
        "added_cost": Decimal("0"),
    }
    return Offer(**(base | overrides))


# --- no_punch -------------------------------------------------------------------------------------------------------


def test_no_punch_fires_at_tolerance():
    (trigger,) = run(now=START + timedelta(minutes=10))
    assert trigger == Trigger(
        kind="no_punch",
        employee_id="ana",
        ref=shift_ref(ANA),
        observed="sem batida de entrada às 14:10",
        threshold="10 min após o início",
        rule_ref="pol_atraso",
    )
    assert trigger.ref == "ana@2027-01-13T14:00:00"


def test_no_punch_does_not_fire_one_minute_before_tolerance():
    assert run(now=START + timedelta(minutes=9)) == []


def test_tolerance_comes_from_the_policy():
    strict = POLICY.model_copy(update={"late_tolerance_min": 5})
    assert [t.kind for t in run(now=START + timedelta(minutes=5), policy=strict)] == ["no_punch"]
    assert run(now=START + timedelta(minutes=4), policy=strict) == []


def test_punch_in_on_time_suppresses_no_punch():
    assert run(now=START + timedelta(minutes=30), punches=[*PUNCHES, punch_in(ANA)]) == []


def test_late_punch_before_now_suppresses_no_punch():
    late = punch_in(ANA, at=START + timedelta(minutes=12))
    assert run(now=START + timedelta(minutes=12), punches=[*PUNCHES, late]) == []


def test_punch_after_now_does_not_count():
    future = punch_in(ANA, at=START + timedelta(minutes=30))
    assert [t.ref for t in run(now=START + timedelta(minutes=10), punches=[*PUNCHES, future])] == [shift_ref(ANA)]


def test_punch_out_or_for_another_shift_does_not_count():
    out = Punch(employee_id="ana", shift_start=START, kind="out", at=START)
    other_day = Punch(employee_id="ana", shift_start=START - timedelta(days=1), kind="in", at=START)
    triggers = run(now=START + timedelta(minutes=10), punches=[*PUNCHES, out, other_day])
    assert [t.ref for t in triggers] == [shift_ref(ANA)]


@pytest.mark.parametrize("status", ["aguardando_colaborador", "oferta_enviada", "coberto", "descoberto", "decidido"])
def test_any_case_for_the_shift_suppresses_no_punch(status):
    assert run(now=START + timedelta(minutes=10), cases=[case(status=status, origin="aviso")]) == []


def test_case_for_another_shift_does_not_suppress_no_punch():
    other = case(employee_id="caio", shift=CAIO, status="decidido")
    assert [t.ref for t in run(now=START + timedelta(minutes=10), cases=[other])] == [shift_ref(ANA)]


def test_future_shifts_are_ignored():
    assert run(now=datetime(2027, 1, 13, 7, 0), punches=[]) == []


# --- no_answer ------------------------------------------------------------------------------------------------------

ASKED = START + timedelta(minutes=10)


def test_no_answer_fires_at_the_answer_deadline():
    (trigger,) = run(now=ASKED + timedelta(minutes=15), cases=[case(asked_at=ASKED)])
    assert trigger.kind == "no_answer"
    assert trigger.ref == "c1"
    assert trigger.employee_id == "ana"
    assert trigger.rule_ref == "pol_atraso"
    assert trigger.threshold == "15 min após a pergunta"
    assert trigger.observed == "sem resposta desde 14:10"


def test_no_answer_does_not_fire_one_minute_before():
    assert run(now=ASKED + timedelta(minutes=14), cases=[case(asked_at=ASKED)]) == []


def test_no_answer_needs_a_question():
    assert run(now=ASKED + timedelta(hours=2), cases=[case(asked_at=None)]) == []


@pytest.mark.parametrize("status", ["oferta_enviada", "aguardando_gestor", "coberto", "atraso_registrado", "decidido"])
def test_no_answer_only_while_waiting_for_the_employee(status):
    assert run(now=ASKED + timedelta(hours=2), cases=[case(status=status, asked_at=ASKED)]) == []


# --- offer_expired --------------------------------------------------------------------------------------------------

DEADLINE = START + timedelta(minutes=40)


def offered(*offers: Offer, status: str = "oferta_enviada") -> Case:
    return case(status=status, origin="aviso", offers=list(offers))


def test_offer_expired_fires_at_the_deadline():
    (trigger,) = run(now=DEADLINE, cases=[offered(offer())])
    assert trigger.kind == "offer_expired"
    assert trigger.ref == "o1"
    assert trigger.employee_id == "caio"
    assert trigger.rule_ref == "pol_oferta_turno"
    assert trigger.threshold == "20 min por candidato"
    assert trigger.observed == "oferta sem resposta até 14:40"


def test_offer_expired_does_not_fire_before_the_deadline():
    assert run(now=DEADLINE - timedelta(minutes=1), cases=[offered(offer())]) == []


@pytest.mark.parametrize("status", ["aceita", "recusada", "vencida"])
def test_only_open_offers_expire(status):
    assert run(now=DEADLINE + timedelta(hours=1), cases=[offered(offer(status=status))]) == []


def test_offers_expire_only_while_the_case_waits_for_them():
    assert run(now=DEADLINE + timedelta(hours=1), cases=[offered(offer(), status="aguardando_gestor")]) == []


def test_only_the_expired_offer_of_a_case_fires():
    old = offer(id="o1", status="vencida")
    current = offer(id="o2", candidate_id="bruno", rank=2, deadline=DEADLINE + timedelta(minutes=20))
    triggers = run(now=DEADLINE + timedelta(minutes=20), cases=[offered(old, current)])
    assert [(t.kind, t.ref, t.employee_id) for t in triggers] == [("offer_expired", "o2", "bruno")]


# --- idempotência pelo `handled` e ordem ----------------------------------------------------------------------------


def test_handled_no_answer_does_not_come_back():
    now = ASKED + timedelta(minutes=15)
    (trigger,) = run(now=now, cases=[case(asked_at=ASKED)])
    assert run(now=now, cases=[case(asked_at=ASKED, handled=[trigger.key])]) == []
    assert run(now=now + timedelta(hours=1), cases=[case(asked_at=ASKED, handled=[trigger.key])]) == []


def test_handled_offer_expired_does_not_come_back():
    (trigger,) = run(now=DEADLINE, cases=[offered(offer())])
    handled = offered(offer()).model_copy(update={"handled": [trigger.key]})
    assert run(now=DEADLINE, cases=[handled]) == []


def test_a_key_handled_by_another_case_does_not_suppress():
    other = case(id="c2", employee_id="caio", shift=CAIO, status="decidido", handled=["no_answer:c1"])
    triggers = run(now=ASKED + timedelta(minutes=15), cases=[case(asked_at=ASKED), other])
    assert [t.key for t in triggers] == ["no_answer:c1"]


def test_same_input_gives_the_same_list():
    now = START + timedelta(hours=1)
    cases = [
        case(asked_at=ASKED),
        offered(offer(id="o9", deadline=now), status="oferta_enviada").model_copy(
            update={"id": "c2", "employee_id": "bruno", "shift": BRUNO}
        ),
    ]
    first = run(now=now, punches=[], cases=cases)
    assert first == run(now=now, punches=[], cases=cases)
    assert first


def test_output_is_sorted_by_kind_then_ref():
    now = START + timedelta(hours=1)
    dani = Shift(employee_id="dani", store_id="norte", start=START, end=datetime(2027, 1, 13, 18, 0))
    schedule = Schedule(week_start=date(2027, 1, 11), shifts=[dani, CAIO, ANA, BRUNO])
    cases = [
        case(id="c2", employee_id="bruno", shift=BRUNO, status="oferta_enviada", offers=[offer(id="o1", deadline=now)]),
        case(id="c1", asked_at=ASKED),
    ]
    triggers = run(now=now, punches=[], cases=cases, schedule=schedule)
    assert [(t.kind, t.ref) for t in triggers] == [
        ("no_answer", "c1"),
        ("no_punch", shift_ref(CAIO)),
        ("no_punch", shift_ref(dani)),
        ("offer_expired", "o1"),
    ]
    reversed_input = run(now=now, punches=[], cases=cases[::-1], schedule=schedule)
    assert reversed_input == triggers


def test_duplicate_shift_in_schedule_gives_one_trigger():
    schedule = Schedule(week_start=date(2027, 1, 11), shifts=[ANA, ANA, BRUNO, CAIO])
    assert len(run(now=START + timedelta(minutes=10), schedule=schedule)) == 1
