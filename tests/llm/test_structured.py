"""Saída estruturada e justificativa: `FakeLLMClient`, sem rede e sem `.env`."""

from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import BaseModel

from escalista.domain.contracts import LLMResult, LLMUnavailableError
from escalista.domain.results import Comparison, Justification, ScheduleMetrics, Violation, ViolationReport
from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import DemandSlot
from escalista.llm.prompts.justify import KIND, TOOL_NAME, JustifyFacts, justify
from escalista.llm.structured import MAX_RESENDS, call_structured, tool_schema_for
from tests.fakes import FakeLLMClient

CARD = RuleCard(
    reference_date=date(2026, 12, 16),
    rules=[
        Rule(
            id="jornada_semanal_max",
            kind="max_weekly_hours",
            layer=RuleLayer.LEI,
            params={"horas": 42},
            status=RuleStatus.INTERPRETACAO,
            source="art. 6º, I, EC 141",
        ),
        Rule(
            id="hora_extra_autorizacao_dp",
            kind="info",
            layer=RuleLayer.POLITICA,
            status=RuleStatus.FICTICIA,
            source="política fictícia da demo",
        ),
    ],
)


def metrics(cost: str, ot: str, viol: int) -> ScheduleMetrics:
    return ScheduleMetrics(
        total_cost=Decimal(cost),
        regular_hours=Decimal("400"),
        overtime_hours=Decimal(ot),
        overtime_cost=Decimal("10"),
        coverage_pct=98.5,
        uncovered_slots=1,
        violations=viol,
    )


FACTS = JustifyFacts(
    comparison=Comparison(
        before=metrics("1000", "30", 4),
        after=metrics("900", "5", 0),
        savings=Decimal("100"),
        overtime_hours_avoided=Decimal("25"),
        violations_avoided=4,
    ),
    report=ViolationReport(
        violations=[
            Violation(
                rule_id="jornada_semanal_max",
                kind="max_weekly_hours",
                employee_id="E-007",
                day=date(2026, 12, 16),
                source="art. 6º",
                detail="Fulana de Tal passou de 42h",
            )
        ]
    ),
    status="feasible",
    uncovered=[DemandSlot(store_id="L1", day=date(2026, 12, 16), start=time(9, 0), required=1)],
)

GOOD = {
    "summary": "A escala nova cumpre a jornada de 42h e reduz o custo.",
    "items": [{"text": "Jornada semanal respeitada.", "rule_refs": ["jornada_semanal_max"]}],
}
BAD_REF = {"summary": "Resumo.", "items": [{"text": "Cita regra inventada.", "rule_refs": ["regra_inventada"]}]}


def result(args: dict | None, content: str | None = None) -> LLMResult:
    return LLMResult(content=content, tool_args=args, model="fake", key_index=1)


def run(client: FakeLLMClient) -> Justification:
    return justify(client, card=CARD, facts=FACTS, run_id="r1", parent_id="p1")


def test_justify_success_first_try() -> None:
    client = FakeLLMClient([result(GOOD)])
    value = run(client)
    assert value == Justification.model_validate(GOOD)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["size"] == "small" and call["run_id"] == "r1" and call["parent_id"] == "p1"
    assert call["tool_schema"]["function"]["name"] == TOOL_NAME


def test_invalid_rule_ref_resends_then_rx12() -> None:
    client = FakeLLMClient([result(BAD_REF)] * 3)
    with pytest.raises(LLMUnavailableError) as exc:
        run(client)
    assert len(client.calls) == MAX_RESENDS + 1 == 3
    card = exc.value.card
    assert card.code == "RX-12"
    assert len(card.evidence) == 3 and "regra_inventada" in card.evidence[0]
    assert card.trace_id == "p1"


def test_success_on_second_attempt_after_invalid_ref() -> None:
    client = FakeLLMClient([result(BAD_REF), result(GOOD)])
    assert run(client) == Justification.model_validate(GOOD)
    assert len(client.calls) == 2
    resend = client.calls[1]["messages"]
    assert resend[-1].role == "user" and "regra_inventada" in resend[-1].content
    assert "jornada_semanal_max" in resend[-1].content  # lembra os ids válidos
    assert len(resend) == len(client.calls[0]["messages"]) + 1  # a conversa original + o motivo, sem acumular


@pytest.mark.parametrize(
    "first",
    [
        result(None, content="texto livre sem ferramenta"),
        result({"summary": "falta items"}),
        result({"summary": "x", "items": "não é lista"}),
        result({"summary": "  ", "items": [{"text": "a", "rule_refs": []}]}),
        result({"summary": "ok", "items": []}),
    ],
)
def test_missing_tool_or_invalid_json_resends(first: LLMResult) -> None:
    client = FakeLLMClient([first, result(GOOD)])
    assert run(client) == Justification.model_validate(GOOD)
    assert len(client.calls) == 2


def test_free_text_never_replaces_the_tool_output() -> None:
    client = FakeLLMClient([result(None, content="Aqui está sua justificativa em texto livre.")] * 3)
    with pytest.raises(LLMUnavailableError) as exc:
        run(client)
    assert len(client.calls) == 3
    assert "texto livre" not in exc.value.card.model_dump_json()


def test_llm_failure_yields_rx12_not_text() -> None:
    client = FakeLLMClient(fail=True)
    with pytest.raises(LLMUnavailableError) as exc:
        run(client)
    assert exc.value.card.code == "RX-12"
    assert len(client.calls) == 1  # falha do cliente não é reenviada aqui


def test_empty_rule_refs_are_allowed_for_number_only_items() -> None:
    args = {"summary": "Resumo.", "items": [{"text": "Economia de R$ 100.", "rule_refs": []}]}
    assert run(FakeLLMClient([result(args)])).items[0].rule_refs == []


def test_schema_has_summary_and_item_rule_refs_without_defs() -> None:
    tool = tool_schema_for(Justification, name=TOOL_NAME)
    assert tool["type"] == "function" and tool["function"]["name"] == TOOL_NAME
    params = tool["function"]["parameters"]
    assert "$defs" not in params and "$ref" not in str(params)
    assert "summary" in params["properties"]
    item = params["properties"]["items"]["items"]
    assert item["type"] == "object"
    assert item["properties"]["rule_refs"]["type"] == "array"
    assert set(item["required"]) == {"text", "rule_refs"}


def test_schema_keeps_a_field_named_title() -> None:
    class WithTitle(BaseModel):
        title: str

    params = tool_schema_for(WithTitle)["function"]["parameters"]
    assert "title" in params["properties"] and params["required"] == ["title"]


def test_prompt_has_ids_sources_and_facts_but_no_personal_data() -> None:
    client = FakeLLMClient([result(GOOD)])
    run(client)
    text = "\n".join(m.content for m in client.calls[0]["messages"])
    assert "jornada_semanal_max" in text and "hora_extra_autorizacao_dp" in text
    assert "art. 6º, I, EC 141" in text and "ficticia" in text
    assert "E-007" in text and "L1" in text and "100" in text
    assert "Fulana" not in text  # `Violation.detail` fica de fora
    assert "sex" not in text


class KindClient:
    """Aceita `kind`, como o `FeatherlessClient`."""

    def __init__(self) -> None:
        self.kinds: list[str | None] = []

    def complete(self, *, size, messages, tool_schema=None, run_id, parent_id=None, kind=None) -> LLMResult:
        self.kinds.append(kind)
        return result(GOOD)


def test_kind_is_forwarded_only_when_the_client_accepts_it() -> None:
    client = KindClient()
    justify(client, card=CARD, facts=FACTS, run_id="r1")
    assert client.kinds == [KIND] == ["llm.justify"]
    FakeLLMClient([result(GOOD)])  # sem `kind`: já coberto por todos os outros testes, sem quebrar


def test_call_structured_is_generic() -> None:
    class Answer(BaseModel):
        n: int

    client = FakeLLMClient([result({"n": "abc"}), result({"n": 3})])
    assert call_structured(client, Answer, messages=[], run_id="r").n == 3
    assert len(client.calls) == 2
