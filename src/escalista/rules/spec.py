"""Conferência da `SolveSpec` formulada pelo modelo e cartão da execução (plano da C6, seções 6 e 10; invariante 4).

- `validate_spec` confere cada restrição em código: a pessoa existe, o dia cai na semana planejada, `max_horas_semana`
  fica **estritamente abaixo** da jornada semanal do cartão, `start < end` e a evidência é trecho literal do pedido do
  gestor ou de uma observação do arquivo (espaços colapsados, sem diferenciar maiúsculas). Item recusado sai da spec e
  volta com o motivo; o resto segue. Itens repetidos (mesmo conteúdo, evidência à parte) ficam um só.
- `card_with_spec` devolve um cartão **novo** com as regras originais intactas e uma regra da camada `execucao` por
  restrição dura. Nunca remove nem altera regra: a spec só restringe.
- `default_spec` é o comportamento da C5; na continuidade, `stability_weight` = 10 (plano, seção 8).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, time, timedelta
from typing import Any

from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.spec import (
    MaxWeeklyHoursConstraint,
    PreferredDayOffConstraint,
    PreferredWindowConstraint,
    SolveSpec,
    UnavailableConstraint,
)

# Mesma forma do `Screen` da formulação (`llm/prompts/formulate.py`); o núcleo não importa de `llm`.
Screen = Callable[[SolveSpec], tuple[SolveSpec, list[tuple[str, str]]]]

CONTINUITY_STABILITY_WEIGHT = 10
WEEKLY_LIMIT_KIND = "jornada_semanal_max"
LOOSEN_REASON = "não pode afrouxar a lei/convenção"
SOURCE_PREFIX = "pedido do gestor: "

AnyConstraint = UnavailableConstraint | MaxWeeklyHoursConstraint | PreferredDayOffConstraint | PreferredWindowConstraint


def default_spec(*, continuity: bool = False) -> SolveSpec:
    """Especificação sem pedido: pesos da C5 e nenhuma restrição; na continuidade, valoriza não mexer na escala."""
    if continuity:
        return SolveSpec(stability_weight=CONTINUITY_STABILITY_WEIGHT)
    return SolveSpec()


def validate_spec(
    spec: SolveSpec,
    *,
    employee_ids: set[str],
    week_start: date,
    card: RuleCard,
    evidence_sources: list[str],
) -> tuple[SolveSpec, list[tuple[str, str]]]:
    """Spec só com os itens aceitos e a lista de recusados `(item, motivo)`. Os pesos já vêm conferidos pelo schema."""
    sources = [_normalize(text) for text in evidence_sources]
    weekly_limit = _weekly_limit(card)
    week_end = week_start + timedelta(days=6)

    accepted: list[AnyConstraint] = []
    seen: set[tuple[Any, ...]] = set()
    rejected: list[tuple[str, str]] = []
    for item in spec.constraints:
        reasons = _reasons(item, employee_ids, week_start, week_end, weekly_limit, sources)
        if reasons:
            rejected.append((_describe(item), "; ".join(reasons)))
            continue
        key = _key(item)
        if key in seen:
            continue
        seen.add(key)
        accepted.append(item)
    return spec.model_copy(update={"constraints": accepted}), rejected


def make_screen(
    *,
    employee_ids: set[str],
    week_start: date,
    card: RuleCard,
    evidence_sources: list[str],
) -> Screen:
    """`validate_spec` com o contexto da execução já ligado, no formato que a formulação injeta."""
    ids, sources = set(employee_ids), list(evidence_sources)

    def screen(spec: SolveSpec) -> tuple[SolveSpec, list[tuple[str, str]]]:
        return validate_spec(spec, employee_ids=ids, week_start=week_start, card=card, evidence_sources=sources)

    return screen


def card_with_spec(card: RuleCard, spec: SolveSpec) -> RuleCard:
    """Cartão novo: as regras originais, intactas e na mesma ordem, mais uma regra `execucao` por restrição dura."""
    added: list[Rule] = []
    unavailable = weekly = 0
    for item in spec.constraints:
        if isinstance(item, UnavailableConstraint):
            unavailable += 1
            added.append(
                _execution_rule(
                    f"exec-indisp-{unavailable}",
                    "indisponibilidade",
                    {
                        "employee_id": item.employee_id,
                        "day": item.day.isoformat(),
                        "start": _hhmm(item.start),
                        "end": _hhmm(item.end),
                    },
                    item.evidence,
                )
            )
        elif isinstance(item, MaxWeeklyHoursConstraint):
            weekly += 1
            added.append(
                _execution_rule(
                    f"exec-maxh-{weekly}",
                    "jornada_semanal_max_pessoa",
                    {"employee_id": item.employee_id, "hours": int(item.hours)},
                    item.evidence,
                )
            )
    return RuleCard(
        reference_date=card.reference_date,
        rules=[*card.rules, *added],
        provisional=list(card.provisional),
        exceptions=list(card.exceptions),
    )


# ---------------------------------------------------------------------------------------------------------------------


def _reasons(
    item: AnyConstraint,
    employee_ids: set[str],
    week_start: date,
    week_end: date,
    weekly_limit: float | None,
    sources: list[str],
) -> list[str]:
    reasons: list[str] = []
    if item.employee_id not in employee_ids:
        reasons.append(f"a pessoa {item.employee_id} não existe no quadro")
    if isinstance(item, UnavailableConstraint | PreferredDayOffConstraint) and not week_start <= item.day <= week_end:
        reasons.append(
            f"o dia {item.day.isoformat()} está fora da semana planejada "
            f"({week_start.isoformat()} a {week_end.isoformat()})"
        )
    if isinstance(item, MaxWeeklyHoursConstraint) and weekly_limit is not None and item.hours >= weekly_limit:
        reasons.append(
            f"{LOOSEN_REASON}: o limite pedido ({item.hours}h) precisa ficar abaixo da jornada semanal máxima do "
            f"cartão ({_fmt_hours(weekly_limit)}h)"
        )
    if (
        isinstance(item, UnavailableConstraint)
        and item.start is not None
        and item.end is not None
        and item.start >= item.end
    ):
        reasons.append(f"o início ({_hhmm(item.start)}) precisa ser antes do fim ({_hhmm(item.end)})")
    evidence = _normalize(item.evidence)
    if not evidence or not any(evidence in source for source in sources):
        reasons.append("a evidência não é trecho literal do pedido do gestor nem das observações do arquivo")
    return reasons


def _weekly_limit(card: RuleCard) -> float | None:
    """Menor `jornada_semanal_max` do cartão; sem ela, um limite por pessoa só restringe e não há o que afrouxar."""
    limits = [float(r.params["hours"]) for r in card.rules if r.kind == WEEKLY_LIMIT_KIND and "hours" in r.params]
    return min(limits) if limits else None


def _key(item: AnyConstraint) -> tuple[Any, ...]:
    return tuple(sorted(item.model_dump(exclude={"evidence"}).items()))


def _describe(item: AnyConstraint) -> str:
    if isinstance(item, UnavailableConstraint):
        window = ""
        if item.start is not None or item.end is not None:
            window = f" {_hhmm(item.start) or '--:--'}–{_hhmm(item.end) or '--:--'}"
        return f"indisponível: {item.employee_id} em {item.day.isoformat()}{window}"
    if isinstance(item, MaxWeeklyHoursConstraint):
        return f"máximo de horas na semana: {item.employee_id}, {item.hours}h"
    if isinstance(item, PreferredDayOffConstraint):
        return f"folga preferida: {item.employee_id} em {item.day.isoformat()}"
    return f"janela preferida: {item.employee_id}, {item.window}"


def _execution_rule(rule_id: str, kind: str, params: dict[str, Any], evidence: str) -> Rule:
    return Rule(
        id=rule_id,
        kind=kind,
        layer=RuleLayer.EXECUCAO,
        status=RuleStatus.PEDIDO,
        params=params,
        source=f"{SOURCE_PREFIX}{evidence}",
    )


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _hhmm(value: time | None) -> str | None:
    return None if value is None else value.strftime("%H:%M")


def _fmt_hours(hours: float) -> str:
    return str(int(hours)) if hours == int(hours) else str(hours)
