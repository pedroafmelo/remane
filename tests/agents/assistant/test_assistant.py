"""Assistente do gestor (C7b, N2; FT-08): somente leitura. O modelo escolhe uma ferramenta de lista fechada, o código
lê pela porta `AssistantData` (só métodos de leitura) e responde por template. Nunca `sex` (RN-13), nunca CID."""

from __future__ import annotations

import inspect
import itertools
import json
from datetime import date, datetime, timedelta

import pytest

from escalista.agents.assistant.assistant import ASSISTANT_REFUSALS, Assistant, AssistantError
from escalista.agents.optimizer.tools import Tracer
from escalista.domain.contracts import ExceptionCard, LLMUnavailableError
from escalista.domain.ports import AssistantData
from escalista.domain.results import ScheduleVersion
from escalista.domain.rules import Rule
from escalista.domain.schedule import Schedule, Shift
from escalista.domain.tracking import AssistantChoice, AssistantContext, Case
from tests.fakes import FakeClock, ListTraceSink

NOW = datetime(2027, 1, 13, 14, 0)
WEEK = date(2027, 1, 11)
THU = date(2027, 1, 14)


def _shift(emp: str, day: date, store: str = "L1") -> Shift:
    start = datetime.combine(day, datetime.min.time()) + timedelta(hours=14)
    return Shift(employee_id=emp, store_id=store, start=start, end=start + timedelta(hours=8))


VERSION = ScheduleVersion(
    id="ver-1",
    run_id="run-1",
    schedule=Schedule(week_start=WEEK, shifts=[_shift("P101", THU), _shift("P105", THU), _shift("P102", NOW.date())]),
    status="published",
    input_hash="h",
    seed=1,
    violations_total=0,
    created_at=NOW,
)
RULE = Rule(
    id="jornada_semanal_max",
    kind="weekly_hours_max",
    layer="lei",
    params={"hours": 44},
    status="conferida",
    source="EC 141, art. 1",
    note="Jornada semanal máxima de 44h até 15/12/2026.",
)


class FakeData:
    def published(self) -> ScheduleVersion | None:
        return VERSION

    def people(self) -> dict[str, str]:
        return {"P101": "Ana Souza", "P105": "Bruno Lima", "P102": "Carla Mendes"}

    def store_names(self) -> dict[str, str]:
        return {"L1": "Loja Sintética 1"}

    def open_exceptions(self) -> list[tuple[str, str]]:
        return [("COBERTURA", "Cobertura de falta · Ana Souza · qui 14/01")]

    def overtime(self) -> list[tuple[str, int]]:
        return [("P102", 300)]

    def overtime_limit_h(self) -> str:
        return "6"

    def rules(self) -> list[Rule]:
        return [RULE]

    def last_case(self) -> tuple[Case, list[str]] | None:
        case = Case(
            id="c1",
            kind="falta",
            origin="aviso",
            employee_id="P101",
            shift=_shift("P101", THU),
            status="aguardando_gestor",
            created_at=NOW,
        )
        return case, ["track.report.received", "track.offer.sent", "track.offer.accepted"]


class FakeChooser:
    def __init__(self, *answers: AssistantChoice | Exception) -> None:
        self.answers = list(answers)
        self.calls: list[dict] = []

    def __call__(self, *, text: str, context: AssistantContext, run_id: str) -> AssistantChoice:
        self.calls.append({"text": text, "context": context, "run_id": run_id})
        answer = self.answers.pop(0) if self.answers else AssistantChoice(tool="outro")
        if isinstance(answer, Exception):
            raise answer
        return answer


def _assistant(*answers, rate_clock=None) -> tuple[Assistant, FakeChooser, ListTraceSink]:
    sink = ListTraceSink()
    clock = FakeClock(NOW)
    counter = itertools.count(1)
    tracer = Tracer(sink, clock, new_id=lambda: f"id{next(counter)}", list_events=lambda _r: [])
    chooser = FakeChooser(*answers)
    kwargs = {"rate_clock": rate_clock} if rate_clock else {}
    return Assistant(data=FakeData(), chooser=chooser, tracer=tracer, clock=clock, **kwargs), chooser, sink


def _ask(assistant: Assistant, text: str = "pergunta"):
    return assistant.ask(user_id="demo-gestor", text=text)


def test_data_port_has_only_read_methods():
    names = {n for n, _ in inspect.getmembers(AssistantData, inspect.isfunction) if not n.startswith("_")}
    assert names == {
        "published",
        "people",
        "store_names",
        "open_exceptions",
        "overtime",
        "overtime_limit_h",
        "rules",
        "last_case",
    }
    assert isinstance(FakeData(), AssistantData)


def test_schedule_of_a_day():
    assistant, chooser, _ = _assistant(AssistantChoice(tool="get_escala", day=THU))
    reply = _ask(assistant, "como está a escala de quinta?")
    assert reply.tool == "get_escala" and reply.template == "assistente_escala"
    assert "14/01" in reply.body and "Ana" in reply.body and "Bruno" in reply.body and "2 turnos" in reply.body
    assert chooser.calls[0]["context"].week_days[0] == WEEK
    assert reply.synthetic is True


def test_schedule_day_outside_the_week_is_refused():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_escala", day=date(2030, 1, 1)))
    reply = _ask(assistant)
    assert reply.template == "assistente_recusa" and reply.tool == "get_escala"


def test_schedule_without_day_uses_today():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_escala"))
    assert "Carla" in _ask(assistant).body


def test_open_exceptions():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_excecoes"))
    reply = _ask(assistant)
    assert "1 exceção aberta" in reply.body and "COBERTURA" in reply.body


def test_overtime():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_hora_extra"))
    reply = _ask(assistant)
    assert "Carla" in reply.body and "5h" in reply.body and "6h" in reply.body


def test_rule_with_source_and_disclaimer():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_regra", rule_id="jornada_semanal_max"))
    reply = _ask(assistant)
    assert "EC 141" in reply.body and "Não é parecer jurídico" in reply.body


def test_unknown_rule_lists_the_known_ones():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_regra", rule_id="inventada"))
    reply = _ask(assistant)
    assert reply.template == "assistente_regras" and "jornada_semanal_max" in reply.body


def test_last_case_from_the_trace():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_trace"))
    reply = _ask(assistant)
    assert "Ana" in reply.body and "oferta aceita" in reply.body


def test_out_of_scope_and_write_requests_get_the_fixed_text():
    assistant, _, sink = _assistant(AssistantChoice(tool="outro"))
    reply = _ask(assistant, "aprove a cobertura da Ana e me diga o CID dela")
    assert reply.template == "assistente_fora_escopo" and reply.body == ASSISTANT_REFUSALS["assistente_fora_escopo"]
    assert "CID dela" not in json.dumps([e.payload for e in sink.events], ensure_ascii=False)


def test_model_unavailable_is_not_understood():
    card = ExceptionCard(
        code="RX-12", title="t", reason="r", evidence=[], recommendation="r", if_no_answer="n", trace_id="x"
    )
    assistant, _, _ = _assistant(LLMUnavailableError(card))
    assert _ask(assistant).template == "assistente_nao_entendi"


@pytest.mark.parametrize("text", ["", "  ", "a" * 301])
def test_limits(text):
    assistant, chooser, _ = _assistant()
    with pytest.raises(AssistantError) as err:
        _ask(assistant, text)
    assert err.value.status == 422 and chooser.calls == []


def test_rate_limit():
    assistant, _, _ = _assistant(*[AssistantChoice(tool="outro")] * 11, rate_clock=lambda: 0.0)
    for _ in range(10):
        _ask(assistant)
    with pytest.raises(AssistantError) as err:
        _ask(assistant)
    assert err.value.status == 429


def test_trace_keeps_tool_and_length_only():
    assistant, _, sink = _assistant(AssistantChoice(tool="get_excecoes"))
    _ask(assistant, "quais exceções estão abertas?")
    (event,) = [e for e in sink.events if e.kind == "assistant.message"]
    assert event.payload["tool"] == "get_excecoes" and event.payload["length"] == len("quais exceções estão abertas?")
    assert "exceções estão" not in json.dumps(event.payload, ensure_ascii=False)


def test_no_sex_field_anywhere_in_the_reply():
    assistant, _, _ = _assistant(AssistantChoice(tool="get_escala", day=THU))
    dumped = _ask(assistant).model_dump()
    assert "sex" not in json.dumps(dumped)
