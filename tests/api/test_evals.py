"""`GET /api/evals`: o retrato do relatório de evals no Impacto. Sem retrato válido, `sem_relatorio` (nunca 500)."""

import json

import pytest

from escalista.api import evals_view
from escalista.domain.contracts import Role
from tests.api.test_access import login, make_client
from tests.evals.report_fixture import sample_report


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("EVALS_SNAPSHOT_PATH", raising=False)


def gestor(tmp_path):
    client = make_client(tmp_path)
    login(client, Role.GESTOR)
    return client


def test_default_snapshot_path_is_the_one_in_data():
    assert evals_view.DEFAULT_SNAPSHOT_PATH == "data/evals/evals-latest.json"


def test_without_a_file_it_is_sem_relatorio(tmp_path, monkeypatch):
    monkeypatch.setenv("EVALS_SNAPSHOT_PATH", str(tmp_path / "nao-existe.json"))
    response = gestor(tmp_path).get("/api/evals")
    assert response.status_code == 200
    assert response.json() == {"status": "sem_relatorio"}


@pytest.mark.parametrize("content", ["{nao e json", "[1, 2]", '{"suite": "all"}', '{"contagem": "x"}', ""])
def test_invalid_file_is_sem_relatorio_not_500(tmp_path, monkeypatch, content):
    path = tmp_path / "evals-latest.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("EVALS_SNAPSHOT_PATH", str(path))
    response = gestor(tmp_path).get("/api/evals")
    assert response.status_code == 200
    assert response.json() == {"status": "sem_relatorio"}


def test_valid_snapshot_is_returned_as_is_with_status_ok(tmp_path, monkeypatch):
    report = sample_report()
    report["campo_novo"] = {"x": 1}  # tolerante: campo desconhecido passa
    path = tmp_path / "evals-latest.json"
    path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("EVALS_SNAPSHOT_PATH", str(path))
    body = gestor(tmp_path).get("/api/evals").json()
    assert body["status"] == "ok"
    assert body["contagem"] == report["contagem"]
    assert body["rn04"]["acerto_atestado"]["status"] == "não medido"
    assert body["modelo"]["cost_usd"] is None  # nulo continua nulo, não vira 0
    assert body["campo_novo"] == {"x": 1}
    assert [c["id"] for c in body["cenarios"]] == ["E1-01", "E3-01"]


def test_snapshot_missing_optional_blocks_is_still_valid(tmp_path, monkeypatch):
    path = tmp_path / "evals-latest.json"
    path.write_text(json.dumps({"contagem": {"cenarios": 3}}), encoding="utf-8")
    monkeypatch.setenv("EVALS_SNAPSHOT_PATH", str(path))
    body = gestor(tmp_path).get("/api/evals").json()
    assert body["status"] == "ok"
    assert body["contagem"]["cenarios"] == 3
    assert body["rn04"] is None


def test_collaborator_cannot_read_evals(tmp_path):
    client = make_client(tmp_path)
    login(client, Role.COLABORADOR)
    assert client.get("/api/evals").status_code == 403
