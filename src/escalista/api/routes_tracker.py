"""Rotas do acompanhamento (C7, SAIDA-AC-10): relógio de demo e celular simulado do colaborador.

Cada rota tem linha na matriz de `tests/api/test_access.py`.
- gestor e colaborador: `GET /api/demo/clock`, `POST /api/demo/clock/advance` (avança e varre);
- só gestor: `POST /api/demo/reset`;
- colaborador: `GET /api/colaborador/pessoas`, `GET /api/colaborador/caixa`, `POST /api/colaborador/aviso`,
  `POST /api/colaborador/caso/{case_id}/anexo` (PDF ou foto PNG/JPEG no corpo bruto),
  `POST /api/colaborador/oferta/{offer_id}`, `POST /api/colaborador/resposta` e (C7b) `POST /api/colaborador/mensagem`.

Quem é o colaborador (`as`): sem `as`, a pessoa padrão da demo (`ExceptionDesk.default_person`). Trocar de pessoa só
com `DEMO_MODE` ligado e só para alguém do quadro da escala publicada (RX-10: o `Tracker.inbound` registra a recusa);
sem `DEMO_MODE`, `as` de outra pessoa é 403.

Privacidade (RN-06, revisto na C7b): o aviso por botão traz só `has_text`; o texto do chat é guardado só no canal, já
sem CID, e só volta na caixa da própria pessoa. Os bytes do anexo ficam em memória e nenhuma resposta ecoa bytes ou CID.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from escalista.agents.tracker.flow import CHAT_MAX_CHARS, Tracker, TrackerError
from escalista.api.deps import require_role
from escalista.api.excecoes import ExceptionDesk
from escalista.api.tracker_wiring import InboundLog, reset_demo
from escalista.clock.demo import DEMO_CLOCK_BASE
from escalista.domain.contracts import Role
from escalista.domain.tracking import Attachment, CaseView, MediaType, Reply

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # 5 MB (MiB)
PDF_MAGIC = b"%PDF"
PNG_MAGIC = b"\x89PNG"
JPEG_MAGIC = b"\xff\xd8\xff"


# --- respostas e corpos ---------------------------------------------------------------------------------------------


class ClockView(BaseModel):
    now: datetime
    base: datetime
    simulated: Literal[True] = True


class AdvanceBody(BaseModel):
    minutes: Literal[15, 1440, 10080]


class TriggerView(BaseModel):
    kind: str
    employee_id: str | None
    ref: str


class AdvanceView(BaseModel):
    now: datetime
    triggers: list[TriggerView]
    events: int


class ResetView(BaseModel):
    now: datetime


class Person(BaseModel):
    id: str
    name: str
    job: str
    store: str


class PeopleView(BaseModel):
    people: list[Person]
    default_id: str


class InboxShift(BaseModel):
    day: date
    start: datetime
    end: datetime


class InboxMessage(BaseModel):
    id: str
    direction: Literal["in", "out"]
    template: str
    body: str | None  # saída: texto nosso; entrada: só o chat da própria pessoa, já sem CID (C7b)
    has_text: bool
    attachment_media_type: str | None
    at: datetime
    case_id: str | None


class InboxOffer(BaseModel):
    offer_id: str
    case_id: str
    start: datetime
    end: datetime
    store: str
    status: str
    deadline: datetime
    overtime_hours: Decimal
    added_cost: Decimal


class InboxQuestion(BaseModel):
    case_id: str
    start: datetime
    end: datetime


class InboxView(BaseModel):
    now: datetime
    employee: Person
    week_start: date
    shifts: list[InboxShift]
    messages: list[InboxMessage]
    offers: list[InboxOffer]
    questions: list[InboxQuestion]
    cases: list[CaseView]
    synthetic: Literal[True] = True


class ReportBody(BaseModel):
    as_: str | None = Field(default=None, alias="as")
    day: date
    kind: Literal["falta", "atraso"]
    has_text: bool = False  # o texto em si fica no celular (RN-06)


class OfferBody(BaseModel):
    as_: str | None = Field(default=None, alias="as")
    accept: bool


class AnswerBody(BaseModel):
    as_: str | None = Field(default=None, alias="as")
    case_id: str
    coming: bool


class MessageBody(BaseModel):
    as_: str | None = Field(default=None, alias="as")
    text: str = Field(max_length=CHAT_MAX_CHARS)


# --- apoio ----------------------------------------------------------------------------------------------------------


def _desk(request: Request) -> ExceptionDesk:
    return request.app.state.desk


def _tracker(request: Request) -> Tracker:
    return request.app.state.tracker


def _inbound(request: Request) -> InboundLog:
    return InboundLog(request.app.state.engine, request.app.state.demo_clock)


def _flow[T](fn: Callable[[], T]) -> T:
    """`TrackerError` vira o status dele; o resto o `Tracker` já transforma em cartão."""
    try:
        return fn()
    except TrackerError as exc:
        raise HTTPException(exc.status, exc.message) from exc


def resolve_person(request: Request, as_: str | None) -> str:
    """A pessoa por trás do celular: a padrão, ou `as` (só com `DEMO_MODE` e só do quadro; RX-10)."""
    _, default = _desk(request).default_person()
    if as_ is None or as_ == default:
        return default
    if not request.app.state.settings.demo_mode:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "trocar de pessoa só no modo de demonstração")
    if not _tracker(request).inbound(as_):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "pessoa fora do quadro")
    return as_


def _guarded[T](log: InboundLog, message_id: str, fn: Callable[[], T]) -> T:
    """Roda o ato do fluxo; se ele for recusado, desfaz a mensagem de entrada já registrada."""
    try:
        return _flow(fn)
    except Exception:
        log.drop(message_id)
        raise


def _media_type(head: bytes) -> MediaType | None:
    """O tipo do anexo pelos bytes iniciais (nunca pelo cabeçalho `Content-Type`): PDF, PNG ou JPEG."""
    if head.lstrip().startswith(PDF_MAGIC):
        return "application/pdf"
    if head.startswith(PNG_MAGIC):
        return "image/png"
    if head.startswith(JPEG_MAGIC):
        return "image/jpeg"
    return None


async def _read_attachment(request: Request) -> tuple[bytes, MediaType]:
    """Lê o corpo bruto em memória (sem arquivo temporário), até 5 MB; só PDF, PNG ou JPEG pelos bytes iniciais."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "o anexo passa de 5 MB")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "o anexo passa de 5 MB")
    media_type = _media_type(bytes(body[:1024]))
    if media_type is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "o anexo precisa ser um PDF, PNG ou JPEG")
    return bytes(body), media_type


# --- rotas ----------------------------------------------------------------------------------------------------------

both = require_role(Role.GESTOR, Role.COLABORADOR)
gestor = require_role(Role.GESTOR)
colaborador = require_role(Role.COLABORADOR)
demo_router = APIRouter(prefix="/api/demo", dependencies=[Depends(both)])
reset_router = APIRouter(prefix="/api/demo", dependencies=[Depends(gestor)])
phone_router = APIRouter(prefix="/api/colaborador", dependencies=[Depends(colaborador)])


@demo_router.get("/clock", response_model=ClockView)
def get_clock(request: Request) -> ClockView:
    return ClockView(now=request.app.state.demo_clock.now(), base=DEMO_CLOCK_BASE)


@demo_router.post("/clock/advance", response_model=AdvanceView)
def advance_clock(body: AdvanceBody, request: Request) -> AdvanceView:
    """Avança o tempo simulado e roda a varredura (no ponto, sem resposta, ofertas vencidas)."""
    now = request.app.state.demo_clock.advance(body.minutes)
    result = _flow(lambda: _tracker(request).run_sweep())
    return AdvanceView(
        now=now,
        triggers=[TriggerView(kind=t.kind, employee_id=t.employee_id, ref=t.ref) for t in result.triggers],
        events=len(result.events),
    )


@reset_router.post("/reset", response_model=ResetView)
def reset(request: Request) -> ResetView:
    """Relógio no início, casos e mensagens apagados e a semana sintética publicada de novo."""
    settings = request.app.state.settings
    now = reset_demo(
        engine=request.app.state.engine,
        clock=request.app.state.demo_clock,
        known_secrets=[key for _, key in settings.featherless_keys],
    )
    return ResetView(now=now)


@phone_router.get("/pessoas", response_model=PeopleView)
def people(request: Request) -> PeopleView:
    desk = _desk(request)
    _, default = desk.default_person()  # também carrega a rede da escala publicada na mesa
    people = [
        Person(id=e.id, name=e.name, job=e.job, store=desk.store_name(e.store_id)) for e in _tracker(request).people()
    ]
    return PeopleView(people=sorted(people, key=lambda p: p.id), default_id=default)


@phone_router.get("/caixa", response_model=InboxView)
def inbox(request: Request, as_: str | None = Query(default=None, alias="as")) -> InboxView:  # noqa: B008
    person = resolve_person(request, as_)
    desk, tracker = _desk(request), _tracker(request)
    version, _ = desk.default_person()
    employee = next(e for e in tracker.people() if e.id == person)
    cases = request.app.state.track_cases.list_cases()
    offers = [
        InboxOffer(
            offer_id=o.id,
            case_id=c.id,
            start=c.shift.start,
            end=c.shift.end,
            store=desk.store_name(c.shift.store_id),
            status=o.status,
            deadline=o.deadline,
            overtime_hours=o.overtime_hours,
            added_cost=o.added_cost,
        )
        for c in cases
        for o in c.offers
        if o.candidate_id == person
    ]
    mine = [c for c in cases if c.employee_id == person]
    shifts = sorted((s for s in version.schedule.shifts if s.employee_id == person), key=lambda s: s.start)
    return InboxView(
        now=request.app.state.demo_clock.now(),
        employee=Person(id=employee.id, name=employee.name, job=employee.job, store=desk.store_name(employee.store_id)),
        week_start=version.schedule.week_start,
        shifts=[InboxShift(day=s.start.date(), start=s.start, end=s.end) for s in shifts],
        messages=[InboxMessage(**m.model_dump(include=set(InboxMessage.model_fields))) for m in tracker.inbox(person)],
        offers=offers,
        questions=[
            InboxQuestion(case_id=c.id, start=c.shift.start, end=c.shift.end)
            for c in mine
            if c.status == "aguardando_colaborador"
        ],
        cases=[CaseView.of(c) for c in mine],
    )


@phone_router.post("/aviso", response_model=CaseView)
def report(body: ReportBody, request: Request) -> CaseView:
    """Aviso de falta ou atraso. O texto livre não vem: o fluxo recebe `text=None` (RN-06 por construção)."""
    person = resolve_person(request, body.as_)
    log = _inbound(request)
    message_id = log.record(party=person, template=f"aviso_{body.kind}", has_text=body.has_text)
    view = _guarded(
        log, message_id, lambda: _tracker(request).report(employee_id=person, day=body.day, kind=body.kind, text=None)
    )
    log.link(message_id, view.case_id)
    return view


@phone_router.post("/caso/{case_id}/anexo", response_model=CaseView)
async def attach(
    case_id: str,
    request: Request,
    as_: str | None = Query(default=None, alias="as"),  # noqa: B008
    file_name: str = Query(default="anexo.pdf", max_length=200),  # noqa: B008
) -> CaseView:
    """Comprovação (PDF ou foto PNG/JPEG) no corpo bruto, até 5 MB, só do dono do caso. Só em memória."""
    person = await run_in_threadpool(resolve_person, request, as_)
    data, media_type = await _read_attachment(request)
    tracker = _tracker(request)
    case = await run_in_threadpool(_flow, lambda: tracker.case(case_id))
    if case.employee_id != person:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "só quem avisou anexa a comprovação deste caso")
    log = _inbound(request)
    message_id = log.record(party=person, template="anexo", case_id=case_id, media_type=media_type)
    attachment = Attachment(data=data, media_type=media_type, filename=file_name)
    return await run_in_threadpool(_guarded, log, message_id, lambda: tracker.attach(case_id, attachment))


@phone_router.post("/oferta/{offer_id}", response_model=CaseView)
def answer_offer(offer_id: str, body: OfferBody, request: Request) -> CaseView:
    """O colega aceita ou recusa a oferta (só o próprio candidato)."""
    person = resolve_person(request, body.as_)
    tracker = _tracker(request)
    case_id = next(
        (c.id for c in request.app.state.track_cases.list_cases() for o in c.offers if o.id == offer_id), None
    )
    if case_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "oferta não encontrada")
    log = _inbound(request)
    template = "oferta_aceita" if body.accept else "oferta_recusada"
    message_id = log.record(party=person, template=template, case_id=case_id)
    return _guarded(
        log, message_id, lambda: tracker.respond_offer(offer_id=offer_id, employee_id=person, accept=body.accept)
    )


@phone_router.post("/resposta", response_model=CaseView)
def answer_question(body: AnswerBody, request: Request) -> CaseView:
    """Resposta à pergunta do agente (não bateu o ponto): "estou a caminho" ou "não vou"."""
    person = resolve_person(request, body.as_)
    tracker = _tracker(request)
    _flow(lambda: tracker.case(body.case_id))  # 404 antes de registrar a mensagem
    log = _inbound(request)
    template = "resposta_vou" if body.coming else "resposta_nao_vou"
    message_id = log.record(party=person, template=template, case_id=body.case_id)
    return _guarded(
        log, message_id, lambda: tracker.answer(case_id=body.case_id, employee_id=person, coming=body.coming)
    )


@phone_router.post("/mensagem", response_model=Reply)
def message(body: MessageBody, request: Request) -> Reply:
    """Mensagem livre do chat (C7b): até 300 caracteres, 10 por minuto. O modelo só classifica; a resposta é texto de
    template. O texto vai ao canal (gravado já sem CID) e ao modelo (sem CID); nunca a rastro, log ou outra resposta."""
    person = resolve_person(request, body.as_)
    return _flow(lambda: _tracker(request).message(employee_id=person, text=body.text))


def install_tracker(app: FastAPI) -> None:
    app.include_router(demo_router)
    app.include_router(reset_router)
    app.include_router(phone_router)
