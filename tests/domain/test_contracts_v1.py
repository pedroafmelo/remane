"""Contratos v1 da fatia (plano da C5, seção 3): fixa nomes de campos e métodos.

Mudar um contrato exige editar este teste no mesmo PR, o que deixa a mudança visível às outras frentes.
Só forma: a lógica de negócio nasce no TDD de cada frente.
"""

import inspect
from datetime import date, datetime, time
from decimal import Decimal

import pytest
from pydantic import ValidationError

from escalista.domain.contracts import ExceptionCard, Role
from escalista.domain.ports import Repository
from escalista.domain.results import (
    Approval,
    Comparison,
    Justification,
    JustificationItem,
    RunState,
    ScheduleMetrics,
    ScheduleVersion,
    SolveRequest,
    SolveResult,
    Violation,
    ViolationReport,
)
from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import (
    CsvIssue,
    DemandSlot,
    Employee,
    EmployeePublic,
    ReadSummary,
    Schedule,
    Shift,
    Store,
)
from tests.fakes import InMemoryRepository

MONDAY = date(2027, 1, 11)
NOW = datetime(2027, 1, 8, 9, 0)


def fields(model):
    return set(model.model_fields)


def employee(**overrides):
    data = {
        "id": "e1",
        "name": "Ana Sintética",
        "store_id": "s1",
        "job": "operador de caixa",
        "hourly_wage": Decimal("9.50"),
        "contract_hours": 42,
        "sex": "F",
    }
    return Employee(**(data | overrides))


def shift(start, end):
    return Shift(employee_id="e1", store_id="s1", start=start, end=end)


def metrics(**overrides):
    data = {
        "total_cost": Decimal("1000.00"),
        "regular_hours": Decimal("400"),
        "overtime_hours": Decimal("10"),
        "overtime_cost": Decimal("142.50"),
        "coverage_pct": 0.97,
        "uncovered_slots": 3,
        "violations": 2,
    }
    return ScheduleMetrics(**(data | overrides))


def version(vid="v1", status="draft"):
    return ScheduleVersion(
        id=vid,
        run_id="r1",
        schedule=Schedule(week_start=MONDAY, shifts=[]),
        status=status,
        input_hash="h",
        seed=42,
        violations_total=0,
        created_at=NOW,
    )


# --- regras ------------------------------------------------------------------------------------------


def test_rule_enums_values():
    assert {s.value for s in RuleStatus} == {"conferida", "interpretacao", "pendente", "ficticia"}
    assert {lay.value for lay in RuleLayer} == {"lei", "convencao", "politica"}


def test_rule_fields_and_frozen():
    assert fields(Rule) == {
        "id",
        "kind",
        "layer",
        "params",
        "valid_from",
        "valid_to",
        "status",
        "source",
        "action",
        "note",
    }
    rule = Rule(id="lei.jornada", kind="jornada_semanal_max", layer="lei", status="conferida", source="EC 141")
    assert rule.params == {} and rule.valid_from is None and rule.action is None
    with pytest.raises(ValidationError):
        rule.kind = "outro"
    with pytest.raises(ValidationError):
        Rule(id="x", kind="info", layer="lei", status="conferida", source="s", action="aprovar")


def test_rule_card_fields():
    assert fields(RuleCard) == {"reference_date", "rules", "provisional", "exceptions"}
    card = RuleCard(reference_date=MONDAY, rules=[], exceptions=[ExceptionCard(code="RX-03", title="t", reason="r")])
    assert card.provisional == [] and card.exceptions[0].code == "RX-03"


# --- escala e entrada ----------------------------------------------------------------------------------


def test_store_and_demand_slot_fields():
    assert fields(Store) == {"id", "name", "opens", "closes"}
    assert fields(DemandSlot) == {"store_id", "day", "start", "required"}
    assert Store(id="s1", name="Loja 1", opens=time(8), closes=time(22)).opens == time(8)


def test_employee_fields_and_profile_default():
    assert fields(Employee) == {"id", "name", "store_id", "job", "hourly_wage", "contract_hours", "sex", "profile"}
    e = employee()
    assert e.profile == "padrao" and isinstance(e.hourly_wage, Decimal)
    with pytest.raises(ValidationError):
        employee(sex="X")
    with pytest.raises(ValidationError):
        employee(profile="estagiario")


def test_employee_public_never_carries_sex():
    """RN-13: o sexo não vai à tela, à resposta da API do gerente nem ao trace."""
    assert fields(EmployeePublic) == fields(Employee) - {"sex"}
    public = EmployeePublic.from_employee(employee())
    assert "sex" not in public.model_dump() and public.id == "e1"


def test_shift_fields_and_end_after_start():
    assert fields(Shift) == {"employee_id", "store_id", "start", "end"}
    overnight = shift(datetime(2027, 1, 11, 22), datetime(2027, 1, 12, 6))
    assert overnight.end.date() == date(2027, 1, 12)
    with pytest.raises(ValidationError):
        shift(datetime(2027, 1, 11, 14), datetime(2027, 1, 11, 14))
    with pytest.raises(ValidationError):
        shift(datetime(2027, 1, 11, 14), datetime(2027, 1, 11, 8))


def test_shift_datetimes_have_no_timezone():
    with pytest.raises(ValidationError):
        shift(datetime.fromisoformat("2027-01-11T08:00+00:00"), datetime.fromisoformat("2027-01-11T16:00+00:00"))


def test_schedule_fields_and_week_starts_on_monday():
    assert fields(Schedule) == {"week_start", "shifts"}
    assert Schedule(week_start=MONDAY, shifts=[]).shifts == []
    with pytest.raises(ValidationError):
        Schedule(week_start=date(2027, 1, 12), shifts=[])


def test_csv_issue_and_read_summary_fields():
    assert fields(CsvIssue) == {"line", "field", "reason"}
    assert fields(ReadSummary) == {
        "file_name", "rows", "employees", "stores", "week_start", "total_hours", "issues", "ok",
    }  # fmt: skip
    summary = ReadSummary(
        file_name="escala.csv",
        rows=2,
        employees=1,
        stores=1,
        week_start=MONDAY,
        total_hours=Decimal("16"),
        issues=[CsvIssue(line=3, field=None, reason="linha vazia")],
        ok=False,
    )
    assert summary.issues[0].line == 3


# --- solver, verificador e custo ----------------------------------------------------------------------


def test_solve_request_and_result_fields():
    assert fields(SolveRequest) == {
        "card", "stores", "employees", "demand", "week_start", "seed", "time_limit_s", "num_workers", "hint",
    }  # fmt: skip
    assert fields(SolveResult) == {"status", "schedule", "uncovered", "wall_ms", "seed", "input_hash", "exception"}
    result = SolveResult(status="infeasible", wall_ms=10, seed=42, input_hash="h")
    assert result.schedule is None and result.uncovered == [] and result.exception is None
    with pytest.raises(ValidationError):
        SolveResult(status="unknown", wall_ms=10, seed=42, input_hash="h")


def test_violation_and_report_total_is_computed():
    assert fields(Violation) == {"rule_id", "kind", "employee_id", "day", "source", "detail"}
    assert fields(ViolationReport) | set(ViolationReport.model_computed_fields) == {"violations", "total"}
    v = Violation(
        rule_id="lei.jornada", kind="jornada_semanal_max", employee_id="e1", day=None, source="EC 141", detail="46h"
    )
    report = ViolationReport(violations=[v, v])
    assert report.total == 2 and report.model_dump()["total"] == 2
    assert ViolationReport(violations=[]).total == 0


def test_metrics_and_comparison_fields():
    assert fields(ScheduleMetrics) == {
        "total_cost", "regular_hours", "overtime_hours", "overtime_cost", "coverage_pct", "uncovered_slots",
        "violations",
    }  # fmt: skip
    assert fields(Comparison) == {"before", "after", "savings", "overtime_hours_avoided", "violations_avoided"}
    comparison = Comparison(
        before=metrics(),
        after=metrics(total_cost=Decimal("900.00")),
        savings=Decimal("100.00"),
        overtime_hours_avoided=Decimal("10"),
        violations_avoided=2,
    )
    assert isinstance(comparison.after.total_cost, Decimal)


def test_justification_fields():
    assert fields(Justification) == {"summary", "items"}
    assert fields(JustificationItem) == {"text", "rule_refs"}
    j = Justification(summary="s", items=[{"text": "t", "rule_refs": ["lei.jornada"]}])
    assert isinstance(j.items[0], JustificationItem)


# --- versão, aprovação e estado da execução --------------------------------------------------------------


def test_schedule_version_and_approval_fields():
    assert fields(ScheduleVersion) == {
        "id", "run_id", "schedule", "status", "input_hash", "seed", "violations_total", "created_at",
    }  # fmt: skip
    assert fields(Approval) == {"id", "version_id", "approved_by", "role", "at"}
    with pytest.raises(ValidationError):
        version(status="rascunho")
    approval = Approval(id="a1", version_id="v1", approved_by="u1", role="gerente", at=NOW)
    assert approval.role is Role.GERENTE


def test_run_state_fields():
    assert fields(RunState) == {
        "run_id", "phase", "summary", "comparison", "report", "justification", "version_id", "exception",
    }  # fmt: skip
    state = RunState(run_id="r1", phase="read")
    assert state.summary is None and state.exception is None
    with pytest.raises(ValidationError):
        RunState(run_id="r1", phase="desconhecida")


# --- porta Repository e falso ------------------------------------------------------------------------------


def test_repository_port_methods():
    params = {
        "save_run": ["self", "state"],
        "get_run": ["self", "run_id"],
        "save_version": ["self", "v"],
        "get_version": ["self", "version_id"],
        "record_approval": ["self", "a"],
        "get_approval": ["self", "version_id"],
        "mark_published": ["self", "version_id", "at"],
        "latest_published": ["self"],
    }
    for name, expected in params.items():
        assert list(inspect.signature(getattr(Repository, name)).parameters) == expected, name


def test_in_memory_repository_satisfies_the_port():
    assert isinstance(InMemoryRepository(), Repository)


def test_in_memory_repository_round_trips():
    repo = InMemoryRepository()
    assert repo.get_run("r1") is None and repo.get_version("v1") is None
    assert repo.get_approval("v1") is None and repo.latest_published() is None
    repo.save_run(RunState(run_id="r1", phase="read"))
    assert repo.get_run("r1").phase == "read"
    repo.save_version(version("v1"))
    repo.save_version(version("v2"))
    approval = Approval(id="a1", version_id="v1", approved_by="u1", role=Role.GERENTE, at=NOW)
    repo.record_approval(approval)
    assert repo.get_approval("v1") == approval
    repo.mark_published("v1", NOW)
    assert repo.get_version("v1").status == "published"
    assert repo.latest_published().id == "v1"
