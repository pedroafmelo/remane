"""Parâmetros do acompanhamento lidos da política fictícia (plano da C7, A2): `TrackPolicy`.

Lê só o que o varredor e o fluxo usam: `pol_atraso` (tolerância e prazo de resposta do colaborador),
`pol_oferta_turno` (prazo por candidato e máximo de candidatos), `pol_hora_extra` (limite semanal) e
`pol_aviso_hora_extra_estourando` (percentual do aviso). Não inventa valor: campo ausente ou não inteiro levanta
`TrackPolicyError` com o caminho do campo (`<id da regra>.<campo>`).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from escalista.domain.tracking import TrackPolicy

# Relativo à raiz do repositório, como `DEFAULT_RULES_DIR` do app.
POLICY_FILE = Path("data/regras/politica/politica_ficticia.yaml")


class TrackPolicyError(ValueError):
    """A política não traz um parâmetro do acompanhamento, ou o traz num formato que não serve."""

    def __init__(self, path: Path, where: str, problem: str) -> None:
        super().__init__(f"{path}: {where}: {problem}")
        self.where = where


def _int(rules: dict[str, dict[str, Any]], path: Path, rule_id: str, field: str) -> int:
    where = f"{rule_id}.{field}"
    if rule_id not in rules:
        raise TrackPolicyError(path, where, f"regra '{rule_id}' ausente em 'regras'")
    if field not in rules[rule_id]:
        raise TrackPolicyError(path, where, "campo obrigatório ausente")
    value = rules[rule_id][field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrackPolicyError(path, where, f"esperado um número inteiro, veio {value!r}")
    return value


def _hours(rules: dict[str, dict[str, Any]], path: Path, rule_id: str, field: str) -> Decimal:
    where = f"{rule_id}.{field}"
    if rule_id not in rules:
        raise TrackPolicyError(path, where, f"regra '{rule_id}' ausente em 'regras'")
    if field not in rules[rule_id]:
        raise TrackPolicyError(path, where, "campo obrigatório ausente")
    value = rules[rule_id][field]
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise TrackPolicyError(path, where, f"esperado um número de horas positivo, veio {value!r}")
    return Decimal(str(value))


def load_track_policy(path: Path = POLICY_FILE) -> TrackPolicy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("regras"), list):
        raise TrackPolicyError(path, "regras", "a política precisa ter a lista 'regras'")
    rules = {r["id"]: r for r in raw["regras"] if isinstance(r, dict) and "id" in r}

    def get(rule_id: str, field: str) -> int:
        return _int(rules, path, rule_id, field)

    return TrackPolicy(
        late_tolerance_min=get("pol_atraso", "tolerancia_min"),
        answer_deadline_min=get("pol_atraso", "prazo_resposta_colaborador_min"),
        offer_deadline_min=get("pol_oferta_turno", "prazo_por_candidato_min"),
        max_candidates=get("pol_oferta_turno", "candidatos_max_antes_de_escalar"),
        overtime_weekly_limit_h=_hours(rules, path, "pol_hora_extra", "limite_semanal_por_pessoa_horas"),
        overtime_warn_pct=get("pol_aviso_hora_extra_estourando", "dispara_em_percentual_do_limite"),
    )
