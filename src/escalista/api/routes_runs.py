"""Rotas da fatia (plano da C5, seção 4, C2; plano da C6, seção 14, C1): enviar a escala, confirmar (e corrigir) o
resumo, planejar a próxima semana sem upload, ver o quadro, ver antes e depois e a grade, aprovar e publicar, ver o
rastro e baixar os arquivos de exemplo.

Todas exigem o papel `gestor` (RF-30): na fatia só o gestor tem tela, e a grade leva o valor da hora de cada pessoa,
que o colaborador não deve ver. Cada rota tem linha na matriz de `tests/api/test_access.py`.

O arquivo vem no corpo bruto (não em multipart) e o nome em `?file_name=`. O tipo é decidido pela extensão **e** pelos
bytes iniciais, nunca pelo `Content-Type`: CSV (`.csv`/`.txt`, texto), XLSX (`.xlsx` com `PK\x03\x04`) ou PDF (`.pdf`
com `%PDF`). Acima de `MAX_UPLOAD_BYTES`: 413. Tipo recusado (`.xlsm`, `.xls` ou planilha OLE antiga, extensão e
conteúdo incoerentes, extensão desconhecida): 422. Nos dois casos a resposta traz o cartão RX-13
(`{"detail": ..., "exception": ...}`) e o agente não é chamado. A codificação do CSV (UTF-8 e afins) é do leitor do
agente, que devolve uma execução `failed` com RX-13 quando não decodifica. Pessoas só saem como `EmployeePublic` (sem
`sex`, RN-13).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path, PurePath
from typing import Annotated

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Query, Request, status
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
    SliceAgentC6,
    get_agent,
    get_demo_files_dir,
    now_brt,
)
from escalista.domain.contracts import ExceptionCard, Role, TraceEvent
from escalista.domain.reading import ConfirmInput, DemandPattern
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.schedule import EmployeePublic, Schedule, Store

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Lista branca dos exemplos da demo: nome -> (tipo do conteúdo, rótulo). O XLSX é binário e segue sem decodificar.
DEMO_FILES: dict[str, tuple[str, str]] = {
    "escala_exemplo_grade.xlsx": (XLSX_MEDIA_TYPE, "Escala de exemplo em planilha (XLSX, grade)"),
    "escala_atual.csv": (CSV_MEDIA_TYPE, "Escala de exemplo em CSV (formato padrão)"),
    "escala_defeito.csv": (CSV_MEDIA_TYPE, "Exemplo com defeitos (mostra os problemas com a linha)"),
}
TEXT_EXTENSIONS = frozenset({".csv", ".txt"})
XLSX_MAGIC = b"PK\x03\x04"
PDF_MAGIC = b"%PDF"
OLE_MAGIC = b"\xd0\xcf\x11\xe0"  # planilha antiga do Excel (.xls)
MACRO_OR_LEGACY = frozenset({".xlsm", ".xls", ".xlsb", ".xltm"})

gestor = require_role(Role.GESTOR)


class ProposedSchedule(BaseModel):
    """A grade proposta e as pessoas dela (sem `sex`)."""

    schedule: Schedule
    employees: list[EmployeePublic]


class PublishedSchedule(BaseModel):
    """A última versão publicada (`version` nulo se ainda não houver) e as pessoas dela (sem `sex`)."""

    version: ScheduleVersion | None
    employees: list[EmployeePublic]


class RosterPublic(BaseModel):
    """O último quadro confirmado, com as pessoas sem `sex` (RN-13)."""

    version: int
    stores: list[Store]
    employees: list[EmployeePublic]
    demand: list[DemandPattern]
    source_run_id: str
    confirmed_by: str
    confirmed_at: datetime


class Rejected(BaseModel):
    """Arquivo recusado na porta (tamanho ou tipo), antes de virar execução."""

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
        recommendation="Enviar a escala como CSV, XLSX (sem macros) ou PDF, com até 1 MB.",
    )


def _type_refusal(file_name: str, content: bytes) -> str | None:
    """Motivo da recusa do tipo do arquivo, ou `None` se a extensão e os bytes iniciais batem (CSV, XLSX ou PDF)."""
    ext = PurePath(file_name).suffix.lower()
    is_zip, is_pdf = content.startswith(XLSX_MAGIC), content.startswith(PDF_MAGIC)
    is_ole = content.startswith(OLE_MAGIC)
    if ext in MACRO_OR_LEGACY:
        return f"Planilhas {ext} não são aceitas (macros ou formato antigo). Salve como .xlsx ou .csv."
    if is_ole:
        return "O arquivo é uma planilha do Excel no formato antigo (.xls). Salve como .xlsx ou .csv."
    if ext == ".xlsx":
        return None if is_zip else "A extensão é .xlsx, mas o conteúdo não é uma planilha XLSX."
    if ext == ".pdf":
        return None if is_pdf else "A extensão é .pdf, mas o conteúdo não é um PDF."
    if ext in TEXT_EXTENSIONS:
        if is_zip or is_pdf:
            return f"A extensão é {ext}, mas o conteúdo é {'um PDF' if is_pdf else 'um arquivo compactado (XLSX?)'}."
        return None
    shown = ext or "sem extensão"
    return f"Tipo de arquivo não aceito ({shown}). Envie a escala como .csv, .xlsx ou .pdf."


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


def _run_or_404(agent: SliceAgentC6, run_id: str) -> RunState:
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
    agent: SliceAgentC6 = Depends(get_agent),  # noqa: B008
):
    """Recebe o arquivo (CSV, XLSX ou PDF) no corpo e devolve o resumo da leitura (`awaiting_confirm`) ou o cartão
    RX-13 (`failed`, inclusive para CSV que não decodifica). Tamanho ou tipo recusado: 413 ou 422, sem chamar o
    agente."""
    try:
        content = await _read_limited(request)
    except _UploadTooLarge:
        return _rejected(status.HTTP_413_CONTENT_TOO_LARGE, file_name, "O arquivo passa de 1 MB.")
    refusal = _type_refusal(file_name, content)
    if refusal is not None:
        return _rejected(status.HTTP_422_UNPROCESSABLE_CONTENT, file_name, refusal)
    return await run_in_threadpool(agent.start_run, file_name, content)


@router.post("/runs/next-week", status_code=status.HTTP_201_CREATED, response_model=RunState)
def next_week(agent: SliceAgentC6 = Depends(get_agent)) -> RunState:  # noqa: B008
    """Planeja a semana seguinte à última publicada, sem upload (modo `continuidade`). Sem publicada ou sem quadro:
    409."""
    return agent.start_next_week()


@router.get("/runs/{run_id}", response_model=RunState)
def get_run(run_id: str, agent: SliceAgentC6 = Depends(get_agent)) -> RunState:  # noqa: B008
    return _run_or_404(agent, run_id)


@router.post("/runs/{run_id}/confirm", response_model=RunState)
def confirm(
    run_id: str,
    data: Annotated[ConfirmInput | None, Body()] = None,
    agent: SliceAgentC6 = Depends(get_agent),  # noqa: B008
) -> RunState:
    """O gestor confirmou (e talvez corrigiu) o resumo: otimiza, verifica, compara e justifica. O corpo JSON
    (`ConfirmInput`) é opcional: sem corpo, vale tudo no padrão."""
    _run_or_404(agent, run_id)
    return agent.confirm(run_id, data)


@router.get("/runs/{run_id}/schedule", response_model=ProposedSchedule)
def proposed_schedule(run_id: str, agent: SliceAgentC6 = Depends(get_agent)) -> ProposedSchedule:  # noqa: B008
    _run_or_404(agent, run_id)
    schedule = agent.get_schedule(run_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a execução ainda não tem grade proposta")
    return ProposedSchedule(schedule=schedule, employees=agent.employees(run_id))


@router.post("/runs/{run_id}/approve", response_model=RunState)
def approve(
    run_id: str,
    agent: SliceAgentC6 = Depends(get_agent),  # noqa: B008
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
def trace(run_id: str, agent: SliceAgentC6 = Depends(get_agent)) -> list[TraceEvent]:  # noqa: B008
    _run_or_404(agent, run_id)
    return agent.trace(run_id)


@router.get("/schedules/published", response_model=PublishedSchedule)
def published(agent: SliceAgentC6 = Depends(get_agent)) -> PublishedSchedule:  # noqa: B008
    version = agent.published()
    employees = agent.employees(version.run_id) if version else []
    return PublishedSchedule(version=version, employees=employees)


@router.get("/roster", response_model=RosterPublic)
def roster(agent: SliceAgentC6 = Depends(get_agent)) -> RosterPublic:  # noqa: B008
    """O último quadro confirmado (lojas, pessoas sem `sex`, padrão de demanda e versão). Sem quadro: 404."""
    current = agent.roster()
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ainda não há quadro confirmado")
    return RosterPublic(
        **current.model_dump(exclude={"employees"}),
        employees=[EmployeePublic.from_employee(e) for e in current.employees],
    )


@router.get("/demo/files/{name}", response_class=FileResponse)
def demo_file(name: str, demo_dir: Path = Depends(get_demo_files_dir)) -> FileResponse:  # noqa: B008
    """Arquivos de exemplo da demo (dados sintéticos). Só os da lista branca; o nome nunca vira caminho livre."""
    if name not in DEMO_FILES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = demo_dir / name
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type=DEMO_FILES[name][0], filename=name)
