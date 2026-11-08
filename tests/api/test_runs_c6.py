"""Rotas da C6 contra o agente falso (plano da C6, seção 14, C1): upload binário (CSV, XLSX e PDF por extensão e bytes
iniciais), `confirm` com `ConfirmInput` opcional, `POST /api/runs/next-week`, `GET /api/roster` sem `sex` (RN-13) e o
adaptador do agente real.

Sempre `Settings(_env_file=None)` com `monkeypatch`: estes testes nunca leem o `.env` real.
"""

from datetime import date, timedelta

import pytest

from escalista.api import wiring
from escalista.api.app import create_app
from escalista.api.fake_agent import NO_FIRST_SCHEDULE, FakeSliceAgent
from escalista.api.optimizer_adapter import OptimizerSliceAgent
from escalista.api.wiring import MAX_UPLOAD_BYTES
from escalista.config import Settings
from escalista.domain.reading import ConfirmInput, IdentityAnswer
from escalista.domain.results import RunState
from escalista.domain.roster import Roster
from tests.api.test_runs import CSV, Recorder, keys_of, make_client, run_happy_flow, upload

XLSX = b"PK\x03\x04" + b"\x14\x00" * 64  # só o começo de um ZIP: a API não abre o arquivo, quem abre é o leitor
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


# --- upload: tipo pela extensão e pelos bytes iniciais ---


@pytest.mark.parametrize(
    ("name", "content", "fmt"),
    [
        ("escala.csv", CSV, "csv"),
        ("ESCALA.CSV", CSV, "csv"),
        ("escala.txt", CSV, "csv"),
        ("escala.xlsx", XLSX, "xlsx"),
        ("Escala Janeiro.XLSX", XLSX, "xlsx"),
        ("escala.pdf", PDF, "pdf"),
    ],
)
def test_accepted_types_reach_the_agent(tmp_path, name, content, fmt):
    client, agent = make_client(tmp_path)
    response = client.post("/api/runs", params={"file_name": name}, content=content)  # sem Content-Type: não importa
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["summary"]["format"] == fmt and body["summary"]["file_name"] == name
    assert list(agent._runs) == [body["run_id"]]


@pytest.mark.parametrize(
    ("name", "content", "fragment"),
    [
        ("escala.xlsm", XLSX, ".xlsm"),
        ("escala.xls", OLE, ".xls"),
        ("escala.csv", OLE, "formato antigo"),
        ("escala.xlsx", OLE, "formato antigo"),
        ("escala.xlsx", CSV, "não é uma planilha XLSX"),
        ("escala.pdf", CSV, "não é um PDF"),
        ("escala.pdf", XLSX, "não é um PDF"),
        ("escala.csv", XLSX, "compactado"),
        ("escala.txt", PDF, "um PDF"),
        ("escala.docx", XLSX, ".docx"),
        ("escala.json", b'{"a": 1}', ".json"),
        ("escala", CSV, "sem extensão"),
    ],
)
def test_refused_types_are_422_with_rx13_and_never_reach_the_agent(tmp_path, name, content, fragment):
    client, agent = make_client(tmp_path)
    response = upload(client.request, content=content, name=name)
    assert response.status_code == 422, response.text
    body = response.json()
    card = body["exception"]
    assert card["code"] == "RX-13" and card["decider"] == "gestor"
    assert fragment in body["detail"] and body["detail"] == card["reason"]
    assert f"arquivo: {name}" in card["evidence"]
    assert agent._runs == {}


@pytest.mark.parametrize(("name", "content"), [("escala.xlsx", XLSX), ("escala.pdf", PDF), ("escala.csv", CSV)])
def test_any_type_over_1mb_is_413_with_rx13(tmp_path, name, content):
    client, agent = make_client(tmp_path)
    response = upload(client.request, content=content + b"\x00" * (MAX_UPLOAD_BYTES + 1 - len(content)), name=name)
    assert response.status_code == 413
    assert response.json()["exception"]["code"] == "RX-13"
    assert agent._runs == {}


def test_xlsx_of_exactly_1mb_is_accepted(tmp_path):
    client, _ = make_client(tmp_path)
    content = XLSX + b"\x00" * (MAX_UPLOAD_BYTES - len(XLSX))
    assert upload(client.request, content=content, name="escala.xlsx").status_code == 201


# --- confirm com ConfirmInput opcional ---


def _started(client) -> str:
    response = upload(client.request)
    assert response.status_code == 201, response.text
    return response.json()["run_id"]


def test_confirm_without_body_passes_none(tmp_path):
    """Compatível com o e2e da C5, que confirma sem corpo."""
    client, agent = make_client(tmp_path)
    run_id = _started(client)
    response = client.post(f"/api/runs/{run_id}/confirm")
    assert response.status_code == 200, response.text
    assert agent.confirm_inputs[run_id] is None


def test_confirm_with_body_passes_the_confirm_input(tmp_path):
    client, agent = make_client(tmp_path)
    run_id = _started(client)
    body = {
        "coverage_pct": {"L01": 86},
        "hourly_wage_default": "16.50",
        "planned_week_start": "2027-01-11",
        "note": "a Ana está de férias na quarta",
        "identity": [{"card_id": "id-1", "same": True}],
    }
    response = client.post(f"/api/runs/{run_id}/confirm", json=body)
    assert response.status_code == 200, response.text
    assert agent.confirm_inputs[run_id] == ConfirmInput(
        coverage_pct={"L01": 86},
        hourly_wage_default="16.50",
        planned_week_start=date(2027, 1, 11),
        note="a Ana está de férias na quarta",
        identity=[IdentityAnswer(card_id="id-1", same=True)],
    )


def test_confirm_with_empty_object_is_all_defaults(tmp_path):
    client, agent = make_client(tmp_path)
    run_id = _started(client)
    assert client.post(f"/api/runs/{run_id}/confirm", json={}).status_code == 200
    assert agent.confirm_inputs[run_id] == ConfirmInput()


@pytest.mark.parametrize(
    "body",
    [
        {"coverage_pct": {"L01": 200}},
        {"coverage_pct": {"L01": 49}},
        {"hourly_wage_default": "0"},
        {"planned_week_start": "2027-01-12"},  # terça
        {"note": "x" * 501},
        {"identity": [{"card_id": "id-1"}]},
    ],
)
def test_invalid_confirm_input_is_422_and_the_agent_is_not_called(tmp_path, body):
    client, agent = make_client(tmp_path)
    run_id = _started(client)
    assert client.post(f"/api/runs/{run_id}/confirm", json=body).status_code == 422
    assert run_id not in agent.confirm_inputs
    assert agent.get_run(run_id).phase == "awaiting_confirm"


def test_confirm_with_body_on_unknown_run_is_404(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.post("/api/runs/nao-existe/confirm", json={}).status_code == 404


# --- próxima semana e quadro ---


def test_next_week_without_a_first_schedule_is_409(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/api/runs/next-week")
    assert response.status_code == 409
    assert "envie a primeira escala" in response.json()["detail"]
    assert NO_FIRST_SCHEDULE.startswith("envie a primeira escala")


def test_next_week_without_publication_is_409_even_with_a_roster(tmp_path):
    client, agent = make_client(tmp_path)
    client.post(f"/api/runs/{_started(client)}/confirm")  # grava o quadro, mas nada publicado
    assert agent.roster() is not None
    assert client.post("/api/runs/next-week").status_code == 409


def test_roster_is_404_before_the_first_confirmation(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.get("/api/roster").status_code == 404


def test_roster_after_confirmation_has_people_without_sex(tmp_path):
    client, agent = make_client(tmp_path)
    run_id = _started(client)
    client.post(f"/api/runs/{run_id}/confirm")
    response = client.get("/api/roster")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 1 and body["source_run_id"] == run_id
    assert body["stores"] and body["demand"] and body["employees"]
    assert any(e.sex for e in agent.roster().employees)  # o agente guarda `sex`; a rota não o devolve
    assert "sex" not in keys_of(body)


def test_next_week_after_publication_plans_the_following_week(tmp_path):
    client, _ = make_client(tmp_path)
    call = Recorder(client)
    first = run_happy_flow(call)
    published = call("GET", "/api/schedules/published").json()
    published_week = date.fromisoformat(published["version"]["schedule"]["week_start"])

    response = call("POST", "/api/runs/next-week")
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["run_id"] != first
    assert run["phase"] == "awaiting_confirm" and run["mode"] == "continuidade"
    assert date.fromisoformat(run["week_start"]) == published_week + timedelta(days=7)
    assert run["before"]["shifts"] and run["roster_version"] == 1
    assert run["summary"]["format"] == "continuidade"

    confirmed = call("POST", f"/api/runs/{run['run_id']}/confirm", json={"coverage_pct": {"L01": 90}})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["phase"] == "awaiting_approval"
    assert call("POST", f"/api/runs/{run['run_id']}/approve").json()["phase"] == "published"
    assert call("GET", "/api/roster").json()["version"] == 1  # a continuidade não grava quadro novo


def test_no_response_of_the_c6_routes_carries_sex(tmp_path):
    """RN-13 (invariante 7): varre o JSON de todas as rotas, inclusive as novas."""
    client, _ = make_client(tmp_path)
    call = Recorder(client)
    call("GET", "/api/roster")  # 404
    call("POST", "/api/runs/next-week")  # 409
    run_id = run_happy_flow(call)
    call("GET", f"/api/runs/{run_id}")
    call("GET", f"/api/runs/{run_id}/trace")
    call("GET", "/api/roster")
    nxt = call("POST", "/api/runs/next-week").json()["run_id"]
    call("POST", f"/api/runs/{nxt}/confirm", json={"note": "teste"})
    call("GET", f"/api/runs/{nxt}/schedule")
    call("GET", f"/api/runs/{nxt}/trace")
    upload(call, content=XLSX, name="escala.xlsx")
    upload(call, content=XLSX, name="escala.xlsm")
    assert len(call.bodies) >= 18
    for body in call.bodies:
        assert "sex" not in keys_of(body), body


# --- adaptador do agente real ---


class _AgentC6:
    """Com as assinaturas da B4a."""

    def __init__(self, roster: Roster | None = None, *, phase_error: bool = False) -> None:
        self.confirmed: list[tuple] = []
        self._roster, self._phase_error = roster, phase_error

    def confirm(self, run_id: str, data: ConfirmInput | None = None) -> RunState:
        self.confirmed.append((run_id, data))
        return RunState(run_id=run_id, phase="awaiting_approval")

    def start_next_week(self) -> RunState:
        from escalista.agents.optimizer import errors as agent_errors

        if self._phase_error:
            raise agent_errors.RunPhaseError("envie a primeira escala")
        return RunState(run_id="run-next", phase="awaiting_confirm", mode="continuidade")

    def roster(self) -> Roster | None:
        return self._roster


def test_adapter_forwards_when_the_agent_has_the_new_methods():
    roster = FakeSliceAgent.with_seeded_runs().roster()
    inner = _AgentC6(roster)
    adapter = OptimizerSliceAgent(inner)  # type: ignore[arg-type]
    data = ConfirmInput(coverage_pct={"L01": 90})
    adapter.confirm("run-1", data)
    adapter.confirm("run-2")
    assert inner.confirmed == [("run-1", data), ("run-2", None)]
    assert adapter.start_next_week().mode == "continuidade"
    assert adapter.roster() is roster


def test_adapter_translates_the_agent_phase_error_of_next_week():
    adapter = OptimizerSliceAgent(_AgentC6(phase_error=True))  # type: ignore[arg-type]
    with pytest.raises(wiring.RunPhaseError, match="envie a primeira escala"):
        adapter.start_next_week()


def test_real_app_answers_next_week_409_and_roster_404_on_a_fresh_database(tmp_path):
    """Com o agente real e o banco vazio: sem 500 (sem publicada nem quadro)."""
    from fastapi.testclient import TestClient

    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "d"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    client = TestClient(create_app(settings))
    assert client.post("/auth/demo/gestor").status_code == 200
    assert client.post("/api/runs/next-week").status_code == 409
    assert client.get("/api/roster").status_code == 404


def test_fake_and_adapter_satisfy_the_c6_protocol():
    assert isinstance(FakeSliceAgent(), wiring.SliceAgentC6)
    assert isinstance(OptimizerSliceAgent(_AgentC6()), wiring.SliceAgentC6)  # type: ignore[arg-type]
