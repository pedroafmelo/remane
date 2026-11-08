"""Fusão das camadas no `RuleCard` (plano da C5, A1). Função pura.

Regra de fusão ("a política só restringe", data/regras/README.md): a ordem é lei > convenção > política. Para
cada primitiva da fatia, entre as regras vigentes na data de referência, vale a mais restritiva (ver `PRIMITIVES`);
no empate, fica a camada mais alta. Se uma camada mais baixa for **mais frouxa** que uma mais alta, a regra mais
restritiva entra **provisoriamente**: o id vai para `RuleCard.provisional` e abre-se um `ExceptionCard` RX-01 ao gestor,
com as duas fontes na evidência. Regras `info` não se fundem: todas as vigentes seguem no cartão.

Cartão da semana (`build_week_card`, plano da C6, seção 8): monta o cartão no 1º dia e em cada dia da semana em que o
conjunto de regras vigentes muda. Sem mudança, é exatamente `build_card(rules, week_start)` (E1 e C5 não mudam). Com
mudança, por primitiva vale a mais restritiva entre os dias, na semana inteira, e o id dela entra em `provisional` se o
valor mudou na semana, se a primitiva falta em algum dia ou se já era provisória em algum dia. Regras `info` e
`ExceptionCard` de qualquer dia seguem no cartão, sem repetir. A `Rule` aplicada é a original (vigência do YAML
intacta): nenhum consumidor filtra o cartão por data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from escalista.domain.contracts import ExceptionCard, Role
from escalista.domain.rules import Rule, RuleCard, RuleLayer


@dataclass(frozen=True)
class Primitive:
    """Primitiva da fatia: chave única em `Rule.params` e sentido do "mais restritivo"."""

    param: str
    stricter: str  # "lower": limite máximo; "higher": mínimo ou adicional (mais protetivo ao trabalhador)


PRIMITIVES: dict[str, Primitive] = {
    "jornada_semanal_max": Primitive("hours", "lower"),
    "jornada_diaria_max": Primitive("hours", "lower"),
    "interjornada_min": Primitive("hours", "higher"),
    "repouso_semanal": Primitive("days", "higher"),
    "adicional_hora_extra": Primitive("percent", "higher"),
}
LAYER_RANK = {RuleLayer.LEI: 0, RuleLayer.CONVENCAO: 1, RuleLayer.POLITICA: 2}
CONFLICT_CODE = "RX-01"


def is_in_force(rule: Rule, day: date) -> bool:
    return (rule.valid_from is None or rule.valid_from <= day) and (rule.valid_to is None or day <= rule.valid_to)


def build_card(rules: list[Rule], reference_date: date) -> RuleCard:
    """Filtra as regras vigentes em `reference_date` e funde as camadas. A ordem de saída é a da primeira aparição."""
    in_force = [r for r in rules if is_in_force(r, reference_date)]
    groups: dict[str, list[Rule]] = {}
    for rule in in_force:
        if rule.kind in PRIMITIVES:
            groups.setdefault(rule.kind, []).append(rule)

    merged: list[Rule] = []
    provisional: list[str] = []
    exceptions: list[ExceptionCard] = []
    emitted: set[str] = set()
    for rule in in_force:
        if rule.kind not in PRIMITIVES:
            merged.append(rule)
            continue
        if rule.kind in emitted:
            continue
        emitted.add(rule.kind)
        winner, conflicts = _merge_primitive(groups[rule.kind])
        merged.append(winner)
        if conflicts:
            provisional.append(winner.id)
            exceptions += [_conflict_card(winner, looser, stricter) for looser, stricter in conflicts]

    return RuleCard(reference_date=reference_date, rules=merged, provisional=provisional, exceptions=exceptions)


def build_week_card(rules: list[Rule], week_start: date) -> RuleCard:
    """Cartão da semana que começa em `week_start` (segunda-feira). Função pura; ver o docstring do módulo."""
    if week_start.weekday() != 0:
        raise ValueError("week_start deve ser uma segunda-feira")
    days = [week_start + timedelta(days=i) for i in range(7)]
    in_force = [frozenset(i for i, r in enumerate(rules) if is_in_force(r, d)) for d in days]
    change_days = [d for d, prev, cur in zip(days[1:], in_force, in_force[1:], strict=False) if cur != prev]
    if not change_days:
        return build_card(rules, week_start)

    cards = [build_card(rules, d) for d in [week_start, *change_days]]
    provisional_kinds = {r.kind for c in cards for r in c.rules if r.id in c.provisional}
    merged: list[Rule] = []
    provisional: list[str] = []
    seen: set[str] = set()
    for card in cards:
        for rule in card.rules:
            key = rule.kind if rule.kind in PRIMITIVES else rule.model_dump_json()
            if key in seen:
                continue
            seen.add(key)
            if rule.kind not in PRIMITIVES:
                merged.append(rule)
                continue
            winners = [r for c in cards for r in c.rules if r.kind == rule.kind]
            chosen = winners[0]
            for other in winners[1:]:
                if _stricter(other, chosen):
                    chosen = other
            merged.append(chosen)
            changed = len(winners) < len(cards) or any(_value(w) != _value(chosen) for w in winners)
            if (changed or rule.kind in provisional_kinds) and chosen.id not in provisional:
                provisional.append(chosen.id)

    exceptions: list[ExceptionCard] = []
    for card in cards:
        exceptions += [e for e in card.exceptions if e not in exceptions]
    return RuleCard(reference_date=week_start, rules=merged, provisional=provisional, exceptions=exceptions)


def _value(rule: Rule) -> float:
    primitive = PRIMITIVES[rule.kind]
    return rule.params[primitive.param]


def _stricter(a: Rule, b: Rule) -> bool:
    """`a` é estritamente mais restritiva que `b`."""
    if PRIMITIVES[a.kind].stricter == "lower":
        return _value(a) < _value(b)
    return _value(a) > _value(b)


def _merge_primitive(rules: list[Rule]) -> tuple[Rule, list[tuple[Rule, Rule]]]:
    """Devolve a regra aplicada e os pares (mais frouxa de camada baixa, mais restritiva de camada alta)."""
    ordered = sorted(rules, key=lambda r: LAYER_RANK[r.layer])  # estável: no empate, a primeira aparição
    winner = ordered[0]
    conflicts: list[tuple[Rule, Rule]] = []
    bound: Rule | None = None  # a mais restritiva das camadas acima da atual
    for layer in RuleLayer:
        in_layer = [r for r in ordered if r.layer is layer]
        if bound is not None:
            conflicts += [(r, bound) for r in in_layer if _stricter(bound, r)]
        for r in in_layer:
            if bound is None or _stricter(r, bound):
                bound = r
            if _stricter(r, winner):
                winner = r
    return winner, conflicts


def _describe(rule: Rule) -> str:
    primitive = PRIMITIVES[rule.kind]
    return f"{rule.layer.value}: {primitive.param}={_value(rule)} ({rule.source}; status {rule.status.value})"


def _conflict_card(applied: Rule, looser: Rule, stricter: Rule) -> ExceptionCard:
    return ExceptionCard(
        code=CONFLICT_CODE,
        title=f"Conflito entre camadas em {applied.id}",
        reason=(
            f"A camada {looser.layer.value} é mais frouxa que a {stricter.layer.value} em {applied.id}. "
            "A regra mais restritiva foi aplicada de forma provisória até o gestor decidir."
        ),
        decider=Role.GESTOR,
        evidence=[_describe(looser), _describe(stricter), f"aplicada (provisória): {_describe(applied)}"],
        recommendation=f"Manter a mais restritiva ({_describe(applied)}) e corrigir a camada {looser.layer.value}.",
        if_no_answer="A regra mais restritiva segue aplicada como provisória.",
    )
