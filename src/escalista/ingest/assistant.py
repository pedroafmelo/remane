"""Escolhedor da ferramenta de leitura do assistente do gestor (plano da C7b, N2): `call_structured` com o schema
fechado `AssistantChoice` (modelo `small`). O CID, se aparecer na pergunta, sai antes do modelo."""

from __future__ import annotations

from escalista.audit.protected import strip_cid_any_case
from escalista.domain.ports import AssistantChooser, LLMClient
from escalista.domain.tracking import AssistantChoice, AssistantContext
from escalista.llm.prompts.assistant import KIND, TOOL_DESCRIPTION, TOOL_NAME, build_messages
from escalista.llm.structured import call_structured


def make_chooser(llm: LLMClient) -> AssistantChooser:
    def chooser(*, text: str, context: AssistantContext, run_id: str) -> AssistantChoice:
        return call_structured(
            llm,
            AssistantChoice,
            messages=build_messages(strip_cid_any_case(text), context=context),
            run_id=run_id,
            tool_name=TOOL_NAME,
            tool_description=TOOL_DESCRIPTION,
            size="small",
            kind=KIND,
            what="escolha da ferramenta de leitura",
        )

    return chooser
