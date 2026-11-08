"""Efeitos da hora extra no varredor (C7 T2, RF-27; DEC-060): 80% avisa o gestor; acima do limite avisa colaborador e
gestor e abre o cartão HORA_EXTRA. Nada muda na escala sem o gestor."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from escalista.domain.contracts import Role
from escalista.domain.schedule import Schedule, Shift
from escalista.domain.tracking import Punch
from tests.agents.tracker.conftest import Env, build_env
from tests.fakes import FakePunchSource

# "C" (sintético) faz 08–16h de seg 11/01 a sex 15/01 e sai mais tarde: 90, 90, 60, 60, 75 min.
EXTRA = [90, 90, 60, 60, 75]
SHIFTS = [
    Shift(employee_id="C", store_id="L1", start=datetime(2027, 1, 11 + d, 8), end=datetime(2027, 1, 11 + d, 16))
    for d in range(5)
]
SCHEDULE = Schedule(week_start=date(2027, 1, 11), shifts=SHIFTS)
NEAR = datetime(2027, 1, 14, 17, 0)
LIMIT = datetime(2027, 1, 15, 17, 15)
REF = "C@2027-01-11"


def _punches() -> list[Punch]:
    out = []
    for shift, minutes in zip(SHIFTS, EXTRA, strict=True):
        out.append(Punch(employee_id="C", shift_start=shift.start, kind="in", at=shift.start))
        out.append(
            Punch(employee_id="C", shift_start=shift.start, kind="out", at=shift.end + timedelta(minutes=minutes))
        )
    return out


def _env() -> Env:
    return build_env(schedule=SCHEDULE, punches=FakePunchSource(_punches()))


def _decide(env: Env, option: int) -> str:
    return env.tracker.on_decision(
        case_id=None, code="HORA_EXTRA", option_index=option, approver_id="demo-gestor", role=Role.GESTOR
    )


def test_near_limit_warns_only_the_manager_once():
    env = _env()
    assert env.tracker.run_sweep(NEAR - timedelta(minutes=1)).triggers == []
    result = env.tracker.run_sweep(NEAR)
    assert [(t.kind, t.ref) for t in result.triggers] == [("overtime_near_limit", REF)]
    fired = env.events("track.trigger.fired")
    assert len(fired) == 1 and fired[0].run_id == "track-sweep"
    assert fired[0].rule_ref == "pol_aviso_hora_extra_estourando"
    assert fired[0].payload["trigger"] == "overtime_near_limit" and fired[0].payload["ref"] == REF
    [message] = env.channel.sent
    assert (message.party, message.template, message.case_id) == ("gestor", "hora_extra_80", None)
    assert message.decision_ref == fired[0].id
    assert "5h de hora extra" in message.body
    sent = env.events("track.message.sent")
    assert sent[0].payload == {
        "case_id": None,
        "message_id": message.id,
        "to": "gestor",
        "template": "hora_extra_80",
        "cost_basis": sent[0].payload["cost_basis"],
    }
    assert env.channel.inbox("C") == [] and env.queue.items == []
    assert [e.kind for e in result.events] == ["track.trigger.fired", "track.message.sent"]
    # idempotente: a mesma semana não volta a avisar
    assert env.tracker.run_sweep(NEAR + timedelta(minutes=30)).triggers == []
    assert len(env.channel.sent) == 1


def test_limit_warns_both_and_opens_the_card():
    env = _env()
    env.tracker.run_sweep(NEAR)
    assert env.tracker.run_sweep(LIMIT - timedelta(minutes=1)).triggers == []
    result = env.tracker.run_sweep(LIMIT)
    assert [(t.kind, t.ref) for t in result.triggers] == [("overtime_limit", REF)]
    limit_msgs = [m for m in env.channel.sent if m.template == "hora_extra_limite"]
    assert [m.party for m in limit_msgs] == ["C", "gestor"]
    assert "6h15 de hora extra" in limit_msgs[0].body and "6h15 de hora extra" in limit_msgs[1].body
    [(item_id, card, source)] = env.queue.items
    assert card.code == "HORA_EXTRA"
    assert card.title == "Hora extra acima do limite da política"
    assert card.decider == Role.GESTOR and card.deadline == LIMIT + timedelta(hours=24)
    assert [o.label for o in card.options] == [
        "Compensar no banco de horas",
        "Pedir replanejamento dos próximos turnos",
        "Só registrar",
    ]
    assert source == {"kind": "track", "case_id": None, "run_id": "track-sweep", "employee_id": "C", "ref": REF}
    raised = env.events("exception.raised")
    assert raised[-1].payload["exception_id"] == item_id and raised[-1].payload["code"] == "HORA_EXTRA"
    assert raised[-1].run_id == "track-sweep"
    assert env.tracker.run_sweep(LIMIT + timedelta(hours=1)).triggers == []
    assert len(env.queue.items) == 1


def test_replan_option_records_the_request_and_changes_nothing():
    env = _env()
    env.clock.advance(LIMIT - env.clock.now())
    env.tracker.run_sweep()
    before = env.repo.latest_published()
    text = _decide(env, 1)
    [requested] = env.events("track.replan.requested")
    assert requested.run_id == "track-sweep"
    payload = requested.payload
    assert payload["reason"] == "overtime_limit" and payload["absent_id"] == "C" and payload["case_id"] is None
    assert payload["window_start"] == LIMIT.isoformat()
    assert payload["window_end"] == datetime(2027, 1, 18).isoformat()
    assert payload["replan_id"].startswith("rp-")
    assert "replanejamento" in text
    assert env.repo.latest_published() == before


def test_compensate_and_record_only_register():
    for option in (0, 2):
        env = _env()
        env.tracker.run_sweep(LIMIT)
        before = env.repo.latest_published()
        text = _decide(env, option)
        assert env.events("track.replan.requested") == []
        assert env.repo.latest_published() == before
        assert text


def test_replan_uses_the_card_source_when_given():
    env = _env()
    env.tracker.run_sweep(LIMIT)
    _, _, source = env.queue.items[0]
    env.tracker.on_decision(
        case_id=None,
        code="HORA_EXTRA",
        option_index=1,
        approver_id="demo-gestor",
        role=Role.GESTOR,
        source={**source, "employee_id": "D", "ref": "D@2027-01-11"},
    )
    assert env.events("track.replan.requested")[0].payload["absent_id"] == "D"


def test_after_the_demo_reset_the_warning_fires_again():
    """O "Reiniciar" apaga as mensagens do canal: a chave tratada sai junto e o aviso volta a disparar."""
    env = _env()
    env.tracker.run_sweep(NEAR)
    env.channel.messages.clear()
    assert [t.kind for t in env.tracker.run_sweep(NEAR).triggers] == ["overtime_near_limit"]


def test_without_punch_source_no_overtime():
    env = build_env(schedule=SCHEDULE)
    assert env.tracker.run_sweep(LIMIT).triggers == []


def test_real_scenario_nelson_80_on_thursday_and_limit_on_friday():
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

    def overtime(at: datetime) -> list[tuple[str, str]]:
        return [(t.kind, t.ref) for t in env.tracker.run_sweep(at).triggers if t.kind.startswith("overtime_")]

    assert overtime(datetime(2027, 1, 14, 16, 59)) == []
    assert overtime(datetime(2027, 1, 14, 17, 0)) == [("overtime_near_limit", "P204@2027-01-11")]
    assert overtime(datetime(2027, 1, 15, 17, 14)) == []
    assert overtime(datetime(2027, 1, 15, 17, 15)) == [("overtime_limit", "P204@2027-01-11")]
    assert "HORA_EXTRA" in env.queue.codes()
    assert [m.template for m in env.channel.inbox("P204")] == ["hora_extra_limite"]
    assert "Nelson" in env.channel.inbox("gestor")[-1].body


def test_message_without_case_only_to_the_trigger_person_or_manager():
    import pytest

    from escalista.agents.tracker.tools import enviar_sem_caso
    from escalista.domain.tracking import ToolRefusedError

    env = _env()
    with pytest.raises(ToolRefusedError):
        enviar_sem_caso(
            channel=env.channel,
            tracer=env.tracker._tracer,
            run_id="track-sweep",
            employee_id="C",
            to="D",
            template="hora_extra_limite",
            body="x",
            decision_ref="ev",
            new_id=lambda: "m1",
        )
    assert env.channel.sent == []
    [refused] = env.events("track.tool.refused")
    assert refused.payload["case_id"] is None and refused.run_id == "track-sweep"
