"""Varredor do acompanhamento (plano da C7, seção 4.5; contrato SAIDA-AC-06): núcleo **puro** e determinístico.

`detect` olha a escala, as batidas do ponto, os casos abertos e o instante `now` (sempre recebido, nunca lido do
relógio do sistema) e devolve os gatilhos do T1:

- `no_punch`: o turno começou há pelo menos `pol_atraso.tolerancia_min` e não há batida de entrada até `now`, nem caso
  aberto para ele (qualquer status: o caso já cuida do turno);
- `no_answer`: o agente perguntou ao colaborador e passou `pol_atraso.prazo_resposta_colaborador_min` sem resposta;
- `offer_expired`: a oferta do turno ao colega chegou ao prazo (`Offer.deadline`, de `pol_oferta_turno`) sem resposta.

Quem aplica os efeitos (`Tracker.run_sweep`) grava `Trigger.key` em `Case.handled`; um gatilho já tratado não volta.
Os de hora extra (`overtime_near_limit`, `overtime_limit`) são do T2.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from escalista.domain.schedule import Schedule
from escalista.domain.tracking import Case, Punch, TrackPolicy, Trigger, shift_ref


def _hhmm(moment: datetime) -> str:
    return f"{moment:%H:%M}"


def _no_punch(schedule: Schedule, punches: list[Punch], policy: TrackPolicy, cases: list[Case], now: datetime):
    punched = {(p.employee_id, p.shift_start) for p in punches if p.kind == "in" and p.at <= now}
    with_case = {shift_ref(c.shift) for c in cases}
    tolerance = timedelta(minutes=policy.late_tolerance_min)
    for shift in schedule.shifts:
        ref = shift_ref(shift)
        if shift.start + tolerance > now or (shift.employee_id, shift.start) in punched or ref in with_case:
            continue
        yield Trigger(
            kind="no_punch",
            employee_id=shift.employee_id,
            ref=ref,
            observed=f"sem batida de entrada às {_hhmm(now)}",
            threshold=f"{policy.late_tolerance_min} min após o início",
            rule_ref="pol_atraso",
        )


def _no_answer(case: Case, policy: TrackPolicy, now: datetime):
    if case.status != "aguardando_colaborador" or case.asked_at is None:
        return
    if now >= case.asked_at + timedelta(minutes=policy.answer_deadline_min):
        yield Trigger(
            kind="no_answer",
            employee_id=case.employee_id,
            ref=case.id,
            observed=f"sem resposta desde {_hhmm(case.asked_at)}",
            threshold=f"{policy.answer_deadline_min} min após a pergunta",
            rule_ref="pol_atraso",
        )


def _offer_expired(case: Case, policy: TrackPolicy, now: datetime):
    if case.status != "oferta_enviada":
        return
    for offer in case.offers:
        if offer.status == "enviada" and now >= offer.deadline:
            yield Trigger(
                kind="offer_expired",
                employee_id=offer.candidate_id,
                ref=offer.id,
                observed=f"oferta sem resposta até {_hhmm(offer.deadline)}",
                threshold=f"{policy.offer_deadline_min} min por candidato",
                rule_ref="pol_oferta_turno",
            )


def detect(
    *, schedule: Schedule, punches: list[Punch], policy: TrackPolicy, cases: list[Case], now: datetime
) -> list[Trigger]:
    """Gatilhos no instante `now`, sem repetidos e sem os já tratados, ordenados por tipo e depois por referência."""
    found: dict[str, Trigger] = {t.key: t for t in _no_punch(schedule, punches, policy, cases, now)}
    for case in cases:
        handled = set(case.handled)
        for trigger in (*_no_answer(case, policy, now), *_offer_expired(case, policy, now)):
            if trigger.key not in handled:
                found[trigger.key] = trigger
    return sorted(found.values(), key=lambda t: (t.kind, t.ref))
