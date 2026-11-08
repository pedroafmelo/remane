"""Carregador das camadas de regras (plano da C5, A1). Fixtures YAML no teste; só a fumaça lê `data/regras/`."""

from datetime import date
from pathlib import Path

import pytest

from escalista.domain.rules import RuleLayer, RuleStatus
from escalista.rules.loader import RuleFileError, load_rule_card, parse_layer
from escalista.rules.merge import build_card

DATA = Path(__file__).resolve().parents[2] / "data" / "regras"

LEI = """
regras:
  - id: jornada_semanal_max
    valores:
      - {ate: 2026-12-15, horas: 44}
      - {de: 2026-12-16, horas: 42}
      - {de: 2027-12-16, horas: 40}
    fonte: "art. 6º, I e II"
    status: interpretacao
  - id: jornada_diaria_max
    horas: 8
    fonte: "art. 7º, XIII CF"
    nota: "sem cláusula na CCT, vale 8h"
    status: interpretacao
  - id: interjornada_min
    horas: 11
    consecutivas: true
    fonte: "CLT, art. 66"
    status: conferida
  - id: repouso_semanal
    dias: 2
    vigencia: 2026-12-16
    fonte: "art. 7º, XV CF"
    status: interpretacao
  - id: adicional_hora_extra
    percentual_min: 50
    fonte: "CF, art. 7º, XVI"
    status: interpretacao
"""


def by_id(rules, rule_id):
    found = [r for r in rules if r.id == rule_id]
    assert len(found) == 1, (rule_id, found)
    return found[0]


# 1 ------------------------------------------------------------------------------------------------------


def test_loads_lei_layer():
    rules = parse_layer(LEI, RuleLayer.LEI, "lei/fixture.yaml")

    daily = by_id(rules, "jornada_diaria_max")
    assert daily.kind == "jornada_diaria_max"
    assert daily.layer is RuleLayer.LEI
    assert daily.params == {"hours": 8}
    assert daily.source == "art. 7º, XIII CF"
    assert daily.status is RuleStatus.INTERPRETACAO
    assert daily.note == "sem cláusula na CCT, vale 8h"

    assert by_id(rules, "interjornada_min").params == {"hours": 11}
    assert by_id(rules, "interjornada_min").status is RuleStatus.CONFERIDA
    assert by_id(rules, "repouso_semanal").params == {"days": 2}
    assert by_id(rules, "repouso_semanal").valid_from == date(2026, 12, 16)
    assert by_id(rules, "adicional_hora_extra").kind == "adicional_hora_extra"
    assert by_id(rules, "adicional_hora_extra").params == {"percent": 50}

    weekly = [r for r in rules if r.id == "jornada_semanal_max"]
    assert [r.params["hours"] for r in weekly] == [44, 42, 40]
    assert all(r.kind == "jornada_semanal_max" for r in weekly)


# 2 ------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("missing", ["id", "fonte", "status"])
def test_rejects_rule_without_id_source_or_status(missing):
    fields = {"id": "interjornada_min", "fonte": "CLT, art. 66", "status": "interpretacao"}
    body = "\n".join(f"    {k}: {v}" for k, v in fields.items() if k != missing)
    text = f"regras:\n  - horas: 11\n{body}\n"

    with pytest.raises(RuleFileError) as err:
        parse_layer(text, RuleLayer.LEI, "lei/sem_campo.yaml")

    assert "lei/sem_campo.yaml" in str(err.value)
    assert f"'{missing}'" in str(err.value)
    assert err.value.file_name == "lei/sem_campo.yaml"
    assert err.value.field == missing


def test_rejects_primitive_without_value_and_unknown_status():
    with pytest.raises(RuleFileError) as err:
        parse_layer("regras:\n  - {id: interjornada_min, fonte: f, status: interpretacao}\n", RuleLayer.LEI, "a.yaml")
    assert err.value.field == "horas"

    with pytest.raises(RuleFileError) as err:
        parse_layer("regras:\n  - {id: x, fonte: f, status: conferido}\n", RuleLayer.LEI, "b.yaml")
    assert err.value.field == "status" and "b.yaml" in str(err.value)

    with pytest.raises(RuleFileError) as err:
        parse_layer("regras: [\n", RuleLayer.LEI, "c.yaml")
    assert "c.yaml" in str(err.value)


# 3 ------------------------------------------------------------------------------------------------------


def test_ficticia_status_only_outside_lei():
    text = "regras:\n  - {id: adicional_hora_extra, percentual_min: 60, fonte: 'FICTICIO', status: ficticia}\n"

    for layer in (RuleLayer.CONVENCAO, RuleLayer.POLITICA):
        [rule] = parse_layer(text, layer, f"{layer.value}/demo.yaml")
        assert rule.status is RuleStatus.FICTICIA and rule.layer is layer

    with pytest.raises(RuleFileError) as err:
        parse_layer(text, RuleLayer.LEI, "lei/demo.yaml")
    assert err.value.field == "status" and "lei/demo.yaml" in str(err.value)


# 4 ------------------------------------------------------------------------------------------------------


def test_weekly_limit_by_reference_date():
    rules = parse_layer(LEI, RuleLayer.LEI, "lei/fixture.yaml")

    def weekly(day):
        return by_id(build_card(rules, day).rules, "jornada_semanal_max").params["hours"]

    assert weekly(date(2026, 12, 1)) == 44
    assert weekly(date(2026, 12, 15)) == 44
    assert weekly(date(2026, 12, 16)) == 42
    assert weekly(date(2027, 1, 11)) == 42
    assert weekly(date(2027, 12, 15)) == 42
    assert weekly(date(2027, 12, 16)) == 40

    before = build_card(rules, date(2026, 12, 1))
    assert before.reference_date == date(2026, 12, 1)
    assert not [r for r in before.rules if r.id == "repouso_semanal"]  # ainda não vigente
    assert by_id(build_card(rules, date(2027, 1, 11)).rules, "repouso_semanal").params == {"days": 2}


# 7 ------------------------------------------------------------------------------------------------------


def test_rules_outside_slice_are_info_with_status():
    text = """
regras:
  - id: hipersuficiente_like
    multiplicador: 2.5
    fonte: "art. 8º"
    status: pendente
excecoes:
  - id: regime_12x36
    descricao: "12 por 36"
    fonte: "CLT, art. 59-A"
    acao: escalar
    nota: "fora do solver padrão"
    status: interpretacao
  - id: interjornada_min
    descricao: "mesmo id de primitiva, mas é exceção: não vira restrição"
    fonte: "f"
    acao: verificar_convencao
    status: interpretacao
"""
    info, regime, exc_like = parse_layer(text, RuleLayer.LEI, "lei/info.yaml")

    assert info.kind == "info" and info.status is RuleStatus.PENDENTE and info.action is None
    assert info.params == {"multiplicador": 2.5}
    assert regime.kind == "info" and regime.status is RuleStatus.INTERPRETACAO
    assert regime.action == "escalar" and regime.note == "fora do solver padrão"
    assert regime.params == {"descricao": "12 por 36"}
    assert exc_like.kind == "info" and exc_like.action == "verificar_convencao"

    card = build_card([info, regime], date(2027, 1, 11))
    assert {(r.id, r.kind, r.status) for r in card.rules} == {
        ("hipersuficiente_like", "info", RuleStatus.PENDENTE),
        ("regime_12x36", "info", RuleStatus.INTERPRETACAO),
    }
    assert card.provisional == [] and card.exceptions == []

    with pytest.raises(RuleFileError) as err:
        parse_layer("excecoes:\n  - {id: x, fonte: f, status: pendente, acao: aprovar}\n", RuleLayer.LEI, "e.yaml")
    assert err.value.field == "acao"


# fumaça com os arquivos reais ------------------------------------------------------------------------------


def test_smoke_real_rule_files():
    card = load_rule_card(DATA, date(2027, 1, 11))
    slice_rules = {r.kind: r for r in card.rules if r.kind != "info"}

    assert slice_rules["jornada_semanal_max"].params == {"hours": 42}
    assert slice_rules["jornada_diaria_max"].params == {"hours": 8}
    assert slice_rules["interjornada_min"].params == {"hours": 11}
    assert slice_rules["repouso_semanal"].params == {"days": 2}
    premium = slice_rules["adicional_hora_extra"]
    assert premium.params == {"percent": 60}
    assert premium.layer is RuleLayer.CONVENCAO and premium.status is RuleStatus.FICTICIA
    assert len([r for r in card.rules if r.kind != "info"]) == 5
    assert card.provisional == [] and card.exceptions == []

    policy_exc = by_id(card.rules, "hora_extra_autorizacao_dp")
    assert policy_exc.action == "escalar" and policy_exc.layer is RuleLayer.POLITICA
    assert by_id(card.rules, "regime_12x36").kind == "info"

    before = load_rule_card(DATA, date(2026, 12, 1))
    assert by_id(before.rules, "jornada_semanal_max").params == {"hours": 44}
