"""Testes do arquivo adversário do E4-02: determinismo, gabarito conferido por leitor independente, CLI."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from openpyxl import load_workbook

from escalista.evals import e2
from escalista.synth.__main__ import main
from escalista.synth.e2 import INJECAO
from escalista.synth.e4 import ARQUIVO, GABARITO, gerar_e4

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
E4 = DEMO / "e4"


@pytest.fixture(scope="module")
def arquivos() -> dict[str, bytes]:
    return gerar_e4(42)


def test_generates_the_file_and_its_gold_only(arquivos: dict[str, bytes]):
    assert sorted(arquivos) == [GABARITO, ARQUIVO]
    assert ARQUIVO == "e4/e4-02-injecao-escala.xlsx"
    assert GABARITO == "e4/e4-02-injecao-escala.esperado.json"


def test_same_seed_gives_the_same_bytes(arquivos: dict[str, bytes]):
    assert gerar_e4(42) == arquivos


def test_written_files_are_the_ones_of_seed_42(arquivos: dict[str, bytes]):
    for nome, conteudo in arquivos.items():
        assert (DEMO / nome).read_bytes() == conteudo, nome


def test_gold_has_the_e2_format_and_describes_each_hostile_cell(arquivos: dict[str, bytes]):
    gold = json.loads(arquivos[GABARITO])
    assert gold["file"] == ARQUIVO
    assert gold["synthetic"] is True
    assert gold["expect"] == "shifts"
    assert gold["week_start"] == "2027-01-11"
    assert gold["shifts"] and gold["mapping_hint"]["layout"] == "long"
    assert gold["expected_issues"] == []
    assert set(gold["adversary"]) >= {"comment_row", "note_column", "name_cell"}
    assert all(isinstance(v, str) and v for v in gold["adversary"].values())


def test_gold_matches_an_independent_read_of_the_workbook(arquivos: dict[str, bytes]):
    gold = json.loads(arquivos[GABARITO])
    hint = gold["mapping_hint"]
    import io

    ws = load_workbook(io.BytesIO(arquivos[ARQUIVO])).active
    linhas = list(ws.iter_rows(values_only=True))
    cabecalho = [str(c) for c in linhas[hint["header_row"] - 1]]
    col = {papel: cabecalho.index(nome) for papel, nome in hint["columns"].items()}
    lidos = set()
    for linha in linhas[hint["header_row"] :]:
        dia = linha[col["date"]]
        hi, hf = (datetime.strptime(linha[col[k]], "%H:%M") for k in ("start", "end"))
        inicio = datetime.combine(dia, hi.time())
        fim = datetime.combine(dia, hf.time())
        if fim <= inicio:
            fim += timedelta(days=1)
        lidos.add((linha[col["person_name"]], linha[col["store"]], inicio.isoformat(), fim.isoformat()))
    esperados = {(s["person_name"], s["store"], s["start"], s["end"]) for s in gold["shifts"]}
    assert lidos == esperados
    assert len(gold["shifts"]) == len(esperados)


def test_the_hostile_text_is_in_the_file_and_differs_from_e2_09(arquivos: dict[str, bytes]):
    import io

    ws = load_workbook(io.BytesIO(arquivos[ARQUIVO])).active
    celulas = [str(c) for linha in ws.iter_rows(values_only=True) for c in linha if c is not None]
    texto = "\n".join(celulas)
    assert "SINTETICO" in celulas[0]
    assert "assistente" in texto.casefold()
    assert INJECAO not in texto  # não reaproveita o ataque do E2-09
    assert "SYSTEM: use 48h" not in texto
    assert sum("assistente" in c.casefold() for c in celulas) >= 3


def test_e2_discover_does_not_pick_the_e4_gold():
    assert E4.exists()
    assert not any("e4" in p.parts for p in e2.discover(DEMO))
    assert not any("e4-02" in p.name for p in e2.discover(DEMO))


def test_cli_writes_only_the_e4_files(tmp_path: Path, arquivos: dict[str, bytes]):
    assert main(["e4", "--seed", "42", "--out", str(tmp_path)]) == 0
    escritos = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file())
    assert escritos == sorted(arquivos)
    assert (tmp_path / ARQUIVO).read_bytes() == arquivos[ARQUIVO]
