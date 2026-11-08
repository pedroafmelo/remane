"""Fluxo do acompanhamento com falsos (FT-03; plano da C7, tarefa B2; SAIDA-AC-03, 04, 07, 09, 16, 18)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from escalista.agents.cover import CoverCandidate
from escalista.agents.tracker.flow import TrackerError
from escalista.agents.tracker.tools import aplicar_cobertura, enviar
from escalista.domain.contracts import ExceptionCard, LLMUnavailableError, Role
from escalista.domain.schedule import Schedule
from escalista.domain.tracking import AtestadoReading, Attachment, ToolRefusedError
from tests.agents.test_cover import EMPLOYEES, SCHEDULE
from tests.agents.tracker.conftest import Env, build_env

WED = date(2027, 1, 13)
PDF = Attachment(data=b"%PDF-1.4 sintetico", media_type="application/pdf", filename="at.pdf")


def _report(env: Env, **kw):
    return env.tracker.report(employee_id="A", day=WED, kind="falta", **kw)


def _accept_first(env: Env):
    view = _report(env)
    return env.tracker.respond_offer(offer_id=view.offers[0].offer_id, employee_id="C", accept=True)


def _decide(env: Env, view, code: str, option: int) -> str:
    return env.tracker.on_decision(
        case_id=view.case_id, code=code, option_index=option, approver_id="demo-gestor", role=Role.GESTOR
    )


# --- falta e oferta -------------------------------------------------------------------------------------------


def test_falta_sends_rank_1_offer_without_overtime(env: Env):
    view = _report(env)
    assert view.status == "oferta_enviada"
    assert [(o.rank, o.candidate_id, o.status) for o in view.offers] == [(1, "C", "enviada")]
    assert view.offers[0].deadline == env.clock.now() + timedelta(minutes=20)
    case = env.cases.get_case(view.case_id)
    assert case.ranked == ["C", "D"] and case.offers[0].overtime_hours == 0
    run = f"track-{view.case_id}"
    assert env.kinds(run) == [
        "track.report.received",
        "track.message.sent",
        "track.replan.requested",
        "track.cover.searched",
        "track.offer.sent",
        "track.message.sent",
    ]
    searched = env.events("track.cover.searched")[0].payload
    assert (searched["evaluated"], searched["eligible"], searched["ranked"]) == (4, 2, ["C", "D"])
    assert searched["overtime_needed"] is False
    offer_msg = env.channel.inbox("C")[0]
    assert offer_msg.template == "oferta" and "qua 13/01, 14–22h" in offer_msg.body
    assert "Sem hora extra" in offer_msg.body


def test_messages_point_to_the_event_that_generated_them(env: Env):
    _report(env)
    by_id = {e.id: e for e in env.sink.events}
    sent = env.events("track.message.sent")
    assert len(sent) == len(env.channel.sent) == 2
    for msg, event in zip(env.channel.sent, sent, strict=True):
        assert msg.decision_ref in by_id
        assert event.parent_id == msg.decision_ref
        assert event.payload == {
            "case_id": msg.case_id,
            "message_id": msg.id,
            "to": msg.party,
            "template": msg.template,
            "cost_basis": "sem chamada de modelo",
        }


def test_report_errors(env: Env):
    with pytest.raises(TrackerError) as no_shift:
        env.tracker.report(employee_id="A", day=date(2027, 1, 16), kind="falta")
    assert no_shift.value.status == 422
    _report(env)
    with pytest.raises(TrackerError) as dup:
        _report(env)
    assert dup.value.status == 409


def test_report_without_published_schedule_is_409(env: Env):
    env.repo.published_at.clear()
    with pytest.raises(TrackerError) as exc:
        _report(env)
    assert exc.value.status == 409


def test_decline_goes_to_rank_2(env: Env):
    view = _report(env)
    view = env.tracker.respond_offer(offer_id=view.offers[0].offer_id, employee_id="C", accept=False)
    assert [(o.rank, o.candidate_id, o.status) for o in view.offers] == [(1, "C", "recusada"), (2, "D", "enviada")]
    assert view.status == "oferta_enviada"
    assert "track.offer.declined" in env.kinds()


# --- aceite e validação ----------------------------------------------------------------------------------------


def test_accept_opens_cobertura_card(env: Env):
    view = _accept_first(env)
    assert view.status == "aguardando_gestor"
    item_id, card, source = env.queue.items[-1]
    assert card.code == "COBERTURA" and source["kind"] == "track" and source["case_id"] == view.case_id
    assert card.title == "Cobertura: C (sintético) aceitou · qua 13/01, 14–22h"
    assert [o.label for o in card.options] == [
        "Validar: C (sintético) cobre · sem hora extra · +R$ 96,00",
        "Recusar e oferecer ao próximo",
        "Deixar o turno descoberto",
    ]
    assert card.deadline == env.clock.now() + timedelta(minutes=30)
    assert card.decider == Role.GESTOR
    assert any("Avaliados 4" in e and "aprovou 2" in e for e in card.evidence)
    assert any("R$ 96,00" in e for e in card.evidence)
    assert card.recommendation.startswith(card.options[0].label)
    assert view.exception_ids == [item_id]
    assert env.channel.inbox("C")[-1].template == "aceite_recebido"
    assert env.repo.latest_published().id == "ver-base"  # nada muda sem o gestor


def test_validation_republishes_and_closes(env: Env):
    view = _accept_first(env)
    env.clock.advance(timedelta(minutes=7))
    result = _decide(env, view, "COBERTURA", 0)
    assert "republicada" in result
    published = env.repo.latest_published()
    assert published.id != "ver-base" and published.status == "published"
    shift = env.cases.get_case(view.case_id).shift
    assert shift.model_copy(update={"employee_id": "C"}) in published.schedule.shifts
    assert shift not in published.schedule.shifts
    assert env.repo.get_approval(published.id).approved_by == "demo-gestor"
    closed = env.events("track.case.closed")[-1].payload
    assert closed["outcome"] == "coberta" and closed["new_violations"] == 0
    assert closed["minutes_to_close"] == 7 and closed["overtime_hours_added"] == "0.00"
    assert env.tracker.case(view.case_id).status == "coberto"
    assert len(env.channel.sent) >= 4
    assert {m.template for m in env.channel.sent} >= {"recebido", "oferta", "cobertura_confirmada", "falta_coberta"}
    run = f"track-{view.case_id}"
    kinds = env.kinds(run)
    assert kinds.index("approval.recorded") < kinds.index("schedule.republished") < kinds.index("track.case.closed")
    assert kinds[-1] == "track.case.closed"
    assert "schedule.publish" in env.kinds("run-base")


def test_cobertura_option_1_offers_next(env: Env):
    view = _accept_first(env)
    _decide(env, view, "COBERTURA", 1)
    after = env.tracker.case(view.case_id)
    assert [(o.candidate_id, o.status) for o in after.offers] == [("C", "recusada"), ("D", "enviada")]
    assert after.status == "oferta_enviada"


def test_cobertura_option_2_leaves_uncovered(env: Env):
    view = _accept_first(env)
    _decide(env, view, "COBERTURA", 2)
    assert env.tracker.case(view.case_id).status == "descoberto"
    assert env.events("track.case.closed")[-1].payload["outcome"] == "descoberta"
    assert env.repo.latest_published().id == "ver-base"


def test_cobertura_when_schedule_changed_is_409(env: Env):
    view = _accept_first(env)
    base = env.repo.get_version("ver-base")
    other = base.model_copy(
        update={"id": "ver-other", "schedule": Schedule(week_start=base.schedule.week_start, shifts=[])}
    )
    env.repo.save_version(other)
    env.repo.mark_published("ver-other", env.clock.advance(timedelta(minutes=1)))
    with pytest.raises(TrackerError) as exc:
        _decide(env, view, "COBERTURA", 0)
    assert exc.value.status == 409


# --- portões ---------------------------------------------------------------------------------------------------


def test_aplicar_cobertura_without_approval_is_refused(env: Env):
    view = _accept_first(env)
    case = env.cases.get_case(view.case_id)
    draft = env.repo.get_version("ver-base").model_copy(update={"id": "ver-draft", "status": "draft"})
    env.repo.save_version(draft)
    with pytest.raises(ToolRefusedError):
        aplicar_cobertura(repo=env.repo, tracer=env.tracker._tracer, case=case, version_id="ver-draft")
    refused = env.events("track.tool.refused")[-1].payload
    assert refused["tool"] == "aplicar_cobertura" and refused["case_id"] == case.id
    assert env.repo.latest_published().id == "ver-base"


def test_aplicar_cobertura_without_accepted_offer_is_refused(env: Env):
    view = _report(env)
    case = env.cases.get_case(view.case_id)
    with pytest.raises(ToolRefusedError):
        aplicar_cobertura(repo=env.repo, tracer=env.tracker._tracer, case=case, version_id="ver-base")
    assert env.events("track.tool.refused")[-1].payload["tool"] == "aplicar_cobertura"
    assert env.repo.latest_published().id == "ver-base"


def test_respond_offer_by_someone_else_is_403_and_refused(env: Env):
    view = _report(env)
    with pytest.raises(TrackerError) as exc:
        env.tracker.respond_offer(offer_id=view.offers[0].offer_id, employee_id="D", accept=True)
    assert exc.value.status == 403
    refused = env.events("track.tool.refused")[-1].payload
    assert refused["tool"] == "respond_offer" and refused["case_id"] == view.case_id
    assert env.tracker.case(view.case_id).offers[0].status == "enviada"


def test_respond_offer_errors(env: Env):
    with pytest.raises(TrackerError) as missing:
        env.tracker.respond_offer(offer_id="nope", employee_id="C", accept=True)
    assert missing.value.status == 404
    view = _accept_first(env)
    with pytest.raises(TrackerError) as twice:
        env.tracker.respond_offer(offer_id=view.offers[0].offer_id, employee_id="C", accept=True)
    assert twice.value.status == 409


def test_enviar_refuses_party_outside_the_case(env: Env):
    view = _report(env)
    case = env.cases.get_case(view.case_id)
    with pytest.raises(ToolRefusedError):
        enviar(
            channel=env.channel,
            tracer=env.tracker._tracer,
            case=case,
            to="F",
            template="oferta",
            body="x",
            decision_ref="id0001",
            new_id=lambda: "m",
        )
    assert env.events("track.tool.refused")[-1].payload["tool"] == "enviar"
    assert env.channel.inbox("F") == []


def test_validation_by_colaborador_role_is_403(env: Env):
    view = _accept_first(env)
    with pytest.raises(TrackerError) as exc:
        env.tracker.on_decision(
            case_id=view.case_id, code="COBERTURA", option_index=0, approver_id="x", role=Role.COLABORADOR
        )
    assert exc.value.status == 403
    assert env.repo.latest_published().id == "ver-base"


# --- exceções --------------------------------------------------------------------------------------------------


def test_no_candidate_opens_rx05_and_uncovered_option_closes():
    only_blocked = [e for e in EMPLOYEES if e.id in {"A", "B", "E"}]
    schedule = Schedule(
        week_start=SCHEDULE.week_start, shifts=[s for s in SCHEDULE.shifts if s.employee_id in {"A", "B", "E"}]
    )
    env = build_env(employees=only_blocked, schedule=schedule)
    view = _report(env)
    assert view.status == "aguardando_gestor" and view.offers == []
    _, card, _ = env.queue.items[-1]
    assert card.code == "RX-05" and "A (sintético)" in card.title
    assert any("Avaliados 2" in e for e in card.evidence)
    _decide(env, view, "RX-05", 2)
    assert env.tracker.case(view.case_id).status == "descoberto"


def test_rx05_other_option_is_just_registered():
    only_blocked = [e for e in EMPLOYEES if e.id in {"A", "B", "E"}]
    schedule = Schedule(
        week_start=SCHEDULE.week_start, shifts=[s for s in SCHEDULE.shifts if s.employee_id in {"A", "B", "E"}]
    )
    env = build_env(employees=only_blocked, schedule=schedule)
    view = _report(env)
    _decide(env, view, "RX-05", 0)
    assert env.tracker.case(view.case_id).status == "decidido"
    assert env.events("track.case.closed")[-1].payload["outcome"] == "decidida"


def _fake_cover(ids: list[str], overtime: str = "0"):
    def cover(schedule, shift, employees, card):
        by_id = {e.id: e for e in employees}
        return len(ids), [
            CoverCandidate(
                employee=by_id[i], schedule=schedule, added_cost=Decimal("80.00"), overtime_hours=Decimal(overtime)
            )
            for i in ids
        ]

    return cover


def test_three_declines_open_rx06():
    env = build_env(cover_fn=_fake_cover(["B", "C", "D", "E"]))
    view = _report(env)
    for expected in ["B", "C", "D"]:
        offer = view.offers[-1]
        assert offer.candidate_id == expected
        view = env.tracker.respond_offer(offer_id=offer.offer_id, employee_id=expected, accept=False)
    assert [o.rank for o in view.offers] == [1, 2, 3]
    assert view.status == "aguardando_gestor"
    assert env.queue.codes() == ["RX-06"]


def test_advance_offer_expires_and_ends_in_rx06_when_list_runs_out(env: Env):
    view = _report(env)
    env.clock.advance(timedelta(minutes=20))
    view = env.tracker.advance_offer(env.cases.get_case(view.case_id))
    assert [(o.candidate_id, o.status) for o in view.offers] == [("C", "vencida"), ("D", "enviada")]
    assert env.events("track.offer.expired")[-1].payload["candidate_id"] == "C"
    view = env.tracker.advance_offer(view.case_id)
    assert view.status == "aguardando_gestor" and env.queue.codes() == ["RX-06"]
    _decide(env, view, "RX-06", 2)
    assert env.tracker.case(view.case_id).status == "descoberto"


def test_advance_offer_does_nothing_after_accept(env: Env):
    view = _accept_first(env)
    after = env.tracker.advance_offer(view.case_id)
    assert after == view and "track.offer.expired" not in env.kinds()


def test_advance_offer_recomputes_search_after_restart(env: Env):
    view = _report(env)
    env.tracker._searches.clear()  # processo reiniciado: só as tabelas
    view = env.tracker.advance_offer(view.case_id)
    assert view.offers[-1].candidate_id == "D" and view.offers[-1].rank == 2


def test_overtime_needed_warns_gestor():
    env = build_env(cover_fn=_fake_cover(["C"], overtime="2.00"))
    view = _report(env)
    fired = env.events("track.trigger.fired")
    assert len(fired) == 1 and fired[0].rule_ref == "pol_aviso_necessidade_hora_extra"
    assert fired[0].payload["trigger"] == "overtime_needed" and fired[0].payload["employee_id"] == "C"
    assert env.events("track.cover.searched")[0].payload["overtime_needed"] is True
    gestor = env.channel.inbox("gestor")
    assert [m.template for m in gestor] == ["aviso_hora_extra"] and "2h extra" in gestor[0].body
    assert "2h extra" in env.channel.inbox("C")[0].body
    assert view.status == "oferta_enviada"


def test_cover_failure_opens_rx12_and_retry_offers():
    calls = {"n": 0}
    real = _fake_cover(["C"])

    def flaky(*args):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("busca fora")
        return real(*args)

    env = build_env(cover_fn=flaky)
    view = _report(env)
    assert view.status == "aguardando_gestor" and env.queue.codes() == ["RX-12"]
    assert env.queue.items[0][1].title.startswith("Busca de cobertura indisponível")
    _decide(env, view, "RX-12", 0)
    assert env.tracker.case(view.case_id).status == "oferta_enviada"


# --- comprovação -----------------------------------------------------------------------------------------------


class _Reader:
    def __init__(self, reading: AtestadoReading | None = None, fail: bool = False) -> None:
        self.reading, self.fail, self.calls = reading, fail, []

    def __call__(self, *, data, media_type, run_id, expected_day, employee_name):
        self.calls.append({"run_id": run_id, "expected_day": expected_day, "employee_name": employee_name})
        if self.fail:
            raise LLMUnavailableError(ExceptionCard(code="RX-12", title="Modelo indisponível", reason="falha simulada"))
        return self.reading


def test_reader_unavailable_opens_rx12_and_offer_still_goes_out():
    env = build_env(reader=_Reader(fail=True))
    view = _report(env, attachment=PDF)
    assert view.abono == "provisorio" and view.reading is None
    assert env.queue.codes() == ["RX-12"]
    assert env.queue.items[0][1].title.startswith("Leitura do atestado indisponível")
    assert [o.label for o in env.queue.items[0][1].options] == [
        "Seguir com o abono provisório",
        "Pedir o atestado de novo",
    ]
    assert view.status == "oferta_enviada" and view.offers[0].candidate_id == "C"
    assert "track.atestado.read" not in env.kinds()
    # decidir o RX-12 da leitura não mexe na oferta
    _decide(env, view, "RX-12", 1)
    assert env.tracker.case(view.case_id).status == "oferta_enviada"
    assert env.channel.inbox("A")[-1].template == "pedir_comprovacao"


def test_without_reader_attachment_also_opens_rx12():
    env = build_env()
    view = _report(env, attachment=PDF)
    assert view.abono == "provisorio" and env.queue.codes() == ["RX-12"]


def test_inconsistent_reading_opens_rx08_with_provisional_abono():
    reading = AtestadoReading(
        legible=True, issued_on=WED, start_on=date(2027, 1, 20), days=1, has_crm=True, verdict="inconsistente",
        reasons=["data_nao_bate"],
    )  # fmt: skip
    reader = _Reader(reading)
    env = build_env(reader=reader)
    view = _report(env, attachment=PDF)
    assert reader.calls == [{"run_id": f"track-{view.case_id}", "expected_day": WED, "employee_name": "A (sintético)"}]
    assert view.abono == "provisorio" and view.reading.verdict == "inconsistente"
    assert env.queue.codes() == ["RX-08"]
    read = env.events("track.atestado.read")[0].payload
    assert (
        read["verdict"] == "inconsistente" and read["reasons"] == ["data_nao_bate"] and read["start_on"] == "2027-01-20"
    )
    assert env.events("track.abono.provisional")[0].payload["days"] == 1
    assert view.status == "oferta_enviada"
    _decide(env, view, "RX-08", 1)
    assert env.channel.inbox("A")[-1].template == "pedir_comprovacao"


def test_valid_reading_opens_no_card():
    reading = AtestadoReading(legible=True, issued_on=WED, start_on=WED, days=2, has_crm=True, verdict="valido")
    env = build_env(reader=_Reader(reading))
    view = _report(env, attachment=PDF)
    assert env.queue.codes() == [] and view.reading.days == 2


def test_attach_after_report():
    reading = AtestadoReading(legible=False, verdict="ilegivel", reasons=["ilegivel"])
    env = build_env(reader=_Reader(reading))
    view = _report(env)
    view = env.tracker.attach(view.case_id, PDF)
    assert view.abono == "provisorio" and env.queue.codes() == ["RX-08"]
    evidence = " ".join(env.queue.items[0][1].evidence)
    assert "não reconhecido como atestado" in evidence and "outro tipo de documento" in evidence


def test_free_text_never_leaves_the_call():
    planted = "CID J11 dor"
    reading = AtestadoReading(legible=True, issued_on=WED, start_on=WED, days=2, has_crm=True, verdict="valido")
    env = build_env(reader=_Reader(reading))
    view = env.tracker.report(employee_id="A", day=WED, kind="falta", text=planted, attachment=PDF)
    _decide(
        env, env.tracker.respond_offer(offer_id=view.offers[0].offer_id, employee_id="C", accept=True), "COBERTURA", 0
    )
    assert env.events("track.report.received")[0].payload["has_text"] is True
    blobs = [
        json.dumps([e.model_dump(mode="json") for e in env.sink.events]),
        json.dumps([c.model_dump(mode="json") for c in env.cases.list_cases()]),
        json.dumps([m.model_dump(mode="json") for m in env.channel.messages]),
        json.dumps([card.model_dump(mode="json") for _, card, _ in env.queue.items]),
        json.dumps([v.model_dump(mode="json") for v in env.tracker.cases()]),
    ]
    for blob in blobs:
        assert planted not in blob and "J11" not in blob


def test_payloads_carry_no_person_names(env: Env):
    view = _accept_first(env)
    _decide(env, view, "COBERTURA", 0)
    names = {e.name for e in EMPLOYEES}
    for event in env.sink.events:
        dumped = json.dumps(event.payload, default=str)
        assert not any(name in dumped for name in names), event.kind


# --- atraso, RX-09, remetente ----------------------------------------------------------------------------------


def test_atraso_is_registered_without_replanning(env: Env):
    view = env.tracker.report(employee_id="A", day=WED, kind="atraso")
    assert view.status == "atraso_registrado" and view.offers == []
    assert "track.replan.requested" not in env.kinds()
    assert env.events("track.case.closed")[0].payload["outcome"] == "atraso_registrado"
    assert [m.template for m in env.channel.inbox("A")] == ["atraso_recebido"]
    assert [m.template for m in env.channel.inbox("gestor")] == ["atraso_aviso"]


def _punch_case(env: Env):
    """Caso aberto pelo ponto (o varredor de outra tarefa o abre); aqui gravado direto, como a varredura gravaria."""
    from escalista.domain.tracking import Case

    shift = next(s for s in SCHEDULE.shifts if s.employee_id == "A" and s.start.date() == WED)
    now = env.clock.now()
    case = Case(
        id="punch1", kind="atraso", origin="ponto", employee_id="A", shift=shift,
        status="aguardando_colaborador", created_at=now, asked_at=now,
    )  # fmt: skip
    env.cases.save_case(case)
    env.tracker._tracer.step(case.run_id, "track.trigger.fired", payload={"trigger": "no_punch"})
    return env.tracker.case(case.id)


def test_rx09_options(env: Env):
    view = _punch_case(env)
    env.clock.advance(timedelta(minutes=15))
    _decide(env, view, "RX-09", 1)
    case = env.cases.get_case(view.case_id)
    assert case.asked_at == env.clock.now() and env.channel.inbox("A")[-1].template == "pergunta"
    _decide(env, view, "RX-09", 0)
    after = env.tracker.case(view.case_id)
    assert after.kind == "falta" and after.status == "oferta_enviada"
    assert env.events("track.replan.requested")[-1].payload["reason"] == "no_punch"


def test_rx09_register_late(env: Env):
    view = _punch_case(env)
    _decide(env, view, "RX-09", 2)
    assert env.tracker.case(view.case_id).status == "atraso_registrado"
    with pytest.raises(TrackerError) as exc:
        _decide(env, view, "RX-09", 0)
    assert exc.value.status == 409


def test_inbound_rejects_sender_outside_roster(env: Env):
    assert env.tracker.inbound("C") is True
    assert env.tracker.inbound("+55 81 99999-0000") is False
    event = env.events("track.channel.rejected")[0]
    assert event.run_id == "track-sweep" and len(event.payload["sender_hash"]) == 12
    assert "99999" not in json.dumps(event.payload)
    assert env.cases.list_cases() == []


def test_people_cases_inbox(env: Env):
    assert [e.id for e in env.tracker.people()] == [e.id for e in EMPLOYEES]
    view = _report(env)
    assert [c.case_id for c in env.tracker.cases()] == [view.case_id]
    assert [m.template for m in env.tracker.inbox("A")] == ["recebido"]
    with pytest.raises(TrackerError) as exc:
        env.tracker.case("nope")
    assert exc.value.status == 404


def test_unknown_code_is_422(env: Env):
    view = _report(env)
    with pytest.raises(TrackerError) as exc:
        _decide(env, view, "RX-99", 0)
    assert exc.value.status == 422
