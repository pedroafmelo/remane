"""Retrato do relatório `all` para o link público (E6): sem valor plantado, sem exceção silenciosa."""

import json

import pytest

from escalista.evals.snapshot import SNAPSHOT_NAME, LeakCheck, SnapshotLeakError, check_no_leaks, write_snapshot
from tests.evals.report_fixture import sample_report

PLANTED = "F32.1"  # CID plantado de teste, sintético


def seed_planted(data_dir, *values, nested=False):
    folder = data_dir / "demo" / "acompanhamento" / "atestados"
    folder.mkdir(parents=True)
    for i, value in enumerate(values):
        body = {"expect": {"planted_cid": value}} if nested else {"planted_cid": value}
        (folder / f"at-0{i}.esperado.json").write_text(json.dumps(body), encoding="utf-8")


def test_without_planted_files_nothing_is_checked(tmp_path):
    check = check_no_leaks(sample_report(), tmp_path)
    assert check == LeakCheck(leaks=[], planted_checked=0, source=check.source)


def test_clean_report_has_no_leaks_and_counts_the_planted_values(tmp_path):
    seed_planted(tmp_path, PLANTED, ["M54.5", "J11"])
    check = check_no_leaks(sample_report(), tmp_path)
    assert check.leaks == []
    assert check.planted_checked == 3


def test_planted_cid_in_an_obtained_field_is_a_leak_named_by_path_never_by_value(tmp_path):
    seed_planted(tmp_path, PLANTED, nested=True)
    report = sample_report()
    report["cenarios"][1]["obtido"] = f"CID {PLANTED.lower()} lido"  # maiúsculas não escondem
    check = check_no_leaks(report, tmp_path)
    assert check.leaks == ["cenarios[1].obtido"]
    assert PLANTED not in repr(check)


def test_leak_in_a_key_is_found_too(tmp_path):
    seed_planted(tmp_path, PLANTED)
    report = sample_report()
    report["suites"][PLANTED] = {}
    assert check_no_leaks(report, tmp_path).leaks == ["suites.<chave>"]


def test_write_snapshot_refuses_a_leaking_report_and_writes_nothing(tmp_path):
    seed_planted(tmp_path, PLANTED)
    report = sample_report()
    report["cenarios"][0]["obtido"] = PLANTED
    out = tmp_path / "out"
    with pytest.raises(SnapshotLeakError) as err:
        write_snapshot(report, out, tmp_path)
    assert "cenarios[0].obtido" in str(err.value)
    assert PLANTED not in str(err.value)
    assert not (out / SNAPSHOT_NAME).exists()


def test_write_snapshot_writes_a_clean_report(tmp_path):
    seed_planted(tmp_path, PLANTED)
    report = sample_report()
    check = write_snapshot(report, tmp_path / "out", tmp_path)
    written = json.loads((tmp_path / "out" / SNAPSHOT_NAME).read_text(encoding="utf-8"))
    assert check.leaks == [] and check.planted_checked == 1
    assert written["contagem"] == report["contagem"]
    assert written["privacidade"].startswith("conferido")
    assert "privacidade" not in report  # o relatório de entrada não é alterado


def test_snapshot_without_planted_values_says_so(tmp_path):
    check = write_snapshot(sample_report(), tmp_path / "out", tmp_path)
    written = json.loads((tmp_path / "out" / SNAPSHOT_NAME).read_text(encoding="utf-8"))
    assert check.planted_checked == 0
    assert written["privacidade"] == "sem valores plantados disponíveis"


class _FakeLeak:
    def __init__(self, surface: str) -> None:
        self.surface = surface


def test_uses_the_c7_find_leaks_with_the_contract_signature(tmp_path, monkeypatch):
    import types

    seen = {}

    def find_leaks(blobs, planted, *, pattern_surfaces):
        seen.update(blobs=blobs, planted=planted, pattern_surfaces=pattern_surfaces)
        return [_FakeLeak(where) for where, text in blobs.items() if any(p in text for p in planted)]

    module = types.ModuleType("escalista.audit.protected")
    module.find_leaks = find_leaks
    monkeypatch.setitem(__import__("sys").modules, "escalista.audit.protected", module)
    seed_planted(tmp_path, PLANTED)
    report = sample_report()
    report["cenarios"][0]["obtido"] = f"lido {PLANTED}"

    check = check_no_leaks(report, tmp_path)

    assert check.leaks == ["cenarios[0].obtido"]
    assert check.source == "escalista.audit.protected.find_leaks"
    assert seen["planted"] == [PLANTED] and seen["pattern_surfaces"] == set()
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in seen["blobs"].items())


def test_with_the_real_c7_find_leaks_when_it_exists(tmp_path):
    pytest.importorskip("escalista.audit.protected")
    seed_planted(tmp_path, PLANTED)
    report = sample_report()
    report["suites"][PLANTED] = {}
    report["cenarios"][1]["obtido"] = PLANTED.lower()
    check = check_no_leaks(report, tmp_path)
    assert check.source == "escalista.audit.protected.find_leaks"
    assert set(check.leaks) == {"suites.<chave>", "cenarios[1].obtido"}
    assert PLANTED not in repr(check)
