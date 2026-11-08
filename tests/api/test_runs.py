"""Rotas da fatia contra o agente falso (plano da C5, seção 4, C2): fluxo feliz, limites do arquivo, recusa de
`publicar`, rastro com custo e RN-13 (nenhuma resposta leva `sex`).

Sempre `Settings(_env_file=None)` com `monkeypatch`: estes testes nunca leem o `.env` real.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from escalista.api.app import create_app
from escalista.api.fake_agent import FakeSliceAgent
from escalista.api.wiring import MAX_UPLOAD_BYTES, SliceAgent, get_agent, get_demo_files_dir
from escalista.config import Settings

CSV = (
    b"# SINTETICO - dados ficticios\n"
    b"funcionario,loja,dia,inicio,fim\n"
    b"E01,L01,2027-01-11,08:00,18:00\n"
    b"E02,L01,2027-01-11,12:00,22:00\n"
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


class Recorder:
    """Guarda o JSON de toda resposta, para varrer o fluxo inteiro atrás de `sex`."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.bodies: list[Any] = []

    def __call__(self, method: str, url: str, **kwargs):
        response = self.client.request(method, url, **kwargs)
        if response.headers.get("content-type", "").startswith("application/json"):
            self.bodies.append(response.json())
        return response


def make_client(tmp_path, agent: SliceAgent | None = None) -> tuple[TestClient, SliceAgent]:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    agent = agent or FakeSliceAgent()
    app = create_app(settings)
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    (demo_dir / "escala_atual.csv").write_bytes(CSV)
    (tmp_path / "segredo.csv").write_text("nao pode sair")
    app.dependency_overrides[get_agent] = lambda: agent
    app.dependency_overrides[get_demo_files_dir] = lambda: demo_dir
    client = TestClient(app)
    assert client.post("/auth/demo/gerente").status_code == 200
    return client, agent


def upload(call, content: bytes = CSV, name: str = "escala_atual.csv"):
    return call("POST", "/api/runs", params={"file_name": name}, content=content, headers={"Content-Type": "text/csv"})


def keys_of(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_of(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_of(v)}
    return set()


def run_happy_flow(call) -> str:
    started = upload(call)
    assert started.status_code == 201, started.text
    run = started.json()
    assert run["phase"] == "awaiting_confirm"
    assert run["summary"]["ok"] is True and run["summary"]["file_name"] == "escala_atual.csv"
    run_id = run["run_id"]

    assert call("GET", f"/api/runs/{run_id}").json()["phase"] == "awaiting_confirm"
    assert call("GET", f"/api/runs/{run_id}/schedule").status_code == 409  # sem grade antes de otimizar

    confirmed = call("POST", f"/api/runs/{run_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["phase"] == "awaiting_approval"
    assert body["comparison"]["before"]["violations"] > 0
    assert body["comparison"]["after"]["violations"] == 0 and body["report"]["total"] == 0
    assert all(item["rule_refs"] for item in body["justification"]["items"])
    assert body["version_id"]

    grid = call("GET", f"/api/runs/{run_id}/schedule")
    assert grid.status_code == 200
    assert grid.json()["schedule"]["shifts"] and grid.json()["employees"]

    assert call("GET", "/api/schedules/published").json() == {"version": None, "employees": []}
    approved = call("POST", f"/api/runs/{run_id}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["phase"] == "published"

    published = call("GET", "/api/schedules/published").json()
    assert published["version"]["id"] == body["version_id"]
    assert published["version"]["status"] == "published" and published["employees"]
    return run_id


def test_happy_flow_with_fake_agent(tmp_path):
    client, _ = make_client(tmp_path)
    run_happy_flow(Recorder(client))


def test_no_response_of_the_flow_carries_sex(tmp_path):
    """RN-13: o agente falso guarda `Employee` com `sex`; nenhuma resposta, em nenhum nível, pode trazê-lo."""
    client, _ = make_client(tmp_path)
    call = Recorder(client)
    run_id = run_happy_flow(call)
    call("GET", f"/api/runs/{run_id}")
    call("GET", f"/api/runs/{run_id}/trace")
    call("GET", "/api/me")
    upload(call, content=b"# SINTETICO\n")  # execução que falha (RX-13 do agente)
    upload(call, content=b"\xff\xfe\x00")  # recusa na porta
    assert len(call.bodies) >= 12
    for body in call.bodies:
        assert "sex" not in keys_of(body), body


def test_approval_records_session_account_and_role(tmp_path):
    client, agent = make_client(tmp_path)
    run_id = upload(client.request).json()["run_id"]
    client.post(f"/api/runs/{run_id}/confirm")
    client.post(f"/api/runs/{run_id}/approve")
    approval = next(iter(agent._approvals.values()))
    assert approval.approved_by == "demo-gerente" and approval.role == "gerente"
    assert approval.version_id == agent.get_run(run_id).version_id


def test_trace_events_carry_cost(tmp_path):
    client, _ = make_client(tmp_path)
    run_id = run_happy_flow(client.request)
    events = client.get(f"/api/runs/{run_id}/trace").json()
    kinds = [e["kind"] for e in events]
    for kind in ("csv.validate", "read.summary", "read.confirmed", "solver.run", "verifier.check", "cost.compare",
                 "llm.justify", "approval.recorded", "schedule.publish"):  # fmt: skip
        assert kind in kinds
    assert all(e["cost_usd"] is not None for e in events)
    llm = next(e for e in events if e["kind"] == "llm.justify")
    assert float(llm["cost_usd"]) > 0 and llm["key_index"] == 1


def test_refused_publish_is_403_and_traced(tmp_path):
    client, _ = make_client(tmp_path, FakeSliceAgent(refuse_publish=True))
    run_id = upload(client.request).json()["run_id"]
    client.post(f"/api/runs/{run_id}/confirm")
    refused = client.post(f"/api/runs/{run_id}/approve")
    assert refused.status_code == 403
    assert refused.json()["detail"]
    assert client.get("/api/schedules/published").json()["version"] is None
    assert "schedule.publish_refused" in [e["kind"] for e in client.get(f"/api/runs/{run_id}/trace").json()]


def test_csv_over_1mb_is_413_with_rx13(tmp_path):
    client, agent = make_client(tmp_path)
    response = upload(client.request, content=b"a" * (MAX_UPLOAD_BYTES + 1))
    assert response.status_code == 413
    assert response.json()["exception"]["code"] == "RX-13"
    assert agent._runs == {}  # o agente nem foi chamado


def test_csv_of_exactly_1mb_is_accepted(tmp_path):
    client, _ = make_client(tmp_path)
    content = CSV + b"#" * (MAX_UPLOAD_BYTES - len(CSV))
    assert upload(client.request, content=content).status_code == 201


def test_non_utf8_csv_yields_rx13_without_500(tmp_path):
    client, agent = make_client(tmp_path)
    response = upload(client.request, content="funcionário;loja\n".encode("latin-1"))
    assert response.status_code == 422
    card = response.json()["exception"]
    assert card["code"] == "RX-13" and "UTF-8" in card["reason"]
    assert agent._runs == {}


def test_defective_csv_is_failed_run_with_rx13(tmp_path):
    client, _ = make_client(tmp_path)
    response = upload(client.request, content=b"# SINTETICO - dados ficticios\n")
    assert response.status_code == 201
    body = response.json()
    assert body["phase"] == "failed" and body["exception"]["code"] == "RX-13"
    assert body["summary"]["ok"] is False and body["summary"]["issues"][0]["line"] == 1


def test_upload_requires_file_name(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.post("/api/runs", content=CSV).status_code == 422


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "/api/runs/nao-existe"),
        ("POST", "/api/runs/nao-existe/confirm"),
        ("GET", "/api/runs/nao-existe/schedule"),
        ("POST", "/api/runs/nao-existe/approve"),
        ("GET", "/api/runs/nao-existe/trace"),
    ],
)
def test_unknown_run_is_404(tmp_path, method, url):
    client, _ = make_client(tmp_path)
    assert client.request(method, url).status_code == 404


def test_operations_out_of_phase_are_409(tmp_path):
    client, _ = make_client(tmp_path)
    run_id = upload(client.request).json()["run_id"]
    assert client.post(f"/api/runs/{run_id}/approve").status_code == 409  # ainda sem versão
    client.post(f"/api/runs/{run_id}/confirm")
    assert client.post(f"/api/runs/{run_id}/confirm").status_code == 409
    client.post(f"/api/runs/{run_id}/approve")
    assert client.post(f"/api/runs/{run_id}/approve").status_code == 409


def test_demo_file_is_served(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/api/demo/files/escala_atual.csv")
    assert response.status_code == 200 and response.content == CSV
    assert response.headers["content-type"].startswith("text/csv")


@pytest.mark.parametrize(
    "name",
    ["escala_defeito.csv", "segredo.csv", "..%2Fsegredo.csv", "%2E%2E%2Fsegredo.csv", "escala_atual.csv%00", "x"],
)
def test_demo_file_outside_whitelist_or_missing_is_404(tmp_path, name):
    """`escala_defeito.csv` está na lista, mas não existe no diretório de teste; o resto está fora da lista."""
    client, _ = make_client(tmp_path)
    response = client.get(f"/api/demo/files/{name}")
    assert response.status_code == 404
    assert b"nao pode sair" not in response.content


def test_default_app_uses_fake_agent_and_data_demo(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/app.db", web_dist_dir=str(tmp_path / "d"))
    app = create_app(settings)
    assert isinstance(app.state.agent, FakeSliceAgent) and isinstance(app.state.agent, SliceAgent)
    assert app.state.demo_files_dir == "data/demo"
