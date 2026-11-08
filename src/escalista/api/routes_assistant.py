"""Rota do assistente do gestor (C7b N2, FT-08): `POST /api/assistente/mensagem`, só gestor, somente leitura.

Tem linha na matriz de `tests/api/test_access.py`. Sem histórico no servidor: a conversa do gestor vive só na tela.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from escalista.agents.assistant.assistant import MAX_CHARS, AssistantError
from escalista.api.accounts import Account
from escalista.api.deps import require_role
from escalista.domain.contracts import Role
from escalista.domain.tracking import AssistantReply

gestor = require_role(Role.GESTOR)
router = APIRouter(prefix="/api/assistente", dependencies=[Depends(gestor)])


class QuestionBody(BaseModel):
    text: str = Field(max_length=MAX_CHARS)


@router.post("/mensagem", response_model=AssistantReply)
def ask(body: QuestionBody, request: Request, account: Account = Depends(gestor)) -> AssistantReply:  # noqa: B008
    try:
        return request.app.state.assistant.ask(user_id=account.id, text=body.text)
    except AssistantError as exc:
        raise HTTPException(exc.status, exc.message) from exc


def install_assistant(app: FastAPI) -> None:
    app.include_router(router)
