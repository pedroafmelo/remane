"""Verificador independente, sem OR-Tools (núcleo; RF-02). Não importa o solver: confere a escala contra o cartão."""

from __future__ import annotations

from collections.abc import Callable

from escalista.domain.results import Violation, ViolationReport
from escalista.domain.rules import Rule, RuleCard
from escalista.domain.schedule import Schedule
from escalista.verifier.checks import (
    check_daily_hours,
    check_rest_between_shifts,
    check_weekly_hours,
    check_weekly_rest,
)
from escalista.verifier.coverage import coverage_gaps

Check = Callable[[Schedule, Rule], list[Violation]]

# Ordem do relatório. Regra de outro `kind` (ex.: `info`, `adicional_hora_extra`) não é verificada aqui.
CHECKS: dict[str, Check] = {
    "jornada_semanal_max": check_weekly_hours,
    "jornada_diaria_max": check_daily_hours,
    "interjornada_min": check_rest_between_shifts,
    "repouso_semanal": check_weekly_rest,
}


def verify(schedule: Schedule, card: RuleCard) -> ViolationReport:
    """Roda cada primitiva presente no cartão. Regra ausente do cartão: a verificação não roda."""
    violations: list[Violation] = []
    for kind, check in CHECKS.items():
        for rule in card.rules:
            if rule.kind == kind:
                violations += check(schedule, rule)
    return ViolationReport(violations=violations)


__all__ = [
    "CHECKS",
    "check_daily_hours",
    "check_rest_between_shifts",
    "check_weekly_hours",
    "check_weekly_rest",
    "coverage_gaps",
    "verify",
]
