"""Ponto simulado do acompanhamento (plano da C7, tarefa D1). SINTÉTICO: nenhuma batida é de um ponto real.

`SimulatedPunchSource` deriva as batidas da escala corrente e dos desvios plantados em `ponto_desvios.json`. Não lê o
relógio do sistema: quem manda é o argumento `until`, que o chamador tira do relógio de demo.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from escalista.domain.schedule import Schedule
from escalista.domain.tracking import Deviation, Punch


def load_deviations(path: Path) -> list[Deviation]:
    """Lê `ponto_desvios.json` (`{synthetic: true, deviations: [...]}`) e valida cada desvio."""
    corpo = json.loads(path.read_text(encoding="utf-8"))
    return [Deviation.model_validate(item) for item in corpo["deviations"]]


class SimulatedPunchSource:
    """Batidas simuladas. `schedule` é chamada a cada consulta, de modo que uma escala republicada vale na hora.

    Regras, para cada turno da escala corrente:
    - batida `in` no início do turno, mais os minutos de um desvio `atraso`;
    - batida `out` no fim do turno, mais os minutos de um desvio `hora_extra`;
    - desvio `falta`: nenhuma batida (nem de entrada, nem de saída).

    O desvio casa por (`employee_id`, `shift_start`). Se o turno foi reatribuído a outra pessoa (cobertura), o desvio da
    primeira não se aplica à segunda, que bate o ponto normalmente.
    """

    def __init__(self, schedule: Callable[[], Schedule | None], deviations: list[Deviation]) -> None:
        self._schedule = schedule
        self._deviations: dict[tuple[str, datetime], list[Deviation]] = {}
        for desvio in deviations:
            self._deviations.setdefault((desvio.employee_id, desvio.shift_start), []).append(desvio)

    def punches(self, *, until: datetime) -> list[Punch]:
        """Batidas com `at <= until`, da mais antiga para a mais recente."""
        escala = self._schedule()
        if escala is None:
            return []
        batidas: list[Punch] = []
        for turno in escala.shifts:
            desvios = self._deviations.get((turno.employee_id, turno.start), [])
            if any(d.kind == "falta" for d in desvios):
                continue
            entrada = turno.start + timedelta(minutes=sum(d.minutes for d in desvios if d.kind == "atraso"))
            saida = turno.end + timedelta(minutes=sum(d.minutes for d in desvios if d.kind == "hora_extra"))
            for tipo, instante in (("in", entrada), ("out", saida)):
                if instante <= until:
                    batidas.append(
                        Punch(employee_id=turno.employee_id, shift_start=turno.start, kind=tipo, at=instante)
                    )
        return sorted(batidas, key=lambda b: (b.at, b.employee_id, b.kind))
