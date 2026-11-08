"""Comando único dos evals (plano dos evals E3/E4, seção 4): `--suite all|e3|e4`, códigos de saída e o relatório all."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from escalista.domain.contracts import LLMResult, TraceEvent
from escalista.evals import __main__ as evals_cli
from escalista.evals import e1, e2, e3, e4, suite_all
from escalista.evals.common import NotRun, Outcome, Scenario
from escalista.evals.snapshot import SnapshotLeakError
from tests.fakes import TOOL_MAPPING

DATA = Path("data/demo")
NOW = datetime(2026, 11, 8, 10, 0, 0)


def _ok(i: str, suite: str, **kw) -> Scenario:
    return Scenario(i, f"ok {i}", lambda _: Outcome("a", "a", True), suite=suite, **kw)


def _bad(i: str, suite: str) -> Scenario:
    return Scenario(i, f"falha {i}", lambda _: Outcome("a", "b", False), suite=suite)


def _not_run(i: str, suite: str) -> Scenario:
    def run(_):
        raise NotRun("cenário ainda não escrito")

    return Scenario(i, f"nr {i}", run, suite=suite)


@pytest.mark.parametrize(
    ("scenarios", "code"),
    [
        ([_ok("E3-01", "e3")], 0),
        ([_ok("E3-01", "e3"), _bad("E3-02", "e3"), _not_run("E3-03", "e3")], 1),
        ([_ok("E3-01", "e3"), _not_run("E3-03", "e3")], 3),
    ],
)
def test_exit_codes_of_a_single_new_suite(tmp_path: Path, monkeypatch, scenarios, code):
    monkeypatch.setattr(e3, "SCENARIOS", tuple(scenarios))
    assert evals_cli.main(["--suite", "e3", "--out", str(tmp_path)]) == code
    report = json.loads((tmp_path / "e3-latest.json").read_text())
    assert report["suite"] == "e3" and len(report["cenarios"]) == len(scenarios)


def test_e4_suite_runs_alone(tmp_path: Path, capsys):
    assert evals_cli.main(["--suite", "e4", "--out", str(tmp_path)]) == 3
    out = capsys.readouterr().out
    assert "E4-02" in out and "não executado (sem --with-model)" in out


def _small_e2_data(tmp_path: Path) -> Path:
    data = tmp_path / "demo"
    (data / "e2").mkdir(parents=True)
    for name in ("e2-01-csv-cp1252.csv", "e2-01-csv-cp1252.esperado.json"):
        shutil.copy(DATA / "e2" / name, data / "e2")
    return data


@pytest.fixture
def small_all(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(e1, "SCENARIOS", (_ok("E1-01", "e1"), _ok("E1-02", "e1")))
    monkeypatch.setattr(e3, "SCENARIOS", (_ok("E3-05", "e3", tier="T1a"), _not_run("E3-06", "e3")))
    monkeypatch.setattr(e4, "SCENARIOS", (_ok("E4-02", "e4", uses_model=True),))
    return _small_e2_data(tmp_path)


def test_default_is_all_and_writes_the_all_report(tmp_path: Path, small_all: Path, capsys):
    out = tmp_path / "out"
    code = evals_cli.main(["--data", str(small_all), "--out", str(out)])

    assert code == 3  # o com modelo não rodou: nenhum falhou, mas nem todos rodaram
    report = json.loads((out / "all-latest.json").read_text())
    assert report["suite"] == "all" and report["modo"] == "sem_modelo" and report["dados"] == "sintéticos"
    assert "git_sha" in report and "gerado_em" in report
    assert report["contagem"] == {
        "cenarios": 6,
        "sem_modelo": 5,
        "com_modelo": 1,
        "executados": 4,
        "passaram": 4,
        "falharam": 0,
        "nao_executados": 2,
        "com_modelo_executados": 0,
    }
    assert report["dec_019"]["sem_modelo"] == {"meta": 20, "existem": 5, "passaram": 4}
    assert report["dec_019"]["com_modelo"] == {"meta": 10, "existem": 1, "executados": 0, "passaram": 0}
    assert set(report["rn04"]) == {
        "violacoes_nao_detectadas",
        "cobertura",
        "custo_contra_planilha",
        "acerto_atestado",
    }
    assert all(block["status"] == "não medido" for block in report["rn04"].values())
    assert report["modelo"]["chamadas"] == 0 and report["modelo"]["cost_usd"] is None
    assert report["modelo"]["teto_usd"] == "1.00"
    assert set(report["suites"]) == {"e1", "e2", "e3", "e4"}
    assert report["suites"]["e2"]["placar"] == "1/1" and report["suites"]["e2"]["totais"]["inventados"] == 0
    e2_rows = [c for c in report["cenarios"] if c["suite"] == "e2"]
    assert [(c["id"], c["status"], c["usa_modelo"]) for c in e2_rows] == [("E2-01", "passou", False)]
    assert "medicoes" not in report
    printed = capsys.readouterr().out
    assert "6 cenários (5 sem modelo, 1 com modelo); executados 4 (com modelo: 0); passaram 4; falharam 0; " in printed
    assert "não executados 2" in printed
    assert "não executado (cenário ainda não escrito)" in printed
    assert list(out.glob("all-2*.json"))


def test_all_returns_one_when_an_e2_file_invents_a_shift(tmp_path: Path, small_all: Path):
    gold_path = small_all / "e2" / "e2-01-csv-cp1252.esperado.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["shifts"].pop()
    gold_path.write_text(json.dumps(gold), encoding="utf-8")

    assert evals_cli.main(["--suite", "all", "--data", str(small_all), "--out", str(tmp_path / "o")]) == 1


def test_with_model_and_no_key_marks_model_scenarios_as_not_run(tmp_path: Path, small_all: Path, monkeypatch):
    def no_key():
        raise SystemExit("nenhuma chave")

    monkeypatch.setattr(e2, "_real_client_factory", no_key)
    code = evals_cli.main(["--with-model", "--data", str(small_all), "--out", str(tmp_path / "o")])

    assert code == 3
    report = json.loads((tmp_path / "o" / "all-latest.json").read_text())
    assert report["modo"] == "com_modelo"
    row = next(c for c in report["cenarios"] if c["id"] == "E4-02")
    assert row["status"] == "não executado" and row["motivo"] == "sem chave"


class _EmittingFake:
    """Cliente injetado (nunca o real): devolve o mapeamento da heurística e emite um evento com custo."""

    def __init__(self, sink, answers) -> None:
        self.sink = sink
        self.answers = list(answers)

    def complete(self, *, size, messages, tool_schema=None, run_id, parent_id=None, kind=None):
        self.sink.emit(
            TraceEvent(
                id=f"ev-{id(self)}-{len(self.answers)}",
                run_id=run_id,
                kind=kind or "llm.call",
                at=NOW,
                model="fake-real-like",
                tokens_in=10,
                tokens_out=5,
                cost_usd=Decimal("0.0001"),
                latency_ms=7,
            )
        )
        return LLMResult(tool_args=self.answers.pop(0), model="fake-real-like", key_index=1)


def test_with_model_measures_e2_again_without_counting_scenarios(tmp_path: Path, small_all: Path):
    from escalista.ingest.tables import read_tables
    from escalista.rules.header_aliases import guess_mapping

    path = small_all / "e2" / "e2-01-csv-cp1252.csv"
    mapping = guess_mapping(read_tables(path.name, path.read_bytes()).tables)
    assert mapping is not None
    answers = {TOOL_MAPPING: [mapping.model_dump(mode="json")]}

    code = suite_all.main(
        ["--with-model", "--data", str(small_all), "--out", str(tmp_path / "o")],
        client_factory=lambda sink: _EmittingFake(sink, answers[TOOL_MAPPING]),
    )

    report = json.loads((tmp_path / "o" / "all-latest.json").read_text())
    assert report["contagem"]["cenarios"] == 6  # o E2 com modelo não dobra (B3)
    block = report["medicoes"]["e2_com_modelo"]
    assert block["placar"] == "1/1" and block["modelo"]["chamadas"] == 1 and block["modelo"]["cost_usd"] == "0.0001"
    assert report["modelo"]["chamadas"] == 1 and report["modelo"]["cost_usd"] == "0.0001"
    assert report["modelo"]["latencia_ms_p50"] == 7 and report["modelo"]["latencia_ms_max"] == 7
    assert code == 3  # E4-02 do fixture não chamou modelo nenhum: forçado a `não executado`


def test_report_carries_the_command_line_without_env(tmp_path: Path, small_all: Path):
    out = tmp_path / "o"
    evals_cli.main(["--suite", "all", "--data", str(small_all), "--out", str(out)])
    report = json.loads((out / "all-latest.json").read_text())
    assert report["comando"] == f"uv run python -m escalista.evals --suite all --data {small_all} --out {out}"
    assert {"cenarios", "passaram", "falharam", "nao_executados"} <= set(report["suites"]["e3"])


def test_snapshot_goes_through_the_leak_checked_writer(tmp_path: Path, small_all: Path, monkeypatch):
    seen = []
    real = suite_all.write_snapshot

    def spy(report, out_dir, data_dir):
        seen.append((report["suite"], out_dir, data_dir))
        return real(report, out_dir, data_dir)

    monkeypatch.setattr(suite_all, "write_snapshot", spy)
    snap = tmp_path / "snap"

    code = evals_cli.main(["--data", str(small_all), "--out", str(tmp_path / "o"), "--snapshot", str(snap)])

    assert code == 3 and seen == [("all", snap, Path("data"))]
    saved = json.loads((snap / "evals-latest.json").read_text())
    report = json.loads((tmp_path / "o" / "all-latest.json").read_text())
    assert saved.pop("privacidade") and saved == report


def test_snapshot_with_a_leak_writes_nothing_and_exits_one(tmp_path: Path, small_all: Path, monkeypatch, capsys):

    def leaky(report, out_dir, data_dir):
        raise SnapshotLeakError(["cenarios[0].obtido"])

    monkeypatch.setattr(suite_all, "write_snapshot", leaky)
    snap = tmp_path / "snap"

    code = evals_cli.main(["--data", str(small_all), "--out", str(tmp_path / "o"), "--snapshot", str(snap)])

    assert code == 1 and not snap.exists()
    assert "cenarios[0].obtido" in capsys.readouterr().err
