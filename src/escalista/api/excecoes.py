"""Fila de exceções do gestor (FT-04) e falta pelo celular simulado do colaborador (FT-03 mínimo).

Rotas (cada uma com linha na matriz de `tests/api/test_access.py`):
- gestor: `GET /api/exceptions` (abertas, depois as decididas) e `POST /api/exceptions/{id}/decide`;
- colaborador: `GET /api/colaborador/escala` (os próprios turnos da semana publicada, nunca salário nem `sex`) e
  `POST /api/colaborador/falta`.

Fontes da fila: o RX-01 das regras (conflito convenção x EC 141; semeado de forma idempotente na subida) e as faltas.
Na falta, a busca de cobertura é em código (`agents/cover.py`, sem solver nem modelo): com candidatos, o cartão
oferece os 3 melhores e "deixar descoberto"; sem nenhum, abre o RX-05 da política fictícia. Decidir grava o ato humano;
só a opção "<pessoa> cobre" muda algo: cria uma versão nova da escala com o turno reatribuído, grava a aprovação do
gestor e publica pela mesma ferramenta `publicar` da fatia, que relê a aprovação e recusa sem ela.

Quem é o colaborador da demo (conta `demo-colaborador`): se já há falta avisada na execução publicada, é quem avisou
(a identidade não muda depois que a cobertura reatribui turnos); senão, a pessoa com mais turnos na semana publicada,
no empate o menor id. Determinístico e documentado aqui.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import yaml
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from escalista.agents.cover import CoverCandidate, find_cover
from escalista.agents.optimizer import errors as agent_errors
from escalista.agents.optimizer.tools import Tracer, publicar
from escalista.api.accounts import Account
from escalista.api.deps import require_role
from escalista.api.wiring import DEFAULT_DEMO_FILES_DIR, DEFAULT_RULES_DIR, DEMO_WEEK_START, PublishRefusedError
from escalista.config import Settings
from escalista.domain.contracts import ExceptionCard, ExceptionOption, Role
from escalista.domain.ports import Clock, Repository
from escalista.domain.results import Approval, ScheduleVersion
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import Employee, Schedule, Shift, Store
from escalista.store.exceptions import Decision, ExceptionItem, ExceptionStore
from escalista.verifier import verify

POLICY_FILE = Path(DEFAULT_RULES_DIR) / "politica" / "politica_ficticia.yaml"
RULES_RUN = "excecoes-regras"  # run_id do rastro das exceções que não nascem de uma execução (RX-01)
MAX_COVER_OPTIONS = 3
FALLBACK_COVER_DEADLINE_MIN = 30
WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
UNCOVERED_LABEL = "Deixar o turno descoberto"
EXCEPTION_KIND = "exception.raised"  # o mesmo `kind` que o agente de otimização usa


# --- respostas ------------------------------------------------------------------------------------------------------


class ExceptionQueue(BaseModel):
    now: datetime  # relógio da demo, para o "vence em"
    open: list[ExceptionItem]
    decided: list[ExceptionItem]


class DecideBody(BaseModel):
    option_index: int = Field(ge=0)


class MyShift(BaseModel):
    day: date
    start: datetime
    end: datetime


class MyFalta(BaseModel):
    exception_id: str
    day: date
    start: datetime
    end: datetime
    status: Literal["pendente", "coberta", "descoberta", "decidida"]
    covered_by: str | None = None  # primeiro nome de quem cobre
    decision: str | None = None  # rótulo da opção escolhida pela gestora


class Me(BaseModel):
    """O colaborador como ele mesmo se vê: sem salário e sem `sex`."""

    id: str
    name: str
    job: str
    store: str


class MyWeek(BaseModel):
    published: bool
    week_start: date | None = None
    employee: Me | None = None
    shifts: list[MyShift] = Field(default_factory=list)
    faltas: list[MyFalta] = Field(default_factory=list)
    synthetic: bool = True


class FaltaBody(BaseModel):
    day: date
    text: str | None = Field(default=None, max_length=500)  # aceito e não gravado (pode conter dado de saúde)


# --- textos ---------------------------------------------------------------------------------------------------------


def _brl(value: Decimal) -> str:
    whole, cents = f"{value:.2f}".split(".")
    return f"R$ {int(whole):,}".replace(",", ".") + f",{cents}"


def _hour(moment: datetime) -> str:
    return f"{moment.hour}" if moment.minute == 0 else f"{moment.hour}:{moment.minute:02d}"


def shift_label(shift: Shift) -> str:
    """'qua 13/01, 14–22h' (o padrão de horário do design system)."""
    d = shift.start
    return f"{WEEKDAYS[d.weekday()]} {d:%d/%m}, {_hour(shift.start)}–{_hour(shift.end)}h"


def _overtime(hours: Decimal) -> str:
    return "sem hora extra" if hours == 0 else f"{hours}h extra".replace(".", ",")


def _first_name(name: str) -> str:
    return name.split()[0]


def load_policy_exceptions(path: Path = POLICY_FILE) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {e["code"]: e for e in raw.get("excecoes_demo", [])}


def policy_card(raw: dict[str, Any], now: datetime, evidence: list[str]) -> ExceptionCard:
    """Cartão a partir de uma entrada de `excecoes_demo` (os campos espelham o `ExceptionCard`)."""
    vetoed = [f"Opção vedada: {v}" for v in raw.get("opcoes_vedadas", [])]
    return ExceptionCard(
        code=raw["code"],
        title=raw["titulo"],
        reason=raw["motivo"],
        decider=Role(raw["decisor"]),
        deadline=now + timedelta(minutes=raw["prazo_min"]),
        evidence=[*evidence, *vetoed, f"Fonte: {raw['fonte']}"],
        options=[ExceptionOption(label=o["rotulo"], effect=o["efeito"]) for o in raw["opcoes"]],
        recommendation=raw["recomendacao"],
        if_no_answer=raw["sem_resposta"],
    )


# --- a mesa de exceções ---------------------------------------------------------------------------------------------


class ExceptionDesk:
    def __init__(
        self,
        *,
        store: ExceptionStore,
        repo: Repository,
        tracer: Tracer,
        clock: Clock,
        card: RuleCard,
        stores: list[Store],
        employees: list[Employee],
        policy: dict[str, dict[str, Any]],
        new_id=lambda: uuid4().hex,  # noqa: ANN001
    ) -> None:
        self._store = store
        self._repo = repo
        self._tracer = tracer
        self._clock = clock
        self._card = card
        self._store_names = {s.id: s.name for s in stores}
        self._employees = list(employees)
        self._by_id = {e.id: e for e in employees}
        self._policy = policy
        self._new_id = new_id
        self._lock = threading.Lock()

    # --- semente ---

    def seed(self) -> None:
        """RX-01 na fila, uma vez só (idempotente pelo id): do cartão, se a fusão abriu; senão, da política."""
        now = self._clock.now()
        cards = list(self._card.exceptions)
        if not cards and "RX-01" in self._policy:
            cards = [policy_card(self._policy["RX-01"], now, ["Gatilho: cct_repouso_semanal (convenção fictícia)"])]
        for i, card in enumerate(cards):
            if card.deadline is None:
                card = card.model_copy(update={"deadline": now + timedelta(days=2)})
            item = ExceptionItem(id=f"rx01-{i + 1}", created_at=now, card=card, source={"kind": "regras"})
            if self._store.add(item):
                self._tracer.step(RULES_RUN, EXCEPTION_KIND, payload={"exception_id": item.id, "code": card.code})

    # --- gestor ---

    def queue(self) -> ExceptionQueue:
        items = self._store.list()
        return ExceptionQueue(
            now=self._clock.now(),
            open=[i for i in items if i.status == "open"],
            decided=[i for i in items if i.status == "decided"],
        )

    def decide(self, item_id: str, option_index: int, account: Account) -> ExceptionItem:
        with self._lock:
            item = self._store.get(item_id)
            if item is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "exceção não encontrada")
            if item.status != "open":
                raise HTTPException(status.HTTP_409_CONFLICT, "esta exceção já foi decidida")
            if option_index >= len(item.card.options):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "opção inexistente neste cartão")
            run_id = item.source.get("run_id", RULES_RUN)
            candidates: list[str] = item.source.get("candidates", [])
            covering = item.source.get("kind") == "falta" and option_index < len(candidates)
            new_version = self._covered_version(item, candidates[option_index]) if covering else None

            self._tracer.human(
                run_id,
                "exception.decided",
                payload={
                    "exception_id": item.id,
                    "code": item.card.code,
                    "option_index": option_index,
                    "decided_by": account.id,
                    "role": account.role.value,
                },
            )
            if new_version is not None:
                outcome = self._publish(run_id, item, new_version, account, candidates[option_index])
            elif item.source.get("kind") == "falta" and item.card.options[option_index].label == UNCOVERED_LABEL:
                outcome = "O turno fica descoberto; a escala publicada não muda."
            else:
                outcome = "Decisão registrada. Nesta demo, nada além do registro é feito automaticamente."
            decided = item.model_copy(
                update={
                    "status": "decided",
                    "decision": Decision(
                        option_index=option_index,
                        label=item.card.options[option_index].label,
                        by=account.id,
                        role=account.role,
                        at=self._clock.now(),
                        outcome=outcome,
                    ),
                }
            )
            self._store.save(decided)
            return decided

    def _covered_version(self, item: ExceptionItem, cover_id: str) -> ScheduleVersion:
        latest = self._repo.latest_published()
        shift = Shift.model_validate(item.source["shift"])
        if latest is None or shift not in latest.schedule.shifts:
            raise HTTPException(status.HTTP_409_CONFLICT, "a escala publicada mudou desde a falta; ela não se aplica")
        others = [s for s in latest.schedule.shifts if s != shift]
        schedule = Schedule(
            week_start=latest.schedule.week_start, shifts=[*others, shift.model_copy(update={"employee_id": cover_id})]
        )
        return ScheduleVersion(
            id=f"ver-{self._new_id()}",
            run_id=latest.run_id,
            schedule=schedule,
            status="draft",
            input_hash=latest.input_hash,
            seed=latest.seed,
            violations_total=verify(schedule, self._card).total,
            created_at=self._clock.now(),
        )

    def _publish(
        self, run_id: str, item: ExceptionItem, version: ScheduleVersion, account: Account, cover_id: str
    ) -> str:
        """Versão nova com a aprovação do gestor gravada; `publicar` relê a aprovação e recusa sem ela."""
        from_version = self._repo.latest_published()
        self._repo.save_version(version)
        approval = Approval(
            id=f"apr-{self._new_id()[:12]}",
            version_id=version.id,
            approved_by=account.id,
            role=account.role,
            at=self._clock.now(),
        )
        self._repo.record_approval(approval)
        self._tracer.human(
            run_id,
            "approval.recorded",
            payload={"approval_id": approval.id, "version_id": version.id, "role": account.role.value},
        )
        try:
            publicar(repo=self._repo, tracer=self._tracer, run_id=run_id, version_id=version.id)
        except agent_errors.PublishRefusedError as exc:
            raise PublishRefusedError(exc.reason, exc.card) from exc
        self._tracer.step(
            run_id,
            "schedule.republished",
            payload={
                "exception_id": item.id,
                "from_version": from_version.id if from_version else None,
                "to_version": version.id,
                "absent_id": item.source["employee_id"],
                "cover_id": cover_id,
            },
        )
        return f"Escala republicada (versão {version.id}) com o turno reatribuído."

    # --- colaborador ---

    def _faltas(self, run_id: str) -> list[ExceptionItem]:
        items = [i for i in self._store.list() if i.source.get("kind") == "falta" and i.source.get("run_id") == run_id]
        return sorted(items, key=lambda i: i.created_at)

    def colaborador_id(self, version: ScheduleVersion) -> str | None:
        faltas = self._faltas(version.run_id)
        if faltas:
            return faltas[0].source["employee_id"]
        counts = Counter(s.employee_id for s in version.schedule.shifts if s.employee_id in self._by_id)
        if not counts:
            return None
        return min(counts, key=lambda eid: (-counts[eid], eid))

    def my_week(self) -> MyWeek:
        version = self._repo.latest_published()
        emp_id = self.colaborador_id(version) if version else None
        if version is None or emp_id is None:
            return MyWeek(published=False)
        emp = self._by_id[emp_id]
        shifts = sorted((s for s in version.schedule.shifts if s.employee_id == emp_id), key=lambda s: s.start)
        return MyWeek(
            published=True,
            week_start=version.schedule.week_start,
            employee=Me(id=emp.id, name=emp.name, job=emp.job, store=self._store_names.get(emp.store_id, emp.store_id)),
            shifts=[MyShift(day=s.start.date(), start=s.start, end=s.end) for s in shifts],
            faltas=[self._falta_view(i) for i in self._faltas(version.run_id) if i.source["employee_id"] == emp_id],
        )

    def _falta_view(self, item: ExceptionItem) -> MyFalta:
        shift = Shift.model_validate(item.source["shift"])
        view = MyFalta(
            exception_id=item.id, day=shift.start.date(), start=shift.start, end=shift.end, status="pendente"
        )
        if item.decision is None:
            return view
        candidates = item.source.get("candidates", [])
        if item.decision.option_index < len(candidates):
            cover = self._by_id.get(candidates[item.decision.option_index])
            return view.model_copy(
                update={"status": "coberta", "covered_by": _first_name(cover.name) if cover else None}
            )
        if item.decision.label == UNCOVERED_LABEL:
            return view.model_copy(update={"status": "descoberta"})
        return view.model_copy(update={"status": "decidida", "decision": item.decision.label})

    def report_falta(self, day: date, has_text: bool) -> MyWeek:
        with self._lock:
            version = self._repo.latest_published()
            emp_id = self.colaborador_id(version) if version else None
            if version is None or emp_id is None:
                raise HTTPException(status.HTTP_409_CONFLICT, "a escala da semana ainda não foi publicada")
            shift = next(
                (s for s in version.schedule.shifts if s.employee_id == emp_id and s.start.date() == day), None
            )
            if shift is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "você não tem turno nesse dia")
            if any(Shift.model_validate(i.source["shift"]) == shift for i in self._faltas(version.run_id)):
                raise HTTPException(status.HTTP_409_CONFLICT, "a falta desse dia já foi avisada")
            run_id = version.run_id
            self._tracer.step(
                run_id,
                "falta.received",
                payload={
                    "employee_id": emp_id,
                    "day": day.isoformat(),
                    "channel": "celular simulado",
                    "has_text": has_text,
                },
            )
            started = time.perf_counter()
            evaluated, found = find_cover(version.schedule, shift, self._employees, self._card)
            top = found[:MAX_COVER_OPTIONS]
            self._tracer.step(
                run_id,
                "cover.search",
                started=started,
                payload={"evaluated": evaluated, "eligible": len(found), "offered": [c.employee.id for c in top]},
            )
            card = self._cover_card(shift, evaluated, found, top) if top else self._rx05(shift, evaluated)
            item = ExceptionItem(
                id=f"exc-{self._new_id()[:12]}",
                created_at=self._clock.now(),
                card=card,
                source={
                    "kind": "falta",
                    "run_id": run_id,
                    "version_id": version.id,
                    "employee_id": emp_id,
                    "shift": shift.model_dump(mode="json"),
                    "candidates": [c.employee.id for c in top],
                },
            )
            self._store.add(item)
            self._tracer.step(run_id, EXCEPTION_KIND, payload={"exception_id": item.id, "code": card.code})
        return self.my_week()

    def _cover_card(
        self, shift: Shift, evaluated: int, found: list[CoverCandidate], top: list[CoverCandidate]
    ) -> ExceptionCard:
        absent = self._by_id[shift.employee_id]
        best = top[0]
        options = [
            ExceptionOption(
                label=f"{c.employee.name} cobre · {_overtime(c.overtime_hours)} · +{_brl(c.added_cost)}",
                effect=f"{c.employee.job}. A escala é republicada com o turno reatribuído, com a sua aprovação.",
            )
            for c in top
        ]
        options.append(ExceptionOption(label=UNCOVERED_LABEL, effect="A escala publicada não muda."))
        same_job = "mesma função" if best.employee.job == absent.job else f"função {best.employee.job}"
        overtime = _overtime(best.overtime_hours)
        prazo = self._policy.get("RX-05", {}).get("prazo_min", FALLBACK_COVER_DEADLINE_MIN)
        return ExceptionCard(
            code="FALTA",
            title=f"Falta de {absent.name} · {shift_label(shift)}",
            reason=(
                f"{_first_name(absent.name)} avisou pelo celular simulado que não vem. Procurei quem cubra na mesma "
                f"loja: {evaluated} de folga nesse dia, {len(found)} sem violar nenhuma regra do cartão."
            ),
            decider=Role.GESTOR,
            deadline=self._clock.now() + timedelta(minutes=prazo),
            evidence=[
                f"Turno: {shift_label(shift)}, {self._store_names.get(shift.store_id, shift.store_id)}",
                f"Avaliados {evaluated} colegas de folga; o verificador aprovou {len(found)}.",
                "Custo adicional medido pela mesma função de custo do antes e depois.",
            ],
            options=options,
            recommendation=(
                f"{best.employee.name} cobre: {overtime}, {same_job}, +{_brl(best.added_cost)}. "
                "Ordem usada: sem hora extra, mesma função, menor custo; nenhuma violação nova no verificador."
            ),
            if_no_answer="Nada é publicado sem a sua decisão; o turno segue sem cobertura.",
        )

    def _rx05(self, shift: Shift, evaluated: int) -> ExceptionCard:
        evidence = [
            f"Turno: {shift_label(shift)}, {self._store_names.get(shift.store_id, shift.store_id)}",
            f"Avaliados {evaluated} colegas de folga; nenhum cobre sem violar regra.",
        ]
        card = policy_card(self._policy["RX-05"], self._clock.now(), evidence)
        absent = self._by_id[shift.employee_id]
        return card.model_copy(update={"title": f"{card.title} · {absent.name} · {shift_label(shift)}"})


# --- ligação --------------------------------------------------------------------------------------------------------


def build_desk(settings: Settings, engine: Engine) -> ExceptionDesk:
    from escalista.audit.sink import SqlTraceSink
    from escalista.clock.system import SystemClock
    from escalista.db import init_db
    from escalista.ingest.demo_network import load_demo_network
    from escalista.rules.loader import load_rule_card
    from escalista.store.sql_repository import SqlRepository

    init_db(engine)
    sink = SqlTraceSink(engine, known_secrets=[key for _, key in settings.featherless_keys])
    clock = SystemClock()
    stores, employees, _ = load_demo_network(Path(DEFAULT_DEMO_FILES_DIR))
    desk = ExceptionDesk(
        store=ExceptionStore(engine),
        repo=SqlRepository(engine),
        tracer=Tracer(sink, clock, new_id=lambda: uuid4().hex, list_events=sink.list_events),
        clock=clock,
        card=load_rule_card(Path(DEFAULT_RULES_DIR), DEMO_WEEK_START),
        stores=stores,
        employees=employees,
        policy=load_policy_exceptions(),
    )
    desk.seed()
    return desk


def get_desk(request: Request) -> ExceptionDesk:
    return request.app.state.desk


gestor = require_role(Role.GESTOR)
colaborador = require_role(Role.COLABORADOR)
gestor_router = APIRouter(prefix="/api", dependencies=[Depends(gestor)])
colaborador_router = APIRouter(prefix="/api/colaborador", dependencies=[Depends(colaborador)])


@gestor_router.get("/exceptions", response_model=ExceptionQueue)
def list_exceptions(desk: ExceptionDesk = Depends(get_desk)) -> ExceptionQueue:  # noqa: B008
    return desk.queue()


@gestor_router.post("/exceptions/{item_id}/decide", response_model=ExceptionItem)
def decide(
    item_id: str,
    body: DecideBody,
    desk: ExceptionDesk = Depends(get_desk),  # noqa: B008
    account: Account = Depends(gestor),  # noqa: B008
) -> ExceptionItem:
    """Ato humano: grava a opção, quem decidiu e quando; a cobertura republica a escala com essa aprovação."""
    return desk.decide(item_id, body.option_index, account)


@colaborador_router.get("/escala", response_model=MyWeek)
def my_week(desk: ExceptionDesk = Depends(get_desk)) -> MyWeek:  # noqa: B008
    return desk.my_week()


@colaborador_router.post("/falta", response_model=MyWeek)
def report_falta(body: FaltaBody, desk: ExceptionDesk = Depends(get_desk)) -> MyWeek:  # noqa: B008
    return desk.report_falta(body.day, bool(body.text and body.text.strip()))


def install_excecoes(app: FastAPI) -> None:
    app.include_router(gestor_router)
    app.include_router(colaborador_router)
