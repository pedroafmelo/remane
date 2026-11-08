"""Varredor do acompanhamento (plano da C7, seção 4.5; contrato SAIDA-AC-06): núcleo **puro** e determinístico.

`detect` olha a escala, as batidas do ponto, os casos abertos e o instante `now` (sempre recebido, nunca lido do
relógio do sistema) e devolve os gatilhos do T1:

- `no_punch`: o turno começou há pelo menos `pol_atraso.tolerancia_min` e não há batida de entrada até `now`, nem caso
  aberto para ele (qualquer status: o caso já cuida do turno);
- `no_answer`: o agente perguntou ao colaborador e passou `pol_atraso.prazo_resposta_colaborador_min` sem resposta;
- `offer_expired`: a oferta do turno ao colega chegou ao prazo (`Offer.deadline`, de `pol_oferta_turno`) sem resposta.

e os de hora extra do T2 (RF-27, DEC-060), por pessoa e semana (segunda a domingo do turno batido):

- `overtime_near_limit`: a hora extra acumulada chegou a `pol_aviso_hora_extra_estourando` (80%) do limite semanal de
  `pol_hora_extra` (6 h), sem passar dele;
- `overtime_limit`: passou do limite (estritamente acima). Varredura que já chega acima do limite só devolve este.

Hora extra de um turno = max(0, (saída − entrada) − (fim − início do turno)), só com as duas batidas até `now`.

Quem aplica os efeitos (`Tracker.run_sweep`) grava `Trigger.key` em `Case.handled`; um gatilho já tratado não volta.
Os de hora extra não têm caso: o chamador passa as chaves já tratadas em `handled`.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import date, datetime, timedelta
from decimal import Decimal

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


def _hm(minutes: Decimal | int) -> str:
    """'4h48', '6h', '6h15' (minutos inteiros)."""
    hours, rest = divmod(int(minutes), 60)
    return f"{hours}h" if rest == 0 else f"{hours}h{rest:02d}"


def week_of(day: date) -> date:
    """A segunda-feira da semana (segunda a domingo) de `day`."""
    return day - timedelta(days=day.weekday())


def _overtime_by_week(schedule: Schedule, punches: list[Punch], now: datetime) -> dict[tuple[str, date], int]:
    """Minutos de hora extra por (pessoa, segunda da semana), só dos turnos com entrada e saída batidas até `now`."""
    ends = {(s.employee_id, s.start): s.end for s in schedule.shifts}
    ins = {(p.employee_id, p.shift_start): p.at for p in punches if p.kind == "in" and p.at <= now}
    totals: dict[tuple[str, date], int] = {}
    for punch in punches:
        key = (punch.employee_id, punch.shift_start)
        if punch.kind != "out" or punch.at > now or key not in ins or key not in ends:
            continue
        worked = punch.at - ins[key]
        planned = ends[key] - punch.shift_start
        extra = max(0, int((worked - planned).total_seconds() // 60))
        week = (punch.employee_id, week_of(punch.shift_start.date()))
        totals[week] = totals.get(week, 0) + extra
    return totals


def overtime_minutes(schedule: Schedule, punches: list[Punch], employee_id: str, monday: date, now: datetime) -> int:
    """Hora extra (min) de `employee_id` na semana que começa em `monday`, até `now`."""
    return _overtime_by_week(schedule, punches, now).get((employee_id, monday), 0)


def _overtime(schedule: Schedule, punches: list[Punch], policy: TrackPolicy, now: datetime):
    limit = policy.overtime_weekly_limit_h * 60
    warn = limit * policy.overtime_warn_pct / 100
    for (employee_id, monday), total in sorted(_overtime_by_week(schedule, punches, now).items()):
        ref = f"{employee_id}@{monday.isoformat()}"
        observed = f"{_hm(total)} de hora extra na semana de {monday:%d/%m}"
        if total > limit:
            yield Trigger(
                kind="overtime_limit",
                employee_id=employee_id,
                ref=ref,
                observed=observed,
                threshold=f"limite de {_hm(limit)} por semana",
                rule_ref="pol_hora_extra",
            )
        elif total >= warn:
            yield Trigger(
                kind="overtime_near_limit",
                employee_id=employee_id,
                ref=ref,
                observed=observed,
                threshold=f"{_hm(warn)} ({policy.overtime_warn_pct}% do limite de {_hm(limit)})",
                rule_ref="pol_aviso_hora_extra_estourando",
            )


def detect(
    *,
    schedule: Schedule,
    punches: list[Punch],
    policy: TrackPolicy,
    cases: list[Case],
    now: datetime,
    handled: Collection[str] = (),
) -> list[Trigger]:
    """Gatilhos no instante `now`, sem repetidos e sem os já tratados, ordenados por tipo e depois por referência.

    `handled`: chaves (`Trigger.key`) já tratadas fora de um caso (os gatilhos de hora extra)."""
    found: dict[str, Trigger] = {t.key: t for t in _no_punch(schedule, punches, policy, cases, now)}
    for trigger in _overtime(schedule, punches, policy, now):
        if trigger.key not in handled:
            found[trigger.key] = trigger
    for case in cases:
        handled = set(case.handled)
        for trigger in (*_no_answer(case, policy, now), *_offer_expired(case, policy, now)):
            if trigger.key not in handled:
                found[trigger.key] = trigger
    return sorted(found.values(), key=lambda t: (t.kind, t.ref))
