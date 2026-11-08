"""Roteiro da demo da C7 de ponta a ponta (plano da C7, seção 1, passos 1 a 6), só por HTTP (`TestClient`).

Um fluxo único: gestor reinicia → Ana avisa e anexa o atestado → a oferta passa de P105 (recusa) a P107 (aceita) →
gestor valida e a escala é republicada → +15 min duas vezes (Carla não bateu o ponto) → RX-09 → aviso numa loja sem
candidato (RX-05 e `overtime_needed`) → métricas do rastro. SQLite em arquivo temporário, `DEMO_MODE` ligado e o
modelo falso (`FakeLLMClient` só para `read_atestado`): nunca chama o modelo real nem lê o `.env`.
Dados sintéticos de `data/demo/acompanhamento`; os ids e os instantes vêm do gabarito `cenario.esperado.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from escalista.agents.tracker.metrics import summarize
from escalista.api.app import create_app
from escalista.api.fake_agent import FakeSliceAgent
from escalista.api.tracker_wiring import SCENARIO_RUN
from escalista.audit.sink import SqlTraceSink
from escalista.config import Settings
from escalista.store.sql_repository import SqlRepository
from tests.e2e.test_fatia import ENV_NAMES
from tests.fakes import FakeLLMClient

DEMO = Path("data/demo/acompanhamento")
ATESTADO = DEMO / "atestados" / "at-01-legivel.pdf"
EXPECTED = json.loads((DEMO / "cenario.esperado.json").read_text())
CASES = {c["id"]: c for c in EXPECTED["cases"]}
ANA, CARLA = CASES["PL-01"], CASES["DV-01"]
NO_CANDIDATE = CASES["PL-02"]  # loja 2: ninguém cobre dentro das regras
THURSDAY = "2027-01-14"
READING = {
    "legible": True,
    "issued_on": "2027-01-13",
    "start_on": THURSDAY,
    "days": 2,
    "patient_matches": True,
    "has_crm": True,
}

pytestmark = pytest.mark.usefixtures("clean_env")


@pytest.fixture
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def kinds(events) -> list[str]:
    return [e.kind for e in events]


def test_demo_script_end_to_end(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=True,
        session_secret="segredo-de-teste",
    )
    llm = FakeLLMClient(by_tool={"read_atestado": [READING]})
    api = TestClient(create_app(settings, agent=FakeSliceAgent(), tracker_llm=llm))
    engine = api.app.state.engine
    repo, sink = SqlRepository(engine), SqlTraceSink(engine)

    session = {"role": ""}

    def login(role: str) -> None:
        if session["role"] != role:  # a sessão é por cookie: só troca de papel quando preciso
            assert api.post(f"/auth/demo/{role}").status_code == 200
            session["role"] = role

    def box(person: str) -> dict:
        previous = session["role"]
        login("colaborador")
        response = api.get("/api/colaborador/caixa", params={"as": person})
        assert response.status_code == 200, response.text
        login(previous or "colaborador")
        return response.json()

    def templates(person: str, direction: str = "out") -> list[str]:
        return [m["template"] for m in box(person)["messages"] if m["direction"] == direction]

    def queue_item(code: str) -> dict:
        items = [i for i in api.get("/api/exceptions").json()["open"] if i["card"]["code"] == code]
        assert items, f"sem cartão {code} na fila"
        return items[-1]

    def decide(item: dict, option: int = 0) -> dict:
        response = api.post(f"/api/exceptions/{item['id']}/decide", json={"option_index": option})
        assert response.status_code == 200, response.text
        return response.json()

    # 1. gestor reinicia: relógio em qua 13/01 13:55 e a escala sintética publicada
    login("gestor")
    assert api.post("/api/demo/reset").json() == {"now": EXPECTED["demo_clock"]}
    assert api.get("/api/demo/clock").json()["now"] == EXPECTED["demo_clock"]
    seeded = repo.latest_published()
    assert seeded.run_id == SCENARIO_RUN and seeded.schedule.week_start.isoformat() == EXPECTED["week_start"]

    # 2. Ana (P101) avisa a falta de qui 14/01 e anexa o atestado legível
    login("colaborador")
    case = api.post("/api/colaborador/aviso", json={"as": ANA["employee_id"], "day": THURSDAY, "kind": "falta"})
    assert case.status_code == 200, case.text
    case = case.json()
    case_id = case["case_id"]
    assert case["offers"][0]["candidate_id"] == ANA["ranked"][0] == "P105"  # rank 1
    attached = api.post(
        f"/api/colaborador/caso/{case_id}/anexo",
        params={"as": "P101", "file_name": ATESTADO.name},
        content=ATESTADO.read_bytes(),
        headers={"Content-Type": "application/pdf"},
    )
    assert attached.status_code == 200, attached.text
    attached = attached.json()
    assert attached["abono"] == "provisorio" and attached["reading"]["verdict"] == "valido"
    assert "recebido" in templates("P101")
    assert box("P101")["offers"] == [] and "oferta" in templates("P105")

    # 3. P105 vê a oferta sem hora extra; P107 não pode responder por ela; P105 recusa e a oferta vai a P107
    offer = box("P105")["offers"][0]
    assert offer["status"] == "enviada" and float(offer["overtime_hours"]) == 0
    forbidden = api.post(f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": "P107", "accept": True})
    assert forbidden.status_code == 403
    declined = api.post(f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": "P105", "accept": False})
    assert declined.status_code == 200, declined.text
    second = box("P107")["offers"]
    assert len(second) == 1 and second[0]["status"] == "enviada"
    accepted = api.post(f"/api/colaborador/oferta/{second[0]['offer_id']}", json={"as": "P107", "accept": True})
    assert accepted.status_code == 200 and accepted.json()["status"] == "aguardando_gestor"

    # 4. gestor valida a cobertura: escala republicada com P107 no turno de qui 14h; 0 violações novas
    login("gestor")
    assert api.get("/api/exceptions").json()["now"] == EXPECTED["demo_clock"]
    outcome = decide(queue_item("COBERTURA"))
    assert outcome["decision"]["outcome"].startswith("Escala republicada")
    latest = repo.latest_published()
    assert latest.id != seeded.id and repo.get_approval(latest.id) is not None
    thursday = {s.employee_id for s in latest.schedule.shifts if s.start.isoformat() == ANA["shift_start"]}
    assert "P107" in thursday and "P101" not in thursday
    assert "cobertura_confirmada" in templates("P107")
    assert "falta_coberta" in templates("P101")
    # `GET /api/runs/{id}/trace` é do agente da escala e não cobre `track-<caso>`: lê-se o sink pelo `app.state`
    assert api.get(f"/api/runs/track-{case_id}/trace").status_code == 404
    events = sink.list_events(f"track-{case_id}")
    closed = [e for e in events if e.kind == "track.case.closed"]
    assert closed and closed[-1].payload["new_violations"] == 0 and closed[-1].payload["outcome"] == "coberta"
    assert {"track.offer.accepted", "exception.decided", "schedule.republished"} <= set(kinds(events))

    # 5. +15 min: 14:10, Carla (P102) não bateu o ponto e recebe a pergunta
    advanced = api.post("/api/demo/clock/advance", json={"minutes": 15}).json()
    assert advanced["now"] == CARLA["fires_at"]
    assert ("no_punch", CARLA["employee_id"]) in {(t["kind"], t["employee_id"]) for t in advanced["triggers"]}
    assert box("P102")["questions"] and "pergunta" in templates("P102")
    #    +15 min: 14:25, sem resposta, abre o RX-09; a decisão 0 manda a oferta de cobertura a alguém da loja 1
    advanced = api.post("/api/demo/clock/advance", json={"minutes": 15}).json()
    assert advanced["now"] == CARLA["no_answer"]["fires_at"]
    rx09 = queue_item("RX-09")
    decide(rx09, 0)
    carla_case = next(c for c in box("P102")["cases"])
    candidates = {o["candidate_id"] for o in carla_case["offers"]}
    assert candidates and all(c.startswith("P1") for c in candidates)  # P1xx: pessoas da loja 1
    assert candidates <= set(CARLA["ranked"]) | {"P107"}
    assert any(box(p)["offers"] for p in candidates)

    # 6. falta numa loja sem candidato: RX-05 na fila e o gatilho overtime_needed (RF-28)
    absent = NO_CANDIDATE["employee_id"]
    day = NO_CANDIDATE["shift_start"][:10]
    login("colaborador")
    lonely = api.post("/api/colaborador/aviso", json={"as": absent, "day": day, "kind": "falta"})
    assert lonely.status_code == 200, lonely.text
    lonely_id = lonely.json()["case_id"]
    login("gestor")
    assert queue_item("RX-05")["card"]["code"] == "RX-05"
    lonely_events = sink.list_events(f"track-{lonely_id}")
    fired = [e.payload["trigger"] for e in lonely_events if e.kind == "track.trigger.fired"]
    assert "overtime_needed" in fired

    # 7. métricas só do rastro: custo do falso não é medido, e nada foi violado
    every = [e for run in {f"track-{case_id}", f"track-{lonely_id}", "track-sweep"} for e in sink.list_events(run)]
    every += sink.list_events(f"track-{carla_case['case_id']}")
    metrics = summarize(every)
    assert metrics.covered >= 1 and metrics.new_violations_total == 0
    assert metrics.cost_usd_total is None  # o falso não mede custo: "não medido"
