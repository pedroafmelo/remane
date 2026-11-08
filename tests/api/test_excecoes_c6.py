"""Fila de exceções e celular do colaborador sobre uma escala publicada pela C6 (integração com o PR #19).

A C6 grava o quadro na confirmação e publica escalas com os ids dele (`n-<nome>`), de uma semana qualquer (aqui a
seguinte à da demo), não com os ids de `data/demo`. A busca de cobertura, o celular e a republicação precisam achar
as pessoas no quadro guardado e conferir pelo cartão da semana da própria escala. Sem solver e sem modelo; dados
sintéticos.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from escalista.api.app import create_app
from escalista.api.fake_agent import FakeSliceAgent
from escalista.config import Settings
from escalista.domain.contracts import Role
from escalista.domain.results import Approval, ScheduleVersion
from escalista.domain.roster import Roster
from escalista.domain.schedule import Employee, Schedule, Shift, Store
from escalista.store.sql_repository import SqlRepository

WEEK = date(2027, 1, 18)  # a semana seguinte à da demo
RUN_ID, VERSION_ID = "run-c6-publicada", "ver-c6-publicada"
WEDNESDAY = (WEEK + timedelta(days=2)).isoformat()
NOW = datetime(2027, 1, 15, 9, 0)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


def person(slug: str, name: str) -> Employee:
    return Employee(
        id=f"n-{slug}",
        name=name,
        store_id="S1",
        job="Atendente",
        hourly_wage=Decimal("12.00"),
        contract_hours=44,
    )


PEOPLE = [
    person("ana-dantas", "Ana Dantas (sintético)"),  # 5 turnos: é a colaboradora da demo
    person("bruno-lima", "Bruno Lima (sintético)"),  # trabalha na terça à noite: não cobre a quarta cedo (interjornada)
    person("carla-reis", "Carla Reis (sintético)"),  # de folga a semana toda: cobre
    person("diego-nery", "Diego Nery (sintético)"),  # de folga a semana toda: cobre
]


def shift(employee: Employee, day: int, hour: int) -> Shift:
    begin = datetime.combine(WEEK + timedelta(days=day), time(hour))
    return Shift(employee_id=employee.id, store_id="S1", start=begin, end=begin + timedelta(hours=8))


def make_client(tmp_path) -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    app = create_app(settings, agent=FakeSliceAgent())
    repo = SqlRepository(app.state.engine)
    ana, bruno = PEOPLE[0], PEOPLE[1]
    repo.save_roster(
        Roster(
            version=1,
            stores=[Store(id="S1", name="Loja Teste (fictícia)", opens=time(8), closes=time(22))],
            employees=PEOPLE,
            demand=[],
            source_run_id=RUN_ID,
            confirmed_by="demo-gestor",
            confirmed_at=NOW,
        )
    )
    shifts = [shift(ana, d, 8) for d in range(5)] + [shift(bruno, 1, 14)]
    repo.save_version(
        ScheduleVersion(
            id=VERSION_ID,
            run_id=RUN_ID,
            schedule=Schedule(week_start=WEEK, shifts=shifts),
            status="draft",
            input_hash="semente-c6",
            seed=42,
            violations_total=0,
            created_at=NOW,
        )
    )
    repo.record_approval(
        Approval(id="apr-c6", version_id=VERSION_ID, approved_by="demo-gestor", role=Role.GESTOR, at=NOW)
    )
    repo.mark_published(VERSION_ID, NOW)
    return TestClient(app)


def as_role(client: TestClient, role: str) -> TestClient:
    assert client.post(f"/auth/demo/{role}").status_code == 200
    return client


def test_colaborador_sees_the_week_of_a_c6_published_schedule(tmp_path):
    client = as_role(make_client(tmp_path), "colaborador")
    body = client.get("/api/colaborador/escala").json()
    assert body["published"] and body["week_start"] == WEEK.isoformat()
    assert body["employee"] == {
        "id": "n-ana-dantas",
        "name": "Ana Dantas (sintético)",
        "job": "Atendente",
        "store": "Loja Teste (fictícia)",
    }
    assert len(body["shifts"]) == 5


def test_falta_on_a_c6_schedule_finds_cover_in_the_roster_and_republishes(tmp_path):
    client = make_client(tmp_path)
    as_role(client, "colaborador")
    assert client.post("/api/colaborador/falta", json={"day": WEDNESDAY}).status_code == 200
    case = client.get("/api/colaborador/caixa").json()["cases"][0]
    # Bruno trabalha na terça das 14h às 22h: cobrir a quarta às 8h violaria a interjornada; a 1ª oferta vai à Carla
    offer = case["offers"][0]
    assert offer["candidate_id"] == "n-carla-reis"
    accepted = client.post(f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": "n-carla-reis", "accept": True})
    assert accepted.status_code == 200

    as_role(client, "gestor")
    item = next(i for i in client.get("/api/exceptions").json()["open"] if i["source"].get("kind") == "track")
    assert item["card"]["code"] == "COBERTURA"
    assert "Loja Teste (fictícia)" in " ".join(item["card"]["evidence"])
    assert client.post(f"/api/exceptions/{item['id']}/decide", json={"option_index": 0}).status_code == 200
    published = SqlRepository(client.app.state.engine).latest_published()
    assert published is not None and published.id != VERSION_ID and published.schedule.week_start == WEEK
    covering = {s.employee_id for s in published.schedule.shifts if s.start.date().isoformat() == WEDNESDAY}
    assert "n-carla-reis" in covering and "n-ana-dantas" not in covering

    as_role(client, "colaborador")
    week = client.get("/api/colaborador/escala").json()
    assert week["employee"]["id"] == "n-ana-dantas"  # a identidade não muda depois da cobertura
