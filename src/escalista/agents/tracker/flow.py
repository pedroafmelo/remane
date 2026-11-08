"""Acompanhamento de escala (FT-03): a falta ou o atraso vira um turno coberto, com o aceite do colega, a validação do
gestor, a escala republicada sem violação nova, as mensagens registradas e o rastro de cada passo.

Máquina de estados em código (plano da C7, seção 4.1), sem grafo e sem checkpointer: o estado inteiro do caso vive na
tabela de casos (porta `TrackRepository`) e é relido a cada evento (aviso, resposta à oferta, decisão do gestor).
O rastro de cada caso é a execução `track-<case_id>`; payloads só com ids e campos, nunca nome, texto livre ou CID
(RN-06, RN-13). O texto que o colaborador escreve só vira `has_text`: não vai a payload, caso, mensagem nem log.

Atos de consequência (seção 7): o colega aceita (`respond_offer` só do próprio candidato); o gestor valida sempre
(`on_decision` grava a aprovação e `aplicar_cobertura` a relê antes de publicar).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from escalista.agents.cover import CoverCandidate, find_cover
from escalista.agents.optimizer.errors import PublishRefusedError
from escalista.agents.optimizer.tools import Tracer
from escalista.agents.tracker import cards
from escalista.agents.tracker.messages import deadline_label, first_name, overtime_label, render, shift_label
from escalista.agents.tracker.replan import CoverFn, CoverOutcome, dispatch, request_for
from escalista.agents.tracker.tools import GESTOR_PARTY, aplicar_cobertura, enviar, refuse
from escalista.domain.contracts import ExceptionCard, LLMUnavailableError, Role
from escalista.domain.ports import (
    AtestadoReader,
    Channel,
    Clock,
    ExceptionQueue,
    PunchSource,
    Repository,
    TrackRepository,
)
from escalista.domain.results import Approval, ScheduleVersion
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import Employee, Schedule
from escalista.domain.tracking import (
    Attachment,
    Case,
    CaseView,
    ChannelMessage,
    Offer,
    ReplanReason,
    ToolRefusedError,
    TrackPolicy,
    Trigger,
    shift_ref,
)
from escalista.verifier import verify

CHANNEL = "celular simulado"
SWEEP_RUN = "track-sweep"  # rastro dos eventos sem caso (remetente rejeitado, varredura)
CLOSED: frozenset[str] = frozenset({"coberto", "descoberto", "atraso_registrado", "decidido"})
COVER_FAILED = "rx12:cover"  # marca no `Case.handled`: o RX-12 aberto é o da busca de cobertura (bloqueia o caso)
OVERTIME_RULE = "pol_aviso_necessidade_hora_extra"


@dataclass(frozen=True)
class World:
    """A rede de uma escala publicada: pessoas, nomes das lojas e o cartão de regras da semana."""

    employees: list[Employee]
    store_names: dict[str, str]
    card: RuleCard


class TrackerError(Exception):
    """Erro de uso do acompanhamento; a API mapeia `status` para HTTP (404, 409, 422, 403)."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class Tracker:
    def __init__(
        self,
        *,
        repo: Repository,
        cases: TrackRepository,
        queue: ExceptionQueue,
        channel: Channel,
        tracer: Tracer,
        clock: Clock,
        policy: TrackPolicy,
        policy_cards: dict[str, dict[str, Any]],
        world: Callable[[ScheduleVersion], World],
        reader: AtestadoReader | None = None,
        punches: PunchSource | None = None,
        cover_fn: CoverFn = find_cover,
        new_id: Callable[[], str] = lambda: uuid4().hex,
    ) -> None:
        self._repo = repo
        self._cases = cases
        self._queue = queue
        self._channel = channel
        self._tracer = tracer
        self._clock = clock
        self._policy = policy
        self._policy_cards = policy_cards
        self._world = world
        self._reader = reader
        self._punches = punches
        self._cover_fn = cover_fn
        self._new_id = new_id
        self._searches: dict[str, CoverOutcome] = {}  # só cache: sem ele, a busca é refeita a partir das tabelas
        self._lock = threading.RLock()

    # --- entrada do colaborador ---------------------------------------------------------------------------------

    def report(
        self,
        *,
        employee_id: str,
        day: date,
        kind: Literal["falta", "atraso"],
        text: str | None = None,
        attachment: Attachment | None = None,
    ) -> CaseView:
        """Aviso de falta ou de atraso pelo celular simulado (SAIDA-AC-03). `text` só vira `has_text`."""
        has_text = bool(text and text.strip())
        with self._lock:
            version = self._published()
            world = self._world(version)
            shift = next(
                (s for s in version.schedule.shifts if s.employee_id == employee_id and s.start.date() == day), None
            )
            if shift is None:
                raise TrackerError(422, "não há turno dessa pessoa nesse dia na escala publicada")
            if any(c.shift == shift for c in self._cases.list_cases()):
                raise TrackerError(409, "já existe um caso para esse turno")
            case = Case(
                id=self._new_id(),
                kind=kind,
                origin="aviso",
                employee_id=employee_id,
                shift=shift,
                status="aguardando_colaborador",
                created_at=self._clock.now(),
            )
            self._cases.save_case(case)
            received = self._tracer.step(
                case.run_id,
                "track.report.received",
                payload={
                    "case_id": case.id,
                    "employee_id": employee_id,
                    "kind": kind,
                    "day": day.isoformat(),
                    "channel": CHANNEL,
                    "has_text": has_text,
                    "has_attachment": attachment is not None,
                    "media_type": attachment.media_type if attachment else None,
                },
            )
            if kind == "atraso":
                self._send(case, employee_id, "atraso_recebido", received.id)
                name = first_name(self._name(world, employee_id))
                self._send(case, GESTOR_PARTY, "atraso_aviso", received.id, pessoa=name)
                case.status = "atraso_registrado"
                self._close(case, "atraso_registrado")
                return self._save(case)
            self._send(case, employee_id, "recebido", received.id)
            self._cases.save_case(case)
            if attachment is not None:
                self._read(case, attachment, world)
            self._replan(case, version, world, reason="falta", origin=received.id)
            return self._save(case)

    def attach(self, case_id: str, attachment: Attachment) -> CaseView:
        """Comprovação mandada depois do aviso: lê, abre o abono provisório e, se preciso, o RX-08 ou o RX-12."""
        with self._lock:
            case = self._load(case_id)
            version = self._published()
            self._read(case, attachment, self._world(version))
            return self._save(case)

    def respond_offer(self, *, offer_id: str, employee_id: str, accept: bool) -> CaseView:
        """O colega aceita ou recusa (SAIDA-AC-04). Só o próprio candidato responde; o aceite vai ao gestor."""
        with self._lock:
            found = next(((c, o) for c in self._cases.list_cases() for o in c.offers if o.id == offer_id), None)
            if found is None:
                raise TrackerError(404, "oferta não encontrada")
            case, offer = found
            if offer.status != "enviada":
                raise TrackerError(409, "esta oferta já foi respondida ou venceu")
            if employee_id != offer.candidate_id:
                refused = refuse(self._tracer, case, "respond_offer", "quem respondeu não é o candidato da oferta")
                raise TrackerError(403, refused.reason) from refused
            payload = {"case_id": case.id, "offer_id": offer.id, "candidate_id": offer.candidate_id}
            if not accept:
                offer.status = "recusada"
                self._tracer.step(case.run_id, "track.offer.declined", payload=payload)
                return self._advance(case)
            offer.status = "aceita"
            accepted = self._tracer.step(case.run_id, "track.offer.accepted", payload=payload)
            self._send(case, offer.candidate_id, "aceite_recebido", accepted.id)
            self._open_card(case, self._cobertura_card(case, offer))
            case.status = "aguardando_gestor"
            return self._save(case)

    def inbound(self, sender: str) -> bool:
        """RX-10: remetente fora do quadro da escala publicada é rejeitado, sem caso nem resposta; só o hash vai ao
        rastro (SAIDA-AC-18)."""
        if sender in {e.id for e in self.people()}:
            return True
        digest = sha256(sender.encode("utf-8")).hexdigest()[:12]
        self._tracer.step(SWEEP_RUN, "track.channel.rejected", payload={"sender_hash": digest})
        return False

    # --- decisão do gestor --------------------------------------------------------------------------------------

    def on_decision(
        self,
        *,
        case_id: str,
        code: str,
        option_index: int,
        approver_id: str,
        role: Role,
        decision_event_id: str | None = None,
    ) -> str:
        """Efeito da decisão do gestor num cartão do acompanhamento (`source.kind == "track"`). Devolve o texto do
        resultado. `decision_event_id`: o `exception.decided` gravado pela fila (sem ele, o último evento do caso)."""
        with self._lock:
            case = self._load(case_id)
            ref = decision_event_id or self._tracer.parent(case.run_id) or ""
            if code == "COBERTURA":
                return self._decide_cobertura(case, option_index, approver_id, role)
            if code in ("RX-05", "RX-06"):
                self._require(case, "aguardando_gestor")
                if cards.option_label(self._policy_cards.get(code), option_index) == cards.UNCOVERED_LABEL:
                    return self._uncovered(case)
                return self._decided(case)
            if code == "RX-09":
                return self._decide_rx09(case, option_index, ref)
            if code == "RX-12" and COVER_FAILED in case.handled and case.status == "aguardando_gestor":
                case.handled.remove(COVER_FAILED)
                if option_index == 0:
                    version = self._published()
                    self._replan(case, version, self._world(version), reason=self._reason(case), origin=ref)
                    self._save(case)
                    return "Busca de cobertura refeita."
                return self._uncovered(case)
            if code in ("RX-08", "RX-12"):  # cartões da comprovação: não mexem no estado do turno
                if option_index == 1:
                    self._send(case, case.employee_id, "pedir_comprovacao", ref)
                    self._save(case)
                    return "Pedi ao colaborador uma nova comprovação; a mensagem ficou registrada."
                return "Decisão registrada; o abono segue provisório."
            raise TrackerError(422, f"cartão sem efeito no acompanhamento: {code}")

    def _decide_cobertura(self, case: Case, option_index: int, approver_id: str, role: Role) -> str:
        self._require(case, "aguardando_gestor")
        accepted = next((o for o in reversed(case.offers) if o.status == "aceita"), None)
        if accepted is None:
            raise TrackerError(409, "não há oferta aceita neste caso")
        if option_index == 0:
            return self._apply(case, accepted, approver_id, role)
        if option_index == 1:
            accepted.status = "recusada"
            self._tracer.step(
                case.run_id,
                "track.offer.declined",
                payload={"case_id": case.id, "offer_id": accepted.id, "candidate_id": accepted.candidate_id},
            )
            self._advance(case)
            return "Oferta desfeita; o próximo da lista recebe a oferta."
        if option_index == 2:
            return self._uncovered(case)
        raise TrackerError(422, "opção inexistente neste cartão")

    def _decide_rx09(self, case: Case, option_index: int, ref: str) -> str:
        if case.status in CLOSED:
            raise TrackerError(409, "este caso já foi encerrado")
        if option_index == 0:
            case.kind = "falta"
            version = self._published()
            self._replan(case, version, self._world(version), reason=self._reason(case), origin=ref)
            self._save(case)
            return "Tratado como falta; a busca de cobertura começou."
        if option_index == 1:
            case.asked_at = self._clock.now()
            self._send(case, case.employee_id, "pergunta", ref)
            self._save(case)
            return "Perguntei de novo ao colaborador; espero mais um prazo de resposta."
        case.status = "atraso_registrado"
        self._close(case, "atraso_registrado")
        self._save(case)
        return "Atraso registrado, sem cobertura."

    def _apply(self, case: Case, accepted: Offer, approver_id: str, role: Role) -> str:
        """Validação: versão nova com o turno reatribuído, aprovação gravada e publicação pelo portão."""
        if role != Role.GESTOR:
            raise TrackerError(403, "só o gestor valida a cobertura")
        latest = self._published()
        if case.shift not in latest.schedule.shifts:
            raise TrackerError(409, "a escala publicada mudou desde a falta; ela não se aplica")
        world = self._world(latest)
        now = self._clock.now()
        others = [s for s in latest.schedule.shifts if s != case.shift]
        moved = case.shift.model_copy(update={"employee_id": accepted.candidate_id})
        schedule = Schedule(week_start=latest.schedule.week_start, shifts=[*others, moved])
        report = verify(schedule, world.card)
        version = ScheduleVersion(
            id=f"ver-{self._new_id()}",
            run_id=latest.run_id,
            schedule=schedule,
            status="draft",
            input_hash=latest.input_hash,
            seed=latest.seed,
            violations_total=report.total,
            created_at=now,
        )
        self._repo.save_version(version)
        approval = Approval(
            id=f"apr-{self._new_id()[:12]}", version_id=version.id, approved_by=approver_id, role=role, at=now
        )
        self._repo.record_approval(approval)
        self._tracer.human(
            case.run_id,
            "approval.recorded",
            payload={"approval_id": approval.id, "version_id": version.id, "role": role.value},
        )
        try:
            aplicar_cobertura(repo=self._repo, tracer=self._tracer, case=case, version_id=version.id)
        except (ToolRefusedError, PublishRefusedError) as exc:
            raise TrackerError(409, exc.reason) from exc
        before = {(v.rule_id, v.employee_id, v.day) for v in verify(latest.schedule, world.card).violations}
        new_violations = len({(v.rule_id, v.employee_id, v.day) for v in report.violations} - before)
        republished = self._tracer.step(
            case.run_id,
            "schedule.republished",
            payload={
                "case_id": case.id,
                "from_version": latest.id,
                "to_version": version.id,
                "absent_id": case.employee_id,
                "cover_id": accepted.candidate_id,
            },
        )
        self._send(case, accepted.candidate_id, "cobertura_confirmada", republished.id)
        self._send(case, case.employee_id, "falta_coberta", republished.id)
        case.status = "coberto"
        self._close(case, "coberta", new_violations=new_violations, overtime=str(accepted.overtime_hours))
        self._save(case)
        return f"Escala republicada com o turno reatribuído ({report.total} violações das regras)."

    # --- ofertas ------------------------------------------------------------------------------------------------

    def advance_offer(self, case: Case | str, *, outcome: Literal["vencida", "recusada"] = "vencida") -> CaseView:
        """Fecha a oferta em aberto (`vencida` por padrão, como na varredura) e oferece ao próximo da ordem, até
        `policy.max_candidates`; sem próximo, RX-06 ao gestor."""
        with self._lock:
            loaded = self._load(case) if isinstance(case, str) else case
            current = loaded.offers[-1] if loaded.offers else None
            if current is not None and current.status == "enviada":
                current.status = outcome
                kind = "track.offer.expired" if outcome == "vencida" else "track.offer.declined"
                self._tracer.step(
                    loaded.run_id,
                    kind,
                    payload={"case_id": loaded.id, "offer_id": current.id, "candidate_id": current.candidate_id},
                )
            return self._advance(loaded)

    def _advance(self, case: Case) -> CaseView:
        last_rank = max((o.rank for o in case.offers), default=0)
        outcome = self._outcome(case)
        if outcome is None:
            self._cover_failed(case)
            return self._save(case)
        by_id = {c.employee.id: c for c in outcome.candidates}
        rank = last_rank + 1
        while rank <= min(self._policy.max_candidates, len(case.ranked)):
            candidate = by_id.get(case.ranked[rank - 1])
            if candidate is not None:
                self._offer(case, candidate, rank)
                return self._save(case)
            rank += 1  # deixou de ser elegível desde a busca: passa ao seguinte
        version = self._published()
        world = self._world(version)
        evidence = [
            f"Turno: {shift_label(case.shift)}, {self._store(world, case)}",
            f"Ofertas sem aceite: {len(case.offers)} de no máximo {self._policy.max_candidates}.",
        ]
        card = cards.policy_card(self._policy_cards["RX-06"], self._clock.now(), evidence)
        self._open_card(case, self._titled(card, case, world))
        case.status = "aguardando_gestor"
        return self._save(case)

    def _offer(self, case: Case, candidate: CoverCandidate, rank: int) -> None:
        now = self._clock.now()
        offer = Offer(
            id=f"of-{self._new_id()}",
            candidate_id=candidate.employee.id,
            rank=rank,
            sent_at=now,
            deadline=now + timedelta(minutes=self._policy.offer_deadline_min),
            overtime_hours=candidate.overtime_hours,
            added_cost=candidate.added_cost,
        )
        case.offers.append(offer)
        case.status = "oferta_enviada"
        sent = self._tracer.step(
            case.run_id,
            "track.offer.sent",
            payload={
                "case_id": case.id,
                "offer_id": offer.id,
                "candidate_id": offer.candidate_id,
                "rank": rank,
                "deadline": offer.deadline.isoformat(),
            },
        )
        self._send(
            case,
            offer.candidate_id,
            "oferta",
            sent.id,
            hora_extra=overtime_label(offer.overtime_hours),
            prazo=deadline_label(offer.deadline),
        )

    # --- replanejamento -----------------------------------------------------------------------------------------

    def _replan(self, case: Case, version: ScheduleVersion, world: World, *, reason: ReplanReason, origin: str) -> None:
        request = request_for(case, reason=reason, request_id=f"rp-{self._new_id()}", origin_trace_id=origin)
        case.replan = request
        self._tracer.step(
            case.run_id,
            "track.replan.requested",
            payload={
                "replan_id": request.id,
                "case_id": case.id,
                "window_start": request.window_start.isoformat(),
                "window_end": request.window_end.isoformat(),
                "absent_id": request.absent_id,
                "reason": reason,
            },
        )
        started = time.perf_counter()
        try:
            outcome = dispatch(
                request,
                cover_fn=self._cover_fn,
                schedule=version.schedule,
                shift=case.shift,
                employees=world.employees,
                card=world.card,
            )
        except Exception:  # noqa: BLE001 -- qualquer falha da busca vira RX-12, nunca erro solto (RN-05)
            self._cover_failed(case)
            return
        self._searches[case.id] = outcome
        case.ranked = outcome.ranked
        self._tracer.step(
            case.run_id,
            "track.cover.searched",
            started=started,
            payload={
                "replan_id": request.id,
                "evaluated": outcome.evaluated,
                "eligible": len(outcome.candidates),
                "ranked": outcome.ranked,
                "overtime_needed": outcome.overtime_needed,
            },
        )
        if not outcome.candidates:
            evidence = [
                f"Turno: {shift_label(case.shift)}, {self._store(world, case)}",
                f"Avaliados {outcome.evaluated} colegas de folga; nenhum cobre sem violar regra.",
            ]
            card = cards.policy_card(self._policy_cards["RX-05"], self._clock.now(), evidence)
            self._open_card(case, self._titled(card, case, world))
            case.status = "aguardando_gestor"
            return
        best = outcome.candidates[0]
        if outcome.overtime_needed:
            self._overtime_needed(case, best)
        self._offer(case, best, 1)

    def _overtime_needed(self, case: Case, best: CoverCandidate) -> None:
        """RF-28: o melhor candidato gera hora extra; o gestor é avisado antes de qualquer aceite."""
        trigger = Trigger(
            kind="overtime_needed",
            employee_id=best.employee.id,
            ref=shift_ref(case.shift),
            observed=f"{best.overtime_hours}h",
            threshold="0h",
            rule_ref=OVERTIME_RULE,
        )
        if trigger.key in case.handled:
            return
        case.handled.append(trigger.key)
        fired = self._tracer.step(
            case.run_id,
            "track.trigger.fired",
            rule_ref=trigger.rule_ref,
            payload={
                "trigger": trigger.kind,
                "employee_id": trigger.employee_id,
                "ref": trigger.ref,
                "observed": trigger.observed,
                "threshold": trigger.threshold,
            },
        )
        self._send(case, GESTOR_PARTY, "aviso_hora_extra", fired.id, hora_extra=overtime_label(best.overtime_hours))

    def _outcome(self, case: Case) -> CoverOutcome | None:
        """A busca do caso: do cache ou refeita sobre a escala publicada (determinística). `None` se falhar."""
        if case.id in self._searches:
            return self._searches[case.id]
        if case.replan is None:
            return None
        version = self._repo.latest_published()
        if version is None:
            return None
        world = self._world(version)
        try:
            outcome = dispatch(
                case.replan,
                cover_fn=self._cover_fn,
                schedule=version.schedule,
                shift=case.shift,
                employees=world.employees,
                card=world.card,
            )
        except Exception:  # noqa: BLE001 -- quem chama trata como RX-12
            return None
        self._searches[case.id] = outcome
        return outcome

    def _cover_failed(self, case: Case) -> None:
        version = self._repo.latest_published()
        store = self._store(self._world(version), case) if version else case.shift.store_id
        if COVER_FAILED not in case.handled:
            case.handled.append(COVER_FAILED)
        self._open_card(case, cards.rx12_cover_card(self._clock.now(), case.shift, store))
        case.status = "aguardando_gestor"

    # --- comprovação --------------------------------------------------------------------------------------------

    def _read(self, case: Case, attachment: Attachment, world: World) -> None:
        """Lê a comprovação pela porta; falha do leitor (ou sem leitor) vira RX-12 e o fluxo segue."""
        reading = None
        if self._reader is not None:
            try:
                reading = self._reader(
                    data=attachment.data,
                    media_type=attachment.media_type,
                    run_id=case.run_id,
                    expected_day=case.shift.start.date(),
                    employee_name=self._name(world, case.employee_id),
                )
            except LLMUnavailableError:
                reading = None
        case.reading = reading
        case.abono = "provisorio"
        if reading is not None:
            self._tracer.step(
                case.run_id,
                "track.atestado.read",
                payload={
                    "case_id": case.id,
                    "verdict": reading.verdict,
                    "reasons": list(reading.reasons),
                    "issued_on": reading.issued_on.isoformat() if reading.issued_on else None,
                    "start_on": reading.start_on.isoformat() if reading.start_on else None,
                    "days": reading.days,
                    "legible": reading.legible,
                },
            )
        self._tracer.step(
            case.run_id,
            "track.abono.provisional",
            payload={"case_id": case.id, "employee_id": case.employee_id, "days": reading.days if reading else None},
        )
        if reading is None:
            self._open_card(case, cards.rx12_reading_card(self._clock.now(), case.shift))
        elif reading.verdict != "valido":
            evidence = [
                f"Turno: {shift_label(case.shift)}, {self._store(world, case)}",
                f"Leitura: {reading.verdict}; motivos: {', '.join(reading.reasons) or 'nenhum'}.",
                "Abono provisório até a sua confirmação.",
            ]
            card = cards.policy_card(self._policy_cards["RX-08"], self._clock.now(), evidence)
            self._open_card(case, self._titled(card, case, world))
        self._cases.save_case(case)

    # --- leitura ------------------------------------------------------------------------------------------------

    def case(self, case_id: str) -> CaseView:
        return CaseView.of(self._load(case_id))

    def cases(self) -> list[CaseView]:
        return [CaseView.of(c) for c in self._cases.list_cases()]

    def inbox(self, employee_id: str) -> list[ChannelMessage]:
        return self._channel.inbox(employee_id)

    def people(self) -> list[Employee]:
        """O quadro da escala publicada (o seletor "Você é:" do celular simulado)."""
        version = self._repo.latest_published()
        return list(self._world(version).employees) if version is not None else []

    # --- apoio --------------------------------------------------------------------------------------------------

    def _published(self) -> ScheduleVersion:
        version = self._repo.latest_published()
        if version is None:
            raise TrackerError(409, "a escala da semana ainda não foi publicada")
        return version

    def _load(self, case_id: str) -> Case:
        case = self._cases.get_case(case_id)
        if case is None:
            raise TrackerError(404, "caso não encontrado")
        return case

    def _save(self, case: Case) -> CaseView:
        self._cases.save_case(case)
        return CaseView.of(case)

    def _require(self, case: Case, status: str) -> None:
        if case.status != status:
            raise TrackerError(409, f"o caso está em '{case.status}', não em '{status}'")

    @staticmethod
    def _reason(case: Case) -> ReplanReason:
        return "no_punch" if case.origin == "ponto" else "falta"

    @staticmethod
    def _name(world: World, employee_id: str) -> str:
        return next((e.name for e in world.employees if e.id == employee_id), employee_id)

    @staticmethod
    def _store(world: World, case: Case) -> str:
        return world.store_names.get(case.shift.store_id, case.shift.store_id)

    def _titled(self, card: ExceptionCard, case: Case, world: World) -> ExceptionCard:
        title = f"{card.title} · {self._name(world, case.employee_id)} · {shift_label(case.shift)}"
        return card.model_copy(update={"title": title})

    def _cobertura_card(self, case: Case, offer: Offer) -> ExceptionCard:
        version = self._published()
        world = self._world(version)
        cover = next((e for e in world.employees if e.id == offer.candidate_id), None)
        outcome = self._searches.get(case.id)
        return cards.cobertura_card(
            now=self._clock.now(),
            shift=case.shift,
            store=self._store(world, case),
            absent_name=self._name(world, case.employee_id),
            cover_name=cover.name if cover else offer.candidate_id,
            cover_job=cover.job if cover else "Colega",
            overtime_hours=offer.overtime_hours,
            added_cost=offer.added_cost,
            evaluated=outcome.evaluated if outcome else None,
            eligible=len(outcome.candidates) if outcome else len(case.ranked),
        )

    def _open_card(self, case: Case, card: ExceptionCard) -> str:
        item_id = self._queue.open(card, {"kind": "track", "case_id": case.id, "run_id": case.run_id})
        case.exception_ids.append(item_id)
        self._tracer.step(case.run_id, "exception.raised", payload={"exception_id": item_id, "code": card.code})
        return item_id

    def _send(self, case: Case, to: str, template: str, decision_ref: str, **fields: str) -> ChannelMessage:
        body = render(template, shift=case.shift, **fields)
        return enviar(
            channel=self._channel,
            tracer=self._tracer,
            case=case,
            to=to,
            template=template,
            body=body,
            decision_ref=decision_ref,
            new_id=self._new_id,
        )

    def _uncovered(self, case: Case) -> str:
        case.status = "descoberto"
        self._close(case, "descoberta")
        self._save(case)
        return "O turno fica descoberto; a escala publicada não muda."

    def _decided(self, case: Case) -> str:
        case.status = "decidido"
        self._close(case, "decidida")
        self._save(case)
        return "Decisão registrada. Nesta demo, nada além do registro é feito automaticamente."

    def _close(self, case: Case, outcome: str, *, new_violations: int = 0, overtime: str = "0") -> None:
        now = self._clock.now()
        case.closed_at = now
        self._tracer.step(
            case.run_id,
            "track.case.closed",
            payload={
                "case_id": case.id,
                "outcome": outcome,
                "minutes_to_close": int((now - case.created_at).total_seconds() // 60),
                "new_violations": new_violations,
                "overtime_hours_added": overtime,
            },
        )
