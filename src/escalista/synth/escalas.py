"""Escalas sintéticas da semana de 11 a 17/01/2027 (plano da C5, seção 4, D2).

- `escala_base`: regime novo (5 dias, 2 folgas, até 8h, interjornada >= 11h). Não tem violação pelas regras novas.
- `escala_atual`: regime de 44h e 1 folga, com hora extra. Julgada pelas regras novas, tem violações.
- `escala_violacoes`: a base, com 7 pessoas planejadas para violar regras de propósito (lista em `PLANTADAS`).
- `escala_defeito`: a base, com 5 defeitos de leitura plantados (um de cada tipo).
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from escalista.domain.schedule import Employee, Shift
from escalista.synth.rede import SEMANA_INICIO

PADROES_NOVOS = {"manha": ("08:00", "15:00"), "tarde": ("13:00", "20:00"), "integral": ("09:00", "17:00")}
PADROES_44H = (("08:00", "15:20"), ("12:40", "20:00"), ("14:00", "22:00"))
# (rule_id, employee_id, day): `day` é None para regras de semana (jornada semanal e repouso)
PLANTADAS: tuple[tuple[str, str, date | None], ...] = (
    ("jornada_semanal_max", "P001", None),
    ("repouso_semanal", "P001", None),
    ("jornada_semanal_max", "P003", None),
    ("repouso_semanal", "P003", None),
    ("repouso_semanal", "P002", None),
    ("jornada_diaria_max", "P004", date(2027, 1, 11)),
    ("jornada_diaria_max", "P005", date(2027, 1, 13)),
    ("interjornada_min", "P006", date(2027, 1, 12)),
    ("interjornada_min", "P007", date(2027, 1, 14)),
)


def _dia(indice: int) -> date:
    return SEMANA_INICIO + timedelta(days=indice)


def _intervalo(indice: int, ini: str, fim: str) -> tuple[datetime, datetime]:
    """Turno no dia `indice`. Se o fim não é depois do início, o turno vira a noite e termina no dia seguinte."""
    inicio = datetime.combine(_dia(indice), time.fromisoformat(ini))
    termino = datetime.combine(_dia(indice), time.fromisoformat(fim))
    if termino <= inicio:
        termino += timedelta(days=1)
    return inicio, termino


def _turno(pessoa: Employee, inicio: datetime, fim: datetime) -> Shift:
    return Shift(employee_id=pessoa.id, store_id=pessoa.store_id, start=inicio, end=fim)


def base_pessoa(rng: random.Random, pessoa: Employee) -> list[Shift]:
    """5 dias por semana, sempre com domingo de folga e mais um dia de folga sorteado (seg a sáb)."""
    folga = rng.randrange(6)
    turnos = []
    for indice in range(6):
        if indice == folga:
            continue
        ini, fim = PADROES_NOVOS[rng.choice(sorted(PADROES_NOVOS))]
        turnos.append(_turno(pessoa, *_intervalo(indice, ini, fim)))
    return turnos


def escala_base(rng: random.Random, pessoas: list[Employee]) -> dict[str, list[Shift]]:
    return {p.id: base_pessoa(rng, p) for p in pessoas}


def escala_atual(rng: random.Random, pessoas: list[Employee]) -> list[Shift]:
    """Regime de 44h e 1 folga: 6 dias de 7h20 ou 8h. Oito pessoas fazem hora extra num dia (9h30 ou 10h)."""
    extras = {p.id for p in rng.sample(pessoas, 8)}
    turnos: list[Shift] = []
    for pessoa in pessoas:
        folga = rng.randrange(7)
        dias = [i for i in range(7) if i != folga]
        marcados = [(i, *_intervalo(i, *rng.choice(PADROES_44H))) for i in dias]
        if pessoa.id in extras:
            k = rng.randrange(len(marcados))
            i, inicio, _fim = marcados[k]
            duracao = timedelta(hours=10) if inicio.hour == 8 else timedelta(hours=9, minutes=30)
            marcados[k] = (i, inicio, inicio + duracao)
        turnos += [_turno(pessoa, inicio, fim) for _i, inicio, fim in marcados]
    return turnos


def escala_violacoes(base: dict[str, list[Shift]], pessoas: list[Employee]) -> list[Shift]:
    """A base, com as 7 pessoas planejadas no lugar. As demais ficam dentro de todas as regras."""
    planos: dict[str, list[tuple[int, str, str]]] = {
        "P001": [(i, "08:00", "15:30") for i in range(6)],  # 45h na semana, 1 folga
        "P002": [(i, "08:00", "15:00") for i in range(6)],  # 42h (no limite), 1 folga
        "P003": [(i, "08:00", "15:40") for i in range(6)],  # 46h40, 1 folga
        "P004": [(0, "08:00", "17:00")] + [(i, "08:00", "15:00") for i in range(1, 5)],  # 9h na segunda
        "P005": [(2, "08:00", "18:00")] + [(i, "08:00", "15:00") for i in (0, 1, 3, 4)],  # 10h na quarta
        "P006": [  # 10h de descanso entre segunda e terça
            (0, "14:00", "22:00"),
            (1, "08:00", "15:00"),
            (2, "13:00", "20:00"),
            (3, "08:00", "15:00"),
            (4, "08:00", "15:00"),
        ],
        "P007": [  # turno que vira a noite (quarta 16h até quinta 0h); 8h de descanso até a quinta 8h
            (0, "08:00", "15:00"),
            (1, "08:00", "15:00"),
            (2, "16:00", "00:00"),
            (3, "08:00", "15:00"),
            (4, "08:00", "15:00"),
        ],
    }
    por_id = {p.id: p for p in pessoas}
    turnos: list[Shift] = []
    for pessoa in pessoas:
        if pessoa.id in planos:
            turnos += [_turno(por_id[pessoa.id], *_intervalo(i, ini, fim)) for i, ini, fim in planos[pessoa.id]]
        else:
            turnos += base[pessoa.id]
    return turnos
