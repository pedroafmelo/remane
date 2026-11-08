"""Rotas da fatia (plano da C5, seção 4, C2): enviar a escala, confirmar o resumo, ver antes e depois e a grade,
aprovar e publicar, ver o rastro e baixar os arquivos de exemplo.

Todas exigem o papel `gestor` (RF-30): na fatia só o gestor tem tela, e a grade leva o valor da hora de cada pessoa,
que o colaborador não deve ver. Cada rota tem linha na matriz de `tests/api/test_access.py`.

O CSV vem no corpo bruto (`Content-Type: text/csv`), não em multipart. Acima de `MAX_UPLOAD_BYTES`: 413. Fora de
UTF-8: 422. Nos dois casos a resposta traz o cartão RX-13 (`{"detail": ..., "exception": ...}`) e o agente não é
chamado. Pessoas só saem como `EmployeePublic` (sem `sex`, RN-13).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from escalista.api.accounts import Account
from escalista.api.deps import require_role
from escalista.api.wiring import (
    MAX_UPLOAD_BYTES,
    PublishRefusedError,
    RunNotFoundError,
    RunPhaseError,
    SliceAgent,
    get_agent,
    get_demo_files_dir,
    now_brt,
)
from escalista.domain.contracts import ExceptionCard, Role, TraceEvent
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.schedule import EmployeePublic, Schedule

DEMO_FILES = frozenset({"escala_atual.csv", "escala_defeito.csv"})

gestor = require_role(Role.GESTOR)


class ProposedSchedule(BaseModel):
    """A grade proposta e as pessoas dela (sem `sex`)."""

    schedule: Schedule
    employees: list[EmployeePublic]


class PublishedSchedule(BaseModel):
    """A última versão publicada (`version` nulo se ainda não houver) e as pessoas dela (sem `sex`)."""

    version: ScheduleVersion | None
    employees: list[EmployeePublic]


class Rejected(BaseModel):
    """Arquivo recusado na porta (tamanho ou codificação), antes de virar execução."""

    detail: str
    exception: ExceptionCard


class _UploadTooLarge(Exception):
    pass


def install_runs(app: FastAPI) -> None:
    """Liga as rotas da fatia e a tradução dos erros do agente em HTTP."""
    app.include_router(router)
    app.add_exception_handler(RunNotFoundError, _status_handler(status.HTTP_404_NOT_FOUND))
    app.add_exception_handler(RunPhaseError, _status_handler(status.HTTP_409_CONFLICT))
    app.add_exception_handler(PublishRefusedError, _refused_handler)


def _status_handler(code: int):
    async def handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(exc) or "execução não encontrada"}, status_code=code)

    return handler


async def _refused_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PublishRefusedError)
    card = exc.card.model_dump(mode="json") if exc.card else None
    return JSONResponse({"detail": exc.reason, "exception": card}, status_code=status.HTTP_403_FORBIDDEN)


def _rx13(file_name: str, reason: str) -> ExceptionCard:
    return ExceptionCard(
        code="RX-13",
        title="Arquivo de escala ilegível",
        reason=reason,
        decider=Role.GESTOR,
        evidence=[f"arquivo: {file_name}"],
        recommendation="Salvar a planilha como CSV em UTF-8, com até 1 MB, e enviar de novo.",
    )


def _rejected(code: int, file_name: str, reason: str) -> JSONResponse:
    body = Rejected(detail=reason, exception=_rx13(file_name, reason))
    return JSONResponse(body.model_dump(mode="json"), status_code=code)


async def _read_limited(request: Request) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise _UploadTooLarge
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_UPLOAD_BYTES:
            raise _UploadTooLarge
    return bytes(body)


def _run_or_404(agent: SliceAgent, run_id: str) -> RunState:
    state = agent.get_run(run_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="execução não encontrada")
    return state


router = APIRouter(prefix="/api", dependencies=[Depends(gestor)])


@router.post(
    "/runs",
    status_code=status.HTTP_201_CREATED,
    response_model=RunState,
    responses={413: {"model": Rejected}, 422: {"model": Rejected}},
)
async def start_run(
    request: Request,
    file_name: str = Query(min_length=1, max_length=255),
    agent: SliceAgent = Depends(get_agent),  # noqa: B008
):
    """Recebe o CSV no corpo e devolve o resumo da leitura (`awaiting_confirm`) ou o cartão RX-13 (`failed`)."""
    try:
        content = await _read_limited(request)
    except _UploadTooLarge:
        return _rejected(status.HTTP_413_CONTENT_TOO_LARGE, file_name, "O arquivo passa de 1 MB.")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        reason = f"O arquivo não está em UTF-8 (byte inválido na posição {exc.start})."
        return _rejected(status.HTTP_422_UNPROCESSABLE_CONTENT, file_name, reason)
    return await run_in_threadpool(agent.start_run, file_name, content)


@router.get("/runs/{run_id}", response_model=RunState)
def get_run(run_id: str, agent: SliceAgent = Depends(get_agent)) -> RunState:  # noqa: B008
    return _run_or_404(agent, run_id)


@router.post("/runs/{run_id}/confirm", response_model=RunState)
def confirm(run_id: str, agent: SliceAgent = Depends(get_agent)) -> RunState:  # noqa: B008
    """O gestor confirmou o resumo: otimiza, verifica, compara e justifica."""
    _run_or_404(agent, run_id)
    return agent.confirm(run_id)


@router.get("/runs/{run_id}/schedule", response_model=ProposedSchedule)
def proposed_schedule(run_id: str, agent: SliceAgent = Depends(get_agent)) -> ProposedSchedule:  # noqa: B008
    _run_or_404(agent, run_id)
    schedule = agent.get_schedule(run_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a execução ainda não tem grade proposta")
    return ProposedSchedule(schedule=schedule, employees=agent.employees(run_id))


@router.post("/runs/{run_id}/approve", response_model=RunState)
def approve(
    run_id: str,
    agent: SliceAgent = Depends(get_agent),  # noqa: B008
    account: Account = Depends(gestor),  # noqa: B008
) -> RunState:
    """Ato humano: grava quem aprovou, com qual papel e quando; o agente só publica com essa aprovação."""
    state = _run_or_404(agent, run_id)
    if state.version_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a execução não tem versão para aprovar")
    approval = Approval(
        id=f"apr-{uuid.uuid4().hex[:12]}",
        version_id=state.version_id,
        approved_by=account.id,
        role=account.role,
        at=now_brt(),
    )
    return agent.approve(run_id, approval)


@router.get("/runs/{run_id}/trace", response_model=list[TraceEvent])
def trace(run_id: str, agent: SliceAgent = Depends(get_agent)) -> list[TraceEvent]:  # noqa: B008
    _run_or_404(agent, run_id)
    return agent.trace(run_id)


@router.get("/schedules/published", response_model=PublishedSchedule)
def published(agent: SliceAgent = Depends(get_agent)) -> PublishedSchedule:  # noqa: B008
    version = agent.published()
    employees = agent.employees(version.run_id) if version else []
    return PublishedSchedule(version=version, employees=employees)


@router.get("/demo/files/{name}", response_class=FileResponse)
def demo_file(name: str, demo_dir: Path = Depends(get_demo_files_dir)) -> FileResponse:  # noqa: B008
    """Arquivos de exemplo da demo (dados sintéticos). Só os da lista branca; o nome nunca vira caminho livre."""
    if name not in DEMO_FILES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = demo_dir / name
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type="text/csv; charset=utf-8", filename=name)
