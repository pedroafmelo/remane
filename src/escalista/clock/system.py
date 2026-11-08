"""Relógio do sistema (porta `Clock`): horário de Brasília sem fuso (datetime naive), como o resto do app.

Brasília não tem horário de verão desde 2019, então um deslocamento fixo de -3h basta e evita depender do `tzdata`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

BRASILIA = timezone(timedelta(hours=-3), "BRT")


def to_brasilia_naive(moment: datetime) -> datetime:
    """Datetime com fuso vira horário de Brasília sem fuso; um naive é tomado como já em Brasília e volta igual."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(BRASILIA).replace(tzinfo=None)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(BRASILIA).replace(tzinfo=None)
