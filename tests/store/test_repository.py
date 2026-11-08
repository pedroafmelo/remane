"""Mesmos comportamentos contra o `InMemoryRepository` (falso) e o `SqlRepository`: o falso não pode divergir."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from escalista.db import init_db, make_engine
from escalista.domain.contracts import ExceptionCard, ExceptionOption, Role
from escalista.domain.ports import Repository, RosterRepository
from escalista.domain.reading import DemandPattern
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
from escalista.domain.roster import Roster
from escalista.domain.schedule import CsvIssue, Employee, ReadSummary, Schedule, Shift, Store
from escalista.domain.spec import MaxWeeklyHoursConstraint, PreferredDayOffConstraint, SolveSpec, UnavailableConstraint
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
            decider=Role.GESTOR,
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
    return Approval(id=aid, version_id=version_id, approved_by=by, role=Role.GESTOR, at=T0)


def roster(n: int = 1, **kw) -> Roster:
    base = {
        "version": n,
        "stores": [Store(id="s1", name="Loja 1", opens=time(8, 0), closes=time(22, 0))],
        "employees": [
            Employee(id="e1", name="Ana", store_id="s1", job="caixa", hourly_wage=Decimal("12.34"), contract_hours=44),
            Employee(
                id="e2",
                name="Bia",
                store_id="s1",
                job="repositora",
                hourly_wage=Decimal("10.05"),
                contract_hours=30,
                sex="F",
                profile="aprendiz",
            ),
        ],
        "demand": [DemandPattern(store_id="s1", weekday=0, start=time(8, 30), required=2)],
        "source_run_id": "run-1",
        "confirmed_by": "u1",
        "confirmed_at": T0 + timedelta(minutes=n),
    }
    return Roster(**{**base, **kw})


def big_schedule(shifts: int = 600) -> Schedule:
    return Schedule(
        week_start=MONDAY,
        shifts=[
            Shift(
                employee_id=f"e{i % 40}",
                store_id=f"s{i % 5}",
                start=datetime(2026, 11, 2 + i % 7, 8, 0),
                end=datetime(2026, 11, 2 + i % 7, 14, 30),
            )
            for i in range(shifts)
        ],
    )


def card(code: str) -> ExceptionCard:
    return ExceptionCard(
        code=code,
        title="Aviso",
        reason="motivo",
        decider=Role.GESTOR,
        deadline=datetime(2026, 11, 8, 9, 0),
        evidence=["linha 3"],
        options=[ExceptionOption(label="seguir", cost_usd=Decimal("0.07"), effect="nada muda")],
        recommendation="seguir",
        if_no_answer="segue",
        trace_id="t9",
    )


def test_sql_repository_satisfies_ports(engine):
    repo = SqlRepository(engine)
    assert isinstance(repo, Repository)
    assert isinstance(repo, RosterRepository)


def test_roster_table_has_search_columns(engine):
    assert {"version", "confirmed_at", "data"} <= {c["name"] for c in inspect(engine).get_columns("roster_version")}


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


def test_roster_roundtrip_preserves_decimal_and_optional_sex(repo):
    r = roster()
    repo.save_roster(r)
    got = repo.get_roster(1)
    assert got == r
    assert got.employees[0].sex is None
    assert got.employees[1].sex == "F"
    assert got.employees[0].hourly_wage == Decimal("12.34")
    assert isinstance(got.employees[0].hourly_wage, Decimal)


def test_get_roster_unknown_and_latest_empty(repo):
    assert repo.latest_roster() is None
    assert repo.get_roster(1) is None
    repo.save_roster(roster(1))
    assert repo.get_roster(2) is None


def test_latest_roster_is_the_highest_version(repo):
    repo.save_roster(roster(1))
    repo.save_roster(roster(3))
    repo.save_roster(roster(2))
    assert repo.latest_roster().version == 3
    assert repo.get_roster(2).version == 2


def test_save_roster_repeated_version_raises_and_keeps_first(repo):
    repo.save_roster(roster(1, confirmed_by="u1"))
    with pytest.raises(ValueError):
        repo.save_roster(roster(1, confirmed_by="u2"))
    assert repo.get_roster(1).confirmed_by == "u1"
    assert repo.latest_roster().confirmed_by == "u1"


def test_roster_with_aware_confirmed_at_roundtrips(repo):
    r = roster(confirmed_at=datetime(2026, 11, 7, 15, 0, tzinfo=UTC))
    repo.save_roster(r)
    assert repo.get_roster(1) == r


def test_sql_roster_persists_across_instances(engine):
    SqlRepository(engine).save_roster(roster(1))
    assert SqlRepository(engine).latest_roster() == roster(1)


def test_run_roundtrip_c6_fields(repo):
    before = big_schedule()
    spec = SolveSpec(
        shortfall_weight=120,
        stability_weight=7,
        constraints=[
            UnavailableConstraint(employee_id="e1", day=date(2026, 11, 3), start=time(8), end=time(12), evidence="x"),
            MaxWeeklyHoursConstraint(employee_id="e2", hours=30, evidence="y"),
            PreferredDayOffConstraint(employee_id="e3", day=date(2026, 11, 4), evidence="z"),
        ],
    )
    state = RunState(
        run_id="run-2",
        phase="optimized",
        mode="continuidade",
        before=before,
        week_start=MONDAY,
        spec=spec,
        notices=[card("RX-02"), card("RX-12")],
        roster_version=3,
        attempts=2,
        comparison=full_run().comparison,
    )
    repo.save_run(state)
    got = repo.get_run("run-2")
    assert got == state
    assert len(got.before.shifts) == 600
    assert got.before == before
    assert got.spec == spec
    assert [n.code for n in got.notices] == ["RX-02", "RX-12"]
    assert got.notices[0].options[0].cost_usd == Decimal("0.07")
    assert (got.mode, got.week_start, got.roster_version, got.attempts) == ("continuidade", MONDAY, 3, 2)


def test_run_c6_defaults_when_absent(repo):
    repo.save_run(RunState(run_id="run-3", phase="read"))
    got = repo.get_run("run-3")
    assert (got.mode, got.before, got.week_start, got.spec, got.notices) == ("upload", None, None, None, [])
    assert (got.roster_version, got.attempts) == (None, 0)
