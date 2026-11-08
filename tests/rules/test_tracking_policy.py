"""Parâmetros do acompanhamento lidos da política fictícia e exceções RX-06 e RX-09 (C7 A2)."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from escalista.domain.tracking import TrackPolicy
from escalista.rules.tracking_policy import POLICY_FILE, TrackPolicyError, load_track_policy

POLICY = yaml.safe_load(Path(POLICY_FILE).read_text(encoding="utf-8"))


def test_reads_the_current_values_of_the_fictional_policy():
    assert load_track_policy() == TrackPolicy(
        late_tolerance_min=10,
        answer_deadline_min=15,
        offer_deadline_min=20,
        max_candidates=3,
        overtime_weekly_limit_h=Decimal("6"),
        overtime_warn_pct=80,
        late_cover_from_min=30,
    )


def test_late_cover_threshold_is_a_fictional_proposal():
    (rule,) = [r for r in POLICY["regras"] if r["id"] == "pol_atraso"]
    assert rule["cobertura_a_partir_de_min"] == 30
    assert rule["status"] == "interpretacao"
    assert "confirmar com Pedro Veloso" in rule["nota_cobertura"]


def test_missing_late_cover_threshold_means_never(tmp_path):
    assert load_track_policy(_write_without(tmp_path, "pol_atraso", "cobertura_a_partir_de_min")).late_cover_from_min is None


def test_non_integer_late_cover_threshold_is_rejected(tmp_path):
    raw = yaml.safe_load(Path(POLICY_FILE).read_text(encoding="utf-8"))
    for rule in raw["regras"]:
        if rule["id"] == "pol_atraso":
            rule["cobertura_a_partir_de_min"] = "meia hora"
    path = tmp_path / "politica.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(TrackPolicyError, match=r"pol_atraso\.cobertura_a_partir_de_min"):
        load_track_policy(path)


def test_weekly_limit_is_decimal():
    assert isinstance(load_track_policy().overtime_weekly_limit_h, Decimal)


def _write_without(tmp_path, rule_id: str, field: str | None) -> Path:
    raw = yaml.safe_load(Path(POLICY_FILE).read_text(encoding="utf-8"))
    if field is None:
        raw["regras"] = [r for r in raw["regras"] if r["id"] != rule_id]
    else:
        for rule in raw["regras"]:
            if rule["id"] == rule_id:
                del rule[field]
    path = tmp_path / "politica.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("rule_id", "field"),
    [
        ("pol_atraso", "tolerancia_min"),
        ("pol_atraso", "prazo_resposta_colaborador_min"),
        ("pol_oferta_turno", "prazo_por_candidato_min"),
        ("pol_oferta_turno", "candidatos_max_antes_de_escalar"),
        ("pol_hora_extra", "limite_semanal_por_pessoa_horas"),
        ("pol_aviso_hora_extra_estourando", "dispara_em_percentual_do_limite"),
    ],
)
def test_missing_field_raises_a_clear_error(tmp_path, rule_id, field):
    with pytest.raises(TrackPolicyError, match=rf"{rule_id}\.{field}"):
        load_track_policy(_write_without(tmp_path, rule_id, field))


def test_missing_rule_raises_a_clear_error(tmp_path):
    with pytest.raises(TrackPolicyError, match="pol_oferta_turno"):
        load_track_policy(_write_without(tmp_path, "pol_oferta_turno", None))


def test_non_integer_value_is_rejected(tmp_path):
    path = tmp_path / "politica.yaml"
    raw = yaml.safe_load(Path(POLICY_FILE).read_text(encoding="utf-8"))
    for rule in raw["regras"]:
        if rule["id"] == "pol_atraso":
            rule["tolerancia_min"] = "dez"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(TrackPolicyError, match=r"pol_atraso\.tolerancia_min"):
        load_track_policy(path)


# --- RX-06 e RX-09 em `excecoes_demo` --------------------------------------------------------------------------------


def _exception(code: str) -> dict:
    (entry,) = [e for e in POLICY["excecoes_demo"] if e["code"] == code]
    return entry


def test_rx06_mirrors_rx05_options_and_recommendation():
    rx05, rx06 = _exception("RX-05"), _exception("RX-06")
    assert rx06["titulo"] == "Ninguém aceitou o turno no prazo"
    assert rx06["motivo"] == "Os colegas elegíveis não aceitaram a oferta do turno dentro do prazo da política."
    assert (rx06["gatilho"], rx06["decisor"], rx06["prazo_min"], rx06["acao"]) == (
        "pol_oferta_turno",
        "gestor",
        30,
        "escalar",
    )
    assert rx06["opcoes"] == rx05["opcoes"]
    assert rx06["recomendacao"] == rx05["recomendacao"]
    assert rx06["sem_resposta"] == "O turno fica descoberto e registrado no painel."
    assert rx06["status"] == "interpretacao"
    assert "proposta do agente (C7)" in rx06["fonte"]


def test_rx09_options():
    rx09 = _exception("RX-09")
    assert rx09["titulo"] == "Colaborador não respondeu sobre a falta ou o atraso"
    assert (
        rx09["motivo"] == "O ponto não registrou a entrada e o colaborador não respondeu à pergunta do agente no prazo."
    )
    expected = ("pol_atraso", "gestor", 30, "escalar")
    assert (rx09["gatilho"], rx09["decisor"], rx09["prazo_min"], rx09["acao"]) == expected
    assert [(o["rotulo"], o["efeito"], o["custo_base"]) for o in rx09["opcoes"]] == [
        (
            "Tratar como falta e buscar cobertura",
            "O agente abre o replanejamento e oferece o turno ao próximo colega elegível.",
            "nenhum",
        ),
        ("Aguardar mais 15 min", "O agente pergunta de novo e espera mais 15 min.", "nenhum"),
        ("Registrar o atraso sem cobertura", "Fica registrado; a escala não muda.", "nenhum"),
    ]
    assert rx09["recomendacao"] == "Tratar como falta e buscar cobertura."
    assert rx09["sem_resposta"] == "O turno fica descoberto e registrado."
    assert rx09["status"] == "interpretacao"
    assert "proposta do agente (C7)" in rx09["fonte"]


@pytest.mark.parametrize("code", ["RX-06", "RX-09"])
def test_new_exceptions_build_a_card_like_the_existing_ones(code):
    from escalista.api.excecoes import load_policy_exceptions, policy_card

    card = policy_card(load_policy_exceptions()[code], datetime(2027, 1, 13, 14, 0), ["evidência"])
    assert card.code == code
    assert card.deadline == datetime(2027, 1, 13, 14, 30)
    assert len(card.options) == 3


def test_exception_codes_are_unique():
    codes = [e["code"] for e in POLICY["excecoes_demo"]]
    assert len(codes) == len(set(codes))


def test_fractional_weekly_limit_is_kept_exact(tmp_path):
    raw = yaml.safe_load(Path(POLICY_FILE).read_text(encoding="utf-8"))
    for rule in raw["regras"]:
        if rule["id"] == "pol_hora_extra":
            rule["limite_semanal_por_pessoa_horas"] = 6.5
    path = tmp_path / "politica.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    assert load_track_policy(path).overtime_weekly_limit_h == Decimal("6.5")
