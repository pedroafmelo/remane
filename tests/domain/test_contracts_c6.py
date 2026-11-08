"""Contratos da C6 (plano da C6, seção 5): leitura por agente, quadro guardado e especificação do problema.

Fixa nomes de campos, `extra="forbid"` nos schemas que o modelo preenche e as faixas. Mudar um contrato exige editar
este teste no mesmo PR. Só forma: a lógica nasce nas tarefas A1 a A5.
"""

import inspect
from datetime import date, datetime, time
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from escalista.domain.contracts import ExceptionCard
from escalista.domain.ports import Repository, RosterRepository
from escalista.domain.reading import (
    CapacityCheck,
    CellRef,
    ColumnMapping,
    ColumnRef,
    ConfirmInput,
    DayColumn,
    DemandPattern,
    IdentityAnswer,
    IdentityCard,
    RawTable,
    ShiftCode,
    ShiftEvidence,
)
from escalista.domain.results import RunState, SolveRequest
from escalista.domain.roster import Roster
from escalista.domain.rules import RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import CsvIssue, Employee, ReadSummary, Schedule, Store
from escalista.domain.spec import (
    MaxWeeklyHoursConstraint,
    PreferredDayOffConstraint,
    PreferredWindowConstraint,
    SolveSpec,
    SpecConstraint,
    UnavailableConstraint,
)
from tests.fakes import (
    TOOL_JUSTIFY,
    TOOL_MAPPING,
    TOOL_SPEC,
    FakeLLMClient,
    InMemoryRepository,
)

MONDAY = date(2027, 1, 11)
TUESDAY = date(2027, 1, 12)
NOW = datetime(2027, 1, 8, 9, 0)


def fields(model):
    return set(model.model_fields)


def col(index=0, header="Colaborador"):
    return ColumnRef(index=index, header=header)


def long_mapping(**overrides):
    data = {
        "table": 0,
        "header_row": 0,
        "layout": "long",
        "person": {"index": 0, "header": "Colaborador"},
        "date": {"index": 1, "header": "Data"},
        "start": {"index": 2, "header": "Entrada"},
        "end": {"index": 3, "header": "Saída"},
        "date_order": "dmy",
    }
    return ColumnMapping.model_validate(data | overrides)


# --- leitura: tabela crua, mapeamento e evidência -----------------------------------------------------


def test_raw_table_fields():
    assert fields(RawTable) == {"name", "rows"}
    table = RawTable(name="Escala", rows=[["Colaborador", "Data"], ["Ana", "2027-01-11"]])
    assert table.rows[1][1] == "2027-01-11"


def test_column_ref_shift_code_and_day_column_fields():
    assert fields(ColumnRef) == {"index", "header"}
    assert fields(ShiftCode) == {"code", "start", "end", "off", "evidence"}
    assert fields(DayColumn) == {"col", "day", "weekday"}
    with pytest.raises(ValidationError):
        ColumnRef(index=-1, header="x")
    code = ShiftCode(code="M", start=time(7), end=time(15))
    assert code.off is False and code.evidence is None
    with pytest.raises(ValidationError):
        ShiftCode(code="MANHA-LONGA", start=time(7), end=time(15))  # mais de 8 caracteres
    with pytest.raises(ValidationError):
        ShiftCode(code="", off=True)
    day = DayColumn(col=col(4, "Seg"), weekday="seg")
    assert day.day is None
    with pytest.raises(ValidationError):
        DayColumn(col=col(4, "Seg"), weekday="segunda")


def test_column_mapping_fields_and_defaults():
    assert fields(ColumnMapping) == {
        "table", "header_row", "layout", "person", "person_code", "store", "date", "start", "end", "shift",
        "day_columns", "date_order", "shift_codes", "wage", "notes",
    }  # fmt: skip
    mapping = long_mapping()
    assert mapping.person.header == "Colaborador" and mapping.store is None and mapping.day_columns == []
    assert mapping.shift_codes == [] and mapping.wage is None and mapping.notes is None
    grid = ColumnMapping(
        table=0,
        header_row=1,
        layout="grid",
        person=col(),
        day_columns=[DayColumn(col=col(1, "11/01"), day=MONDAY)],
        date_order="dmy",
        shift_codes=[ShiftCode(code="F", off=True, evidence="F = folga")],
    )
    assert grid.date is None and grid.start is None and grid.end is None


def test_column_mapping_rejects_extra_fields_and_bad_literals():
    """O modelo não acrescenta campo nenhum ao mapeamento (nem nos itens aninhados)."""
    with pytest.raises(ValidationError):
        long_mapping(rows=[["Ana", "08:00"]])  # o modelo não devolve linhas (invariante 1)
    with pytest.raises(ValidationError):
        long_mapping(person={"index": 0, "header": "Colaborador", "confidence": 0.9})
    with pytest.raises(ValidationError):
        long_mapping(layout="wide")
    with pytest.raises(ValidationError):
        long_mapping(date_order="dym")
    with pytest.raises(ValidationError):
        long_mapping(shift_codes=[{"code": "M", "off": False, "cor": "azul"}])


def test_cell_ref_and_shift_evidence_fields():
    assert fields(CellRef) == {"table", "row", "col"}
    assert fields(ShiftEvidence) == {"shift_index", "cells", "raw"}
    evidence = ShiftEvidence(
        shift_index=0, cells=[CellRef(table=0, row=1, col=2), CellRef(table=0, row=1, col=3)], raw=["08:00", "16:00"]
    )
    assert evidence.cells[1].col == 3


def test_csv_issue_gains_optional_table_and_col():
    assert fields(CsvIssue) == {"line", "field", "reason", "table", "col"}
    old = CsvIssue(line=3, reason="linha vazia")
    assert old.table is None and old.col is None
    assert CsvIssue(line=3, reason="hora inválida", table="Escala", col=2).col == 2


# --- identidade, demanda e capacidade -------------------------------------------------------------------


def test_identity_card_fields_and_literals():
    assert fields(IdentityCard) == {"id", "kind", "names", "rows", "suggestion", "reason"}
    card = IdentityCard(
        id="ic1",
        kind="grafia_parecida",
        names=["Ana Souza", "Ana de Souza"],
        rows=[CellRef(table=0, row=2, col=0)],
        suggestion="mesma",
        reason="nomes parecidos, sem turno sobreposto",
    )
    assert card.kind == "grafia_parecida"
    with pytest.raises(ValidationError):
        IdentityCard(id="x", kind="parecido", names=[], rows=[], suggestion="mesma", reason="r")
    with pytest.raises(ValidationError):
        IdentityCard(id="x", kind="homonimo", names=[], rows=[], suggestion="talvez", reason="r")


def test_demand_pattern_and_capacity_check_fields():
    assert fields(DemandPattern) == {"store_id", "weekday", "start", "required"}
    assert DemandPattern(store_id="s1", weekday=0, start=time(8), required=2).weekday == 0
    with pytest.raises(ValidationError):
        DemandPattern(store_id="s1", weekday=7, start=time(8), required=2)
    assert fields(CapacityCheck) == {"demand_person_hours", "capacity_person_hours", "fits", "max_fitting_pct"}
    check = CapacityCheck(
        demand_person_hours=Decimal("2776"), capacity_person_hours=Decimal("2400"), fits=False, max_fitting_pct=86
    )
    assert isinstance(check.demand_person_hours, Decimal) and not check.fits


# --- resumo da leitura (compatível com a C5) --------------------------------------------------------------


def test_read_summary_gains_fields_with_defaults():
    assert fields(ReadSummary) == {
        "file_name", "rows", "employees", "stores", "week_start", "total_hours", "issues", "ok",
        "format", "mapping", "mapping_source", "assumptions", "identity", "capacity", "planned_week_start",
        "store_ids", "evidence_sample",
    }  # fmt: skip
    old = ReadSummary(
        file_name="escala.csv", rows=2, employees=1, stores=1, week_start=MONDAY, total_hours=Decimal("16"),
        issues=[], ok=True,
    )  # fmt: skip
    assert old.format == "csv" and old.mapping is None and old.mapping_source == "csv_dec039"
    assert old.assumptions == [] and old.identity == [] and old.capacity is None and old.planned_week_start is None
    assert old.store_ids == [] and old.evidence_sample == []
    evidence = ShiftEvidence(shift_index=0, cells=[CellRef(table=0, row=1, col=0)], raw=["Ana"])
    sample = old.model_copy(update={"store_ids": ["L1", "L2"], "evidence_sample": [evidence] * 5})
    assert ReadSummary(**sample.model_dump()).store_ids == ["L1", "L2"]
    with pytest.raises(ValidationError):
        ReadSummary(**(old.model_dump() | {"evidence_sample": [evidence.model_dump()] * 6}))  # até 5
    new = old.model_copy(update={"format": "xlsx", "mapping": long_mapping(), "mapping_source": "modelo"})
    assert new.mapping.layout == "long"
    with pytest.raises(ValidationError):
        ReadSummary(**(old.model_dump() | {"format": "docx"}))
    with pytest.raises(ValidationError):
        ReadSummary(**(old.model_dump() | {"mapping_source": "chute"}))
    with pytest.raises(ValidationError):
        ReadSummary(**(old.model_dump() | {"planned_week_start": TUESDAY}))  # tem de ser segunda


# --- quadro guardado e confirmação -------------------------------------------------------------------------


def test_employee_without_sex_is_valid():
    """Decisão 2 da C6: o quadro lido de arquivo nem tem o campo (RN-13)."""
    e = Employee(id="n-ana", name="Ana", store_id="s1", job="caixa", hourly_wage=Decimal("9.50"), contract_hours=42)
    assert e.sex is None
    with pytest.raises(ValidationError):
        Employee(
            id="n-ana", name="Ana", store_id="s1", job="caixa", hourly_wage=Decimal("9.5"), contract_hours=42, sex="X"
        )
    with pytest.raises(ValidationError):  # o salário-hora segue obrigatório
        Employee(id="n-ana", name="Ana", store_id="s1", job="caixa", contract_hours=42)


def test_roster_fields():
    assert fields(Roster) == {
        "version", "stores", "employees", "demand", "source_run_id", "confirmed_by", "confirmed_at",
    }  # fmt: skip
    roster = Roster(
        version=1,
        stores=[Store(id="s1", name="Loja 1", opens=time(8), closes=time(22))],
        employees=[
            Employee(id="n-ana", name="Ana", store_id="s1", job="caixa", hourly_wage=Decimal("9.5"), contract_hours=42)
        ],
        demand=[DemandPattern(store_id="s1", weekday=0, start=time(8), required=2)],
        source_run_id="r1",
        confirmed_by="u1",
        confirmed_at=NOW,
    )
    assert roster.employees[0].sex is None
    with pytest.raises(ValidationError):
        Roster.model_validate(roster.model_dump() | {"version": 0})  # versões começam em 1


def test_confirm_input_fields_and_ranges():
    assert fields(ConfirmInput) == {"coverage_pct", "hourly_wage_default", "planned_week_start", "note", "identity"}
    assert fields(IdentityAnswer) == {"card_id", "same"}
    default = ConfirmInput()
    assert default.coverage_pct == {} and default.note == "" and default.identity == []
    assert default.hourly_wage_default is None and default.planned_week_start is None
    ok = ConfirmInput(
        coverage_pct={"s1": 50, "s2": 120}, planned_week_start=MONDAY, note="Ana não pode na terça",
        identity=[{"card_id": "ic1", "same": True}],
    )  # fmt: skip
    assert isinstance(ok.identity[0], IdentityAnswer)
    for bad in (49, 121):
        with pytest.raises(ValidationError):
            ConfirmInput(coverage_pct={"s1": bad})
    with pytest.raises(ValidationError):
        ConfirmInput(note="x" * 501)
    assert len(ConfirmInput(note="x" * 500).note) == 500
    with pytest.raises(ValidationError):
        ConfirmInput(planned_week_start=TUESDAY)


# --- especificação do problema (nó 2) -----------------------------------------------------------------------


def test_spec_constraint_variants_fields():
    assert fields(UnavailableConstraint) == {"type", "employee_id", "day", "start", "end", "evidence"}
    assert fields(MaxWeeklyHoursConstraint) == {"type", "employee_id", "hours", "evidence"}
    assert fields(PreferredDayOffConstraint) == {"type", "employee_id", "day", "evidence"}
    assert fields(PreferredWindowConstraint) == {"type", "employee_id", "window", "evidence"}


def test_spec_constraint_is_a_discriminated_union_on_type():
    adapter = TypeAdapter(SpecConstraint)
    cases = {
        "indisponivel": ({"employee_id": "e1", "day": "2027-01-12"}, UnavailableConstraint),
        "max_horas_semana": ({"employee_id": "e1", "hours": 30}, MaxWeeklyHoursConstraint),
        "folga_preferida": ({"employee_id": "e1", "day": "2027-01-12"}, PreferredDayOffConstraint),
        "janela_preferida": ({"employee_id": "e1", "window": "manha"}, PreferredWindowConstraint),
    }
    for kind, (data, cls) in cases.items():
        parsed = adapter.validate_python({"type": kind, "evidence": "trecho literal", **data})
        assert isinstance(parsed, cls) and parsed.type == kind
    unavailable = adapter.validate_python(
        {"type": "indisponivel", "employee_id": "e1", "day": TUESDAY, "evidence": "x"}
    )
    assert unavailable.start is None and unavailable.end is None
    with pytest.raises(ValidationError):  # lista fechada
        adapter.validate_python({"type": "jornada_semanal_max", "employee_id": "e1", "hours": 48, "evidence": "x"})
    with pytest.raises(ValidationError):  # evidência obrigatória
        adapter.validate_python({"type": "folga_preferida", "employee_id": "e1", "day": TUESDAY})
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {"type": "janela_preferida", "employee_id": "e1", "window": "madrugada", "evidence": "x"}
        )


def test_each_spec_constraint_forbids_extra_fields():
    adapter = TypeAdapter(SpecConstraint)
    base = {
        "indisponivel": {"employee_id": "e1", "day": "2027-01-12"},
        "max_horas_semana": {"employee_id": "e1", "hours": 30},
        "folga_preferida": {"employee_id": "e1", "day": "2027-01-12"},
        "janela_preferida": {"employee_id": "e1", "window": "tarde"},
    }
    for kind, data in base.items():
        with pytest.raises(ValidationError):
            adapter.validate_python({"type": kind, "evidence": "x", "layer": "lei", **data})


def test_solve_spec_fields_and_defaults():
    assert fields(SolveSpec) == {"shortfall_weight", "stability_weight", "preference_weight", "constraints"}
    spec = SolveSpec()
    assert (spec.shortfall_weight, spec.stability_weight, spec.preference_weight) == (100, 0, 5)
    assert spec.constraints == []


@pytest.mark.parametrize(
    ("field", "low", "high"),
    [("shortfall_weight", 10, 1000), ("stability_weight", 0, 50), ("preference_weight", 0, 50)],
)
def test_solve_spec_weight_ranges(field, low, high):
    assert getattr(SolveSpec(**{field: low}), field) == low
    assert getattr(SolveSpec(**{field: high}), field) == high
    for bad in (low - 1, high + 1):
        with pytest.raises(ValidationError):
            SolveSpec(**{field: bad})


def test_solve_spec_limits_constraints_and_forbids_card_fields():
    """Invariante 4 (estrutural): a spec não tem campo para regra do cartão."""
    item = {"type": "folga_preferida", "employee_id": "e1", "day": "2027-01-12", "evidence": "x"}
    assert len(SolveSpec(constraints=[item] * 30).constraints) == 30
    with pytest.raises(ValidationError):
        SolveSpec(constraints=[item] * 31)
    with pytest.raises(ValidationError):
        SolveSpec.model_validate({"jornada_semanal_max": 48})
    parsed = SolveSpec.model_validate({"constraints": [item]})
    assert isinstance(parsed.constraints[0], PreferredDayOffConstraint)


# --- alterações compatíveis no solver, nas regras e no estado ------------------------------------------------


def test_solve_request_gains_optional_spec():
    assert "spec" in fields(SolveRequest)
    req = SolveRequest(
        card=RuleCard(reference_date=MONDAY, rules=[]), stores=[], employees=[], demand=[], week_start=MONDAY,
        seed=42, time_limit_s=1.0, num_workers=1,
    )  # fmt: skip
    assert req.spec is None
    assert req.model_copy(update={"spec": SolveSpec()}).spec.shortfall_weight == 100


def test_rule_layer_and_status_gain_execution_and_request():
    assert RuleLayer.EXECUCAO == "execucao" and RuleStatus.PEDIDO == "pedido"
    assert [layer.value for layer in RuleLayer] == ["lei", "convencao", "politica", "execucao"]


def test_run_state_gains_fields_with_defaults():
    assert {"mode", "before", "week_start", "spec", "notices", "roster_version", "attempts"} <= fields(RunState)
    old = RunState(run_id="r1", phase="read")  # estado da C5: só run_id e phase
    assert old.mode == "upload" and old.before is None and old.week_start is None and old.spec is None
    assert old.notices == [] and old.roster_version is None and old.attempts == 0
    state = RunState(
        run_id="r2",
        phase="awaiting_approval",
        mode="continuidade",
        before=Schedule(week_start=MONDAY, shifts=[]),
        week_start=MONDAY,
        spec=SolveSpec(),
        notices=[ExceptionCard(code="RX-12", title="t", reason="r")],
        roster_version=1,
        attempts=2,
    )
    assert RunState.model_validate(state.model_dump(mode="json")) == state
    with pytest.raises(ValidationError):
        RunState(run_id="r1", phase="read", mode="semanal")


# --- porta e falsos ----------------------------------------------------------------------------------------


def test_roster_port_methods():
    params = {"save_roster": ["self", "r"], "latest_roster": ["self"], "get_roster": ["self", "version"]}
    for name, expected in params.items():
        assert list(inspect.signature(getattr(RosterRepository, name)).parameters) == expected, name


def test_in_memory_repository_satisfies_both_ports():
    repo = InMemoryRepository()
    assert isinstance(repo, Repository) and isinstance(repo, RosterRepository)


def roster(version: int, run_id: str = "r1") -> Roster:
    return Roster(
        version=version, stores=[], employees=[], demand=[], source_run_id=run_id, confirmed_by="u1", confirmed_at=NOW
    )


def test_in_memory_repository_appends_roster_versions():
    repo = InMemoryRepository()
    assert repo.latest_roster() is None and repo.get_roster(1) is None
    repo.save_roster(roster(1))
    repo.save_roster(roster(2, "r2"))
    assert repo.latest_roster().version == 2 and repo.get_roster(1).source_run_id == "r1"
    with pytest.raises(ValueError):  # nunca sobrescreve
        repo.save_roster(roster(1, "r3"))
    assert repo.get_roster(1).source_run_id == "r1"


def test_in_memory_repository_keeps_copies_of_rosters():
    repo = InMemoryRepository()
    saved = roster(1)
    repo.save_roster(saved)
    saved.source_run_id = "alterado"
    assert repo.get_roster(1).source_run_id == "r1"


def tool(name: str) -> dict:
    return {"type": "function", "function": {"name": name, "parameters": {}}}


def test_tool_names():
    assert (TOOL_MAPPING, TOOL_SPEC, TOOL_JUSTIFY) == (
        "registrar_mapeamento",
        "registrar_especificacao",
        "registrar_justificativa",
    )


def test_fake_llm_answers_by_tool_name():
    llm = FakeLLMClient(
        by_tool={
            TOOL_MAPPING: [{"table": 0}],
            TOOL_SPEC: [{"shortfall_weight": 100}, {"shortfall_weight": 200}],
        }
    )
    spec1 = llm.complete(size="small", messages=[], tool_schema=tool(TOOL_SPEC), run_id="r1")
    mapping = llm.complete(size="large", messages=[], tool_schema=tool(TOOL_MAPPING), run_id="r1")
    spec2 = llm.complete(size="small", messages=[], tool_schema=tool(TOOL_SPEC), run_id="r1")
    assert mapping.tool_args == {"table": 0}
    assert (spec1.tool_args, spec2.tool_args) == ({"shortfall_weight": 100}, {"shortfall_weight": 200})
    assert [c["tool_name"] for c in llm.calls] == [TOOL_SPEC, TOOL_MAPPING, TOOL_SPEC]
    # fila da ferramenta vazia: cai na fila geral e, depois, no padrão (sem ferramenta)
    fallback = llm.complete(size="small", messages=[], tool_schema=tool(TOOL_SPEC), run_id="r1")
    assert fallback.tool_args is None and fallback.content == "resposta falsa"


def test_fake_llm_by_tool_accepts_llm_results_and_keeps_the_general_queue():
    from escalista.domain.contracts import LLMResult

    justify = LLMResult(tool_args={"summary": "s", "items": []}, model="m", key_index=1)
    llm = FakeLLMClient([LLMResult(content="geral", model="m")], by_tool={TOOL_JUSTIFY: [justify]})
    assert llm.complete(size="small", messages=[], tool_schema=tool(TOOL_JUSTIFY), run_id="r1") == justify
    assert llm.complete(size="small", messages=[], tool_schema=tool(TOOL_MAPPING), run_id="r1").content == "geral"


def test_fake_llm_fails_only_on_the_given_tools():
    from escalista.domain.contracts import LLMUnavailableError

    llm = FakeLLMClient(by_tool={TOOL_JUSTIFY: [{"summary": "s", "items": []}]}, fail_tools={TOOL_MAPPING})
    with pytest.raises(LLMUnavailableError) as exc:
        llm.complete(size="large", messages=[], tool_schema=tool(TOOL_MAPPING), run_id="r1", parent_id="p1")
    assert exc.value.card.code == "RX-12" and exc.value.card.trace_id == "p1"
    assert llm.complete(size="small", messages=[], tool_schema=tool(TOOL_JUSTIFY), run_id="r1").tool_args
    assert len(llm.calls) == 2  # a chamada que falhou também fica registrada


def test_spec_json_schema_requires_type_and_has_no_dangling_mapping():
    """O schema da ferramenta `registrar_especificacao` exige `type` em cada item e não aponta para `$defs` soltos."""
    schema = SolveSpec.model_json_schema()
    assert "discriminator" not in schema["properties"]["constraints"]["items"]
    for name in ("UnavailableConstraint", "MaxWeeklyHoursConstraint", "PreferredDayOffConstraint"):
        assert schema["$defs"][name]["required"][0] == "type"
        assert schema["$defs"][name]["additionalProperties"] is False
    assert schema["additionalProperties"] is False
