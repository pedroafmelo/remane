"""Acompanhamento pela API (C7, C1): o roteiro da demo, passos 1 a 5, com `TestClient`, SQLite em memória,
`DEMO_MODE` ligado e o modelo falso (nunca o real). Dados sintéticos (`data/demo/acompanhamento`)."""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from escalista.api.app import create_app
from escalista.api.fake_agent import FakeSliceAgent
from escalista.api.tracker_wiring import SCENARIO_RUN
from escalista.audit.sink import SqlTraceSink
from escalista.config import Settings
from escalista.store.sql_repository import SqlRepository
from tests.fakes import FakeLLMClient

ATESTADO = Path("data/demo/acompanhamento/atestados/at-09-cid-espalhado.pdf")
CID = "J11"
THURSDAY = "2027-01-14"
READING = {
    "legible": True,
    "issued_on": "2027-01-13",
    "start_on": THURSDAY,
    "days": 3,
    "patient_matches": True,
    "has_crm": True,
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


class Recorder:
    """`TestClient` que guarda o texto de toda resposta, para procurar vazamento de CID ou texto livre."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.bodies: list[str] = []

    def __getattr__(self, method: str):  # noqa: ANN204
        def call(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            response = getattr(self.client, method)(*args, **kwargs)
            self.bodies.append(response.text)
            return response

        return call

    def login(self, role: str) -> None:
        assert self.client.post(f"/auth/demo/{role}").status_code == 200


def make_client(tmp_path, *, demo_mode: bool = True) -> Recorder:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=demo_mode,
        session_secret="segredo-de-teste",
    )
    llm = FakeLLMClient(by_tool={"read_atestado": [READING]})
    return Recorder(TestClient(create_app(settings, agent=FakeSliceAgent(), tracker_llm=llm)))


def test_in_memory_engine_is_shared_by_the_app():
    """O app sobe com `sqlite://` em memória (uma conexão só) e já traz a semana sintética publicada."""
    settings = Settings(_env_file=None, database_url="sqlite://", demo_mode=True, session_secret="s")
    app = create_app(settings, agent=FakeSliceAgent(), tracker_llm=FakeLLMClient())
    assert isinstance(app.state.engine.pool, StaticPool) or app.state.engine.url.database in (None, "", ":memory:")
    assert SqlRepository(app.state.engine).latest_published().run_id == SCENARIO_RUN


def test_demo_script_from_reset_to_republished_cover(tmp_path):
    api = make_client(tmp_path)

    # 1. gestor reinicia: relógio em qua 13/01 13:55 e a semana sintética publicada (sem aprovação fingida)
    api.login("gestor")
    assert api.post("/api/demo/reset").json() == {"now": "2027-01-13T13:55:00"}
    assert api.get("/api/demo/clock").json() == {
        "now": "2027-01-13T13:55:00",
        "base": "2027-01-13T13:55:00",
        "simulated": True,
    }
    repo = SqlRepository(api.client.app.state.engine)
    seeded = repo.latest_published()
    assert seeded.run_id == SCENARIO_RUN and repo.get_approval(seeded.id) is None
    sink = SqlTraceSink(api.client.app.state.engine)
    seeded_event = sink.list_events(SCENARIO_RUN)[-1]
    assert seeded_event.kind == "demo.seeded"
    assert seeded_event.payload["version_id"] == seeded.id and seeded_event.payload["synthetic"] is True

    # 2. Ana avisa a falta de qui 14/01 (só `has_text`) e anexa o atestado em PDF
    api.login("colaborador")
    people = api.get("/api/colaborador/pessoas").json()
    assert people["default_id"] == "P101" and len(people["people"]) == 17
    case = api.post("/api/colaborador/aviso", json={"as": "P101", "day": THURSDAY, "kind": "falta", "has_text": True})
    assert case.status_code == 200, case.text
    case = case.json()
    assert case["status"] == "oferta_enviada" and case["offers"][0]["candidate_id"] == "P105"
    attached = api.post(
        f"/api/colaborador/caso/{case['case_id']}/anexo",
        params={"as": "P101", "file_name": "atestado.pdf"},
        content=ATESTADO.read_bytes(),
        headers={"Content-Type": "application/pdf"},
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["abono"] == "provisorio" and attached.json()["reading"]["verdict"] == "valido"
    box = api.get("/api/colaborador/caixa", params={"as": "P101"}).json()
    assert box["now"] == "2027-01-13T13:55:00" and box["synthetic"] is True
    inbound = [m for m in box["messages"] if m["direction"] == "in"]
    assert [m["template"] for m in inbound] == ["aviso_falta", "anexo"]
    assert inbound[0]["has_text"] is True and inbound[1]["attachment_media_type"] == "application/pdf"
    assert box["messages"][0]["template"] == "aviso_falta"  # o aviso abre a conversa, antes da resposta do Pat
    assert all(m["body"] is None for m in inbound)

    # 3. Elisa (P105) vê a oferta e aceita
    box = api.get("/api/colaborador/caixa", params={"as": "P105"}).json()
    offer = box["offers"][0]
    assert offer["status"] == "enviada" and Decimal(offer["overtime_hours"]) == 0
    assert offer["store"] == "Loja Sintética Centro"
    wrong = api.post(f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": "P106", "accept": True})
    assert wrong.status_code == 403  # só o próprio candidato responde
    accepted = api.post(f"/api/colaborador/oferta/{offer['offer_id']}", json={"as": "P105", "accept": True})
    assert accepted.status_code == 200 and accepted.json()["status"] == "aguardando_gestor"

    # 4. gestor valida a cobertura: escala republicada com o turno de P105, 0 violações novas
    api.login("gestor")
    queue = api.get("/api/exceptions").json()
    assert queue["now"] == "2027-01-13T13:55:00"
    item = next(i for i in queue["open"] if i["card"]["code"] == "COBERTURA")
    decided = api.post(f"/api/exceptions/{item['id']}/decide", json={"option_index": 0})
    assert decided.status_code == 200, decided.text
    assert decided.json()["decision"]["outcome"].startswith("Escala republicada")
    latest = repo.latest_published()
    assert latest.id != seeded.id and latest.run_id == SCENARIO_RUN and repo.get_approval(latest.id) is not None
    thursday = {s.employee_id for s in latest.schedule.shifts if s.start.isoformat() == f"{THURSDAY}T14:00:00"}
    assert "P105" in thursday and "P101" not in thursday
    closed = [e for e in sink.list_events(f"track-{case['case_id']}") if e.kind == "track.case.closed"]
    assert closed[-1].payload["new_violations"] == 0 and closed[-1].payload["outcome"] == "coberta"
    assert "exception.decided" in [e.kind for e in sink.list_events(f"track-{case['case_id']}")]

    # 5. +15 min duas vezes: às 14:10 a Carla (P102) não bateu o ponto
    first = api.post("/api/demo/clock/advance", json={"minutes": 15}).json()
    assert first["now"] == "2027-01-13T14:10:00"
    assert ("no_punch", "P102") in {(t["kind"], t["employee_id"]) for t in first["triggers"]}
    assert first["events"] > 0
    assert api.post("/api/demo/clock/advance", json={"minutes": 7}).status_code == 422

    api.login("colaborador")
    box = api.get("/api/colaborador/caixa", params={"as": "P101"}).json()
    assert box["cases"][0]["status"] == "coberto"
    # a identidade da demo segue a de quem avisou, mesmo com um turno a menos
    assert api.get("/api/colaborador/pessoas").json()["default_id"] == "P101"

    # nenhuma resposta do roteiro ecoa o CID do atestado
    assert not [b for b in api.bodies if CID in b]


def test_reset_clears_cases_messages_and_track_cards(tmp_path):
    api = make_client(tmp_path)
    api.login("colaborador")
    api.post("/api/colaborador/aviso", json={"as": "P101", "day": THURSDAY, "kind": "falta"})
    api.post("/api/demo/clock/advance", json={"minutes": 15})
    api.login("gestor")
    assert api.post("/api/demo/reset").status_code == 200
    assert all(i["source"].get("kind") != "track" for i in api.get("/api/exceptions").json()["open"])
    api.login("colaborador")
    box = api.get("/api/colaborador/caixa", params={"as": "P101"}).json()
    assert box["cases"] == [] and box["messages"] == [] and box["now"] == "2027-01-13T13:55:00"


def test_colaborador_cannot_reset(tmp_path):
    api = make_client(tmp_path)
    api.login("colaborador")
    assert api.post("/api/demo/reset").status_code == 403


def test_person_outside_the_roster_is_403_and_traced(tmp_path):
    api = make_client(tmp_path)
    api.login("colaborador")
    response = api.get("/api/colaborador/caixa", params={"as": "P999"})
    assert response.status_code == 403 and response.json()["detail"] == "pessoa fora do quadro"
    response = api.post("/api/colaborador/aviso", json={"as": "P999", "day": THURSDAY, "kind": "falta"})
    assert response.status_code == 403
    rejected = [e for e in SqlTraceSink(api.client.app.state.engine).list_events("track-sweep")]
    assert [e.kind for e in rejected] == ["track.channel.rejected"] * 2
    assert "P999" not in str([e.payload for e in rejected])  # só o hash


def test_without_demo_mode_as_of_another_person_is_403(tmp_path):
    api = make_client(tmp_path)
    api.login("colaborador")
    app = api.client.app
    app.state.settings = app.state.settings.model_copy(update={"demo_mode": False})
    assert api.get("/api/colaborador/caixa", params={"as": "P105"}).status_code == 403
    assert api.get("/api/colaborador/caixa", params={"as": "P101"}).status_code == 200  # a própria pessoa padrão
    assert api.get("/api/colaborador/caixa").json()["employee"]["id"] == "P101"


def test_attachment_must_be_a_pdf_of_the_case_owner(tmp_path):
    api = make_client(tmp_path)
    api.login("colaborador")
    case = api.post("/api/colaborador/aviso", json={"as": "P101", "day": THURSDAY, "kind": "falta"}).json()
    url = f"/api/colaborador/caso/{case['case_id']}/anexo"
    not_pdf = api.post(url, params={"as": "P101"}, content=b"\x89PNG\r\n imagem", headers={"Content-Type": "image/png"})
    assert not_pdf.status_code == 422
    other = api.post(url, params={"as": "P105"}, content=ATESTADO.read_bytes())
    assert other.status_code == 403
    too_big = api.post(url, params={"as": "P101"}, content=b"%PDF" + b"0" * (5 * 1024 * 1024))
    assert too_big.status_code == 413
    box = api.get("/api/colaborador/caixa", params={"as": "P101"}).json()
    assert [m["template"] for m in box["messages"] if m["direction"] == "in"] == ["aviso_falta"]  # recusas não ficam


def test_refused_report_leaves_no_inbound_message(tmp_path):
    api = make_client(tmp_path)
    api.login("colaborador")
    assert (
        api.post("/api/colaborador/aviso", json={"as": "P101", "day": "2027-01-11", "kind": "falta"}).status_code == 422
    )
    assert api.get("/api/colaborador/caixa", params={"as": "P101"}).json()["messages"] == []


def test_answer_to_the_agent_question(tmp_path):
    api = make_client(tmp_path)
    api.login("gestor")
    api.post("/api/demo/clock/advance", json={"minutes": 15})  # 14:10: pergunta à Carla (P102)
    api.login("colaborador")
    box = api.get("/api/colaborador/caixa", params={"as": "P102"}).json()
    assert len(box["questions"]) == 1
    answered = api.post(
        "/api/colaborador/resposta", json={"as": "P102", "case_id": box["questions"][0]["case_id"], "coming": True}
    )
    assert answered.status_code == 200 and answered.json()["status"] == "atraso_registrado"
    other = api.post(
        "/api/colaborador/resposta", json={"as": "P101", "case_id": box["questions"][0]["case_id"], "coming": False}
    )
    assert other.status_code in (403, 409)


def test_gestor_reads_the_case_trace_and_the_colaborador_does_not(tmp_path):
    """Passo 6 do roteiro: a auditoria do caso pela mesma rota de rastro das execuções (`track-<case_id>`)."""
    api = make_client(tmp_path)
    api.login("colaborador")
    case = api.post(
        "/api/colaborador/aviso", json={"as": "P101", "day": THURSDAY, "kind": "falta", "has_text": True}
    ).json()
    api.post(
        f"/api/colaborador/caso/{case['case_id']}/anexo",
        params={"as": "P101", "file_name": "atestado.pdf"},
        content=ATESTADO.read_bytes(),
    )
    url = f"/api/runs/track-{case['case_id']}/trace"
    assert api.get(url).status_code == 403
    assert api.get("/api/runs/track-sweep/trace").status_code == 403

    api.login("gestor")
    response = api.get(url)
    assert response.status_code == 200
    events = response.json()
    kinds = [e["kind"] for e in events]
    assert kinds[0] == "track.report.received" and "track.atestado.read" in kinds and "track.offer.sent" in kinds
    assert {e["run_id"] for e in events} == {f"track-{case['case_id']}"}
    assert all("cost_usd" in e and "tokens_in" in e and "latency_ms" in e for e in events)
    assert CID not in response.text and "text" not in events[0]["payload"]
    assert api.get("/api/runs/track-sweep/trace").status_code == 200
    assert api.get("/api/runs/track-nao-existe/trace").status_code == 404
