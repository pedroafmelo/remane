"""Cobertura da demanda: métrica, não violação (plano da C5, seção 3.1). Fica fora do `ViolationReport`."""

from __future__ import annotations

from datetime import datetime, timedelta

from escalista.domain.schedule import DemandSlot, Schedule

SLOT = timedelta(minutes=30)


def coverage_gaps(schedule: Schedule, demand: list[DemandSlot]) -> list[DemandSlot]:
    """Faixas com gente a menos. Cada item repete a faixa com `required` = quantas pessoas faltam.

    Um turno cobre a faixa de 30 min quando está na mesma loja e a contém inteira. Faixa sem falta não aparece.
    """
    gaps = []
    for slot in demand:
        begin = datetime.combine(slot.day, slot.start)
        end = begin + SLOT
        present = sum(1 for s in schedule.shifts if s.store_id == slot.store_id and s.start <= begin and s.end >= end)
        if present < slot.required:
            gaps.append(slot.model_copy(update={"required": slot.required - present}))
    return gaps
