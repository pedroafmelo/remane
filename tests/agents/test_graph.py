"""Agente de otimização da fatia (I1): fluxo, exceções RX-02, RX-12 e RX-13, aprovação e rastro."""

from __future__ import annotations

import json
import time
from decimal import Decimal

import pytest

from escalista.agents.optimizer.errors import PublishRefusedError, RunNotFoundError, RunPhaseError
from escalista.agents.optimizer.tools import NO_MODEL
from escalista.api.wiring import SliceAgent
from escalista.audit.sink import SqlTraceSink
from escalista.db import init_db, make_engine
from escalista.domain.contracts import Role
from escalista.domain.schedule import EmployeePublic
from escalista.ingest.demo_network import load_demo_network
from escalista.store.sql_repository import SqlRepository
from tests.agents.support import DEMO_DIR, FAKE_COST, TINY_EMPLOYEES, Harness, tiny_csv, tiny_demand

REFUSED_TEXT = "texto recusado do modelo"
BAD_REF_ARGS = {"summary": REFUSED_TEXT, "items": [{"text": REFUSED_TEXT, "rule_refs": ["inventada"]}]}
STEP_KINDS = {
    "csv.validate",
    "read.summary",
    "read.confirmed",
    "solver.run",
    "verifier.check",
    "cost.compare",
    "llm.justify",
    "approval.recorded",
    "schedule.publish",
}


def _confirmed(h: Harness):
    state = h.agent.start_run("escala.csv", tiny_csv())
    assert state.phase == "awaiting_confirm", state.exception
    return h.agent.confirm(state.run_id)


# --- leitura ----------------------------------------------------------------------------------------------------------


def test_start_run_reads_validates_and_waits_for_confirmation() -> None:
    h = Harness()

    state = h.agent.start_run("escala.csv", tiny_csv())

    assert state.phase == "awaiting_confirm"
    assert state.summary.ok and state.summary.rows == 11 and state.summary.employees == 2
    assert state.exception is None and state.version_id is None
    assert h.repo.get_run(state.run_id) == state
    assert h.kinds(state.run_id) == ["csv.validate", "read.summary"]
    assert h.agent.get_schedule(state.run_id) is None


def test_defect_csv_fails_with_rx13_and_the_lines() -> None:
    stores, employees, demand = load_demo_network(DEMO_DIR)
    h = Harness(stores=stores, employees=employees, demand=demand)

    state = h.agent.start_run("escala_defeito.csv", (DEMO_DIR / "escala_defeito.csv").read_bytes())

    assert state.phase == "failed"
    assert state.exception.code == "RX-13"
    assert not state.summary.ok and all(issue.line > 0 for issue in state.summary.issues)
    assert h.repo.get_run(state.run_id).phase == "failed"
    assert h.kinds(state.run_id) == ["csv.validate", "read.summary", "exception.raised"]
    assert h.events(state.run_id)[-1].payload["code"] == "RX-13"
    with pytest.raises(RunPhaseError):
        h.agent.confirm(state.run_id)


def test_unreadable_csv_fails_with_rx13() -> None:
    h = Harness()

    state = h.agent.start_run("vazio.csv", b"# so comentario\n")

    assert state.phase == "failed" and state.exception.code == "RX-13"


# --- fases ------------------------------------------------------------------------------------------------------------


def test_wrong_phase_raises_run_phase_error() -> None:
    h = Harness()
    read = h.agent.start_run("escala.csv", tiny_csv())

    with pytest.raises(RunPhaseError):
        h.agent.approve(read.run_id, h.approval("qualquer"))
    done = h.agent.confirm(read.run_id)
    with pytest.raises(RunPhaseError):
        h.agent.confirm(read.run_id)
    h.agent.approve(done.run_id, h.approval(done.version_id))
    with pytest.raises(RunPhaseError):
        h.agent.approve(done.run_id, h.approval(done.version_id))


def test_unknown_run() -> None:
    h = Harness()

    with pytest.raises(RunNotFoundError):
        h.agent.confirm("nao-existe")
    with pytest.raises(RunNotFoundError):
        h.agent.approve("nao-existe", h.approval("v"))
    assert h.agent.get_run("nao-existe") is None
    assert h.agent.get_schedule("nao-existe") is None
    assert h.agent.employees("nao-existe") == []
    assert h.agent.trace("nao-existe") == []


# --- otimização -------------------------------------------------------------------------------------------------------


def test_confirm_optimizes_verifies_compares_justifies_and_saves_draft() -> None:
    h = Harness()

    state = _confirmed(h)

    assert state.phase == "awaiting_approval"
    assert state.report.total == 0
    assert state.comparison.before.violations > 0 and state.comparison.after.violations == 0
    assert state.justification is not None and state.justification.items
    version = h.repo.get_version(state.version_id)
    assert version.status == "draft" and version.run_id == state.run_id
    assert version.seed == 42 and version.violations_total == 0 and len(version.input_hash) == 64
    assert h.agent.get_schedule(state.run_id) == version.schedule
    assert h.repo.get_run(state.run_id) == state
    assert len(h.llm.calls) == 1


def test_uncovered_demand_yields_rx02_and_the_flow_goes_on() -> None:
    h = Harness(demand=tiny_demand(required=5))  # 5 por faixa, só 3 pessoas

    state = _confirmed(h)

    assert state.phase == "awaiting_approval"
    assert state.exception.code == "RX-02"
    assert state.report.total == 0 and state.version_id is not None
    assert state.comparison.after.uncovered_slots > 0
    raised = [e for e in h.events(state.run_id) if e.kind == "exception.raised"]
    assert [e.payload["code"] for e in raised] == ["RX-02"]
    assert state.exception.trace_id == raised[0].id


@pytest.mark.parametrize(
    "kwargs",
    [{"llm_fail": True}, {"llm_args": BAD_REF_ARGS}],
    ids=["modelo-fora", "rule-ref-inventada"],
)
def test_llm_failure_yields_rx12_not_text(kwargs) -> None:
    h = Harness(**kwargs)

    state = _confirmed(h)

    assert state.phase == "awaiting_approval"  # a escala é válida; o gerente pode aprovar
    assert state.justification is None
    assert state.exception.code == "RX-12"
    assert state.report.total == 0 and state.version_id is not None
    events = h.events(state.run_id)
    [raised] = [e for e in events if e.kind == "exception.raised"]
    assert raised.payload["code"] == "RX-12" and raised.cost_usd == Decimal(0)
    assert REFUSED_TEXT not in json.dumps(state.model_dump(mode="json"))  # nada do texto recusado é aproveitado
    published = h.agent.approve(state.run_id, h.approval(state.version_id))
    assert published.phase == "published"


# --- aprovação e publicação -------------------------------------------------------------------------------------------


def test_approve_records_approval_and_publishes() -> None:
    h = Harness()
    state = _confirmed(h)

    done = h.agent.approve(state.run_id, h.approval(state.version_id))

    assert done.phase == "published"
    assert h.repo.get_approval(state.version_id).approved_by == "demo-gerente"
    assert h.agent.published().id == state.version_id
    assert h.agent.published().status == "published"
    assert h.kinds(state.run_id)[-2:] == ["approval.recorded", "schedule.publish"]


def test_publish_without_approval_is_refused() -> None:
    """A aprovação de outra versão não é gravada para esta: `publicar` não acha aprovação e recusa."""
    h = Harness()
    state = _confirmed(h)

    with pytest.raises(PublishRefusedError):
        h.agent.approve(state.run_id, h.approval("outra-versao"))

    assert h.repo.get_approval(state.version_id) is None
    assert h.agent.get_run(state.run_id).phase == "awaiting_approval"
    assert h.agent.published() is None
    assert h.kinds(state.run_id)[-1] == "schedule.publish_refused"
    assert "schedule.publish" not in h.kinds(state.run_id)


def test_publish_refused_for_role_without_permission_then_manager_publishes() -> None:
    h = Harness()
    state = _confirmed(h)

    with pytest.raises(PublishRefusedError) as err:
        h.agent.approve(state.run_id, h.approval(state.version_id, role=Role.DP))

    assert "papel" in err.value.reason
    assert h.kinds(state.run_id)[-2:] == ["approval.recorded", "schedule.publish_refused"]
    assert h.agent.get_run(state.run_id).phase == "awaiting_approval"
    assert h.agent.approve(state.run_id, h.approval(state.version_id)).phase == "published"


# --- rastro -----------------------------------------------------------------------------------------------------------


def test_every_step_emits_trace_event_with_cost() -> None:
    h = Harness()
    state = _confirmed(h)
    h.agent.approve(state.run_id, h.approval(state.version_id))

    events = h.agent.trace(state.run_id)

    assert events == h.events(state.run_id)
    assert STEP_KINDS <= {e.kind for e in events}
    assert all(e.cost_usd is not None for e in events)
    assert all(e.latency_ms is not None and e.at == h.clock.now() for e in events)
    for e in events:
        if e.kind == "llm.justify":
            assert e.cost_usd == FAKE_COST
        else:
            assert e.cost_usd == Decimal(0) and e.payload["cost_basis"] == NO_MODEL
    ids = [e.id for e in events]
    assert len(set(ids)) == len(ids)
    assert events[0].parent_id is None
    assert all(e.parent_id in ids[:i] for i, e in enumerate(events) if i > 0)
    checks = [e for e in events if e.kind == "verifier.check"]
    assert {c.payload["target"] for c in checks} == {"enviada", "otimizada"}
    rules = checks[0].payload["rules"]
    assert {"id": "jornada_semanal_max", "status": "interpretacao"} in rules
    assert all(set(r) == {"id", "status"} for r in rules)


def test_no_sex_or_names_in_trace_or_responses() -> None:
    h = Harness()
    state = _confirmed(h)
    done = h.agent.approve(state.run_id, h.approval(state.version_id))
    _assert_no_personal_data(h, done.run_id, [e.name for e in TINY_EMPLOYEES])


def _assert_no_personal_data(h: Harness, run_id: str, names: list[str]) -> None:
    trace = json.dumps([e.model_dump(mode="json") for e in h.agent.trace(run_id)], ensure_ascii=False)
    assert '"sex"' not in trace and not any(name in trace for name in names)
    people = h.agent.employees(run_id)
    assert people and all(isinstance(p, EmployeePublic) for p in people)
    responses = [
        h.agent.get_run(run_id).model_dump(mode="json"),
        h.agent.get_schedule(run_id).model_dump(mode="json"),
        h.agent.published().model_dump(mode="json"),
        [p.model_dump(mode="json") for p in people],
    ]
    assert '"sex"' not in json.dumps(responses)


def test_unexpected_failure_in_a_node_becomes_rx12_not_a_crash() -> None:
    h = Harness()
    read = h.agent.start_run("escala.csv", tiny_csv())

    def broken(**_):
        raise RuntimeError("bug")

    h.agent._justify = broken  # simula um defeito num nó

    state = h.agent.confirm(read.run_id)

    assert state.phase == "failed" and state.exception.code == "RX-12"
    assert h.repo.get_run(read.run_id).phase == "failed"
    assert h.kinds(read.run_id)[-1] == "exception.raised"
    assert h.agent.published() is None


def test_confirm_after_restart_asks_for_the_file_again() -> None:
    h = Harness()
    read = h.agent.start_run("escala.csv", tiny_csv())
    restarted = Harness(repo=h.repo, sink=h.sink).agent  # mesmo banco, memória nova

    with pytest.raises(RunPhaseError):
        restarted.confirm(read.run_id)


def test_agent_satisfies_the_api_protocol() -> None:
    assert isinstance(Harness().agent, SliceAgent)


def test_flow_with_sql_repository_and_trace_sink() -> None:
    """Com os adaptadores reais da frente B (o que a C4 vai ligar): a cadeia do rastro vem de `list_events`."""
    engine = make_engine("sqlite://")
    init_db(engine)
    sink = SqlTraceSink(engine)
    h = Harness(repo=SqlRepository(engine), sink=sink, list_events=sink.list_events)

    state = _confirmed(h)
    done = h.agent.approve(state.run_id, h.approval(state.version_id))

    assert done.phase == "published" and h.agent.get_run(state.run_id) == done
    assert h.agent.published().id == state.version_id
    events = h.agent.trace(state.run_id)
    assert STEP_KINDS <= {e.kind for e in events}
    assert all(e.cost_usd is not None for e in events)
    ids = [e.id for e in events]
    assert all(e.parent_id in ids[:i] for i, e in enumerate(events) if i > 0)


# --- fluxo feliz com os dados da demo (60 pessoas × 7 dias, 1 thread) -------------------------------------------------


@pytest.fixture(scope="module")
def demo_flow():
    stores, employees, demand = load_demo_network(DEMO_DIR)
    h = Harness(stores=stores, employees=employees, demand=demand, time_limit_s=30.0)
    t0 = time.perf_counter()
    read = h.agent.start_run("escala_atual.csv", (DEMO_DIR / "escala_atual.csv").read_bytes())
    confirmed = h.agent.confirm(read.run_id) if read.phase == "awaiting_confirm" else read
    done = (
        h.agent.approve(confirmed.run_id, h.approval(confirmed.version_id))
        if confirmed.phase == "awaiting_approval"
        else confirmed
    )
    return h, employees, read, confirmed, done, time.perf_counter() - t0


def test_demo_happy_path_publishes_a_schedule_without_violations(demo_flow) -> None:
    h, _, read, confirmed, done, elapsed = demo_flow

    assert read.phase == "awaiting_confirm" and read.summary.ok
    assert confirmed.phase == "awaiting_approval"
    assert confirmed.exception is None or confirmed.exception.code == "RX-02"  # a demanda da demo ainda pode mudar
    assert confirmed.report.total == 0
    assert confirmed.comparison.before.violations > 0
    assert confirmed.comparison.after.overtime_hours == 0
    assert confirmed.justification is not None
    assert done.phase == "published"
    assert h.agent.published().id == confirmed.version_id
    assert STEP_KINDS <= set(h.kinds(done.run_id))
    print(f"\nfluxo feliz da demo: {elapsed:.1f} s")


def test_demo_no_sex_or_names_in_trace_or_responses(demo_flow) -> None:
    h, employees, _, _, done, _ = demo_flow
    _assert_no_personal_data(h, done.run_id, [e.name for e in employees])
