"""Justificativa da escala (RF-06): o modelo pequeno escreve só com fatos do solver e regras do cartão.

- Entrada de fatos: `JustifyFacts` (comparação antes/depois, verificação, status do solver, descoberto).
- Sem dado pessoal no prompt (RN-13): só ids (`employee_id`, `store_id`), datas e números; nem `Violation.detail`
  entra, porque o texto livre do verificador pode citar nome.
- Todo `rule_ref` precisa ser um id do cartão: senão reenvia (até 2 vezes) e depois RX-12 (`call_structured`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from escalista.domain.contracts import LLMMessage
from escalista.domain.ports import LLMClient
from escalista.domain.results import Comparison, Justification, SolveResult, ViolationReport
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot
from escalista.llm.structured import call_structured

KIND = "llm.justify"
TOOL_NAME = "registrar_justificativa"
MAX_LISTED = 20  # violações e lacunas listadas no prompt; o resto vira contagem

SYSTEM = (
    "Você escreve a justificativa de uma escala semanal de lojas, em português do Brasil, para o gerente. "
    "Use SOMENTE os fatos e as regras fornecidos. Não invente números, pessoas, regras nem datas. "
    "Cada item explica uma escolha ou um resultado e cita em `rule_refs` apenas ids da lista de regras; "
    "se o item se apoia só em números dos fatos, deixe `rule_refs` vazio. "
    "Regras com status diferente de `conferida` são provisórias ou fictícias: diga isso ao citá-las. "
    "Seja curto: um resumo de 1 a 3 frases e de 2 a 5 itens. Responda chamando a ferramenta."
)


@dataclass(frozen=True)
class JustifyFacts:
    """Fatos medidos pelo solver, pelo verificador e pela função de custo. Nada aqui é dado pessoal."""

    comparison: Comparison
    report: ViolationReport
    status: str  # `SolveResult.status`: optimal, feasible, infeasible ou timeout
    uncovered: list[DemandSlot] = field(default_factory=list)

    @classmethod
    def from_solve(cls, result: SolveResult, comparison: Comparison, report: ViolationReport) -> JustifyFacts:
        return cls(comparison=comparison, report=report, status=result.status, uncovered=list(result.uncovered))


def justify(
    client: LLMClient,
    *,
    card: RuleCard,
    facts: JustifyFacts,
    run_id: str,
    parent_id: str | None = None,
) -> Justification:
    """Justificativa estruturada. Levanta `LLMUnavailableError` (RX-12) se o modelo falhar ou insistir em ref errada."""
    valid_ids = {rule.id for rule in card.rules}

    def check_refs(value: Justification) -> None:
        if not value.summary.strip():
            raise ValueError("`summary` está vazio")
        if not value.items:
            raise ValueError("`items` está vazio")
        bad = sorted({ref for item in value.items for ref in item.rule_refs if ref not in valid_ids})
        if bad:
            raise ValueError(f"rule_refs inexistentes no cartão: {bad}; use só estes ids: {sorted(valid_ids)}")

    return call_structured(
        client,
        Justification,
        messages=build_messages(card, facts),
        run_id=run_id,
        parent_id=parent_id,
        tool_name=TOOL_NAME,
        tool_description="Registra o resumo e os itens da justificativa, cada item com os ids das regras citadas.",
        size="small",
        kind=KIND,
        validate=check_refs,
        what="justificativa",
    )


def build_messages(card: RuleCard, facts: JustifyFacts) -> list[LLMMessage]:
    user = (
        "Regras do cartão (cite só estes ids):\n"
        f"{_dump(_rules(card))}\n\n"
        "Fatos do solver e do verificador:\n"
        f"{_dump(_facts(facts))}\n\n"
        "Escreva a justificativa."
    )
    return [LLMMessage(role="system", content=SYSTEM), LLMMessage(role="user", content=user)]


def _rules(card: RuleCard) -> list[dict[str, Any]]:
    return [
        {"id": r.id, "tipo": r.kind, "status": str(r.status), "fonte": r.source, "parametros": r.params}
        for r in card.rules
    ]


def _facts(facts: JustifyFacts) -> dict[str, Any]:
    violations = facts.report.violations
    uncovered = facts.uncovered
    return {
        "status_solver": facts.status,
        "comparacao": facts.comparison.model_dump(mode="json"),
        "violacoes": {
            "total": facts.report.total,
            "itens": [
                {
                    "regra": v.rule_id,
                    "tipo": v.kind,
                    "colaborador": v.employee_id,
                    "dia": v.day.isoformat() if v.day else None,
                    "fonte": v.source,
                }
                for v in violations[:MAX_LISTED]
            ],
            "omitidas": max(0, len(violations) - MAX_LISTED),
        },
        "descoberto": {
            "faixas": len(uncovered),
            "pessoas_faltantes_total": sum(s.required for s in uncovered),
            "itens": [s.model_dump(mode="json") for s in uncovered[:MAX_LISTED]],
            "omitidas": max(0, len(uncovered) - MAX_LISTED),
        },
    }


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
