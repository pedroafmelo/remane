"""Borda de leitura do CSV da escala (plano da C5, D3; RF-04, RF-23, RX-13). Usa os arquivos sintéticos de
`data/demo/`."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from escalista.ingest.csv_schedule import MAX_BYTES, read_schedule_csv
from escalista.ingest.demo_network import load_demo_network

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
HEADER = "loja_id,pessoa_id,nome,data,inicio,fim"


@pytest.fixture(scope="module")
def network():
    return load_demo_network(DEMO)


def _read(network, name: str, content: bytes, week_start: date | None = None):
    stores, employees, _ = network
    return read_schedule_csv(name, content, employees=employees, stores=stores, week_start=week_start)


def test_load_demo_network(network):
    stores, employees, demand = network

    assert len(stores) == 3
    assert len(employees) == 60
    assert len(demand) == 588


def test_csv_ok_yields_schedule_and_summary(network):
    result = _read(network, "escala_atual.csv", (DEMO / "escala_atual.csv").read_bytes())

    s = result.summary
    assert result.exception is None
    assert s.ok is True and s.issues == []
    assert (s.file_name, s.rows, s.employees, s.stores) == ("escala_atual.csv", 360, 60, 3)
    assert s.week_start == date(2027, 1, 11)
    assert s.total_hours > Decimal(0)
    assert result.schedule is not None
    assert len(result.schedule.shifts) == 360
    assert result.schedule.week_start == date(2027, 1, 11)


def test_defect_csv_yields_exactly_the_planted_issues(network):
    planted = json.loads((DEMO / "defeitos_plantados.json").read_text(encoding="utf-8"))

    result = _read(network, "escala_defeito.csv", (DEMO / "escala_defeito.csv").read_bytes())

    assert [(i.line, i.field) for i in result.summary.issues] == [(p["line"], p["field"]) for p in planted]
    assert result.summary.ok is False
    assert result.exception is not None and result.exception.code == "RX-13"
    assert len(result.exception.evidence) == 5
    assert result.schedule is not None  # as linhas boas ficam; as com problema saem
    assert len(result.schedule.shifts) == result.summary.rows - 5


def test_bom_and_crlf_are_accepted(network):
    text = f"﻿{HEADER}\r\nL1,P001,Quitéria Horta (sintético),2027-01-11,09:00,17:00\r\n"

    result = _read(network, "bom.csv", text.encode("utf-8"))

    assert result.summary.ok is True
    assert len(result.schedule.shifts) == 1


def test_semicolon_delimiter_is_accepted(network):
    text = f"{HEADER.replace(',', ';')}\nL1;P001;Quitéria Horta (sintético);2027-01-11;09:00;17:00\n"

    result = _read(network, "excel.csv", text.encode("utf-8"))

    assert result.summary.ok is True


@pytest.mark.parametrize(
    ("content", "word"),
    [
        ("loja_id,pessoa_id,nome,data,inicio,fim\nL1,P001,João,2027-01-11,09:00,17:00\n".encode("latin-1"), "UTF-8"),
        (b"x" * (MAX_BYTES + 1), "1 MB"),
        (b"", "vazio"),
        (b"# SINTETICO - dados ficticios\n\n", "vazio"),
        (b"isto nao e uma escala\nnem um csv\n", "cabeçalho"),
        (b"loja_id,pessoa_id\x00,nome\n", "CSV"),
    ],
)
def test_non_utf8_or_too_large_is_rx13(network, content: bytes, word: str):
    result = _read(network, "ruim.csv", content)

    assert result.schedule is None
    assert result.exception is not None
    assert result.exception.code == "RX-13"
    assert word in result.exception.reason
    assert result.summary.ok is False
    assert result.summary.issues
