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
    rest = slice_rules["interjornada_min"]
    assert (rest.id, rest.layer, rest.params) == ("pol_interjornada", RuleLayer.POLITICA, {"hours": 12})
    assert slice_rules["repouso_semanal"].params == {"days": 2}
    premium = slice_rules["adicional_hora_extra"]
    assert (premium.id, premium.params) == ("cct_adicional_hora_extra", {"percent": 60})
    assert premium.layer is RuleLayer.CONVENCAO and premium.status is RuleStatus.INTERPRETACAO
    assert len([r for r in card.rules if r.kind != "info"]) == 5
    assert card.provisional == [] and card.exceptions == []  # a ampliação diária da CCT é `info`: sem RX-01
    assert by_id(card.rules, "cct_jornada_diaria_ampliada").kind == "info"

    policy_exc = by_id(card.rules, "hora_extra_autorizacao_dp")
    assert policy_exc.action == "escalar" and policy_exc.layer is RuleLayer.POLITICA
    assert by_id(card.rules, "regime_12x36").kind == "info"

    before = load_rule_card(DATA, date(2026, 12, 1))
    assert by_id(before.rules, "jornada_semanal_max").params == {"hours": 44}


# 8 · `restringe:` apontando para uma primitiva (formato da convenção e da política de Pedro Veloso) --------------

TARGETED = """
regras:
  - id: cct_adicional_hora_extra
    percentual: 60
    percentual_domingo_feriado: 100
    fonte: "Convenção fictícia, cláusula 8ª"
    restringe: adicional_hora_extra
    status: interpretacao
  - id: pol_interjornada
    horas: 12
    fonte: "Política fictícia, item 3"
    restringe: interjornada_min
    status: interpretacao
  - id: cct_jornada_diaria_ampliada
    horas: 9
    de: 2026-12-16
    ate: 2027-08-31
    fonte: "Convenção fictícia, cláusula 5ª"
    amplia: jornada_diaria_max
    status: pendente
  - id: cct_repouso_quinzenal
    dias: 3
    vigencia: 2026-12-16
    fonte: "Convenção fictícia"
    restringe: repouso_semanal
    status: interpretacao
"""


def test_restricting_rule_becomes_the_primitive_it_points_to():
    rules = parse_layer(TARGETED, RuleLayer.CONVENCAO, "convencao/cct.yaml")

    premium = by_id(rules, "cct_adicional_hora_extra")
    assert premium.kind == "adicional_hora_extra"
    assert premium.params == {"percent": 60}
    assert premium.layer is RuleLayer.CONVENCAO and premium.status is RuleStatus.INTERPRETACAO
    assert premium.source == "Convenção fictícia, cláusula 8ª"

    rest = by_id(rules, "pol_interjornada")
    assert (rest.kind, rest.params) == ("interjornada_min", {"hours": 12})

    weekly_rest = by_id(rules, "cct_repouso_quinzenal")
    assert (weekly_rest.kind, weekly_rest.params) == ("repouso_semanal", {"days": 3})
    assert weekly_rest.valid_from == date(2026, 12, 16)

    [policy] = parse_layer(
        "regras:\n  - {id: pol_x, horas: 12, fonte: f, restringe: interjornada_min, status: interpretacao}\n",
        RuleLayer.POLITICA,
        "politica/p.yaml",
    )
    assert (policy.id, policy.kind, policy.layer) == ("pol_x", "interjornada_min", RuleLayer.POLITICA)


def test_widening_rule_stays_info_and_does_not_open_a_conflict():
    """`amplia:` ainda não alimenta o motor (a fatia não precisa: 5 × 8h = 40h < 42h), então não vira RX-01."""
    rules = parse_layer(TARGETED, RuleLayer.CONVENCAO, "convencao/cct.yaml")

    daily = by_id(rules, "cct_jornada_diaria_ampliada")
    assert daily.kind == "info"
    assert daily.params["horas"] == 9 and daily.params["amplia"] == "jornada_diaria_max"
    assert daily.status is RuleStatus.PENDENTE
    assert (daily.valid_from, daily.valid_to) == (date(2026, 12, 16), date(2027, 8, 31))

    law = parse_layer(LEI, RuleLayer.LEI, "lei/fixture.yaml")
    for day in (date(2026, 12, 16), date(2027, 1, 11)):
        card = build_card(law + rules, day)
        assert by_id(card.rules, "jornada_diaria_max").params == {"hours": 8}
        assert by_id(card.rules, "cct_jornada_diaria_ampliada").kind == "info"
        assert card.provisional == [] and card.exceptions == []


@pytest.mark.parametrize(
    "target", ["trabalho_noturno", "compensacao_jornada", "hora_extra_limite_diario", "menor_trabalho_noturno"]
)
def test_targeted_rule_outside_the_slice_stays_info(target):
    text = f"regras:\n  - {{id: c, percentual: 25, horas: 1.5, fonte: f, restringe: {target}, status: interpretacao}}\n"

    [rule] = parse_layer(text, RuleLayer.CONVENCAO, "convencao/c.yaml")

    assert rule.kind == "info"
    assert rule.params["restringe"] == target


def test_targeted_rule_without_a_known_value_field_stays_info():
    text = """
regras:
  - id: cct_repouso_semanal
    dias_por_semana: 1
    fonte: f
    restringe: repouso_semanal
    status: interpretacao
  - id: pol_intervalo
    minimo_min: 60
    fonte: f
    restringe: interjornada_min
    status: interpretacao
"""
    rest, gap = parse_layer(text, RuleLayer.CONVENCAO, "convencao/c.yaml")

    assert (rest.kind, rest.params["dias_por_semana"]) == ("info", 1)  # não inventa o valor
    assert gap.kind == "info"


def test_targeted_rule_with_non_numeric_value_is_rejected():
    text = "regras:\n  - {id: c, percentual: muito, fonte: f, restringe: adicional_hora_extra, status: interpretacao}\n"

    with pytest.raises(RuleFileError) as err:
        parse_layer(text, RuleLayer.CONVENCAO, "convencao/c.yaml")

    assert err.value.field == "percentual" and "convencao/c.yaml" in str(err.value)


def test_exact_id_primitive_still_reads_its_own_field():
    [rule] = parse_layer(
        "regras:\n  - {id: adicional_hora_extra, percentual_min: 55, fonte: f, status: interpretacao}\n",
        RuleLayer.CONVENCAO,
        "convencao/d1.yaml",
    )
    assert (rule.id, rule.kind, rule.params) == ("adicional_hora_extra", "adicional_hora_extra", {"percent": 55})


def test_targeted_rules_merge_with_the_law_by_the_stricter_value():
    law = parse_layer(LEI, RuleLayer.LEI, "lei/fixture.yaml")
    cct = parse_layer(TARGETED, RuleLayer.CONVENCAO, "convencao/cct.yaml")

    card = build_card(law + cct, date(2026, 11, 9))
    applied = {r.kind: r for r in card.rules if r.kind != "info"}
    assert (applied["interjornada_min"].id, applied["interjornada_min"].params) == ("pol_interjornada", {"hours": 12})
    assert (applied["adicional_hora_extra"].id, applied["adicional_hora_extra"].params) == (
        "cct_adicional_hora_extra",
        {"percent": 60},
    )
    assert applied["jornada_diaria_max"].params == {"hours": 8}  # a ampliação ainda não vale
    assert card.provisional == [] and card.exceptions == []  # mais restritiva numa camada de baixo não é conflito


def test_real_files_apply_the_fictitious_cct_and_policy():
    card = load_rule_card(DATA, date(2026, 11, 9))
    applied = {r.kind: r for r in card.rules if r.kind != "info"}

    assert applied["interjornada_min"].params == {"hours": 12}
    assert applied["interjornada_min"].layer is RuleLayer.POLITICA
    assert applied["adicional_hora_extra"].params == {"percent": 60}
    assert applied["adicional_hora_extra"].layer is RuleLayer.CONVENCAO
    assert applied["jornada_diaria_max"].params == {"hours": 8}
    assert card.provisional == [] and card.exceptions == []

    for day in (date(2026, 12, 16), date(2027, 1, 11)):
        later = load_rule_card(DATA, day)
        later_applied = {r.kind: r for r in later.rules if r.kind != "info"}
        assert later_applied["repouso_semanal"].params == {"days": 2}
        assert later_applied["interjornada_min"].params == {"hours": 12}
        assert later_applied["jornada_diaria_max"].params == {"hours": 8}
        assert later.provisional == [] and later.exceptions == [], day


def test_targeted_rule_with_periods_reads_the_field_inside_each_period():
    text = """
regras:
  - id: cct_semana
    valores:
      - {ate: 2026-12-15, horas: 43}
      - {de: 2026-12-16, horas: 41}
    fonte: f
    restringe: jornada_semanal_max
    status: interpretacao
"""
    first, second = parse_layer(text, RuleLayer.CONVENCAO, "convencao/c.yaml")

    assert (first.id, first.kind, first.params, first.valid_to) == (
        "cct_semana",
        "jornada_semanal_max",
        {"hours": 43},
        date(2026, 12, 15),
    )
    assert (second.params, second.valid_from) == ({"hours": 41}, date(2026, 12, 16))
