"""Assistente do gestor (FT-08, DEC-017; plano da C7b, N2): **somente leitura**.

Defesa estrutural, não do prompt: o assistente só tem a porta `AssistantData` (métodos de leitura) e nenhuma ferramenta
de escrita; a implementação lê de um banco aberto como somente leitura. O modelo escolhe **uma** ferramenta de uma
lista fechada (`AssistantChoice`, schema fechado); o código valida o dia e a regra, lê e monta a resposta por template.
Nenhum texto do modelo chega ao gestor. Pessoas só pelo primeiro nome (nunca `sex`, RN-13); nada de CID. Perguntas de
lei citam só o cartão de regras, com a fonte e "não é parecer jurídico".

Rastro: `assistant.message {tool, length}` e `assistant.refused {reason}` na execução `assistant-<user_id>`; nunca o
texto da pergunta.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import date, timedelta

from escalista.agents.optimizer.tools import Tracer
from escalista.agents.tracker.messages import WEEKDAYS, first_name, shift_label
from escalista.domain.contracts import LLMUnavailableError
from escalista.domain.ports import AssistantChooser, AssistantData, Clock
from escalista.domain.tracking import AssistantChoice, AssistantContext, AssistantReply, AssistantTool

MAX_CHARS = 300
RATE_MAX = 10
RATE_WINDOW_S = 60.0
NAMES_SHOWN = 8
DISCLAIMER = "Não é parecer jurídico."

TEMPLATES: dict[str, str] = {
    "assistente_escala": "Escala publicada de {dia}: {total} turnos. {lojas}.",
    "assistente_excecoes": "{resumo}",
    "assistente_hora_extra": "{resumo} Limite da política: {limite}h por semana.",
    "assistente_regra": "{regra}: {texto} Fonte: {fonte}. Situação: {status}. " + DISCLAIMER,
    "assistente_regras": "Não achei essa regra. Regras da semana: {ids}. " + DISCLAIMER,
    "assistente_caso": 'Último caso: {tipo} de {pessoa} em {turno}, situação "{status}". Passos no rastro: {passos}.',
    "assistente_recusa": "{motivo}",
    "assistente_fora_escopo": (
        "Só leio a escala publicada, as exceções abertas, a hora extra, as regras e o rastro dos casos. Não mudo a "
        "escala nem decido por você: as decisões ficam na fila de exceções."
    ),
    "assistente_nao_entendi": (
        'Não entendi. Pergunte, por exemplo, "quais exceções estão abertas?" ou "como está a escala de quinta?".'
    ),
}
ASSISTANT_REFUSALS = {k: TEMPLATES[k] for k in ("assistente_fora_escopo", "assistente_nao_entendi")}
SUGGESTIONS = [
    "Quais exceções estão abertas?",
    "Quem faz hora extra esta semana?",
    "Como está a escala de quinta?",
    "O que diz a regra da jornada semanal?",
    "O que aconteceu no último caso?",
]
STEP_LABELS = {
    "track.report.received": "aviso recebido",
    "track.atestado.read": "atestado lido",
    "track.abono.provisional": "abono provisório",
    "track.replan.requested": "replanejamento pedido",
    "track.cover.searched": "busca de cobertura",
    "track.offer.sent": "oferta enviada",
    "track.offer.accepted": "oferta aceita",
    "track.offer.declined": "oferta recusada",
    "track.offer.expired": "oferta vencida",
    "exception.raised": "cartão ao gestor",
    "approval.recorded": "aprovação do gestor",
    "schedule.republished": "escala republicada",
    "track.case.closed": "caso encerrado",
}
STATUS_LABELS = {
    "aguardando_colaborador": "esperando o colaborador",
    "oferta_enviada": "oferta enviada",
    "aguardando_gestor": "esperando a sua decisão",
    "coberto": "coberto",
    "descoberto": "descoberto",
    "atraso_registrado": "atraso registrado",
    "decidido": "decidido",
}


class AssistantError(Exception):
    """Erro de uso; a API mapeia `status` para HTTP (422, 429)."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _day_label(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]} {day:%d/%m}"


def _hm(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    return f"{hours}h" if rest == 0 else f"{hours}h{rest:02d}"


class Assistant:
    def __init__(
        self,
        *,
        data: AssistantData,
        chooser: AssistantChooser | None,
        tracer: Tracer,
        clock: Clock,
        rate_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._data = data
        self._chooser = chooser
        self._tracer = tracer
        self._clock = clock
        self._rate_clock = rate_clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def ask(self, *, user_id: str, text: str) -> AssistantReply:
        run_id = f"assistant-{user_id}"
        with self._lock:
            self._rate(user_id, run_id)
        if not text.strip() or len(text) > MAX_CHARS:
            self._refused(run_id, "limite")
            raise AssistantError(422, f"a pergunta precisa ter de 1 a {MAX_CHARS} caracteres")
        context = self._context()
        choice: AssistantChoice | None = None
        if self._chooser is not None:
            try:
                choice = self._chooser(text=text, context=context, run_id=run_id)
            except LLMUnavailableError:
                choice = None
        if choice is None:
            self._refused(run_id, "nao_entendi")
            return self._reply("assistente_nao_entendi", None)
        self._tracer.step(run_id, "assistant.message", payload={"tool": choice.tool, "length": len(text)})
        return self._run(choice, context, run_id)

    def _run(self, choice: AssistantChoice, context: AssistantContext, run_id: str) -> AssistantReply:
        tool = choice.tool
        if tool == "get_escala":
            return self._escala(choice.day or context.today, context, run_id)
        if tool == "get_excecoes":
            items = self._data.open_exceptions()
            if not items:
                return self._reply("assistente_excecoes", tool, resumo="Nenhuma exceção aberta na fila.")
            shown = "; ".join(f"{code}: {title}" for code, title in items[:5])
            more = f" e mais {len(items) - 5}" if len(items) > 5 else ""
            noun = "exceção aberta" if len(items) == 1 else "exceções abertas"
            return self._reply("assistente_excecoes", tool, resumo=f"{len(items)} {noun}: {shown}{more}.")
        if tool == "get_hora_extra":
            people = self._data.people()
            rows = sorted(self._data.overtime(), key=lambda r: -r[1])
            if not rows:
                summary = "Ninguém com hora extra registrada no ponto simulado até agora nesta semana."
            else:
                listed = ", ".join(f"{first_name(people.get(e, e))} {_hm(m)}" for e, m in rows[:NAMES_SHOWN])
                summary = f"Hora extra registrada no ponto simulado nesta semana: {listed}."
            return self._reply("assistente_hora_extra", tool, resumo=summary, limite=self._data.overtime_limit_h())
        if tool == "get_regra":
            rules = {r.id: r for r in self._data.rules()}
            rule = rules.get(choice.rule_id or "")
            if rule is None:
                return self._reply("assistente_regras", tool, ids=", ".join(sorted(rules)) or "nenhuma")
            text = (rule.note or f"{rule.kind} {rule.params}").strip()
            if not text.endswith("."):
                text += "."
            return self._reply(
                "assistente_regra", tool, regra=rule.id, texto=text, fonte=rule.source, status=str(rule.status)
            )
        if tool == "get_trace":
            found = self._data.last_case()
            if found is None:
                return self._reply("assistente_recusa", tool, motivo="Ainda não há caso no acompanhamento.")
            case, kinds = found
            steps = [STEP_LABELS[k] for k in kinds if k in STEP_LABELS]
            return self._reply(
                "assistente_caso",
                tool,
                tipo=case.kind,
                pessoa=first_name(self._data.people().get(case.employee_id, case.employee_id)),
                turno=shift_label(case.shift),
                status=STATUS_LABELS.get(case.status, case.status),
                passos=" → ".join(steps) or "nenhum",
            )
        self._refused(run_id, "fora_de_contexto")
        return self._reply("assistente_fora_escopo", None)

    def _escala(self, day: date, context: AssistantContext, run_id: str) -> AssistantReply:
        version = self._data.published()
        if version is None:
            return self._reply("assistente_recusa", "get_escala", motivo="Ainda não há escala publicada.")
        if day not in context.week_days:
            self._refused(run_id, "dia_fora_da_semana")
            first, last = context.week_days[0], context.week_days[-1]
            motivo = f"Só leio a semana publicada: de {_day_label(first)} a {_day_label(last)}."
            return self._reply("assistente_recusa", "get_escala", motivo=motivo)
        people, stores = self._data.people(), self._data.store_names()
        shifts = sorted((s for s in version.schedule.shifts if s.start.date() == day), key=lambda s: s.start)
        by_store: dict[str, list[str]] = {}
        for s in shifts:
            by_store.setdefault(s.store_id, []).append(first_name(people.get(s.employee_id, s.employee_id)))
        parts = []
        for store_id, names in sorted(by_store.items()):
            shown = ", ".join(names[:NAMES_SHOWN]) + (
                f" e mais {len(names) - NAMES_SHOWN}" if len(names) > NAMES_SHOWN else ""
            )
            parts.append(f"{stores.get(store_id, store_id)} ({len(names)}): {shown}")
        return self._reply(
            "assistente_escala",
            "get_escala",
            dia=_day_label(day),
            total=str(len(shifts)),
            lojas="; ".join(parts) or "nenhum turno",
        )

    def _context(self) -> AssistantContext:
        version = self._data.published()
        week = [version.schedule.week_start + timedelta(days=i) for i in range(7)] if version is not None else []
        return AssistantContext(
            today=self._clock.now().date(), week_days=week, rule_ids=sorted(r.id for r in self._data.rules())
        )

    def _reply(self, template: str, tool: AssistantTool | None, **fields: str) -> AssistantReply:
        return AssistantReply(
            template=template, body=TEMPLATES[template].format(**fields), tool=tool, suggestions=list(SUGGESTIONS)
        )

    def _refused(self, run_id: str, reason: str) -> None:
        self._tracer.step(run_id, "assistant.refused", payload={"reason": reason})

    def _rate(self, user_id: str, run_id: str) -> None:
        now = self._rate_clock()
        hits = self._hits.setdefault(user_id, deque())
        while hits and hits[0] <= now - RATE_WINDOW_S:
            hits.popleft()
        if len(hits) >= RATE_MAX:
            self._refused(run_id, "taxa")
            raise AssistantError(429, f"muitas perguntas: no máximo {RATE_MAX} por minuto")
        hits.append(now)
