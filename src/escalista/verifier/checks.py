"""Uma função pura por primitiva da fatia (RF-02). Escrita sem olhar o solver, a partir do cartão e do contrato.

Semântica combinada no núcleo:
- o turno que vira a noite conta inteiro no dia em que começa (jornada diária e dia trabalhado);
- a semana vai de `schedule.week_start` (segunda) a domingo; turno que começa fora dela não conta;
- interjornada usa o fim real do turno (no dia seguinte, se virou a noite) e marca o dia do turno seguinte.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from escalista.domain.results import Violation
from escalista.domain.rules import Rule
from escalista.domain.schedule import Schedule, Shift

_SECONDS_PER_HOUR = Decimal(3600)


def hours(delta: timedelta) -> Decimal:
    return Decimal(int(delta.total_seconds())) / _SECONDS_PER_HOUR


def fmt_hours(value: Decimal) -> str:
    """`Decimal("43")` → `"43,0h"` (uma casa, vírgula decimal)."""
    return f"{value.quantize(Decimal('0.1'))}h".replace(".", ",")


def _limit(value: object) -> str:
    """Limite do cartão como está no YAML: `42` → `"42h"`, `7.5` → `"7,5h"`."""
    return f"{value}h".replace(".", ",")


def week_days(schedule: Schedule) -> list[date]:
    return [schedule.week_start + timedelta(days=i) for i in range(7)]


def _by_employee(schedule: Schedule) -> dict[str, list[Shift]]:
    grouped: dict[str, list[Shift]] = defaultdict(list)
    for shift in schedule.shifts:
        grouped[shift.employee_id].append(shift)
    return {emp: sorted(shifts, key=lambda s: (s.start, s.end)) for emp, shifts in sorted(grouped.items())}


def _in_week(schedule: Schedule, shift: Shift) -> bool:
    return schedule.week_start <= shift.start.date() < schedule.week_start + timedelta(days=7)


def _violation(rule: Rule, employee_id: str, day: date | None, detail: str) -> Violation:
    return Violation(
        rule_id=rule.id, kind=rule.kind, employee_id=employee_id, day=day, source=rule.source, detail=detail
    )


def check_weekly_hours(schedule: Schedule, rule: Rule) -> list[Violation]:
    """`jornada_semanal_max`: soma das horas da pessoa na semana acima de `params["hours"]`."""
    limit = Decimal(str(rule.params["hours"]))
    found = []
    for emp, shifts in _by_employee(schedule).items():
        total = sum((hours(s.end - s.start) for s in shifts if _in_week(schedule, s)), Decimal(0))
        if total > limit:
            detail = f"{fmt_hours(total)} na semana; limite {_limit(rule.params['hours'])}"
            found.append(_violation(rule, emp, None, detail))
    return found


def check_daily_hours(schedule: Schedule, rule: Rule) -> list[Violation]:
    """`jornada_diaria_max`: horas que começam num mesmo dia acima de `params["hours"]`."""
    limit = Decimal(str(rule.params["hours"]))
    found = []
    for emp, shifts in _by_employee(schedule).items():
        per_day: dict[date, Decimal] = defaultdict(Decimal)
        for s in shifts:
            if _in_week(schedule, s):
                per_day[s.start.date()] += hours(s.end - s.start)
        for day in sorted(per_day):
            if per_day[day] > limit:
                detail = f"{fmt_hours(per_day[day])} em {day:%d/%m}; limite {_limit(rule.params['hours'])}"
                found.append(_violation(rule, emp, day, detail))
    return found


def check_rest_between_shifts(schedule: Schedule, rule: Rule) -> list[Violation]:
    """`interjornada_min`: descanso entre o fim de um turno e o início do seguinte abaixo de `params["hours"]`."""
    limit = Decimal(str(rule.params["hours"]))
    found = []
    for emp, shifts in _by_employee(schedule).items():
        for prev, nxt in zip(shifts, shifts[1:], strict=False):
            if not _in_week(schedule, nxt):
                continue
            rest = hours(nxt.start - prev.end)
            if rest < limit:
                detail = (
                    f"{fmt_hours(rest)} de descanso entre {prev.end:%d/%m %H:%M} e {nxt.start:%d/%m %H:%M}; "
                    f"mínimo {_limit(rule.params['hours'])}"
                )
                found.append(_violation(rule, emp, nxt.start.date(), detail))
    return found


def check_weekly_rest(schedule: Schedule, rule: Rule) -> list[Violation]:
    """`repouso_semanal`: dias da semana sem turno começando abaixo de `params["days"]`."""
    required = int(rule.params["days"])
    days = week_days(schedule)
    found = []
    for emp, shifts in _by_employee(schedule).items():
        worked = {s.start.date() for s in shifts}
        free = sum(1 for d in days if d not in worked)
        if free < required:
            word = "dia" if free == 1 else "dias"
            detail = f"{free} {word} de repouso na semana; mínimo {required}"
            found.append(_violation(rule, emp, None, detail))
    return found
