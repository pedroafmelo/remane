"""Testes do cenário sintético do acompanhamento e do ponto simulado (C7, tarefa D1)."""

from __future__ import annotations

import ast
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter

from escalista.agents.cover import find_cover
from escalista.domain.schedule import Employee, Schedule, Shift, Store
from escalista.domain.tracking import Deviation
from escalista.rules.loader import load_rule_card
from escalista.synth.__main__ import main
from escalista.synth.acompanhamento import gerar_acompanhamento
from escalista.synth.ponto import SimulatedPunchSource, load_deviations
from escalista.verifier import verify

RAIZ = Path(__file__).resolve().parents[2]
DEMO = RAIZ / "data" / "demo"
PASTA = DEMO / "acompanhamento"
SEMANA = date(2027, 1, 11)


@pytest.fixture(scope="module")
def arquivos() -> dict[str, bytes]:
    return gerar_acompanhamento(42)


@pytest.fixture(scope="module")
def cenario(arquivos: dict[str, bytes]) -> dict:
    return json.loads(arquivos["acompanhamento/cenario_folga.json"])


@pytest.fixture(scope="module")
def pessoas(cenario: dict) -> list[Employee]:
    return TypeAdapter(list[Employee]).validate_python(cenario["employees"])


@pytest.fixture(scope="module")
def escala(cenario: dict) -> Schedule:
    return Schedule(week_start=date.fromisoformat(cenario["week_start"]), shifts=cenario["shifts"])


@pytest.fixture(scope="module")
def cartao():
    return load_rule_card(RAIZ / "data" / "regras", SEMANA)


@pytest.fixture(scope="module")
def esperado(arquivos: dict[str, bytes]) -> dict:
    return json.loads(arquivos["acompanhamento/cenario.esperado.json"])


def _por_nome(pessoas: list[Employee], nome: str) -> Employee:
    return next(p for p in pessoas if p.name == nome)


def _turno(escala: Schedule, pessoa: str, dia: datetime) -> Shift:
    return next(t for t in escala.shifts if t.employee_id == pessoa and t.start.date() == dia.date())


# ---------------------------------------------------------------------------------------------------- cenário


def test_scenario_is_synthetic_and_validates_with_the_domain_models(cenario: dict) -> None:
    assert cenario["synthetic"] is True
    assert cenario["week_start"] == "2027-01-11"
    assert len(TypeAdapter(list[Store]).validate_python(cenario["stores"])) == 3
    assert all(p["name"].endswith("(sintético)") for p in cenario["employees"])
    assert {p["profile"] for p in cenario["employees"]} == {"padrao"}


def test_schedule_has_zero_violations_in_the_independent_verifier(escala: Schedule, cartao) -> None:
    assert verify(escala, cartao).violations == []


def test_store_1_cover_for_ana_has_two_candidates_and_the_first_without_overtime(
    escala: Schedule, pessoas: list[Employee], cartao
) -> None:
    ana = _por_nome(pessoas, "Ana (sintético)")
    turno = _turno(escala, ana.id, datetime(2027, 1, 14))
    assert (turno.start, turno.end) == (datetime(2027, 1, 14, 14), datetime(2027, 1, 14, 22))
    assert turno.store_id == "L1"
    _avaliados, candidatos = find_cover(escala, turno, pessoas, cartao)
    assert len(candidatos) >= 2
    assert candidatos[0].overtime_hours == 0
    assert {c.employee.contract_hours for c in candidatos} == {24}  # meio período, folgando nesse dia


def test_store_1_cover_for_carla_has_a_candidate(escala: Schedule, pessoas: list[Employee], cartao) -> None:
    carla = _por_nome(pessoas, "Carla (sintético)")
    turno = _turno(escala, carla.id, datetime(2027, 1, 13))
    assert (turno.start, turno.end) == (datetime(2027, 1, 13, 14), datetime(2027, 1, 13, 22))
    _avaliados, candidatos = find_cover(escala, turno, pessoas, cartao)
    assert len(candidatos) >= 1
    assert candidatos[0].overtime_hours == 0


def test_store_3_absence_has_no_candidate(escala: Schedule, pessoas: list[Employee], cartao, esperado: dict) -> None:
    caso = next(c for c in esperado["cases"] if c["id"] == "PL-03")
    turno = _turno(escala, caso["employee_id"], datetime.fromisoformat(caso["shift_start"]))
    avaliados, candidatos = find_cover(escala, turno, pessoas, cartao)
    assert turno.store_id == "L3"
    assert (avaliados, candidatos) == (0, [])  # ninguém livre no dia: RX-05
    assert caso["expect_rx05"] is True


def test_store_2_absence_has_free_colleagues_but_no_candidate_within_the_rules(
    escala: Schedule, pessoas: list[Employee], cartao, esperado: dict
) -> None:
    caso = next(c for c in esperado["cases"] if c["id"] == "PL-02")
    turno = _turno(escala, caso["employee_id"], datetime.fromisoformat(caso["shift_start"]))
    avaliados, candidatos = find_cover(escala, turno, pessoas, cartao)
    assert turno.store_id == "L2"
    assert avaliados >= 1  # há colegas livres no dia, mas nenhuma cobertura passa no verificador
    assert candidatos == []
    assert caso["expect_rx05"] is True and caso["overtime_needed"] is False


def test_known_limit_find_cover_never_returns_overtime_on_this_scenario(
    escala: Schedule, pessoas: list[Employee], cartao
) -> None:
    """Limite documentado no README: o cartão proíbe toda hora extra numa escala verificada (8 h/dia, 42 h/semana e
    2 repousos), então `find_cover` nunca devolve candidato com hora extra. Se este teste quebrar, o cartão ou o
    `find_cover` mudou e o cenário da loja 2 pode ganhar o caso `overtime_needed`."""
    for turno in escala.shifts:
        _, candidatos = find_cover(escala, turno, pessoas, cartao)
        assert all(c.overtime_hours == 0 for c in candidatos)


def test_expected_ranked_is_the_find_cover_output(
    escala: Schedule, pessoas: list[Employee], cartao, esperado: dict
) -> None:
    for caso in esperado["cases"]:
        if caso["kind"] != "falta":
            continue
        turno = _turno(escala, caso["employee_id"], datetime.fromisoformat(caso["shift_start"]))
        avaliados, candidatos = find_cover(escala, turno, pessoas, cartao)
        assert caso["evaluated"] == avaliados
        assert caso["ranked"] == [c.employee.id for c in candidatos]
        assert caso["new_violations"] == 0
        assert all(verify(c.schedule, cartao).violations == [] for c in candidatos)
    assert esperado["schedule_violations"] == 0


# ---------------------------------------------------------------------------------------------------- ponto


@pytest.fixture(scope="module")
def desvios() -> list[Deviation]:
    return load_deviations(PASTA / "ponto_desvios.json")


def _fonte(escala: Schedule, desvios: list[Deviation]) -> SimulatedPunchSource:
    return SimulatedPunchSource(lambda: escala, desvios)


def _batidas(fonte: SimulatedPunchSource, pessoa: str, inicio: datetime, ate: datetime) -> dict[str, datetime]:
    return {b.kind: b.at for b in fonte.punches(until=ate) if b.employee_id == pessoa and b.shift_start == inicio}


def test_deviations_file_is_synthetic_and_has_the_three_kinds(desvios: list[Deviation]) -> None:
    assert json.loads((PASTA / "ponto_desvios.json").read_text(encoding="utf-8"))["synthetic"] is True
    assert {d.kind for d in desvios} == {"falta", "atraso", "hora_extra"}
    assert [d.minutes for d in desvios if d.kind == "atraso"] == [25]


def test_absence_has_no_punch_in(escala: Schedule, desvios: list[Deviation]) -> None:
    falta = next(d for d in desvios if d.kind == "falta")
    fonte = _fonte(escala, desvios)
    assert _batidas(fonte, falta.employee_id, falta.shift_start, datetime(2027, 1, 17, 23, 59)) == {}
    # os colegas do mesmo turno batem o ponto normalmente
    todas = fonte.punches(until=falta.shift_start + timedelta(minutes=1))
    assert all(b.shift_start != falta.shift_start or b.employee_id != falta.employee_id for b in todas)
    assert any(b.at == falta.shift_start and b.kind == "in" for b in todas)  # colegas do mesmo horário batem


def test_delay_punches_in_25_minutes_late(escala: Schedule, desvios: list[Deviation]) -> None:
    atraso = next(d for d in desvios if d.kind == "atraso")
    fonte = _fonte(escala, desvios)
    antes = _batidas(fonte, atraso.employee_id, atraso.shift_start, atraso.shift_start + timedelta(minutes=24))
    assert antes == {}
    depois = _batidas(fonte, atraso.employee_id, atraso.shift_start, atraso.shift_start + timedelta(minutes=25))
    assert depois == {"in": atraso.shift_start + timedelta(minutes=25)}


def test_overtime_pushes_the_punch_out_and_respects_until(escala: Schedule, desvios: list[Deviation]) -> None:
    extra = next(d for d in desvios if d.kind == "hora_extra")
    fim = _turno(escala, extra.employee_id, extra.shift_start).end
    fonte = _fonte(escala, desvios)
    assert "out" not in _batidas(
        fonte, extra.employee_id, extra.shift_start, fim + timedelta(minutes=extra.minutes - 1)
    )
    saida = _batidas(fonte, extra.employee_id, extra.shift_start, fim + timedelta(minutes=extra.minutes))["out"]
    assert saida == fim + timedelta(minutes=extra.minutes)


def test_punches_are_cut_by_until_and_sorted(escala: Schedule, desvios: list[Deviation]) -> None:
    ate = datetime(2027, 1, 12, 12, 0)
    batidas = _fonte(escala, desvios).punches(until=ate)
    assert batidas and all(b.at <= ate for b in batidas)
    assert [b.at for b in batidas] == sorted(b.at for b in batidas)


def test_cover_punches_normally_and_the_original_deviation_does_not_apply(
    escala: Schedule, pessoas: list[Employee], cartao, desvios: list[Deviation]
) -> None:
    falta = next(d for d in desvios if d.kind == "falta")
    turno = _turno(escala, falta.employee_id, falta.shift_start)
    _, candidatos = find_cover(escala, turno, pessoas, cartao)
    coberta = candidatos[0].schedule
    fonte = SimulatedPunchSource(lambda: coberta, desvios)
    batidas = _batidas(fonte, candidatos[0].employee.id, turno.start, turno.end)
    assert batidas == {"in": turno.start, "out": turno.end}  # batidas normais, sem atraso nem falta
    todas = fonte.punches(until=turno.end)
    assert all(b.employee_id != falta.employee_id or b.shift_start != turno.start for b in todas)


def test_schedule_is_queried_on_every_call_and_none_means_no_punch(escala: Schedule, desvios: list[Deviation]) -> None:
    estado: list[Schedule | None] = [None]
    fonte = SimulatedPunchSource(lambda: estado[0], desvios)
    ate = datetime(2027, 1, 17, 23, 59)
    assert fonte.punches(until=ate) == []
    estado[0] = escala
    assert fonte.punches(until=ate)


# ---------------------------------------------------------------------------------------------------- gabarito


def test_generation_is_deterministic(arquivos: dict[str, bytes]) -> None:
    assert gerar_acompanhamento(42) == arquivos


def test_committed_files_are_the_seed_42_ones(arquivos: dict[str, bytes]) -> None:
    for nome, conteudo in arquivos.items():
        assert (DEMO / nome).read_bytes() == conteudo, nome


def test_cli_writes_the_same_files(tmp_path: Path, arquivos: dict[str, bytes]) -> None:
    assert main(["acompanhamento", "--seed", "42", "--out", str(tmp_path)]) == 0
    for nome, conteudo in arquivos.items():
        assert (tmp_path / nome).read_bytes() == conteudo, nome


def test_expected_instants_follow_the_policy_arithmetic(esperado: dict) -> None:
    """Recalcula os instantes a partir do YAML da política, de forma independente do gerador."""
    politica = {
        r["id"]: r
        for r in yaml.safe_load((RAIZ / "data" / "regras" / "politica" / "politica_ficticia.yaml").read_text("utf-8"))[
            "regras"
        ]
    }
    tolerancia = politica["pol_atraso"]["tolerancia_min"]
    resposta = politica["pol_atraso"]["prazo_resposta_colaborador_min"]
    prazo = politica["pol_oferta_turno"]["prazo_por_candidato_min"]
    assert (tolerancia, resposta, prazo) == (10, 15, 20)  # os números que o roteiro assume
    assert politica["pol_oferta_turno"]["candidatos_max_antes_de_escalar"] == 3
    assert esperado["policy"]["pol_atraso"] == {"tolerancia_min": 10, "prazo_resposta_colaborador_min": 15}
    minutos = timedelta(minutes=1)
    for caso in esperado["cases"]:
        if caso["kind"] not in ("falta", "atraso"):
            continue
        inicio = datetime.fromisoformat(caso["shift_start"])
        assert caso["trigger"] == "no_punch"
        assert datetime.fromisoformat(caso["fires_at"]) == inicio + tolerancia * minutos
        assert datetime.fromisoformat(caso["not_before"]) == inicio + 9 * minutos
        if caso["no_answer"]:
            pergunta = datetime.fromisoformat(caso["no_answer"]["question_at"])
            assert pergunta == inicio + 10 * minutos
            assert datetime.fromisoformat(caso["no_answer"]["fires_at"]) == pergunta + 15 * minutos
            assert datetime.fromisoformat(caso["no_answer"]["not_before"]) == pergunta + 14 * minutos
    ana = next(c for c in esperado["cases"] if c["id"] == "PL-01")
    envio = datetime.fromisoformat(ana["offers"]["reported_at"])
    assert envio == datetime.fromisoformat(esperado["demo_clock"])
    for i, oferta in enumerate(ana["offers"]["list"]):
        assert datetime.fromisoformat(oferta["sent_at"]) == envio + 20 * i * minutos
        assert datetime.fromisoformat(oferta["deadline"]) == envio + 20 * (i + 1) * minutos
    assert len(ana["offers"]["list"]) == 3
    assert datetime.fromisoformat(ana["offers"]["rx06_at"]) == envio + 60 * minutos
    assert datetime.fromisoformat(ana["offers"]["rx06_not_before"]) == envio + 59 * minutos


def test_overtime_cases_cross_80_and_100_percent_of_6_hours(esperado: dict) -> None:
    extras = [c for c in esperado["cases"] if c["kind"] == "hora_extra"]
    assert sum(c["extra_minutes"] for c in extras) > 6 * 60
    gatilhos = {c["trigger"]: c for c in extras if c["trigger"]}
    assert set(gatilhos) == {"overtime_near_limit", "overtime_limit"}
    assert gatilhos["overtime_near_limit"]["threshold_minutes"] == 288  # 80% de 6 h
    assert gatilhos["overtime_limit"]["threshold_minutes"] == 360
    assert gatilhos["overtime_near_limit"]["cumulative_minutes"] >= 288
    assert gatilhos["overtime_limit"]["cumulative_minutes"] > 360
    for caso in extras:
        if caso["trigger"]:
            fim = datetime.fromisoformat(caso["shift_end"])
            assert datetime.fromisoformat(caso["fires_at"]) == fim + timedelta(minutes=caso["extra_minutes"])


def test_synth_never_imports_the_sweep() -> None:
    """O gabarito não pode ser calculado pela função que ele testa (PEDIDO-EV-20)."""
    for arquivo in sorted((RAIZ / "src" / "escalista" / "synth").glob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            modulos = []
            if isinstance(no, ast.ImportFrom):
                modulos = [no.module or "", *(f"{no.module}.{a.name}" for a in no.names)]
            elif isinstance(no, ast.Import):
                modulos = [a.name for a in no.names]
            assert not any("tracker.sweep" in m or m.endswith(".sweep") for m in modulos), arquivo.name
