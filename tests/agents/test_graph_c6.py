"""Agente na C6 (B4a): nó 1 `ler_e_padronizar` com as bordas reais (leitor de tabelas, cadastro simulado, prompts de
mapeamento e de formulação amarrados ao `FakeLLMClient`), reserva sem modelo, identidade, confirmação que grava o
`Roster`, publicação e a continuidade (`start_next_week`) sem upload. O nó 2 e o laço do solver (B4b) estão em
`test_graph_c6_formulate.py`, com este mesmo `C6Harness`.

Os arquivos pequenos do E2 (até 8 pessoas) rodam o solver em menos de 1 s; o exemplo de 60 pessoas com solver é
`slow`.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from functools import partial
from pathlib import Path

import pytest

from escalista.agents.optimizer.errors import RunPhaseError
from escalista.agents.optimizer.graph import OptimizerAgent, _line_text
from escalista.agents.optimizer.tools import NO_MODEL
from escalista.api.wiring import SliceAgent, SliceAgentC6
from escalista.domain.contracts import Role
from escalista.domain.reading import ConfirmInput, IdentityAnswer
from escalista.domain.results import Approval, RunState
from escalista.domain.schedule import CsvIssue, EmployeePublic
from escalista.ingest.cadastro import enrich, load_cadastro
from escalista.ingest.tables import read_tables
from escalista.llm.prompts.formulate import formulate
from escalista.llm.prompts.justify import make_justifier
from escalista.llm.prompts.map_columns import propose_mapping
from escalista.rules.header_aliases import guess_mapping
from escalista.rules.loader import load_rule_card_for_week
from escalista.rules.mapping import check_mapping
from escalista.rules.spec import default_spec
from escalista.rules.week import shift_schedule
from tests.agents.support import DEMO_DIR, GOOD_JUSTIFICATION, NOW, RULES_DIR
from tests.fakes import (
    TOOL_JUSTIFY,
    TOOL_MAPPING,
    TOOL_SPEC,
    FakeLLMClient,
    FixedClock,
    InMemoryRepository,
    ListTraceSink,
)

E2_DIR = DEMO_DIR / "e2"
EXAMPLE = DEMO_DIR / "escala_exemplo_grade.xlsx"
GRID = E2_DIR / "e2-02-grade-horario.xlsx"  # 8 pessoas, 1 loja, 48 turnos
LONG = E2_DIR / "e2-01-csv-cp1252.csv"  # 8 pessoas, 2 lojas, 48 turnos
IDENTITY = E2_DIR / "e2-08-identidade.csv"  # homônimo em duas lojas e grafia parecida
DUPLICATES = E2_DIR / "e2-07-duplicatas.csv"  # 36 turnos e 6 linhas duplicadas
DEFECT = DEMO_DIR / "escala_defeito.csv"  # hora ilegível (48), turno sobreposto (59), fim vazio (69)
FILE_WEEK = date(2027, 1, 11)
NOTE = "a Ana Souza está de férias na quarta"


def model_mapping(path: Path) -> dict:
    """Um mapeamento válido para o falso devolver: o da heurística para o mesmo arquivo."""
    mapping = guess_mapping(read_tables(path.name, path.read_bytes()).tables)
    assert mapping is not None
    return mapping.model_dump(mode="json")


class C6Harness:
    """Agente no modo C6 com as bordas reais e o modelo falso (mapeamento, formulação e justificativa por ferramenta).

    `formulate_spec` é o `formulate` real amarrado ao falso (o que o wiring da C3-bis vai ligar); `with_formulate=False`
    reproduz o wiring de hoje (sem formulação: especificação padrão, sem aviso)."""

    def __init__(
        self,
        *,
        mappings: list[dict] | None = None,
        specs: list[dict] | None = None,
        fail_mapping: bool = False,
        fail_spec: bool = False,
        with_model: bool = True,
        with_formulate: bool = True,
        repo: InMemoryRepository | None = None,
        sink: ListTraceSink | None = None,
        time_limit_s: float = 10.0,
    ) -> None:
        self.repo = repo or InMemoryRepository()
        self.sink = sink or ListTraceSink()
        self.clock = FixedClock(NOW)
        failing = {TOOL_MAPPING} if fail_mapping else set()
        if fail_spec:
            failing.add(TOOL_SPEC)
        self.llm = FakeLLMClient(
            by_tool={TOOL_MAPPING: mappings or [], TOOL_SPEC: specs or [], TOOL_JUSTIFY: [GOOD_JUSTIFICATION] * 10},
            fail_tools=failing,
        )

        def map_columns(tables, run_id, parent_id):  # o que o wiring da C3 vai ligar
            return propose_mapping(self.llm, tables, run_id=run_id, parent_id=parent_id, check=check_mapping)

        self.agent = OptimizerAgent(
            repo=self.repo,
            sink=self.sink,
            clock=self.clock,
            justify=make_justifier(self.llm),
            list_events=self.events,
            read_tables=read_tables,
            map_columns=map_columns if with_model else None,
            cadastro=load_cadastro(DEMO_DIR),
            enrich=enrich,
            load_card=partial(load_rule_card_for_week, RULES_DIR),
            formulate_spec=partial(formulate, self.llm) if with_formulate else None,
            seed=42,
            time_limit_s=time_limit_s,
            num_workers=1,
        )

    def events(self, run_id: str):
        return [e for e in self.sink.events if e.run_id == run_id]

    def kinds(self, run_id: str) -> list[str]:
        return [e.kind for e in self.events(run_id)]

    def event(self, run_id: str, kind: str):
        [found] = [e for e in self.events(run_id) if e.kind == kind]
        return found

    def read(self, path: Path) -> RunState:
        return self.agent.start_run(path.name, path.read_bytes())

    def approval(self, version_id: str):
        return Approval(
            id=f"apr-{version_id}", version_id=version_id, approved_by="demo-gestor", role=Role.GESTOR, at=NOW
        )

    def publish(self, state: RunState) -> RunState:
        assert state.phase == "awaiting_approval", state.exception
        done = self.agent.approve(state.run_id, self.approval(state.version_id))
        assert done.phase == "published"
        return done


def _read_ok(h: C6Harness, path: Path) -> RunState:
    state = h.read(path)
    assert state.phase == "awaiting_confirm", state.exception
    return state


# --- leitura ------------------------------------------------------------------------------------------------------


def test_example_xlsx_with_model_reads_and_waits_for_confirmation() -> None:
    h = C6Harness(mappings=[model_mapping(EXAMPLE)])

    state = _read_ok(h, EXAMPLE)

    s = state.summary
    assert state.exception is None and state.notices == []
    assert state.mode == "upload" and state.week_start == FILE_WEEK
    assert s.format == "xlsx" and s.mapping_source == "modelo" and s.mapping is not None
    assert s.ok and s.rows == 360 and s.employees == 60 and s.stores == 3
    assert s.week_start == FILE_WEEK and s.planned_week_start == FILE_WEEK
    assert len(s.store_ids) == 3 and len(s.evidence_sample) == 5 and s.issues == [] and s.identity == []
    # demanda com o horário das lojas do cadastro simulado (08h às 22h); com o horário inferido do arquivo seria 2.777
    assert s.capacity.demand_person_hours == Decimal("2774.50")
    assert s.capacity.capacity_person_hours == Decimal("2400")
    assert not s.capacity.fits and s.capacity.max_fitting_pct == 80
    assert any("cadastro simulado" in a for a in s.assumptions)
    assert [c["tool_name"] for c in h.llm.calls] == [TOOL_MAPPING]
    stored = h.repo.get_run(state.run_id)
    assert stored == state and len(stored.before.shifts) == 360  # o "antes" é persistido
    assert h.kinds(state.run_id) == [
        "ingest.parse",
        "ingest.apply_mapping",
        "identity.cards",
        "demand.inferred",
        "read.summary",
    ]
    applied = h.event(state.run_id, "ingest.apply_mapping").payload
    assert applied["source"] == "modelo" and applied["shifts"] == 360 and applied["invented"] == 0
    assert h.event(state.run_id, "ingest.parse").payload["format"] == "xlsx"
    assert h.agent.get_schedule(state.run_id) is None
    assert len(h.agent.employees(state.run_id)) == 60


@pytest.mark.parametrize(
    ("kwargs", "reason_part"),
    [
        ({"fail_mapping": True}, "não conseguiu mapear"),
        ({"mappings": [{"table": 0}] * 3}, "não conseguiu mapear"),  # saída inválida 3 vezes
        ({"with_model": False}, "não está configurado"),
    ],
    ids=["modelo-fora", "saida-invalida", "sem-modelo"],
)
def test_without_the_model_reads_by_heuristic_with_rx12_notice(kwargs, reason_part) -> None:
    h = C6Harness(**kwargs)

    state = _read_ok(h, LONG)

    assert state.exception is None
    assert state.summary.mapping_source == "heuristica" and state.summary.rows == 48
    [notice] = state.notices
    assert notice.code == "RX-12" and reason_part in notice.reason
    kinds = h.kinds(state.run_id)
    assert kinds[:3] == ["ingest.parse", "ingest.fallback", "exception.raised"]
    fallback = h.event(state.run_id, "ingest.fallback").payload
    assert fallback["from"] == "modelo" and fallback["to"] == "heuristica"
    assert notice.trace_id == h.event(state.run_id, "exception.raised").id


@pytest.mark.parametrize(
    "name",
    ["e2-11a-macro.xlsm", "e2-11b-corrompido.xlsx", "e2-11c-zip-bomba.xlsx", "e2-11d-pdf-sem-tabela.pdf"],
)
def test_unreadable_file_fails_with_rx13(name: str) -> None:
    h = C6Harness()

    state = h.read(E2_DIR / name)

    assert state.phase == "failed" and state.exception.code == "RX-13"
    assert h.kinds(state.run_id) == ["ingest.parse", "exception.raised"]
    assert h.llm.calls == []  # o modelo nem é chamado
    with pytest.raises(RunPhaseError):
        h.agent.confirm(state.run_id)


def test_unrecognized_columns_fail_with_rx13_and_the_model_notice() -> None:
    h = C6Harness(fail_mapping=True)
    content = b"coluna a;coluna b\nx;y\nz;w\n"

    state = h.agent.start_run("planilha.csv", content)

    assert state.phase == "failed" and state.exception.code == "RX-13"
    assert "colunas" in state.exception.reason
    assert "não parece uma escala de trabalho" in state.exception.reason
    assert [n.code for n in state.notices] == ["RX-12"]


def test_restart_between_read_and_confirm_asks_for_the_file_again() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    state = _read_ok(h, GRID)
    restarted = C6Harness(repo=h.repo, sink=h.sink)  # mesmo banco, memória nova

    assert restarted.repo.get_run(state.run_id).before is not None  # persistido mesmo assim
    with pytest.raises(RunPhaseError, match="envie o arquivo de novo"):
        restarted.agent.confirm(state.run_id)


def test_problem_lines_raise_rx13_notice_and_the_read_still_waits_for_confirmation() -> None:
    """RX-13 (requisitos): dado inconsistente vira exceção ao gestor com o motivo. Com turnos válidos, o cartão vai em
    `notices` (não bloqueia) e o resumo fica `ok=False`; o gestor corrige o arquivo ou confirma só as linhas boas."""
    h = C6Harness(mappings=[model_mapping(DEFECT)])

    state = _read_ok(h, DEFECT)

    assert state.exception is None
    assert {i.line for i in state.summary.issues} >= {48, 59, 69}
    [notice] = state.notices
    assert notice.code == "RX-13" and notice.decider == Role.GESTOR
    assert notice.title == "A escala tem linhas com problema"
    assert f"{len(state.summary.issues)} problema(s)" in notice.reason
    assert "confirme para seguir só com as linhas válidas" in notice.recommendation and notice.if_no_answer
    assert [e.split(":")[0] for e in notice.evidence] == ["linha 48, inicio", "linha 59, turno", "linha 69, fim"]
    names = {p.name for p in h.agent.employees(state.run_id)}
    assert names and not any(name in e or "sintético" in e for e in notice.evidence for name in names)
    kinds = h.kinds(state.run_id)
    assert kinds[-2:] == ["exception.raised", "read.summary"]
    assert notice.trace_id == h.event(state.run_id, "exception.raised").id
    assert h.event(state.run_id, "read.summary").payload["notices"] == ["RX-13"]


def test_confirm_after_the_rx13_notice_follows_with_the_valid_lines() -> None:
    h = C6Harness(mappings=[model_mapping(DUPLICATES)])
    read = _read_ok(h, DUPLICATES)
    [notice] = read.notices
    assert notice.code == "RX-13" and len(notice.evidence) == 6
    assert all(e.startswith("linha ") and "duplicada da linha" in e for e in notice.evidence)

    state = h.agent.confirm(read.run_id)

    assert state.phase == "awaiting_approval", state.exception
    assert len(state.before.shifts) == read.summary.rows == 36
    assert "RX-13" in [n.code for n in state.notices]  # o aviso da leitura segue visível


def test_rx13_evidence_never_names_the_person() -> None:
    reason = "turno de 'Ana Souza' (n-ana-souza) sobreposto a outro da mesma pessoa (linha 9)"
    overlap = CsvIssue(line=12, field="pessoa", col=1, reason=reason)
    too_many = CsvIssue(line=20, field="turno", reason="mais de 2 turnos de Ana Souza em 12/01/2027")
    plain = CsvIssue(line=5, reason="Ana Souza sem loja")

    texts = [_line_text(i, {"Ana Souza"}) for i in (overlap, too_many, plain)]

    assert texts == [
        "linha 12, pessoa: turno sobreposto a outro da mesma pessoa (linha 9)",
        "linha 20, turno: mais de 2 turnos da mesma pessoa em 12/01/2027",
        "linha 5: a pessoa sem loja",
    ]


# --- identidade ---------------------------------------------------------------------------------------------------


def test_pending_homonym_blocks_confirmation_until_answered() -> None:
    h = C6Harness(mappings=[model_mapping(IDENTITY)])
    state = _read_ok(h, IDENTITY)
    cards = {c.kind: c for c in state.summary.identity}
    assert set(cards) == {"homonimo", "grafia_parecida"}
    pending = h.event(state.run_id, "identity.cards").payload
    assert pending["pending"] is True and pending["by_kind"] == {"grafia_parecida": 1, "homonimo": 1}

    with pytest.raises(RunPhaseError, match="homônimo"):
        h.agent.confirm(state.run_id)
    with pytest.raises(RunPhaseError, match="homônimo"):
        h.agent.confirm(state.run_id, ConfirmInput(identity=[IdentityAnswer(card_id=cards["grafia_parecida"].id,
                                                                             same=True)]))  # fmt: skip
    assert h.repo.get_run(state.run_id).phase == "awaiting_confirm"
    assert h.repo.latest_roster() is None

    answers = [
        IdentityAnswer(card_id=cards["homonimo"].id, same=False),
        IdentityAnswer(card_id=cards["grafia_parecida"].id, same=True),
    ]
    done = h.agent.confirm(state.run_id, ConfirmInput(identity=answers))

    assert done.phase == "awaiting_approval" and done.report.total == 0
    roster = h.repo.latest_roster()
    # 5 grupos lidos: o homônimo vira 2 pessoas (uma por loja) e as duas grafias da Ana viram 1
    assert len(roster.employees) == 5
    assert len([e for e in roster.employees if e.id.startswith("n-bruno-lima")]) == 2
    confirmed = h.event(state.run_id, "read.confirmed").payload
    assert confirmed["identity_answers"] == 2 and confirmed["identity_same"] == 1


# --- confirmação, quadro e publicação ----------------------------------------------------------------------------


def test_confirmation_saves_roster_v1_and_approval_publishes() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    read = _read_ok(h, GRID)

    state = h.agent.confirm(read.run_id)

    assert state.phase == "awaiting_approval" and state.report.total == 0
    assert state.roster_version == 1 and state.week_start == FILE_WEEK and state.spec == default_spec()
    roster = h.agent.roster()
    assert roster == h.repo.get_roster(1)
    assert roster.version == 1 and roster.source_run_id == read.run_id
    assert roster.confirmed_by == "gestor" and roster.confirmed_at == NOW
    assert len(roster.employees) == 8 and len(roster.stores) == 1 and roster.demand
    assert all(e.sex is None for e in roster.employees)
    assert state.comparison.before.violations >= 0 and state.justification is not None
    kinds = h.kinds(read.run_id)
    assert kinds[kinds.index("read.summary") + 1 :][:5] == [
        "read.confirmed",
        "roster.saved",
        "llm.formulate",
        "spec.validate",
        "solver.run",
    ]
    assert h.event(read.run_id, "roster.saved").payload["version"] == 1

    done = h.publish(state)

    assert h.agent.published().run_id == done.run_id
    assert h.agent.published().schedule.week_start == FILE_WEEK


def test_confirm_input_scales_demand_moves_the_week_and_keeps_the_note_out_of_the_trace() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    read = _read_ok(h, GRID)
    [store_id] = read.summary.store_ids
    planned = FILE_WEEK + timedelta(weeks=1)
    data = ConfirmInput(coverage_pct={store_id: 80}, planned_week_start=planned, note=NOTE,
                        hourly_wage_default=Decimal("13.50"))  # fmt: skip

    state = h.agent.confirm(read.run_id, data)

    assert state.phase == "awaiting_approval", state.exception
    assert state.week_start == planned and state.summary.planned_week_start == planned
    assert state.before.week_start == planned
    assert state.before == shift_schedule(read.before, 1)
    assert h.agent.get_schedule(read.run_id).week_start == planned
    full_slots = read.summary.capacity.demand_person_hours * 2  # pessoa-faixa de 30 min, a 100%
    scaled = sum(p.required for p in h.agent.roster().demand)
    assert 0.8 * float(full_slots) <= scaled < full_slots  # 80% por faixa, arredondado para cima
    confirmed = h.event(read.run_id, "read.confirmed").payload
    assert confirmed["coverage_pct"] == {store_id: 80} and confirmed["week_changed"] is True
    assert confirmed["has_note"] is True and confirmed["hourly_wage_default"] == "13.50"
    trace = json.dumps([e.model_dump(mode="json") for e in h.events(read.run_id)], ensure_ascii=False)
    assert NOTE not in trace and "Ana Souza" not in trace


def test_no_sex_or_names_in_trace_and_people_as_public() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    read = _read_ok(h, GRID)
    state = h.agent.confirm(read.run_id)
    h.publish(state)

    names = [e.name for e in h.agent.roster().employees]
    trace = json.dumps([e.model_dump(mode="json") for e in h.agent.trace(read.run_id)], ensure_ascii=False)
    assert '"sex"' not in trace and not any(name in trace for name in names)
    people = h.agent.employees(read.run_id)
    assert len(people) == 8 and all(isinstance(p, EmployeePublic) for p in people)
    assert '"sex"' not in json.dumps([p.model_dump(mode="json") for p in people])
    for e in h.agent.trace(read.run_id):
        if e.kind == "llm.formulate":  # sem pedido: o nó 2 não chama o modelo
            assert e.cost_usd == Decimal(0) and e.payload["cost_basis"] == "sem entrada para o modelo"
        elif e.kind != "llm.justify":
            assert e.cost_usd == Decimal(0) and e.payload["cost_basis"] == NO_MODEL


# --- continuidade -------------------------------------------------------------------------------------------------


def test_next_week_without_publication_or_roster_is_refused() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    with pytest.raises(RunPhaseError, match="envie a primeira escala"):
        h.agent.start_next_week()

    read = _read_ok(h, GRID)
    h.agent.confirm(read.run_id)  # quadro gravado, nada publicado
    assert h.agent.roster() is not None
    with pytest.raises(RunPhaseError, match="envie a primeira escala"):
        h.agent.start_next_week()


def test_next_week_plans_without_upload_and_publishes_twice() -> None:
    h = C6Harness(mappings=[model_mapping(LONG)])
    first = h.agent.confirm(_read_ok(h, LONG).run_id)
    h.publish(first)
    published = h.agent.published()

    h.clock.set(NOW + timedelta(days=7))
    nxt = h.agent.start_next_week()

    assert nxt.phase == "awaiting_confirm" and nxt.mode == "continuidade"
    assert nxt.week_start == FILE_WEEK + timedelta(weeks=1) and nxt.roster_version == 1
    assert nxt.before == shift_schedule(published.schedule, 1)
    s = nxt.summary
    assert s.format == "continuidade" and s.mapping_source == "plataforma" and s.mapping is None
    assert s.file_name == "última escala publicada (semana de 11/01)"
    assert s.planned_week_start == nxt.week_start and s.capacity is not None and len(s.store_ids) == 2
    assert h.repo.get_run(nxt.run_id) == nxt
    assert h.kinds(nxt.run_id) == ["run.next_week"]
    assert h.event(nxt.run_id, "run.next_week").payload["from_version_id"] == published.id
    assert len(h.agent.employees(nxt.run_id)) == 8

    confirmed = h.agent.confirm(nxt.run_id)

    assert confirmed.phase == "awaiting_approval" and confirmed.report.total == 0
    assert h.agent.roster().version == 1  # a continuidade não grava quadro novo
    assert h.event(nxt.run_id, "solver.run").payload["hint_shifts"] == len(nxt.before.shifts) > 0
    assert h.event(nxt.run_id, "read.confirmed").payload["mode"] == "continuidade"
    h.clock.set(NOW + timedelta(days=8))
    h.publish(confirmed)
    assert h.agent.published().schedule.week_start == FILE_WEEK + timedelta(weeks=1)

    h.clock.set(NOW + timedelta(days=14))
    third = h.agent.start_next_week()
    assert third.week_start == FILE_WEEK + timedelta(weeks=2)
    assert third.summary.file_name == "última escala publicada (semana de 18/01)"


def test_next_week_coverage_change_saves_a_new_roster_version() -> None:
    h = C6Harness(mappings=[model_mapping(GRID)])
    h.publish(h.agent.confirm(_read_ok(h, GRID).run_id))
    h.clock.set(NOW + timedelta(days=7))
    nxt = h.agent.start_next_week()
    [store_id] = nxt.summary.store_ids

    state = h.agent.confirm(nxt.run_id, ConfirmInput(coverage_pct={store_id: 90}, planned_week_start=date(2027, 2, 1)))

    assert state.phase == "awaiting_approval"
    assert state.roster_version == 2 and h.agent.roster().version == 2
    assert h.agent.roster().source_run_id == nxt.run_id
    assert state.week_start == nxt.week_start  # a semana não muda na continuidade
    assert h.event(nxt.run_id, "read.confirmed").payload["ignored"] == ["planned_week_start"]
    assert h.event(nxt.run_id, "roster.saved").payload["version"] == 2


def test_agent_in_c6_mode_satisfies_the_api_protocols() -> None:
    agent = C6Harness().agent
    assert isinstance(agent, SliceAgent) and isinstance(agent, SliceAgentC6)


# --- exemplo da demo com solver (60 pessoas) ---------------------------------------------------------------------


@pytest.mark.slow
def test_example_xlsx_full_flow_publishes_without_violations() -> None:
    h = C6Harness(mappings=[model_mapping(EXAMPLE)], time_limit_s=30.0)
    read = _read_ok(h, EXAMPLE)

    state = h.agent.confirm(read.run_id)

    assert state.phase == "awaiting_approval", state.exception
    assert state.report.total == 0 and state.comparison.before.violations > 0
    assert [n.code for n in state.notices] == ["RX-02"]  # a demanda inferida não cabe no quadro sob 42h
    h.publish(state)
    assert h.agent.roster().version == 1 and len(h.agent.roster().employees) == 60
