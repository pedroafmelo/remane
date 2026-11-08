"""Gatilhos de hora extra do varredor (C7 T2, RF-27; DEC-060): 80% do limite semanal avisa, acima de 100% escala."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from escalista.agents.tracker.sweep import detect, overtime_minutes
from escalista.domain.schedule import Schedule, Shift
from escalista.domain.tracking import Punch, TrackPolicy, Trigger

POLICY = TrackPolicy(
    late_tolerance_min=10,
    answer_deadline_min=15,
    offer_deadline_min=20,
    max_candidates=3,
    overtime_weekly_limit_h=Decimal("6"),
    overtime_warn_pct=80,
)
# Nelson (sintético) faz 08–16h de seg 11/01 a sex 15/01 e sai mais tarde: 90, 90, 60, 60, 75 min (DV-03 a DV-07).
EXTRA = [90, 90, 60, 60, 75]
SHIFTS = [
    Shift(employee_id="P204", store_id="L2", start=datetime(2027, 1, 11 + d, 8), end=datetime(2027, 1, 11 + d, 16))
    for d in range(5)
]
SCHEDULE = Schedule(week_start=date(2027, 1, 11), shifts=SHIFTS)


def _punches(extra: list[int] = EXTRA, shifts: list[Shift] = SHIFTS) -> list[Punch]:
    out: list[Punch] = []
    for shift, minutes in zip(shifts, extra, strict=True):
        out.append(Punch(employee_id=shift.employee_id, shift_start=shift.start, kind="in", at=shift.start))
        out.append(
            Punch(
                employee_id=shift.employee_id,
                shift_start=shift.start,
                kind="out",
                at=shift.end + timedelta(minutes=minutes),
            )
        )
    return out


def run(now: datetime, *, punches=None, handled=(), schedule=SCHEDULE) -> list[Trigger]:
    punches = _punches() if punches is None else punches
    visible = [p for p in punches if p.at <= now]
    return detect(schedule=schedule, punches=visible, policy=POLICY, cases=[], now=now, handled=set(handled))


def overtime(triggers: list[Trigger]) -> list[Trigger]:
    return [t for t in triggers if t.kind.startswith("overtime_")]


def test_minutes_sum_only_closed_shifts_up_to_now():
    assert overtime_minutes(SCHEDULE, _punches(), "P204", date(2027, 1, 11), datetime(2027, 1, 14, 16, 59)) == 240
    assert overtime_minutes(SCHEDULE, _punches(), "P204", date(2027, 1, 11), datetime(2027, 1, 14, 17, 0)) == 300
    assert overtime_minutes(SCHEDULE, _punches(), "P204", date(2027, 1, 11), datetime(2027, 1, 15, 17, 15)) == 375


def test_near_limit_fires_at_thursday_17_00_and_not_at_16_59():
    assert overtime(run(datetime(2027, 1, 14, 16, 59))) == []
    [trigger] = overtime(run(datetime(2027, 1, 14, 17, 0)))
    assert trigger.kind == "overtime_near_limit"
    assert trigger.employee_id == "P204"
    assert trigger.ref == "P204@2027-01-11"
    assert trigger.rule_ref == "pol_aviso_hora_extra_estourando"
    assert "5h" in trigger.observed
    assert "4h48" in trigger.threshold


def test_limit_fires_at_friday_17_15_and_not_at_17_14():
    handled = {"overtime_near_limit:P204@2027-01-11"}
    before = overtime(run(datetime(2027, 1, 15, 17, 14), handled=handled))
    assert before == []
    [trigger] = overtime(run(datetime(2027, 1, 15, 17, 15), handled=handled))
    assert trigger.kind == "overtime_limit"
    assert trigger.ref == "P204@2027-01-11"
    assert trigger.rule_ref == "pol_hora_extra"
    assert "6h15" in trigger.observed
    assert "6h" in trigger.threshold


def test_handled_keys_do_not_come_back():
    now = datetime(2027, 1, 15, 17, 15)
    assert overtime(run(now, handled={"overtime_near_limit:P204@2027-01-11", "overtime_limit:P204@2027-01-11"})) == []


def test_above_the_limit_only_the_limit_fires():
    """Varredura que chega direto acima do limite: só o `overtime_limit` (o aviso de 80% fica superado)."""
    assert [t.kind for t in overtime(run(datetime(2027, 1, 16, 9, 0)))] == ["overtime_limit"]


def test_open_shift_without_out_punch_does_not_count():
    punches = [p for p in _punches() if not (p.kind == "out" and p.shift_start.day == 14)]
    assert overtime(run(datetime(2027, 1, 14, 23, 0), punches=punches)) == []


def test_weeks_are_counted_separately():
    """A segunda seguinte abre outra semana: as horas de seg a qui (300 min) não se somam às da semana nova."""
    next_week = Shift(employee_id="P204", store_id="L2", start=datetime(2027, 1, 18, 8), end=datetime(2027, 1, 18, 16))
    shifts = [*SHIFTS[:4], next_week]
    schedule = Schedule(week_start=date(2027, 1, 11), shifts=shifts)
    triggers = overtime(run(datetime(2027, 1, 18, 23, 0), punches=_punches(shifts=shifts), schedule=schedule))
    assert [(t.kind, t.ref) for t in triggers] == [("overtime_near_limit", "P204@2027-01-11")]


def test_late_arrival_reduces_overtime():
    """Hora extra = tempo batido além da duração do turno: quem entrou 30 min atrasado e saiu 60 min depois fez 30."""
    shift = SHIFTS[0]
    punches = [
        Punch(employee_id="P204", shift_start=shift.start, kind="in", at=shift.start + timedelta(minutes=30)),
        Punch(employee_id="P204", shift_start=shift.start, kind="out", at=shift.end + timedelta(minutes=60)),
    ]
    assert overtime_minutes(SCHEDULE, punches, "P204", date(2027, 1, 11), datetime(2027, 1, 12)) == 30
