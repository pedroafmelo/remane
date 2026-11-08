"""Testes dos geradores sintéticos (D2). O checador de violações aqui é independente de `verifier/` (frente D4)
de propósito: serve só para confirmar que as violações plantadas são exatas."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from escalista.domain.schedule import DemandSlot, Employee, Shift, Store
from escalista.synth.__main__ import main
from escalista.synth.demanda import make_demanda
from escalista.synth.escalas import PLANTADAS
from escalista.synth.rede import SEMANA_INICIO
from escalista.synth.saida import MARCA, gerar

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
CABECALHO = "loja_id,pessoa_id,nome,data,inicio,fim"
SEMANA = [SEMANA_INICIO + timedelta(days=i) for i in range(7)]


@pytest.fixture(scope="module")
def arquivos() -> dict[str, str]:
    return gerar(42)


@pytest.fixture(scope="module")
def pessoas(arquivos: dict[str, str]) -> list[Employee]:
    return TypeAdapter(list[Employee]).validate_json(arquivos["pessoas.json"])


def _linhas_csv(texto: str) -> list[tuple[int, list[str]]]:
    """Linhas de dados com o número físico (linha 1 é a marca, linha 2 o cabeçalho)."""
    return [(n, next(csv.reader([linha]))) for n, linha in enumerate(texto.splitlines(), start=1) if n > 2]


def _turno(campos: list[str]) -> Shift:
    loja, pessoa, _nome, data, inicio, fim = campos
    inicio_dt = datetime.combine(date.fromisoformat(data), time.fromisoformat(inicio))
    fim_dt = datetime.combine(date.fromisoformat(data), time.fromisoformat(fim))
    if fim_dt <= inicio_dt:
        fim_dt += timedelta(days=1)
    return Shift(employee_id=pessoa, store_id=loja, start=inicio_dt, end=fim_dt)


def _turnos(texto: str) -> list[Shift]:
    return [_turno(campos) for _n, campos in _linhas_csv(texto)]


def _horas(turno: Shift) -> Decimal:
    return Decimal(str((turno.end - turno.start).total_seconds())) / Decimal(3600)


def _checar(turnos: list[Shift]) -> set[tuple[str, str, str | None]]:
    """Checador de referência (só para este teste): jornada semanal > 42h, diária > 8h, interjornada < 11h e
    menos de 2 dias sem turno que começa. Devolve (rule_id, employee_id, day ISO ou None)."""
    por_pessoa: dict[str, list[Shift]] = defaultdict(list)
    for t in turnos:
        por_pessoa[t.employee_id].append(t)
    achados: set[tuple[str, str, str | None]] = set()
    for pessoa, lista in por_pessoa.items():
        lista.sort(key=lambda t: t.start)
        if sum((_horas(t) for t in lista), Decimal(0)) > 42:
            achados.add(("jornada_semanal_max", pessoa, None))
        por_dia: dict[date, Decimal] = defaultdict(Decimal)
        for t in lista:
            por_dia[t.start.date()] += _horas(t)
        for dia, horas in por_dia.items():
            if horas > 8:
                achados.add(("jornada_diaria_max", pessoa, dia.isoformat()))
        for anterior, seguinte in zip(lista, lista[1:], strict=False):
            if seguinte.start - anterior.end < timedelta(hours=11):
                achados.add(("interjornada_min", pessoa, seguinte.start.date().isoformat()))
        if 7 - len({t.start.date() for t in lista}) < 2:
            achados.add(("repouso_semanal", pessoa, None))
    return achados


def test_mesma_seed_gera_arquivos_identicos(tmp_path: Path) -> None:
    primeiro, segundo = tmp_path / "a", tmp_path / "b"
    assert gerar(42) == gerar(42)
    main(["--seed", "42", "--out", str(primeiro)])
    main(["--seed", "42", "--out", str(segundo)])
    nomes = sorted(p.name for p in primeiro.iterdir())
    assert nomes == sorted(p.name for p in segundo.iterdir())
    for nome in nomes:
        assert (primeiro / nome).read_bytes() == (segundo / nome).read_bytes(), nome


def test_seed_diferente_muda_os_dados() -> None:
    assert gerar(43)["escala_atual.csv"] != gerar(42)["escala_atual.csv"]


def test_dados_commitados_sao_os_da_seed_42(arquivos: dict[str, str]) -> None:
    for nome, conteudo in arquivos.items():
        assert (DEMO / nome).read_text(encoding="utf-8") == conteudo, nome


def test_rede_tem_3_lojas_e_55_a_65_pessoas(arquivos: dict[str, str]) -> None:
    lojas = TypeAdapter(list[Store]).validate_json(arquivos["lojas.json"])
    pessoas = TypeAdapter(list[Employee]).validate_json(arquivos["pessoas.json"])
    assert len(lojas) == 3
    assert 55 <= len(pessoas) <= 65
    for loja in lojas:
        assert (loja.opens, loja.closes) == (time(8, 0), time(22, 0))
        assert len([p for p in pessoas if p.store_id == loja.id]) == 20
    for p in pessoas:
        assert p.contract_hours == 44 and p.profile == "padrao" and p.sex in ("F", "M")
        assert isinstance(p.hourly_wage, Decimal) and "sintético" in p.name
    assert {p.sex for p in pessoas} == {"F", "M"}


def test_csv_tem_marca_e_cabecalho_exatos(arquivos: dict[str, str]) -> None:
    for nome in ("escala_atual.csv", "escala_violacoes.csv", "escala_defeito.csv"):
        linhas = arquivos[nome].splitlines()
        assert linhas[0] == MARCA, nome
        assert linhas[1] == CABECALHO, nome


def test_escala_atual_e_violacoes_sao_parseaveis_e_na_semana(arquivos: dict[str, str], pessoas: list[Employee]) -> None:
    ids = {p.id for p in pessoas}
    for nome in ("escala_atual.csv", "escala_violacoes.csv"):
        linhas = _linhas_csv(arquivos[nome])
        assert len(linhas) > 300, nome
        for _n, campos in linhas:
            turno = _turno(campos)  # levanta se a linha não parsear ou se fim não for depois do início
            assert turno.employee_id in ids
            assert turno.start.date() in SEMANA or (turno.end.date() in SEMANA)


def test_escala_atual_tem_violacoes_pelas_regras_novas(arquivos: dict[str, str]) -> None:
    achados = _checar(_turnos(arquivos["escala_atual.csv"]))
    tipos = {regra for regra, _p, _d in achados}
    assert {"jornada_semanal_max", "jornada_diaria_max", "repouso_semanal"} <= tipos


def test_violacoes_plantadas_sao_exatas(arquivos: dict[str, str]) -> None:
    planejadas = json.loads(arquivos["violacoes_plantadas.json"])
    esperado = {(v["rule_id"], v["employee_id"], v["day"]) for v in planejadas}
    assert esperado == {(r, p, d.isoformat() if d else None) for r, p, d in PLANTADAS}
    assert _checar(_turnos(arquivos["escala_violacoes.csv"])) == esperado
    contagem = Counter(v["rule_id"] for v in planejadas)
    assert all(contagem[r] >= 2 for r in ("jornada_semanal_max", "jornada_diaria_max", "interjornada_min"))
    assert contagem["repouso_semanal"] >= 2
    assert all(set(v) == {"rule_id", "kind", "employee_id", "day"} for v in planejadas)


def test_violacao_com_turno_que_vira_a_noite(arquivos: dict[str, str]) -> None:
    noturnos = [t for t in _turnos(arquivos["escala_violacoes.csv"]) if t.end.date() > t.start.date()]
    assert noturnos, "precisa existir pelo menos um turno que termina no dia seguinte"
    assert any(t.employee_id == "P007" for t in noturnos)
    assert ("interjornada_min", "P007", "2027-01-14") in _checar(_turnos(arquivos["escala_violacoes.csv"]))


def _issues(texto: str, pessoas: set[str]) -> set[tuple[int, str]]:
    """Leitura de referência dos defeitos: (linha física, campo). Só para este teste."""
    issues: set[tuple[int, str]] = set()
    vistos: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for numero, campos in _linhas_csv(texto):
        loja, pessoa, _nome, data, inicio, fim = campos
        vazio = [
            c
            for c, valor in zip(("loja_id", "pessoa_id", "nome", "data", "inicio", "fim"), campos, strict=True)
            if not valor
        ]
        if vazio:
            issues.add((numero, vazio[0]))
            continue
        if pessoa not in pessoas:
            issues.add((numero, "pessoa_id"))
            continue
        try:
            dia = date.fromisoformat(data)
        except ValueError:
            issues.add((numero, "data"))
            continue
        if dia not in SEMANA:
            issues.add((numero, "data"))
            continue
        try:
            inicio_dt = datetime.combine(dia, datetime.strptime(inicio, "%H:%M").time())
        except ValueError:
            issues.add((numero, "inicio"))
            continue
        try:
            fim_dt = datetime.combine(dia, datetime.strptime(fim, "%H:%M").time())
        except ValueError:
            issues.add((numero, "fim"))
            continue
        if fim_dt <= inicio_dt:
            fim_dt += timedelta(days=1)
        if any(inicio_dt < f and i < fim_dt for i, f in vistos[pessoa]):
            issues.add((numero, "inicio"))
            continue
        vistos[pessoa].append((inicio_dt, fim_dt))
    return issues


def test_defeito_tem_exatamente_as_5_linhas_plantadas(arquivos: dict[str, str], pessoas: list[Employee]) -> None:
    plantados = json.loads(arquivos["defeitos_plantados.json"])
    assert len(plantados) == 5
    assert {p["field"] for p in plantados} == {"inicio", "pessoa_id", "data", "fim"}
    assert Counter(p["field"] for p in plantados)["inicio"] == 2  # hora inválida e sobreposição
    esperado = {(p["line"], p["field"]) for p in plantados}
    assert _issues(arquivos["escala_defeito.csv"], {p.id for p in pessoas}) == esperado
    linhas = arquivos["escala_defeito.csv"].splitlines()
    for p in plantados:
        assert p["reason"]
        assert p["line"] <= len(linhas)


def test_demanda_cabe_na_capacidade(arquivos: dict[str, str], pessoas: list[Employee]) -> None:
    demanda = TypeAdapter(list[DemandSlot]).validate_json(arquivos["demanda.json"])
    assert all(s.required >= 1 for s in demanda)
    assert {s.day for s in demanda} == set(SEMANA)
    pedidas = sum(s.required for s in demanda) / 2  # faixas de 30 min
    assert pedidas <= 0.85 * len(pessoas) * 42
    # as regras novas limitam a 40h na prática (5 dias de até 8h), então a folga real é maior
    assert pedidas <= 0.85 * len(pessoas) * 40
    for loja in ("L1", "L2", "L3"):
        por_loja = sum(s.required for s in demanda if s.store_id == loja) / 2
        assert por_loja <= 0.85 * 20 * 40


def test_demanda_e_deterministica_e_sem_global() -> None:
    import random

    lojas = [Store(id="L1", name="x", opens=time(8, 0), closes=time(22, 0))]
    assert make_demanda(random.Random(7), lojas) == make_demanda(random.Random(7), lojas)
