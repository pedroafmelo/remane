"""Semana de referência (plano da C6, A3; seção 8). Funções puras.

- `monday_of`: a segunda-feira da semana de uma data.
- `shift_schedule`: desloca a escala em semanas inteiras (mesmo dia da semana, mesma hora). É o "antes" quando o
  gestor planeja outra semana que não a do arquivo, e nas semanas seguintes (a publicada deslocada 1 semana).
- `next_week_start`: a segunda-feira seguinte.

O cartão de regras por semana (`load_rule_card_for_week`) mora em `loader.py`, ao lado de `load_rule_card`.
"""

from __future__ import annotations

from datetime import date, timedelta

from escalista.domain.schedule import Schedule

WEEK = timedelta(weeks=1)


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def next_week_start(week_start: date) -> date:
    return monday_of(week_start) + WEEK


def shift_schedule(schedule: Schedule, weeks: int) -> Schedule:
    """Escala nova com `week_start` e todos os turnos deslocados `weeks` semanas (negativo volta). Não muda a
    entrada."""
    delta = timedelta(weeks=weeks)
    return Schedule(
        week_start=schedule.week_start + delta,
        shifts=[s.model_copy(update={"start": s.start + delta, "end": s.end + delta}) for s in schedule.shifts],
    )
