"""Mesmos comportamentos contra o `InMemoryRepository` (falso) e o `SqlRepository`: o falso não pode divergir."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from escalista.db import init_db, make_engine
from escalista.domain.contracts import ExceptionCard, ExceptionOption, Role
from escalista.domain.ports import Repository
from escalista.domain.results import (
    Approval,
    Comparison,
    Justification,
    JustificationItem,
    RunState,
    ScheduleMetrics,
    ScheduleVersion,
    Violation,
    ViolationReport,
)
from escalista.domain.schedule import CsvIssue, ReadSummary, Schedule, Shift
from escalista.store.sql_repository import SqlRepository
from tests.fakes import InMemoryRepository

MONDAY = date(2026, 11, 2)
T0 = datetime(2026, 11, 7, 12, 0)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    init_db(eng)
    return eng


@pytest.fixture(params=["memory", "sql"])
def repo(request, engine) -> Repository:
    return InMemoryRepository() if request.param == "memory" else SqlRepository(engine)


def metrics(total: str, over: str) -> ScheduleMetrics:
    return ScheduleMetrics(
        total_cost=Decimal(total),
        regular_hours=Decimal("1234.50"),
        overtime_hours=Decimal(over),
        overtime_cost=Decimal("0.10") * Decimal(over),
        coverage_pct=97.5,
        uncovered_slots=3,
        violations=2,
    )


def full_run(run_id: str = "run-1") -> RunState:
    return RunState(
        run_id=run_id,
        phase="awaiting_approval",
        summary=ReadSummary(
            file_name="escala.csv",
            rows=10,
            employees=4,
            stores=2,
            week_start=MONDAY,
            total_hours=Decimal("160.25"),
            issues=[CsvIssue(line=3, field="inicio", reason="hora inválida")],
            ok=True,
        ),
        comparison=Comparison(
            before=metrics("10000.10", "40.25"),
            after=metrics("9000.07", "10.5"),
            savings=Decimal("1000.03"),
            overtime_hours_avoided=Decimal("29.75"),
            violations_avoided=5,
        ),
        report=ViolationReport(
            violations=[
                Violation(
                    rule_id="R-INTERJORNADA",
                    kind="interjornada",
                    employee_id="e1",
                    day=MONDAY,
                    source="convencao",
                    detail="descanso de 9h",
                )
            ]
        ),
        justification=Justification(
            summary="Menos horas extras.", items=[JustificationItem(text="Cobertura mantida", rule_refs=["R-1"])]
        ),
        version_id="v1",
        exception=ExceptionCard(
            code="RX-02",
            title="Sem solução viável",
            reason="demanda acima da capacidade",
            decider=Role.GERENTE,
            deadline=datetime(2026, 11, 8, 9, 0, tzinfo=UTC),
            evidence=["loja 2, sexta"],
            options=[ExceptionOption(label="contratar", cost_usd=Decimal("12.5"), effect="cobre a sexta")],
            recommendation="relaxar a demanda",
            if_no_answer="mantém a escala atual",
            trace_id="t1",
        ),
    )


def version(vid: str = "v1", status: str = "draft", **kw) -> ScheduleVersion:
    shift = Shift(employee_id="e1", store_id="s1", start=datetime(2026, 11, 2, 8, 0), end=datetime(2026, 11, 2, 16, 0))
    base = {
        "id": vid,
        "run_id": "run-1",
        "schedule": Schedule(week_start=MONDAY, shifts=[shift]),
        "status": status,
        "input_hash": "abc123",
        "seed": 42,
        "violations_total": 0,
        "created_at": T0,
    }
    return ScheduleVersion(**{**base, **kw})


def approval(version_id: str = "v1", aid: str = "a1", by: str = "u1") -> Approval:
    return Approval(id=aid, version_id=version_id, approved_by=by, role=Role.GERENTE, at=T0)


def test_sql_repository_satisfies_port(engine):
    assert isinstance(SqlRepository(engine), Repository)


def test_tables_have_search_columns(engine):
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("schedule_version")}
    assert {"id", "run_id", "status", "created_at", "published_at", "publish_seq"} <= cols
    assert {"run_id", "phase", "version_id"} <= {c["name"] for c in insp.get_columns("run_state")}
    assert {"id", "version_id"} <= {c["name"] for c in insp.get_columns("approval")}


def test_run_roundtrip_full_state(repo):
    state = full_run()
    repo.save_run(state)
    got = repo.get_run("run-1")
    assert got == state
    assert got.comparison.savings == Decimal("1000.03")
    assert isinstance(got.comparison.before.total_cost, Decimal)
    assert got.report.total == 1
    assert got.exception.code == "RX-02"


def test_get_run_unknown_is_none(repo):
    assert repo.get_run("nope") is None


def test_save_run_upserts(repo):
    repo.save_run(RunState(run_id="run-1", phase="read"))
    repo.save_run(full_run())
    got = repo.get_run("run-1")
    assert got.phase == "awaiting_approval"
    assert got.version_id == "v1"


def test_save_run_stores_copy(repo):
    state = RunState(run_id="run-1", phase="read")
    repo.save_run(state)
    state.phase = "failed"
    assert repo.get_run("run-1").phase == "read"


def test_version_roundtrip_and_unknown(repo):
    v = version()
    repo.save_version(v)
    assert repo.get_version("v1") == v
    assert repo.get_version("nope") is None


def test_save_version_upserts(repo):
    repo.save_version(version())
    repo.save_version(version(status="approved", violations_total=1))
    got = repo.get_version("v1")
    assert (got.status, got.violations_total) == ("approved", 1)


def test_version_with_aware_created_at_roundtrips(repo):
    v = version(created_at=datetime(2026, 11, 7, 15, 0, tzinfo=UTC))
    repo.save_version(v)
    assert repo.get_version("v1") == v


def test_approval_roundtrip_and_missing_is_none(repo):
    repo.save_version(version())
    assert repo.get_approval("v1") is None
    a = approval()
    repo.record_approval(a)
    assert repo.get_approval("v1") == a
    assert repo.get_approval("v2") is None


def test_second_approval_replaces_first(repo):
    repo.record_approval(approval(aid="a1", by="u1"))
    repo.record_approval(approval(aid="a2", by="u2"))
    got = repo.get_approval("v1")
    assert (got.id, got.approved_by) == ("a2", "u2")


def test_mark_published_sets_status_and_latest(repo):
    repo.save_version(version("v1"))
    repo.save_version(version("v2"))
    assert repo.latest_published() is None
    repo.mark_published("v1", T0)
    assert repo.get_version("v1").status == "published"
    assert repo.get_version("v2").status == "draft"
    assert repo.latest_published().id == "v1"


def test_latest_published_is_the_last_published(repo):
    for vid in ("v1", "v2", "v3"):
        repo.save_version(version(vid))
    repo.mark_published("v1", datetime(2026, 11, 7, 10, 0))
    repo.mark_published("v3", datetime(2026, 11, 7, 11, 0))
    repo.mark_published("v2", datetime(2026, 11, 7, 12, 0))
    assert repo.latest_published().id == "v2"
    repo.mark_published("v1", datetime(2026, 11, 7, 13, 0))
    assert repo.latest_published().id == "v1"


def test_mark_published_unknown_raises_key_error(repo):
    with pytest.raises(KeyError):
        repo.mark_published("nope", T0)
    assert repo.latest_published() is None


def test_sql_latest_published_follows_write_order_not_clock(engine):
    repo = SqlRepository(engine)
    repo.save_version(version("v1"))
    repo.save_version(version("v2"))
    repo.mark_published("v1", datetime(2026, 11, 7, 12, 0))
    repo.mark_published("v2", datetime(2026, 11, 7, 9, 0))  # relógio voltou
    assert repo.latest_published().id == "v2"


def test_sql_data_persists_across_instances(engine):
    first = SqlRepository(engine)
    first.save_run(full_run())
    first.save_version(version())
    first.record_approval(approval())
    first.mark_published("v1", T0)
    second = SqlRepository(engine)
    assert second.get_run("run-1") == full_run()
    assert second.get_version("v1").status == "published"
    assert second.get_approval("v1") == approval()
    assert second.latest_published().id == "v1"
