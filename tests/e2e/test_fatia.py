"""Fumaça ponta a ponta da fatia (plano da C5, seção 6, item 4).

`TestClient` + falso de LLM (emite `llm.justify` com custo falso, como o cliente real) + SQLite em memória + o **agente
real** ligado pela mesma fábrica da produção (`build_agent`, com `engine` e `llm_factory` injetados). Dados sintéticos
de `data/demo/`.

C6 (C3 do plano): `build_agent` liga o caminho da C6. O falso de LLM só sabe justificar; o pedido de mapeamento volta
com saída inválida e o agente lê o `escala_atual.csv` (formato da DEC-039) pela heurística de aliases, com o aviso
RX-12. O fluxo com modelo de mapeamento está em `test_c6.py`. Sempre `Settings(_env_file=None)`: nunca lê o `.env` real.

O solver leva ~12 s por fluxo com 1 thread: o fluxo feliz e o fluxo com LLM falhando rodam uma vez cada, em fixtures de
módulo, e os casos só leem o resultado.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import StaticPool

from escalista.agents.optimizer.tools import PUBLISHER_ROLES, publicar
from escalista.api.accounts import SEEDED_ACCOUNTS
from escalista.api.app import create_app
from escalista.api.routes_runs import gestor
from escalista.api.wiring import build_agent
from escalista.config import Settings
from escalista.domain.contracts import Role
from escalista.store.sql_repository import SqlRepository
from tests.agents.support import FAKE_COST, GOOD_JUSTIFICATION, JustifyLLM

DEMO = Path("data/demo")
SEX_VALUES = {e["sex"] for e in __import__("json").loads((DEMO / "pessoas.json").read_text())}
STEP_KINDS = (
    "ingest.parse",
    "ingest.apply_mapping",
    "read.summary",
    "read.confirmed",
    "solver.run",
    "verifier.check",
    "cost.compare",
    "llm.justify",
    "approval.recorded",
    "schedule.publish",
)
ENV_NAMES = ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR") + tuple(
    f"FEATHERLESS_API_KEY_{i}" for i in range(1, 5)
)


def memory_engine() -> Engine:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record) -> None:  # pragma: no cover - chamado pelo driver
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


@dataclass
class Stack:
    """O app completo (agente real, SQL em memória) e o registro de todo JSON respondido."""

    client: TestClient
    engine: Engine
    app: Any
    bodies: list[Any] = field(default_factory=list)

    def call(self, method: str, url: str, **kwargs):
        response = self.client.request(method, url, **kwargs)
        if response.headers.get("content-type", "").startswith("application/json"):
            self.bodies.append(response.json())
        return response

    def upload(self, name: str):
        csv = self.call("GET", f"/api/demo/files/{name}")
        assert csv.status_code == 200, csv.text
        return self.call(
            "POST",
            "/api/runs",
            params={"file_name": name},
            content=csv.content,
            headers={"Content-Type": "text/csv"},
        )

    def trace(self, run_id: str) -> list[dict]:
        response = self.call("GET", f"/api/runs/{run_id}/trace")
        assert response.status_code == 200, response.text
        return response.json()


def make_stack(*, llm_fail: bool = False) -> Stack:
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        web_dist_dir="/nao/existe",
        demo_mode=True,
        session_secret="segredo-e2e",
    )
    engine = memory_engine()
    agent = build_agent(
        settings,
        engine=engine,
        llm_factory=lambda sink, clock: JustifyLLM(sink, clock, fail=llm_fail),  # type: ignore[arg-type]
    )
    app = create_app(settings, agent=agent)
    stack = Stack(TestClient(app), engine, app)
    assert stack.call("POST", "/auth/demo/gestor").status_code == 200
    return stack


@dataclass
class Flow:
    stack: Stack
    run_id: str
    started: dict
    confirmed: dict
    approved: dict | None = None


def run_until_approval(stack: Stack) -> Flow:
    started = stack.upload("escala_atual.csv")
    assert started.status_code == 201, started.text
    assert started.json()["phase"] == "awaiting_confirm"
    run_id = started.json()["run_id"]
    confirmed = stack.call("POST", f"/api/runs/{run_id}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    return Flow(stack, run_id, started.json(), confirmed.json())


@pytest.fixture(scope="module", autouse=True)
def clean_env() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as mp:
        for name in ENV_NAMES:
            mp.delenv(name, raising=False)
        yield


@pytest.fixture(scope="module")
def happy(clean_env) -> Flow:
    """Fluxo feliz completo: login, escala atual, confirmação, aprovação e publicação."""
    stack = make_stack()
    flow = run_until_approval(stack)
    approved = stack.call("POST", f"/api/runs/{flow.run_id}/approve")
    assert approved.status_code == 200, approved.text
    flow.approved = approved.json()
    return flow


@pytest.fixture(scope="module")
def rx12(clean_env) -> Flow:
    """Fluxo com o LLM falhando: para na aprovação, sem justificativa."""
    return run_until_approval(make_stack(llm_fail=True))


def keys_of(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_of(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_of(v)}
    return set()


# --- 1. fluxo feliz -------------------------------------------------------------------------------------------------


def test_happy_path_from_demo_login_to_published_version(happy: Flow) -> None:
    stack = happy.stack
    assert happy.started["summary"]["ok"] is True and happy.started["summary"]["file_name"] == "escala_atual.csv"

    confirmed = happy.confirmed
    assert confirmed["phase"] == "awaiting_approval"
    assert confirmed["report"]["total"] == 0  # o verificador independente: 0 violações na otimizada
    assert confirmed["comparison"]["before"]["violations"] > 0  # as violações que a EC 141 cria na escala atual
    assert confirmed["comparison"]["after"]["violations"] == 0
    justification = confirmed["justification"]
    assert justification["summary"] == GOOD_JUSTIFICATION["summary"]
    assert all(item["rule_refs"] for item in justification["items"])
    assert confirmed["exception"] is None and confirmed["version_id"]

    grid = stack.call("GET", f"/api/runs/{happy.run_id}/schedule")
    assert grid.status_code == 200 and grid.json()["schedule"]["shifts"]

    assert happy.approved["phase"] == "published"
    published = stack.call("GET", "/api/schedules/published")
    assert published.status_code == 200
    body = published.json()
    assert body["version"]["id"] == confirmed["version_id"] and body["version"]["status"] == "published"
    assert body["version"]["violations_total"] == 0
    assert body["employees"] and all("name" in e for e in body["employees"])


# --- 2. recusa de `publicar` ----------------------------------------------------------------------------------------


def test_publish_refused_for_wrong_role_returns_403_and_traces_the_refusal(rx12: Flow) -> None:
    """A rota sempre grava a aprovação da sessão antes de publicar, então a recusa pela rota vem de um caminho real
    diferente: a aprovação de um papel sem permissão (colaborador). Forçamos o papel só no teste, trocando a
    dependência de acesso; `publicar` relê a aprovação gravada no SQL e recusa."""
    stack = rx12.stack
    colaborador = next(a for a in SEEDED_ACCOUNTS if a.role is Role.COLABORADOR)
    stack.app.dependency_overrides[gestor] = lambda: colaborador
    try:
        response = stack.call("POST", f"/api/runs/{rx12.run_id}/approve")
    finally:
        del stack.app.dependency_overrides[gestor]

    assert response.status_code == 403, response.text
    assert "colaborador" in response.json()["detail"]
    kinds = [e["kind"] for e in stack.trace(rx12.run_id)]
    assert "schedule.publish_refused" in kinds and "schedule.publish" not in kinds
    assert stack.call("GET", f"/api/runs/{rx12.run_id}").json()["phase"] == "awaiting_approval"
    assert stack.call("GET", "/api/schedules/published").json()["version"] is None


def test_publish_tool_without_any_approval_is_refused_in_the_real_repository(rx12: Flow) -> None:
    """Sem aprovação gravada para a versão, a ferramenta `publicar` recusa, e a recusa fica no rastro do SQL."""
    stack = rx12.stack
    agent = stack.app.state.agent._agent  # o OptimizerAgent por trás do adaptador
    repo = SqlRepository(stack.engine)
    version_id = rx12.confirmed["version_id"]
    repo_approval = repo.get_approval(version_id)
    if repo_approval is not None:  # a recusa de papel errado do teste anterior gravou a aprovação do colaborador
        with stack.engine.begin() as conn:
            conn.exec_driver_sql("DELETE FROM approval")
    assert repo.get_approval(version_id) is None

    with pytest.raises(Exception) as refused:  # noqa: PT011 (PublishRefusedError do agente)
        publicar(
            repo=repo,
            tracer=agent._tracer,
            run_id=rx12.run_id,
            version_id=version_id,
            allowed_roles=PUBLISHER_ROLES,
        )
    assert type(refused.value).__name__ == "PublishRefusedError"
    assert "aprovação humana não encontrada" in str(refused.value)
    refusals = [e for e in stack.trace(rx12.run_id) if e["kind"] == "schedule.publish_refused"]
    assert refusals and refusals[-1]["payload"]["approval_id"] is None
    assert repo.get_version(version_id).status != "published"


# --- 3. um evento por passo, com custo ------------------------------------------------------------------------------


def test_every_step_has_a_trace_event_with_cost(happy: Flow) -> None:
    events = happy.stack.trace(happy.run_id)
    by_kind = {e["kind"]: e for e in events}
    for kind in STEP_KINDS:
        assert kind in by_kind, f"sem evento {kind}"
        assert by_kind[kind]["cost_usd"] is not None, f"{kind} sem cost_usd"
        assert by_kind[kind]["latency_ms"] is not None or kind == "llm.justify"
    for kind in set(STEP_KINDS) - {"llm.justify"}:
        assert Decimal(str(by_kind[kind]["cost_usd"])) == 0  # sem modelo: custo 0 com a base declarada
        assert by_kind[kind]["payload"]["cost_basis"]
    assert Decimal(str(by_kind["llm.justify"]["cost_usd"])) == FAKE_COST
    assert by_kind["solver.run"]["latency_ms"] > 0
    order = [e["kind"] for e in events]
    # a ordem dos 8 passos (o verificador roda duas vezes: na otimizada e na enviada)
    assert list(dict.fromkeys(k for k in order if k in STEP_KINDS)) == list(STEP_KINDS)
    assert all(e["run_id"] == happy.run_id for e in events)


# --- 4. CSV com defeito ---------------------------------------------------------------------------------------------


def test_defect_csv_lists_the_issues_with_their_lines(clean_env) -> None:
    """C6: o defeito do `escala_defeito.csv` já não vira RX-13 (que ficou para o arquivo ilegível, teste 7). O leitor
    de tabelas lê o que dá e devolve os problemas com a linha no resumo; quem decide é o gestor."""
    stack = make_stack()
    response = stack.upload("escala_defeito.csv")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["phase"] == "awaiting_confirm" and body["exception"] is None
    issues = body["summary"]["issues"]
    assert issues and all(i["line"] > 0 for i in issues)
    assert {i["line"] for i in issues} >= {48, 59, 69}  # hora ilegível, turno sobreposto, fim vazio
    run_id = body["run_id"]
    kinds = [e["kind"] for e in stack.trace(run_id)]
    assert kinds[0] == "ingest.parse" and kinds[-1] == "read.summary" and "solver.run" not in kinds


# --- 5. LLM falhando ------------------------------------------------------------------------------------------------


def test_llm_failure_shows_rx12_and_no_justification_text(rx12: Flow) -> None:
    confirmed = rx12.confirmed
    assert confirmed["phase"] == "awaiting_approval"  # a escala é válida e o gestor ainda decide
    assert confirmed["exception"] is None  # C6: RX-12 da justificativa é aviso, não bloqueia
    codes = [n["code"] for n in confirmed["notices"]]
    # RX-12 do mapeamento (heurística), RX-12 da justificativa e RX-02 (a demanda do cadastro excede a capacidade)
    assert codes.count("RX-12") == 2 and set(codes) <= {"RX-12", "RX-02"}
    assert confirmed["justification"] is None
    assert confirmed["report"]["total"] == 0
    dump = str(rx12.stack.bodies)
    assert GOOD_JUSTIFICATION["summary"] not in dump
    kinds = [e["kind"] for e in rx12.stack.trace(rx12.run_id)]
    assert "llm.justify" not in kinds and "exception.raised" in kinds


# --- 6. RN-13 -------------------------------------------------------------------------------------------------------


def test_no_response_carries_sex(happy: Flow, rx12: Flow) -> None:
    assert SEX_VALUES  # o dado de origem tem `sex`: sem ele a varredura não provaria nada
    for flow in (happy, rx12):
        flow.stack.call("GET", f"/api/runs/{flow.run_id}/schedule")
        flow.stack.call("GET", "/api/schedules/published")
        flow.stack.trace(flow.run_id)
        assert len(flow.stack.bodies) >= 5
        assert "sex" not in keys_of(flow.stack.bodies)
        assert not any(k in keys_of(flow.stack.bodies) for k in ("sexo", "gender"))


# --- 7. Upload da C6: a codificação é do leitor do agente ------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content"),
    [
        # bytes que não decodificam nem em UTF-8 nem em cp1252 (0x81, 0x8D, 0x8F não existem no cp1252)
        ("escala.csv", b"funcion\x81rio,loja,dia,inicio,fim\nE01,L\x8d01,2027-01-11,08:00,16:\x8f00\n"),
        ("escala.xlsx", b"PK\x03\x04" + b"\x00" * 64),  # ZIP truncado: o leitor recusa, a API não abre
    ],
)
def test_unreadable_file_is_rx13_from_the_agent(clean_env, name: str, content: bytes) -> None:
    """A API não confere mais UTF-8 (C6, C1): o agente real recebe o arquivo e devolve `failed` com RX-13, sem 500."""
    stack = make_stack()
    response = stack.call("POST", "/api/runs", params={"file_name": name}, content=content)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["phase"] == "failed" and body["exception"]["code"] == "RX-13"
    assert body["summary"] is None  # C6: o arquivo ilegível não chega a ter resumo, só o cartão
    assert "solver.run" not in [e["kind"] for e in stack.trace(body["run_id"])]


def test_next_week_and_roster_without_a_first_schedule(clean_env) -> None:
    """Banco vazio: 409 para planejar a próxima semana e 404 para o quadro, com o agente de hoje e com o da B4a."""
    stack = make_stack()
    assert stack.call("POST", "/api/runs/next-week").status_code == 409
    assert stack.call("GET", "/api/roster").status_code == 404
