"""Catálogo de turnos do solver (plano da C5, A2). Função pura.

Um turno do catálogo é um par (início, duração) em minutos a partir da meia-noite do dia de início. O catálogo
depende só do horário da loja e do limite diário: inícios em passos de `start_step_min` (30 min), durações de
`min_hours` (4h) até `jornada_diaria_max`, em passos de `duration_step_min`, sempre dentro do horário da loja.

Tamanho (loja 08h–22h, limite de 8h): passos de 30 min nos dois eixos dão 153 turnos por pessoa e dia; durações
em passos de 60 min (o padrão) dão 85. O benchmark mediu os dois (ver `bench.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

MIN_SHIFT_HOURS = 4
START_STEP_MIN = 30
DURATION_STEP_MIN = 60


@dataclass(frozen=True, order=True)
class CatalogShift:
    start_min: int  # minutos desde a meia-noite do dia de início
    duration_min: int

    @property
    def end_min(self) -> int:
        return self.start_min + self.duration_min

    @property
    def label(self) -> str:
        """Nome estável, usado nos nomes das variáveis (ex.: `0800+480`)."""
        h, m = divmod(self.start_min, 60)
        return f"{h:02d}{m:02d}+{self.duration_min}"

    def covers(self, slot_start_min: int, slot_min: int = 30) -> bool:
        """Cobre a faixa inteira (mesma regra de `cost.py`: início ≤ faixa e fim ≥ fim da faixa)."""
        return self.start_min <= slot_start_min and self.end_min >= slot_start_min + slot_min


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def build_catalog(
    opens: time,
    closes: time,
    daily_max_min: int,
    *,
    min_hours: float = MIN_SHIFT_HOURS,
    start_step_min: int = START_STEP_MIN,
    duration_step_min: int = DURATION_STEP_MIN,
) -> list[CatalogShift]:
    """Turnos dentro do horário da loja. Loja que fecha "antes" de abrir (ex.: 18h–02h) fecha no dia seguinte."""
    open_min = _minutes(opens)
    close_min = _minutes(closes)
    if close_min <= open_min:
        close_min += 24 * 60
    min_dur = int(round(min_hours * 60))
    # inclui sempre o limite diário; com limite abaixo do mínimo (ex.: 3h), o único turno é o do limite
    durations = list(range(daily_max_min, min_dur - 1, -duration_step_min)) or [daily_max_min]
    out = [
        CatalogShift(start, dur) for dur in durations for start in range(open_min, close_min - dur + 1, start_step_min)
    ]
    return sorted(set(out))
