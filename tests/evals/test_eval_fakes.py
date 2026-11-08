"""Falsos de `src/escalista/evals/fakes.py` (relógio de passo e LLM roteirizado), usados pelos cenários do E3/E4."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from escalista.domain.contracts import LLMMessage, LLMResult, LLMUnavailableError
from escalista.domain.ports import Clock, LLMClient
from escalista.evals.fakes import ScriptedLLM, StepClock


def _tool(name: str) -> dict:
    return {"type": "function", "function": {"name": name, "parameters": {}}}


def _call(llm: ScriptedLLM, name: str | None, **kw) -> LLMResult:
    return llm.complete(
        size="small",
        messages=[LLMMessage(role="user", content="oi")],
        tool_schema=_tool(name) if name else None,
        run_id="r1",
        **kw,
    )


def test_step_clock_is_a_clock_and_advances():
    clock = StepClock(datetime(2027, 1, 11, 8, 0))
    assert isinstance(clock, Clock)
    assert clock.now() == datetime(2027, 1, 11, 8, 0)
    clock.advance(timedelta(minutes=15))
    assert clock.now() == datetime(2027, 1, 11, 8, 15)


def test_scripted_llm_answers_by_tool_name_and_records_calls():
    llm = ScriptedLLM(by_tool={"read_atestado": [{"days": 2}, LLMResult(tool_args={"days": 3}, model="fake")]})
    assert isinstance(llm, LLMClient)

    first = _call(llm, "read_atestado", kind="track.llm.read_atestado")
    second = _call(llm, "read_atestado")
    third = _call(llm, "read_atestado")

    assert first.tool_args == {"days": 2} and first.model == "fake" and first.key_index == 1
    assert second.tool_args == {"days": 3}
    assert third.tool_args is None and third.content  # fila vazia: só texto (recusa para a saída estruturada)
    assert [c["tool_name"] for c in llm.calls] == ["read_atestado"] * 3
    assert llm.calls[0]["kind"] == "track.llm.read_atestado"


def test_scripted_llm_fails_per_tool_or_always():
    llm = ScriptedLLM(fail_tools={"read_atestado"})
    with pytest.raises(LLMUnavailableError):
        _call(llm, "read_atestado")
    assert _call(llm, "outra").model == "fake"

    with pytest.raises(LLMUnavailableError) as exc:
        _call(ScriptedLLM(fail=True), None)
    assert exc.value.card.code == "RX-12"


def test_scripted_llm_general_queue():
    llm = ScriptedLLM(results=[LLMResult(content="x", model="fake")])
    assert _call(llm, None).content == "x"
