"""Varredura aplicada pelo `Tracker`, resposta à pergunta do agente e RF-28 sem candidato (C7 B4; SAIDA-AC-06)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from escalista.agents.cover import CoverCandidate
from escalista.agents.tracker.flow import TrackerError
from escalista.domain.contracts import Role
from escalista.domain.schedule import Schedule
from escalista.domain.tracking import Punch
from tests.agents.test_cover import EMPLOYEES, SCHEDULE
from tests.agents.tracker.conftest import Env, build_env
from tests.fakes import FakePunchSource

START = datetime(2027, 1, 13, 14, 0)  # turno de A na quarta, 14–22h
MISSING = ("A", START)


def _punches(schedule: Schedule = SCHEDULE, missing: tuple[str, datetime] = MISSING) -> list[Punch]:
    """Todo mundo bate o ponto no início e no fim, menos o turno `missing`."""
    out = []
    for s in schedule.shifts:
        if (s.employee_id, s.start) == missing:
            continue
        out.append(Punch(employee_id=s.employee_id, shift_start=s.start, kind="in", at=s.start))
        out.append(Punch(employee_id=s.employee_id, shift_start=s.start, kind="out", at=s.end))
    return out


def _fake_cover(ids: list[str]):
    def cover(schedule, shift, employees, card):
        by_id = {e.id: e for e in employees}
        return len(ids), [
            CoverCandidate(employee=by_id[i], schedule=schedule, added_cost=Decimal("80.00"), overtime_hours=Decimal(0))
            for i in ids
        ]

    return cover


def _env(**kw) -> Env:
    kw.setdefault("punches", FakePunchSource(_punches()))
    return build_env(**kw)


def _at(minutes: int) -> datetime:
    return START + timedelta(minutes=minutes)


def _decide(env: Env, case_id: str, code: str, option: int) -> str:
    return env.tracker.on_decision(
        case_id=case_id, code=code, option_index=option, approver_id="demo-gestor", role=Role.GESTOR
    )


def _open_by_punch(env: Env) -> str:
    result = env.tracker.run_sweep(_at(10))
    assert [t.kind for t in result.triggers] == ["no_punch"]
    return env.cases.list_cases()[0].id


# --- no_punch e pergunta -----------------------------------------------------------------------------------------


def test_no_punch_fires_at_tolerance_and_not_before():
    env = _env()
    assert env.tracker.run_sweep(_at(9)).triggers == []
    assert env.cases.list_cases() == []
    result = env.tracker.run_sweep(_at(10))
    assert [(t.kind, t.employee_id, t.ref) for t in result.triggers] == [("no_punch", "A", f"A@{START.isoformat()}")]
    (case,) = env.cases.list_cases()
    assert (case.origin, case.kind, case.status, case.asked_at) == ("ponto", "falta", "aguardando_colaborador", _at(10))
    assert result.triggers[0].key in case.handled
    question = env.channel.inbox("A")[-1]
    assert question.template == "pergunta" and "não bateu o ponto às 14:00" in question.body
    assert [e.kind for e in result.events] == ["track.trigger.fired", "track.message.sent"]
    fired = result.events[0]
    assert fired.run_id == case.run_id and fired.rule_ref == "pol_atraso" and fired.payload["trigger"] == "no_punch"
    assert result.at == _at(10)


def test_sweep_is_idempotent_at_the_same_instant():
    env = _env()
    env.tracker.run_sweep(_at(10))
    again = env.tracker.run_sweep(_at(10))
    assert again.triggers == [] and again.events == []
    assert len(env.cases.list_cases()) == 1 and len(env.channel.sent) == 1


def test_sweep_uses_the_clock_when_now_is_omitted():
    env = _env()
    env.clock.set(_at(10))
    assert [t.kind for t in env.tracker.run_sweep().triggers] == ["no_punch"]


def test_no_answer_opens_rx09_at_deadline_and_not_before():
    env = _env()
    case_id = _open_by_punch(env)
    assert env.tracker.run_sweep(_at(24)).triggers == []
    result = env.tracker.run_sweep(_at(25))
    assert [t.kind for t in result.triggers] == ["no_answer"]
    assert env.queue.codes() == ["RX-09"]
    _, card, source = env.queue.items[0]
    assert source["case_id"] == case_id and "A (sintético)" in card.title
    assert env.tracker.case(case_id).status == "aguardando_gestor"
    assert env.tracker.run_sweep(_at(40)).triggers == []


def test_rx09_option_0_starts_the_offers():
    env = _env()
    case_id = _open_by_punch(env)
    env.tracker.run_sweep(_at(25))
    env.clock.set(_at(26))
    _decide(env, case_id, "RX-09", 0)
    view = env.tracker.case(case_id)
    assert view.status == "oferta_enviada" and view.offers[0].candidate_id == "C"


def test_rx09_wait_restarts_the_answer_deadline():
    env = _env()
    case_id = _open_by_punch(env)
    env.tracker.run_sweep(_at(25))
    env.clock.set(_at(26))
    _decide(env, case_id, "RX-09", 1)
    assert env.tracker.case(case_id).status == "aguardando_colaborador"
    assert env.tracker.run_sweep(_at(40)).triggers == []
    assert [t.kind for t in env.tracker.run_sweep(_at(41)).triggers] == ["no_answer"]
    assert env.queue.codes() == ["RX-09", "RX-09"]


# --- resposta do colaborador -------------------------------------------------------------------------------------


def test_answer_coming_registers_the_delay():
    env = _env()
    case_id = _open_by_punch(env)
    view = env.tracker.answer(case_id=case_id, employee_id="A", coming=True)
    assert view.status == "atraso_registrado" and view.kind == "atraso"
    assert env.channel.inbox("gestor")[-1].template == "atraso_aviso"
    assert env.events("track.case.closed")[-1].payload["outcome"] == "atraso_registrado"
    assert env.tracker.run_sweep(_at(30)).triggers == []  # sem no_answer depois da resposta


def test_answer_not_coming_starts_the_replan():
    env = _env()
    case_id = _open_by_punch(env)
    view = env.tracker.answer(case_id=case_id, employee_id="A", coming=False)
    assert view.status == "oferta_enviada" and view.offers[0].candidate_id == "C"
    assert env.events("track.replan.requested")[-1].payload["reason"] == "falta"


def test_answer_errors():
    env = _env()
    case_id = _open_by_punch(env)
    with pytest.raises(TrackerError) as other:
        env.tracker.answer(case_id=case_id, employee_id="C", coming=True)
    assert other.value.status == 403
    assert env.events("track.tool.refused")[-1].payload == {
        "tool": "answer",
        "reason": "quem respondeu não é o colaborador do caso",
        "case_id": case_id,
        "cost_basis": "sem chamada de modelo",
    }
    env.tracker.answer(case_id=case_id, employee_id="A", coming=True)
    with pytest.raises(TrackerError) as twice:
        env.tracker.answer(case_id=case_id, employee_id="A", coming=False)
    assert twice.value.status == 409
    with pytest.raises(TrackerError) as missing:
        env.tracker.answer(case_id="nope", employee_id="A", coming=False)
    assert missing.value.status == 404


# --- ofertas vencendo --------------------------------------------------------------------------------------------


def test_offers_expire_every_20_min_until_rx06_at_first_offer_plus_60():
    env = _env(cover_fn=_fake_cover(["B", "C", "D", "E"]))
    view = env.tracker.report(employee_id="A", day=date(2027, 1, 13), kind="falta")
    t0 = view.offers[0].deadline - timedelta(minutes=20)

    def sweep(minutes: int) -> list[str]:
        env.clock.set(t0 + timedelta(minutes=minutes))
        return [t.kind for t in env.tracker.run_sweep().triggers if t.kind == "offer_expired"]

    assert sweep(19) == []
    assert sweep(20) == ["offer_expired"]
    assert sweep(20) == []  # idempotente
    assert sweep(40) == ["offer_expired"]
    assert sweep(59) == []
    assert env.queue.codes() == []
    assert sweep(60) == ["offer_expired"]
    view = env.tracker.case(view.case_id)
    assert [(o.rank, o.candidate_id, o.status) for o in view.offers] == [
        (1, "B", "vencida"),
        (2, "C", "vencida"),
        (3, "D", "vencida"),
    ]
    assert view.status == "aguardando_gestor" and env.queue.codes() == ["RX-06"]
    assert len(env.events("track.offer.expired")) == 3


# --- ponto fora --------------------------------------------------------------------------------------------------


def test_punch_source_down_records_failure_and_rx12_once():
    env = _env(punches=FakePunchSource(fail=True))
    first = env.tracker.run_sweep(_at(10))
    assert first.triggers == []
    assert [e.kind for e in first.events] == ["track.sweep.failed", "exception.raised"]
    assert first.events[0].run_id == "track-sweep" and first.events[0].payload["reason"] == "PunchUnavailableError"
    second = env.tracker.run_sweep(_at(25))
    assert [e.kind for e in second.events] == ["track.sweep.failed"]
    assert env.queue.codes() == ["RX-12"] and env.queue.items[0][2]["case_id"] is None
    assert env.cases.list_cases() == []
    assert "Decisão registrada" in env.tracker.on_decision(
        case_id=None, code="RX-12", option_index=0, approver_id="g", role=Role.GESTOR
    )


def test_without_punch_source_only_case_triggers_run():
    env = build_env()
    assert env.tracker.run_sweep(_at(10)).triggers == []


def test_no_published_schedule_sweeps_nothing():
    env = _env()
    env.repo.published_at.clear()
    assert env.tracker.run_sweep(_at(10)).triggers == []


# --- RF-28 -------------------------------------------------------------------------------------------------------


def test_rf28_fires_when_no_candidate_within_rules():
    only_blocked = [e for e in EMPLOYEES if e.id in {"A", "B", "E"}]
    schedule = Schedule(
        week_start=SCHEDULE.week_start, shifts=[s for s in SCHEDULE.shifts if s.employee_id in {"A", "B", "E"}]
    )
    env = build_env(employees=only_blocked, schedule=schedule)
    env.tracker.report(employee_id="A", day=date(2027, 1, 13), kind="falta")
    assert env.events("track.cover.searched")[0].payload["overtime_needed"] is True
    (fired,) = env.events("track.trigger.fired")
    assert fired.payload["trigger"] == "overtime_needed" and fired.payload["employee_id"] is None
    assert fired.rule_ref == "pol_aviso_necessidade_hora_extra"
    (warning,) = env.channel.inbox("gestor")
    assert warning.template == "aviso_hora_extra" and "nenhum colega cobre dentro das regras" in warning.body
    assert env.queue.codes() == ["RX-05"]


def test_rf28_still_fires_when_first_candidate_needs_overtime():
    def cover(schedule, shift, employees, card):
        by_id = {e.id: e for e in employees}
        return 1, [CoverCandidate(by_id["C"], schedule, Decimal("120.00"), Decimal("2.00"))]

    env = build_env(cover_fn=cover)
    env.tracker.report(employee_id="A", day=date(2027, 1, 13), kind="falta")
    (fired,) = env.events("track.trigger.fired")
    assert fired.payload["employee_id"] == "C"
    assert "2h extra do 1º da lista" in env.channel.inbox("gestor")[0].body


# --- cenário sintético real --------------------------------------------------------------------------------------


def test_real_scenario_carla_no_punch_at_14_10():
    from escalista.rules.tracking_policy import load_track_policy
    from escalista.synth.acompanhamento import montar_rede
    from escalista.synth.ponto import SimulatedPunchSource, load_deviations

    _, employees, schedule = montar_rede(42)
    deviations = load_deviations(Path("data/demo/acompanhamento/ponto_desvios.json"))
    raw = yaml.safe_load(Path("data/regras/politica/politica_ficticia.yaml").read_text(encoding="utf-8"))
    env = build_env(
        employees=employees,
        schedule=schedule,
        punches=SimulatedPunchSource(lambda: schedule, deviations),
        policy=load_track_policy(),
        policy_cards={e["code"]: e for e in raw["excecoes_demo"]},
    )
    assert env.tracker.run_sweep(datetime(2027, 1, 13, 14, 9)).triggers == []
    result = env.tracker.run_sweep(datetime(2027, 1, 13, 14, 10))
    assert [(t.kind, t.ref) for t in result.triggers] == [("no_punch", "P102@2027-01-13T14:00:00")]
    assert "não bateu o ponto às 14:00" in env.channel.inbox("P102")[-1].body
    assert env.tracker.run_sweep(datetime(2027, 1, 13, 14, 24)).triggers == []
    no_answer = env.tracker.run_sweep(datetime(2027, 1, 13, 14, 25))
    assert [t.kind for t in no_answer.triggers] == ["no_answer"] and env.queue.codes() == ["RX-09"]
    case_id = env.cases.list_cases()[0].id
    _decide(env, case_id, "RX-09", 0)
    assert env.tracker.case(case_id).status in {"oferta_enviada", "aguardando_gestor"}
