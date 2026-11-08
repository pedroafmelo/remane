"""Fluxo ponta a ponta da C6 (plano da C6, seções 14 e 19): XLSX em grade com cabeçalhos livres → resumo com o
mapeamento, a capacidade e as lojas → confirmação com `ConfirmInput` → 0 violações → aprovação → publicação →
"planejar a próxima semana" sem upload (continuidade, semana +7) → confirmação → 0 violações → aprovação → publicação.

`TestClient` + `FakeLLMClient` (mapeamento por ferramenta, o da heurística para o mesmo arquivo; justificativa
fixa) + SQLite em memória + o agente real ligado por `build_agent`, com `llm_factory`. Dados sintéticos de
`data/demo/`. Sempre `Settings(_env_file=None)`: nunca lê o `.env` real e nunca chama o modelo real.

O solver 60 x 7 leva de 10 a 20 s por solve com 1 thread: o fluxo completo roda uma vez, em fixture de módulo, e é
`slow`. Os casos de reserva e de 409 não rodam o solver.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from escalista.api.app import create_app
from escalista.api.wiring import build_agent
from escalista.config import Settings
from escalista.ingest.tables import read_tables
from escalista.rules.header_aliases import guess_mapping
from escalista.rules.identity import person_id
from tests.agents.support import GOOD_JUSTIFICATION
from tests.e2e.test_fatia import ENV_NAMES, keys_of, memory_engine
from tests.fakes import TOOL_JUSTIFY, TOOL_MAPPING, TOOL_SPEC, FakeLLMClient

DEMO = Path("data/demo")
EXAMPLE = DEMO / "escala_exemplo_grade.xlsx"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FILE_WEEK = date(2027, 1, 11)
SEX_VALUES = {e["sex"] for e in __import__("json").loads((DEMO / "pessoas.json").read_text())}

pytestmark = pytest.mark.usefixtures("clean_env")


@pytest.fixture(scope="module")
def clean_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as mp:
        for name in ENV_NAMES:
            mp.delenv(name, raising=False)
        yield


def model_mapping() -> dict:
    """Um mapeamento válido para o falso devolver: o da heurística para o mesmo arquivo."""
    mapping = guess_mapping(read_tables(EXAMPLE.name, EXAMPLE.read_bytes()).tables)
    assert mapping is not None
    return mapping.model_dump(mode="json")


@dataclass
class Stack:
    client: TestClient
    llm: FakeLLMClient
    bodies: list[Any] = field(default_factory=list)

    def call(self, method: str, url: str, **kwargs):
        response = self.client.request(method, url, **kwargs)
        if response.headers.get("content-type", "").startswith("application/json"):
            self.bodies.append(response.json())
        return response

    def upload_example(self):
        return self.call(
            "POST",
            "/api/runs",
            params={"file_name": EXAMPLE.name},
            content=EXAMPLE.read_bytes(),
            headers={"Content-Type": XLSX},
        )

    def trace(self, run_id: str) -> list[dict]:
        response = self.call("GET", f"/api/runs/{run_id}/trace")
        assert response.status_code == 200, response.text
        return response.json()


def make_stack(*, fail_mapping: bool = False, specs: list[dict] | None = None, fail_spec: bool = False) -> Stack:
    by_tool: dict[str, list] = {TOOL_MAPPING: [model_mapping()] * 4, TOOL_JUSTIFY: [GOOD_JUSTIFICATION] * 4}
    if specs is not None:
        by_tool[TOOL_SPEC] = specs * 3  # a mesma resposta nas tentativas de reenvio
    fail_tools = ({TOOL_MAPPING} if fail_mapping else set()) | ({TOOL_SPEC} if fail_spec else set())
    llm = FakeLLMClient(by_tool=by_tool, fail_tools=fail_tools)
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        web_dist_dir="/nao/existe",
        demo_mode=True,
        session_secret="segredo-e2e",
    )
    agent = build_agent(settings, engine=memory_engine(), llm_factory=lambda sink, clock: llm)  # type: ignore[arg-type,return-value]
    stack = Stack(TestClient(create_app(settings, agent=agent)), llm)
    assert stack.call("POST", "/auth/demo/gestor").status_code == 200
    return stack


# --- 1. leitura e reserva do modelo (sem solver) ----------------------------------------------------------------------


def test_reading_with_the_model_shows_mapping_capacity_and_stores(clean_env) -> None:
    stack = make_stack()

    started = stack.upload_example()

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["phase"] == "awaiting_confirm" and body["mode"] == "upload" and body["notices"] == []
    summary = body["summary"]
    assert summary["ok"] is True and summary["format"] == "xlsx" and summary["mapping_source"] == "modelo"
    assert summary["mapping"] is not None
    assert summary["rows"] == 360 and summary["employees"] == 60 and summary["stores"] == 3
    assert summary["week_start"] == str(FILE_WEEK) and len(summary["store_ids"]) == 3
    capacity = summary["capacity"]
    assert capacity["fits"] is False and capacity["max_fitting_pct"] == 80
    applied = next(e for e in stack.trace(body["run_id"]) if e["kind"] == "ingest.apply_mapping")
    assert applied["payload"]["source"] == "modelo" and applied["payload"]["invented"] == 0  # 0 turnos inventados
    assert [c["tool_name"] for c in stack.llm.calls] == [TOOL_MAPPING]


def test_model_failure_reads_by_heuristic_with_rx12_and_the_flow_goes_on(clean_env) -> None:
    stack = make_stack(fail_mapping=True)

    started = stack.upload_example()

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["phase"] == "awaiting_confirm" and body["exception"] is None
    assert body["summary"]["mapping_source"] == "heuristica" and body["summary"]["ok"] is True
    assert body["summary"]["rows"] == 360
    assert [n["code"] for n in body["notices"]] == ["RX-12"]
    kinds = [e["kind"] for e in stack.trace(body["run_id"])]
    assert "ingest.fallback" in kinds and "exception.raised" in kinds and "solver.run" not in kinds
    assert "sex" not in keys_of(stack.bodies)


def test_without_any_key_the_real_client_falls_back_to_the_heuristic(clean_env) -> None:
    """Produção sem chave: `build_agent` sem `llm_factory` usa o cliente real, que levanta RX-12 sem rede, e o agente
    cai na heurística com o aviso (nenhuma chamada ao modelo)."""
    settings = Settings(
        _env_file=None, database_url="sqlite://", web_dist_dir="/nao/existe", demo_mode=True, session_secret="s-e2e"
    )
    client = TestClient(create_app(settings, agent=build_agent(settings, engine=memory_engine())))
    assert client.post("/auth/demo/gestor").status_code == 200

    started = client.post(
        "/api/runs", params={"file_name": EXAMPLE.name}, content=EXAMPLE.read_bytes(), headers={"Content-Type": XLSX}
    )

    assert started.status_code == 201, started.text
    body = started.json()
    assert body["phase"] == "awaiting_confirm" and body["summary"]["mapping_source"] == "heuristica"
    assert [n["code"] for n in body["notices"]] == ["RX-12"]


def test_next_week_without_a_published_schedule_is_409_and_roster_is_404(clean_env) -> None:
    stack = make_stack()
    assert stack.call("POST", "/api/runs/next-week").status_code == 409
    assert stack.call("GET", "/api/roster").status_code == 404


# --- 2. o fluxo completo: 1ª escala e a semana seguinte (solver 60 x 7) ----------------------------------------------


@dataclass
class Flow:
    stack: Stack
    first: dict
    confirmed: dict
    published: dict
    next_started: dict
    next_confirmed: dict
    next_published: dict


@pytest.fixture(scope="module")
def flow(clean_env) -> Flow:
    from escalista.domain.reading import ConfirmInput

    stack = make_stack()
    first = stack.upload_example()
    assert first.status_code == 201, first.text
    first_body = first.json()
    run_id = first_body["run_id"]
    fit = first_body["summary"]["capacity"]["max_fitting_pct"]
    confirm = ConfirmInput(coverage_pct={sid: fit for sid in first_body["summary"]["store_ids"]})  # ajustar para caber
    confirmed = stack.call("POST", f"/api/runs/{run_id}/confirm", json=confirm.model_dump(mode="json"))
    assert confirmed.status_code == 200, confirmed.text
    approved = stack.call("POST", f"/api/runs/{run_id}/approve")
    assert approved.status_code == 200, approved.text

    nxt = stack.call("POST", "/api/runs/next-week")
    assert nxt.status_code == 201 or nxt.status_code == 200, nxt.text
    nxt_id = nxt.json()["run_id"]
    nxt_confirmed = stack.call("POST", f"/api/runs/{nxt_id}/confirm")
    assert nxt_confirmed.status_code == 200, nxt_confirmed.text
    nxt_approved = stack.call("POST", f"/api/runs/{nxt_id}/approve")
    assert nxt_approved.status_code == 200, nxt_approved.text
    return Flow(
        stack, first_body, confirmed.json(), approved.json(), nxt.json(), nxt_confirmed.json(), nxt_approved.json()
    )


@pytest.mark.slow
def test_first_schedule_goes_from_xlsx_to_published_with_zero_violations(flow: Flow) -> None:
    assert flow.confirmed["phase"] == "awaiting_approval" and flow.confirmed["exception"] is None
    assert flow.confirmed["report"]["total"] == 0
    comparison = flow.confirmed["comparison"]
    assert comparison["after"]["violations"] == 0
    assert comparison["after"]["coverage_pct"] > 0 and comparison["before"]["total_cost"]
    assert flow.confirmed["justification"]["summary"] == GOOD_JUSTIFICATION["summary"]
    assert flow.published["phase"] == "published"
    assert flow.published["version_id"] == flow.confirmed["version_id"]


@pytest.mark.slow
def test_next_week_plans_without_upload_in_continuity_mode_one_week_later(flow: Flow) -> None:
    started = flow.next_started
    assert started["phase"] == "awaiting_confirm" and started["mode"] == "continuidade"
    assert date.fromisoformat(started["week_start"]) == FILE_WEEK + timedelta(days=7)
    assert started["run_id"] != flow.first["run_id"]
    assert flow.next_confirmed["phase"] == "awaiting_approval" and flow.next_confirmed["report"]["total"] == 0
    assert flow.next_confirmed["comparison"]["after"]["violations"] == 0
    assert flow.next_published["phase"] == "published"
    published = flow.stack.call("GET", "/api/schedules/published").json()
    assert published["version"]["id"] == flow.next_confirmed["version_id"]
    assert published["version"]["id"] != flow.confirmed["version_id"]


@pytest.mark.slow
def test_roster_and_every_response_are_free_of_sex(flow: Flow) -> None:
    assert SEX_VALUES
    roster = flow.stack.call("GET", "/api/roster")
    assert roster.status_code == 200, roster.text
    body = roster.json()
    assert len(body["employees"]) == 60 and all("name" in e for e in body["employees"])
    flow.stack.call("GET", f"/api/runs/{flow.first['run_id']}/schedule")
    flow.stack.trace(flow.first["run_id"])
    assert len(flow.stack.bodies) >= 10
    assert "sex" not in keys_of(flow.stack.bodies)
    assert not any(k in keys_of(flow.stack.bodies) for k in ("sexo", "gender"))


# --- 3. o pedido do gestor vira especificação (nó 2) e o solver a respeita (seção 19 do plano) -----------------------

PERSON = next(e for e in __import__("json").loads((DEMO / "pessoas.json").read_text()) if e["id"] == "P037")
PERSON_ID = person_id(PERSON["name"], None)  # a grade não traz matrícula: o id é o do nome normalizado
WEDNESDAY = FILE_WEEK + timedelta(days=2)
REQUEST = f"{PERSON['name']} não pode na quarta"


def confirm_with_request(stack: Stack, note: str) -> dict:
    from escalista.domain.reading import ConfirmInput

    started = stack.upload_example().json()
    fit = started["summary"]["capacity"]["max_fitting_pct"]
    confirm = ConfirmInput(coverage_pct={sid: fit for sid in started["summary"]["store_ids"]}, note=note)
    response = stack.call("POST", f"/api/runs/{started['run_id']}/confirm", json=confirm.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    return response.json()


def unavailable_spec(evidence: str) -> dict:
    return {
        "constraints": [
            {"type": "indisponivel", "employee_id": PERSON_ID, "day": WEDNESDAY.isoformat(), "evidence": evidence}
        ]
    }


@pytest.mark.slow
def test_request_becomes_a_hard_unavailability_the_solver_respects(clean_env) -> None:
    stack = make_stack(specs=[unavailable_spec(REQUEST)])

    body = confirm_with_request(stack, REQUEST)

    run_id = body["run_id"]
    assert body["phase"] == "awaiting_approval" and body["exception"] is None
    assert body["report"]["total"] == 0 and body["comparison"]["after"]["violations"] == 0
    proposed = stack.call("GET", f"/api/runs/{run_id}/schedule").json()
    assert PERSON_ID in {e["id"] for e in proposed["employees"]}
    shifts = [s for s in proposed["schedule"]["shifts"] if s["employee_id"] == PERSON_ID]
    assert shifts, "a pessoa do pedido precisa ter turnos na semana, para o teste valer"
    assert not [s for s in shifts if s["start"].startswith(WEDNESDAY.isoformat())]
    assert [c["type"] for c in body["spec"]["constraints"]] == ["indisponivel"]
    assert body["spec"]["constraints"][0]["employee_id"] == PERSON_ID
    assert "RX-12" not in [n["code"] for n in body["notices"]]  # o modelo respondeu; o RX-02 é da capacidade
    kinds = [e["kind"] for e in stack.trace(run_id)]
    # o `llm.formulate` é emitido pelo cliente real (o falso não grava rastro): aqui vale a chamada da ferramenta
    assert "spec.validate" in kinds and "solver.run" in kinds
    validated = next(e for e in stack.trace(run_id) if e["kind"] == "spec.validate")
    assert validated["payload"]["used_model"] is True and validated["payload"]["accepted"] == {"indisponivel": 1}
    assert TOOL_SPEC in [c["tool_name"] for c in stack.llm.calls]
    assert "sex" not in keys_of(stack.bodies)


@pytest.mark.slow
def test_request_to_loosen_a_limit_is_refused_and_listed_in_the_assumptions(clean_env) -> None:
    note = f"{PERSON['name']} pode trabalhar 50 horas por semana"
    loosen = {"constraints": [{"type": "max_horas_semana", "employee_id": PERSON_ID, "hours": 50, "evidence": note}]}
    stack = make_stack(specs=[loosen])

    body = confirm_with_request(stack, note)

    assert body["phase"] == "awaiting_approval" and body["report"]["total"] == 0
    assert body["spec"]["constraints"] == []
    assumptions = body["summary"]["assumptions"]
    assert any(a.startswith("Pedido não aplicado") for a in assumptions), assumptions
    validated = next(e for e in stack.trace(body["run_id"]) if e["kind"] == "spec.validate")
    assert validated["payload"]["accepted"] == {} and len(validated["payload"]["rejected"]) == 1


@pytest.mark.slow
def test_formulation_failure_falls_back_to_the_default_spec_with_rx12(clean_env) -> None:
    stack = make_stack(fail_spec=True)

    body = confirm_with_request(stack, REQUEST)

    assert body["phase"] == "awaiting_approval" and body["exception"] is None
    assert body["report"]["total"] == 0 and body["spec"]["constraints"] == []
    assert "RX-12" in [n["code"] for n in body["notices"]]
    kinds = [e["kind"] for e in stack.trace(body["run_id"])]
    assert "spec.validate" in kinds and "solver.run" in kinds
