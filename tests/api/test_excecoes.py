"""Fila de exceções (FT-04) e falta pelo celular simulado (FT-03 mínimo), pela API, sem solver nem modelo."""

import pytest
from fastapi.testclient import TestClient

from escalista.api.app import create_app
from escalista.api.excecoes import RULES_RUN
from escalista.api.fake_agent import FakeSliceAgent
from escalista.audit.sink import SqlTraceSink
from escalista.config import Settings
from escalista.domain.results import ScheduleVersion
from escalista.store.sql_repository import SqlRepository
from tests.api.published_seed import RUN_ID, VERSION_ID, seed_published

WEDNESDAY, MONDAY, SATURDAY = "2027-01-13", "2027-01-11", "2027-01-16"
L1_THIRD_GROUP = {"P003", "P006", "P009", "P012", "P015", "P018"}  # i % 3 == 2: de folga na quarta


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


def make_client(tmp_path, *, published: bool = True) -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    app = create_app(settings, agent=FakeSliceAgent(), seed_demo=published)
    if published:
        seed_published(app.state.engine)
    return TestClient(app)


def as_role(client: TestClient, role: str) -> TestClient:
    assert client.post(f"/auth/demo/{role}").status_code == 200
    return client


def kinds(client: TestClient, run_id: str) -> list[str]:
    return [e.kind for e in SqlTraceSink(client.app.state.engine).list_events(run_id)]


def test_rx01_is_seeded_once_and_decided_by_the_gestor(tmp_path):
    client = as_role(make_client(tmp_path), "gestor")
    client.app.state.desk.seed()  # idempotente: a segunda semente não duplica
    queue = client.get("/api/exceptions").json()
    assert [i["card"]["code"] for i in queue["open"]] == ["RX-01"]
    item = queue["open"][0]
    assert item["card"]["deadline"] and item["card"]["options"] and item["card"]["recommendation"]

    response = client.post(f"/api/exceptions/{item['id']}/decide", json={"option_index": 0})
    assert response.status_code == 200
    decision = response.json()["decision"]
    assert decision["by"] == "demo-gestor" and decision["role"] == "gestor" and decision["option_index"] == 0

    queue = client.get("/api/exceptions").json()
    assert queue["open"] == [] and [i["id"] for i in queue["decided"]] == [item["id"]]
    assert "exception.decided" in kinds(client, RULES_RUN)
    assert client.post(f"/api/exceptions/{item['id']}/decide", json={"option_index": 0}).status_code == 409


def test_decide_rejects_unknown_item_and_option(tmp_path):
    client = as_role(make_client(tmp_path), "gestor")
    assert client.post("/api/exceptions/nao-existe/decide", json={"option_index": 0}).status_code == 404
    assert client.post("/api/exceptions/rx01-1/decide", json={"option_index": 9}).status_code == 422
    assert client.post("/api/exceptions/rx01-1/decide", json={"option_index": -1}).status_code == 422


def test_colaborador_without_published_schedule(tmp_path):
    client = as_role(make_client(tmp_path, published=False), "colaborador")
    assert client.get("/api/colaborador/escala").json()["published"] is False
    assert client.post("/api/colaborador/falta", json={"day": WEDNESDAY}).status_code == 409


def test_colaborador_sees_own_week_without_salary_or_sex(tmp_path):
    client = as_role(make_client(tmp_path), "colaborador")
    response = client.get("/api/colaborador/escala")
    body = response.json()
    assert body["published"] and body["synthetic"]
    assert body["employee"]["id"] == "P001"  # mais turnos na semana, menor id
    assert len(body["shifts"]) == 5
    for forbidden in ("hourly_wage", "wage", "salario", '"sex"', "contract_hours"):
        assert forbidden not in response.text


def test_falta_becomes_a_tracking_case_offered_accepted_validated_and_republished(tmp_path):
    """C7: a rota antiga da falta vira caso do acompanhamento: oferta ao 1º candidato, aceite dele pelo celular,
    cartão COBERTURA ao gestor e republicação com a aprovação dele."""
    client = make_client(tmp_path)
    as_role(client, "colaborador")
    assert client.post("/api/colaborador/falta", json={"day": WEDNESDAY, "text": "não vou poder ir"}).status_code == 200
    assert client.post("/api/colaborador/falta", json={"day": WEDNESDAY}).status_code == 409  # já avisada
    assert client.post("/api/colaborador/falta", json={"day": SATURDAY}).status_code == 422  # sem turno

    box = client.get("/api/colaborador/caixa").json()
    assert box["employee"]["id"] == "P001" and [c["status"] for c in box["cases"]] == ["oferta_enviada"]
    offer = box["cases"][0]["offers"][0]
    assert offer["candidate_id"] in L1_THIRD_GROUP
    accepted = client.post(
        f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": offer["candidate_id"], "accept": True}
    )
    assert accepted.status_code == 200 and accepted.json()["status"] == "aguardando_gestor"

    as_role(client, "gestor")
    item = next(i for i in client.get("/api/exceptions").json()["open"] if i["source"].get("kind") == "track")
    assert item["card"]["code"] == "COBERTURA"
    decided = client.post(f"/api/exceptions/{item['id']}/decide", json={"option_index": 0})
    assert decided.status_code == 200 and decided.json()["decision"]["outcome"].startswith("Escala republicada")
    published = ScheduleVersion.model_validate(SqlRepository(client.app.state.engine).latest_published())
    assert published.id != VERSION_ID and published.run_id == RUN_ID and published.status == "published"
    wednesday = [s for s in published.schedule.shifts if s.start.date().isoformat() == WEDNESDAY and s.start.hour == 8]
    assert offer["candidate_id"] in {s.employee_id for s in wednesday}
    assert "P001" not in {s.employee_id for s in wednesday}

    as_role(client, "colaborador")
    week = client.get("/api/colaborador/escala").json()
    assert week["employee"]["id"] == "P001"  # a identidade não muda depois da cobertura
    assert WEDNESDAY not in {s["day"] for s in week["shifts"]}


def test_falta_without_eligible_cover_opens_rx05(tmp_path):
    client = make_client(tmp_path)
    as_role(client, "colaborador")
    client.post("/api/colaborador/falta", json={"day": MONDAY})
    as_role(client, "gestor")
    item = next(i for i in client.get("/api/exceptions").json()["open"] if i["source"].get("kind") == "track")
    assert item["card"]["code"] == "RX-05"
    labels = [o["label"] for o in item["card"]["options"]]
    assert "Deixar o turno descoberto" in labels
    response = client.post(
        f"/api/exceptions/{item['id']}/decide", json={"option_index": labels.index("Deixar o turno descoberto")}
    )
    assert response.status_code == 200
    assert SqlRepository(client.app.state.engine).latest_published().id == VERSION_ID  # nada republicado

    as_role(client, "colaborador")
    assert client.get("/api/colaborador/caixa").json()["cases"][0]["status"] == "descoberto"
