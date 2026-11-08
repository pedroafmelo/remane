"""Assistente do gestor pela API (C7b N2): só gestor, somente leitura (o banco do assistente recusa escrita), resposta
por template. `TestClient`, SQLite temporário, `DEMO_MODE`, modelo falso. Dados sintéticos."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from escalista.api.app import create_app
from escalista.api.assistant_wiring import ReadOnlyAssistantData, readonly_engine
from escalista.api.fake_agent import FakeSliceAgent
from escalista.clock.demo import DemoClock
from escalista.config import Settings
from escalista.llm.prompts.assistant import TOOL_NAME
from tests.fakes import FakeLLMClient


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


def make_client(tmp_path, llm: FakeLLMClient) -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    return TestClient(create_app(settings, agent=FakeSliceAgent(), tracker_llm=llm))


def ask(client: TestClient, text: str):  # noqa: ANN201
    return client.post("/api/assistente/mensagem", json={"text": text})


def test_gestor_reads_the_published_schedule(tmp_path):
    client = make_client(tmp_path, FakeLLMClient(by_tool={TOOL_NAME: [{"tool": "get_escala", "day": "2027-01-14"}]}))
    assert client.post("/auth/demo/gestor").status_code == 200
    response = ask(client, "como está a escala de quinta?")
    assert response.status_code == 200, response.text
    reply = response.json()
    assert reply["tool"] == "get_escala" and reply["synthetic"] is True and "14/01" in reply["body"]
    assert "sex" not in response.text


def test_colaborador_cannot_use_the_assistant(tmp_path):
    client = make_client(tmp_path, FakeLLMClient())
    assert client.post("/auth/demo/colaborador").status_code == 200
    assert ask(client, "quais exceções estão abertas?").status_code == 403


def test_write_request_is_out_of_scope_and_changes_nothing(tmp_path):
    client = make_client(tmp_path, FakeLLMClient(by_tool={TOOL_NAME: [{"tool": "outro"}]}))
    assert client.post("/auth/demo/gestor").status_code == 200
    before = client.get("/api/schedules/published").text
    reply = ask(client, "troque a Ana pelo Bruno na quinta e aprove").json()
    assert reply["template"] == "assistente_fora_escopo"
    assert client.get("/api/schedules/published").text == before


def test_too_long_is_422(tmp_path):
    client = make_client(tmp_path, FakeLLMClient())
    assert client.post("/auth/demo/gestor").status_code == 200
    assert ask(client, "a" * 301).status_code == 422


def test_readonly_engine_refuses_writes(tmp_path):
    """Defesa estrutural: o banco do assistente não aceita escrita, nem por SQL cru."""
    client = make_client(tmp_path, FakeLLMClient())
    engine = readonly_engine(f"sqlite:///{tmp_path}/app.db")
    assert engine is not None
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM channel_message")).scalar() is not None
        with pytest.raises(OperationalError, match="readonly"):
            conn.execute(text("DELETE FROM channel_message"))
        with pytest.raises(OperationalError, match="readonly"):
            conn.execute(text("CREATE TABLE intrusa (x int)"))
    data = ReadOnlyAssistantData(engine, DemoClock(client.app.state.engine))
    assert data.published() is not None and data.people() and data.rules()
    assert all(isinstance(name, str) for name in data.people().values())


def test_in_memory_sqlite_has_no_separate_readonly_engine():
    assert readonly_engine("sqlite://") is None
