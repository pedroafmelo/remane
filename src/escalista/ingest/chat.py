"""Interpretador da mensagem livre do colaborador (plano da C7b, E2): borda entre o texto e `ChatInterpretation`.

Caminho: `audit.protected.strip_cid` (o CID sai **antes** do modelo) → `call_structured` com o schema fechado
`ChatInterpretation` (modelo `small`, ferramenta `classify_message`). Campo extra, intenção fora da lista ou falha do
cliente terminam em `LLMUnavailableError`; o `Tracker` responde "não entendi" e nada mais acontece. O texto fica em
memória: nada vai a log nem ao rastro (o evento do cliente leva só tamanho, tokens, custo e latência).
"""

from __future__ import annotations

from escalista.audit.protected import strip_cid
from escalista.domain.ports import LLMClient, MessageInterpreter
from escalista.domain.tracking import ChatContext, ChatInterpretation
from escalista.llm.prompts.classify_message import KIND, TOOL_DESCRIPTION, TOOL_NAME, build_messages
from escalista.llm.structured import call_structured


def make_interpreter(llm: LLMClient) -> MessageInterpreter:
    """Interpretador que satisfaz a porta `MessageInterpreter`, com o cliente do modelo já preso."""

    def interpreter(*, text: str, employee_name: str, context: ChatContext, run_id: str) -> ChatInterpretation:
        return call_structured(
            llm,
            ChatInterpretation,
            messages=build_messages(strip_cid(text), employee_name=employee_name, context=context),
            run_id=run_id,
            tool_name=TOOL_NAME,
            tool_description=TOOL_DESCRIPTION,
            size="small",
            kind=KIND,
            what="classificação da mensagem",
        )

    return interpreter
