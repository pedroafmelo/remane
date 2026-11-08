"""Fusão das camadas: "a política só restringe"; conflito → mais restritiva provisória + exceção ao gestor (RX-01)."""

from datetime import date

from escalista.domain.contracts import Role
from escalista.domain.rules import RuleLayer, RuleStatus
from escalista.rules.loader import parse_layer
from escalista.rules.merge import build_card

DAY = date(2027, 1, 11)

LEI = """
regras:
  - {id: jornada_semanal_max, horas: 42, fonte: "LEI-semana", status: interpretacao}
  - {id: jornada_diaria_max, horas: 8, fonte: "LEI-dia", status: interpretacao}
  - {id: interjornada_min, horas: 11, fonte: "LEI-interjornada", status: interpretacao}
  - {id: repouso_semanal, dias: 2, fonte: "LEI-repouso", status: interpretacao}
  - {id: adicional_hora_extra, percentual_min: 50, fonte: "LEI-adicional", status: interpretacao}
"""


def card_of(**layers):
    rules = parse_layer(LEI, RuleLayer.LEI, "lei/fixture.yaml")
    for name, text in layers.items():
        layer = RuleLayer(name)
        rules += parse_layer(text, layer, f"{name}/fixture.yaml")
    return build_card(rules, DAY)


def only(card, rule_id):
    found = [r for r in card.rules if r.id == rule_id]
    assert len(found) == 1, found
    return found[0]


# 5 ------------------------------------------------------------------------------------------------------


def test_policy_more_restrictive_wins():
    politica = """
regras:
  - {id: jornada_semanal_max, horas: 40, fonte: "POL-semana", status: ficticia}
  - {id: interjornada_min, horas: 12, fonte: "POL-interjornada", status: ficticia}
  - {id: repouso_semanal, dias: 2, fonte: "POL-repouso", status: ficticia}
"""
    convencao = "regras:\n  - {id: adicional_hora_extra, percentual_min: 60, fonte: CCT-adicional, status: ficticia}\n"
    card = card_of(convencao=convencao, politica=politica)

    weekly = only(card, "jornada_semanal_max")
    assert weekly.params == {"hours": 40} and weekly.layer is RuleLayer.POLITICA and weekly.source == "POL-semana"
    assert weekly.status is RuleStatus.FICTICIA
    assert only(card, "interjornada_min").params == {"hours": 12}
    assert only(card, "adicional_hora_extra").params == {"percent": 60}
    assert only(card, "adicional_hora_extra").layer is RuleLayer.CONVENCAO
    repouso = only(card, "repouso_semanal")  # empate: fica a camada mais alta
    assert repouso.layer is RuleLayer.LEI and repouso.source == "LEI-repouso"
    assert only(card, "jornada_diaria_max").params == {"hours": 8}
    assert card.provisional == [] and card.exceptions == []


# 6 ------------------------------------------------------------------------------------------------------


def test_policy_looser_than_law_applies_law_provisionally_and_opens_exception():
    politica = """
regras:
  - {id: jornada_semanal_max, horas: 44, fonte: "POL-semana", status: ficticia}
  - {id: interjornada_min, horas: 10, fonte: "POL-interjornada", status: ficticia}
"""
    convencao = "regras:\n  - {id: adicional_hora_extra, percentual_min: 40, fonte: CCT-adicional, status: ficticia}\n"
    card = card_of(convencao=convencao, politica=politica)

    weekly = only(card, "jornada_semanal_max")
    assert weekly.params == {"hours": 42} and weekly.layer is RuleLayer.LEI and weekly.source == "LEI-semana"
    assert only(card, "interjornada_min").params == {"hours": 11}
    assert only(card, "adicional_hora_extra").params == {"percent": 50}
    assert sorted(card.provisional) == ["adicional_hora_extra", "interjornada_min", "jornada_semanal_max"]

    assert len(card.exceptions) == 3
    assert all(e.decider is Role.GESTOR and e.code == "RX-01" for e in card.exceptions)
    weekly_exc = next(e for e in card.exceptions if "jornada_semanal_max" in e.title)
    evidence = " | ".join(weekly_exc.evidence)
    assert "POL-semana" in evidence and "LEI-semana" in evidence
    assert "44" in evidence and "42" in evidence


def test_policy_looser_than_convention_is_also_a_conflict():
    convencao = "regras:\n  - {id: adicional_hora_extra, percentual_min: 60, fonte: CCT-adicional, status: ficticia}\n"
    politica = "regras:\n  - {id: adicional_hora_extra, percentual_min: 55, fonte: 'POL-adicional', status: ficticia}\n"
    card = card_of(convencao=convencao, politica=politica)

    assert only(card, "adicional_hora_extra").params == {"percent": 60}
    assert card.provisional == ["adicional_hora_extra"]
    [exc] = card.exceptions
    assert "CCT-adicional" in " ".join(exc.evidence) and "POL-adicional" in " ".join(exc.evidence)


def test_merge_only_considers_rules_in_force():
    politica = "regras:\n  - {id: jornada_semanal_max, horas: 44, ate: 2026-12-31, fonte: POL-old, status: ficticia}\n"
    card = card_of(politica=politica)
    assert only(card, "jornada_semanal_max").params == {"hours": 42}
    assert card.provisional == [] and card.exceptions == []
