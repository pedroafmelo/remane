"""Função de custo pura e comparação antes e depois (plano da C5, frente A, A3; RF-14 parcial).

A **mesma** `compute_metrics` mede a escala enviada (antes) e a otimizada (depois); `compare_schedules` garante isso.
Sem I/O e sem relógio. Não importa `escalista.rules`: lê `rule.kind` e `rule.params` direto do cartão.

Semântica:
- **Horas de um turno** contam inteiras no **dia de início**, inclusive no turno que vira a noite (seg 22h a ter 06h
  conta 8h na segunda). É o mesmo dia a que a jornada diária se refere no turno noturno, e é simples de explicar.
- **Hora extra (HE), por pessoa:** HE = máx(soma dos excessos diários acima de `jornada_diaria_max`, excesso semanal
  acima de `jornada_semanal_max`). A hora que excede os dois limites conta uma vez só. Horas normais = total − HE.
  Sem um dos limites no cartão, aquela dimensão não gera HE.
- **Custo:** horas normais × `hourly_wage` + HE × `hourly_wage` × (1 + percentual/100). O percentual é o
  `params["percent"]` do `adicional_hora_extra` do cartão; sem essa regra, 50% (mínimo da lei).
- **Arredondamento:** contas em `Decimal` sem arredondar; só a saída é arredondada, com `ROUND_HALF_UP`: dinheiro e
  horas em 2 casas (centavos e centésimos de hora), `coverage_pct` em 2 casas. Por isso `total_cost` pode diferir em
  1 centavo da soma das partes arredondadas.
- **Cobertura:** cada `DemandSlot` (loja, dia, início, 30 min) tem cobertas `min(required, pessoas distintas com turno
  na loja que cobre a faixa inteira)`. `coverage_pct` = soma das cobertas / soma de `required` × 100 (100.0 se a soma
  de `required` for 0). `uncovered_slots` = nº de faixas com cobertas < `required`.
- **Violações** vêm do verificador independente; a função só as copia.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from escalista.domain.results import Comparison, ScheduleMetrics
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift

LAW_MIN_OVERTIME_PERCENT = Decimal(50)
SLOT = timedelta(minutes=30)
CENT = Decimal("0.01")
_ZERO = Decimal(0)


def _round2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _param(card: RuleCard, kind: str, key: str) -> Decimal | None:
    for rule in card.rules:
        if rule.kind == kind and key in rule.params:
            return Decimal(str(rule.params[key]))
    return None


def _hours(shift: Shift) -> Decimal:
    return Decimal(int((shift.end - shift.start).total_seconds())) / Decimal(3600)


def _overtime(daily_hours: dict[date, Decimal], daily_max: Decimal | None, weekly_max: Decimal | None) -> Decimal:
    total = sum(daily_hours.values(), _ZERO)
    daily_excess = (
        sum((max(h - daily_max, _ZERO) for h in daily_hours.values()), _ZERO) if daily_max is not None else _ZERO
    )
    weekly_excess = max(total - weekly_max, _ZERO) if weekly_max is not None else _ZERO
    return max(daily_excess, weekly_excess)


def _coverage(schedule: Schedule, demand: list[DemandSlot]) -> tuple[float, int]:
    total_required = sum(s.required for s in demand)
    if total_required <= 0:
        return 100.0, 0
    covered_sum = 0
    uncovered = 0
    for slot in demand:
        start = datetime.combine(slot.day, slot.start)
        end = start + SLOT
        people = {
            sh.employee_id
            for sh in schedule.shifts
            if sh.store_id == slot.store_id and sh.start <= start and sh.end >= end
        }
        covered = min(slot.required, len(people))
        covered_sum += covered
        uncovered += covered < slot.required
    pct = _round2(Decimal(covered_sum) * 100 / Decimal(total_required))
    return float(pct), uncovered


def compute_metrics(
    schedule: Schedule,
    employees: list[Employee],
    demand: list[DemandSlot],
    card: RuleCard,
    violations: int,
) -> ScheduleMetrics:
    """Custo, horas normais e extras, cobertura e violações de uma escala. `violations` vem do verificador."""
    wages = {e.id: e.hourly_wage for e in employees}
    daily_max = _param(card, "jornada_diaria_max", "hours")
    weekly_max = _param(card, "jornada_semanal_max", "hours")
    percent = _param(card, "adicional_hora_extra", "percent")
    premium = 1 + (percent if percent is not None else LAW_MIN_OVERTIME_PERCENT) / 100

    by_employee: dict[str, dict[date, Decimal]] = defaultdict(lambda: defaultdict(lambda: _ZERO))
    for shift in schedule.shifts:
        if shift.employee_id not in wages:
            raise ValueError(f"turno de colaborador desconhecido: {shift.employee_id}")
        by_employee[shift.employee_id][shift.start.date()] += _hours(shift)

    regular_hours = overtime_hours = regular_cost = overtime_cost = _ZERO
    for employee_id, daily in by_employee.items():
        wage = wages[employee_id]
        overtime = _overtime(daily, daily_max, weekly_max)
        regular = sum(daily.values(), _ZERO) - overtime
        regular_hours += regular
        overtime_hours += overtime
        regular_cost += regular * wage
        overtime_cost += overtime * wage * premium

    coverage_pct, uncovered_slots = _coverage(schedule, demand)
    return ScheduleMetrics(
        total_cost=_round2(regular_cost + overtime_cost),
        regular_hours=_round2(regular_hours),
        overtime_hours=_round2(overtime_hours),
        overtime_cost=_round2(overtime_cost),
        coverage_pct=coverage_pct,
        uncovered_slots=uncovered_slots,
        violations=violations,
    )


def compare(before: ScheduleMetrics, after: ScheduleMetrics) -> Comparison:
    """Diferenças antes − depois. Valor negativo quer dizer que o depois ficou pior naquela métrica."""
    return Comparison(
        before=before,
        after=after,
        savings=before.total_cost - after.total_cost,
        overtime_hours_avoided=before.overtime_hours - after.overtime_hours,
        violations_avoided=before.violations - after.violations,
    )


def compare_schedules(
    before: Schedule,
    after: Schedule,
    employees: list[Employee],
    demand: list[DemandSlot],
    card: RuleCard,
    *,
    before_violations: int,
    after_violations: int,
) -> Comparison:
    """Mede as duas escalas com a mesma `compute_metrics` (mesmos colaboradores, demanda e cartão) e compara."""
    return compare(
        compute_metrics(before, employees, demand, card, before_violations),
        compute_metrics(after, employees, demand, card, after_violations),
    )
