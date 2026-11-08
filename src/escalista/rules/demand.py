"""Demanda inferida da escala lida e conta de capacidade (plano da C6, A3; seção 9). Funções puras.

`[HIPÓTESE]` de produto: a demanda de uma loja, num dia da semana e numa faixa de 30 min, é o número de pessoas que a
escala lida põe ali. O gestor corrige pela cobertura-alvo por loja (`coverage_pct`), não faixa a faixa.

- **Horário da loja** (`infer_store_hours`): abre no menor início e fecha no maior fim dos turnos da loja,
  arredondados para fora em 30 min. Os horários são medidos a partir da meia-noite do dia de início do turno, então
  um turno que vira a noite (ex.: 18:00 → 01:10) faz a loja fechar **depois da meia-noite** (01:30): `closes` fica
  menor que `opens`, que é a convenção que `solver/catalog.py` já lê como "fecha no dia seguinte" (`Store` não tem
  validador de ordem). Fim exatamente à meia-noite dá `closes = 00:00` (= 24:00 para o catálogo). Se o fechamento
  depois da meia-noite passar da abertura, a loja fica 24 h (`closes = opens`). Loja sem turno fica de fora: sem
  dado não há horário, e o modelo não inventa um.
- **Padrão** (`infer_demand_pattern`): pessoas distintas por faixa; a faixa coberta **parcialmente** conta (é o fato
  medido de 2.776 pessoa-hora no exemplo). Só entram as faixas dentro do horário da loja, todas, inclusive as com 0,
  nos 7 dias. A faixa depois da meia-noite pertence ao dia do calendário em que cai (dia da semana seguinte), como
  um `DemandSlot` com `day` e `start`.
- **Escala** (`scale_pattern`): `ceil(required × pct / 100)` por faixa, em inteiros; faixa com ≥ 1 fica com ≥ 1;
  faixa com 0 fica 0; loja ausente do dicionário = 100%.
- **Capacidade** (`capacity_check`): demanda = soma das faixas × 0,5 h; capacidade = pessoas × mín(limite semanal,
  (7 − repousos) × limite diário), a mesma conta de `Limits.per_person_week_min` do solver (o núcleo `rules` não
  importa `solver`). Sem uma das três primitivas no cartão, levanta `ValueError`, como o solver.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from escalista.domain.reading import CapacityCheck, DemandPattern
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift, Store

from .identity import StoreDraft

SLOT_MIN = 30
DAY_MIN = 24 * 60
DAYS = 7
MIN_PCT = 50
MAX_PCT = 100
SLOT = timedelta(minutes=SLOT_MIN)


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


def _since_start_day(moment: datetime, start: datetime) -> int:
    """Minutos de `moment` contados da meia-noite do dia de `start`."""
    return int((moment - datetime.combine(start.date(), time())).total_seconds() // 60)


def infer_store_hours(shifts: list[Shift], stores: list[StoreDraft]) -> list[Store]:
    """Horário de cada loja pelos turnos dela, na ordem de `stores`. Ver o docstring do módulo."""
    by_store: dict[str, list[Shift]] = defaultdict(list)
    for s in shifts:
        by_store[s.store_id].append(s)
    out: list[Store] = []
    for draft in stores:
        own = by_store.get(draft.id)
        if not own:
            continue
        open_min = min(_minutes(s.start.time()) for s in own) // SLOT_MIN * SLOT_MIN
        close_min = math.ceil(max(_since_start_day(s.end, s.start) for s in own) / SLOT_MIN) * SLOT_MIN
        if close_min >= DAY_MIN:  # fecha depois da meia-noite
            close_min -= DAY_MIN
            if close_min > open_min:  # o fechamento passa da abertura: 24 h
                close_min = open_min
        out.append(Store(id=draft.id, name=draft.name, opens=_time(open_min), closes=_time(close_min)))
    return out


def _open_slots(store: Store) -> list[int]:
    """Inícios das faixas (minutos do dia) dentro do horário da loja, em ordem."""
    open_min, close_min = _minutes(store.opens), _minutes(store.closes)
    if close_min > open_min:
        return list(range(open_min, close_min, SLOT_MIN))
    return sorted([*range(open_min, DAY_MIN, SLOT_MIN), *range(0, close_min, SLOT_MIN)])


def infer_demand_pattern(schedule: Schedule, stores: list[Store]) -> list[DemandPattern]:
    """Pessoas que a escala põe em cada loja, dia da semana e faixa de 30 min dentro do horário da loja."""
    people: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    for s in schedule.shifts:
        slot = datetime.combine(s.start.date(), time()) + timedelta(
            minutes=_minutes(s.start.time()) // SLOT_MIN * SLOT_MIN
        )
        while slot < s.end:
            people[s.store_id, slot.weekday(), _minutes(slot.time())].add(s.employee_id)
            slot += SLOT
    return [
        DemandPattern(
            store_id=store.id, weekday=weekday, start=_time(m), required=len(people.get((store.id, weekday, m), ()))
        )
        for store in stores
        for weekday in range(DAYS)
        for m in _open_slots(store)
    ]


def _scale(required: int, pct: int) -> int:
    if required <= 0:
        return 0
    return max(1, -(-required * pct // 100))


def scale_pattern(pattern: list[DemandPattern], coverage_pct: dict[str, int]) -> list[DemandPattern]:
    """Demanda escalada pela cobertura-alvo de cada loja (ausente = 100). Não muda a entrada."""
    return [p.model_copy(update={"required": _scale(p.required, coverage_pct.get(p.store_id, 100))}) for p in pattern]


def demand_for_week(pattern: list[DemandPattern], week_start: date) -> list[DemandSlot]:
    """O padrão materializado nas datas da semana que começa em `week_start` (segunda-feira)."""
    if week_start.weekday() != 0:
        raise ValueError("week_start deve ser uma segunda-feira")
    return [
        DemandSlot(store_id=p.store_id, day=week_start + timedelta(days=p.weekday), start=p.start, required=p.required)
        for p in pattern
    ]


def _param(card: RuleCard, kind: str, key: str) -> float:
    for rule in card.rules:
        if rule.kind == kind and key in rule.params:
            return float(rule.params[key])
    raise ValueError(f"o cartão não tem a primitiva {kind} ({key}); a capacidade não é calculável sem ela")


def _per_person_week_min(card: RuleCard) -> int:
    weekly = round(_param(card, "jornada_semanal_max", "hours") * 60)
    daily = round(_param(card, "jornada_diaria_max", "hours") * 60)
    rest_days = round(_param(card, "repouso_semanal", "days"))
    return min(weekly, max(DAYS - rest_days, 0) * daily)


def _hours(minutes: int) -> Decimal:
    value = Decimal(minutes) / Decimal(60)
    return value if minutes % 60 == 0 else value.quantize(Decimal("0.01"))


def capacity_check(pattern: list[DemandPattern], employees: list[Employee], card: RuleCard) -> CapacityCheck:
    """A demanda cabe no quadro sob o cartão? E qual a maior cobertura (50 a 100%) que cabe?"""
    capacity_min = len(employees) * _per_person_week_min(card)

    def demand_min(pct: int) -> int:
        return sum(_scale(p.required, pct) for p in pattern) * SLOT_MIN

    full = sum(p.required for p in pattern) * SLOT_MIN
    max_pct = next((pct for pct in range(MAX_PCT, MIN_PCT - 1, -1) if demand_min(pct) <= capacity_min), MIN_PCT)
    return CapacityCheck(
        demand_person_hours=_hours(full),
        capacity_person_hours=_hours(capacity_min),
        fits=full <= capacity_min,
        max_fitting_pct=max_pct,
    )
