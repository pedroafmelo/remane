"""Restrições duras pedidas pelo gestor (camada `execucao`, C6, D4; RF-02). Escrito sem olhar o solver nem a `spec`.

Contrato das regras (`card_with_spec`):
- `indisponibilidade`: `params = {employee_id, day: "YYYY-MM-DD", start: "HH:MM" | None, end: "HH:MM" | None}`. Sem
  `start`, a janela começa às 00:00; sem `end`, termina às 24:00. Viola qualquer turno da pessoa com interseção de
  duração positiva com a janela daquele dia (inclusive o que vem da noite anterior ou vira a noite). Uma violação por
  regra, com todos os turnos em conflito no detalhe.
- `jornada_semanal_max_pessoa`: `params = {employee_id, hours}`. Viola se as horas da pessoa na semana passam de
  `hours`, contadas como `jornada_semanal_max` conta (turno pertence à semana pelo dia em que começa).

Regra com `params` malformados não quebra o verificador: vira violação "regra de pedido malformada: ..." (o rastro
mostra). O detalhe nunca leva nome de pessoa, só o id (RN-13, minimização).
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from escalista.domain.results import Violation
from escalista.domain.rules import Rule
from escalista.domain.schedule import Schedule
from escalista.verifier.checks import fmt_hours, hours

_MALFORMED = "regra de pedido malformada: "


class _Malformed(ValueError):
    pass


def _violation(rule: Rule, employee_id: str | None, day: date | None, detail: str) -> Violation:
    return Violation(
        rule_id=rule.id, kind=rule.kind, employee_id=employee_id, day=day, source=rule.source, detail=detail
    )


def _employee_id(rule: Rule) -> str | None:
    value = rule.params.get("employee_id")
    return value if isinstance(value, str) and value.strip() else None


def _require_employee(rule: Rule) -> str:
    employee = _employee_id(rule)
    if employee is None:
        raise _Malformed("employee_id ausente ou vazio")
    return employee


def _day(rule: Rule) -> date:
    value = rule.params.get("day")
    if not isinstance(value, str):
        raise _Malformed("day ausente; esperado AAAA-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _Malformed(f"day {value!r} fora do formato AAAA-MM-DD") from None


def _clock(rule: Rule, key: str, default: timedelta) -> timedelta:
    """Hora do dia como deslocamento desde 00:00. Aceita `"24:00"` (fim do dia)."""
    value = rule.params.get(key)
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "24:00":
        return timedelta(hours=24)
    try:
        if not isinstance(value, str) or len(value.strip()) != 5:
            raise ValueError
        parsed = time.fromisoformat(value.strip())
    except ValueError:
        raise _Malformed(f"{key} {value!r} fora do formato HH:MM") from None
    return timedelta(hours=parsed.hour, minutes=parsed.minute)


def _limit_hours(rule: Rule) -> Decimal:
    value = rule.params.get("hours")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _Malformed(f"hours {value!r} não é número")
    if isinstance(value, float) and not math.isfinite(value):
        raise _Malformed(f"hours {value!r} não é finito")
    if value < 0:
        raise _Malformed(f"hours {value!r} negativo")
    return Decimal(str(value))


def _fmt_limit(value: object) -> str:
    return f"{value}h".replace(".", ",")


def _fmt_clock(offset: timedelta) -> str:
    minutes = int(offset.total_seconds()) // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def check_unavailability(schedule: Schedule, rule: Rule) -> list[Violation]:
    """`indisponibilidade`: turno da pessoa que cruza a janela indisponível daquele dia."""
    try:
        employee = _require_employee(rule)
        day = _day(rule)
        start = _clock(rule, "start", timedelta(0))
        end = _clock(rule, "end", timedelta(hours=24))
        if end <= start:
            raise _Malformed(f"janela {_fmt_clock(start)} a {_fmt_clock(end)} vazia ou invertida")
    except _Malformed as exc:
        return [_violation(rule, _employee_id(rule), None, _MALFORMED + str(exc))]

    midnight = datetime.combine(day, time())
    window_start, window_end = midnight + start, midnight + end
    conflicts = sorted(
        (s for s in schedule.shifts if s.employee_id == employee and s.start < window_end and s.end > window_start),
        key=lambda s: (s.start, s.end),
    )
    if not conflicts:
        return []
    whole_day = start == timedelta(0) and end == timedelta(hours=24)
    window = "dia inteiro" if whole_day else f"{_fmt_clock(start)} a {_fmt_clock(end)}"
    shifts = "; ".join(f"{s.start:%d/%m %H:%M} a {s.end:%d/%m %H:%M}" for s in conflicts)
    word = "turno" if len(conflicts) == 1 else "turnos"
    detail = f"{word} {shifts} na indisponibilidade de {day:%d/%m} ({window})"
    return [_violation(rule, employee, day, detail)]


def check_weekly_hours_per_person(schedule: Schedule, rule: Rule) -> list[Violation]:
    """`jornada_semanal_max_pessoa`: horas da pessoa na semana acima do teto pedido."""
    try:
        employee = _require_employee(rule)
        limit = _limit_hours(rule)
    except _Malformed as exc:
        return [_violation(rule, _employee_id(rule), None, _MALFORMED + str(exc))]

    week_end = schedule.week_start + timedelta(days=7)
    total = sum(
        (
            hours(s.end - s.start)
            for s in schedule.shifts
            if s.employee_id == employee and schedule.week_start <= s.start.date() < week_end
        ),
        Decimal(0),
    )
    if total <= limit:
        return []
    detail = f"{fmt_hours(total)} na semana; teto pedido {_fmt_limit(rule.params['hours'])}"
    return [_violation(rule, employee, None, detail)]
