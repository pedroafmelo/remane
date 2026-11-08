"""Contratos do acompanhamento de escala (FT-03; plano da C7, seção 5.1; contrato com os evals, SAIDA-AC-01 a 18).

Puro: só tipos. O estado do caso vive na tabela `track_case` (JSON do `Case`), as mensagens em `channel_message`.
RN-06: nenhum modelo aqui tem campo de CID, de nome do médico, de texto livre do colaborador ou de imagem persistida;
`Attachment` existe só em memória e nunca é gravado.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from escalista.domain.schedule import Shift

MediaType = Literal["application/pdf", "image/png", "image/jpeg"]


class Attachment(BaseModel):
    """Comprovação recebida (PDF ou foto). **Só em memória**: nunca persistida nem enviada ao rastro (RN-06)."""

    model_config = ConfigDict(frozen=True)

    data: bytes = Field(repr=False)
    media_type: MediaType
    filename: str = Field(default="anexo", repr=False)


class Punch(BaseModel):
    """Batida do ponto simulado."""

    model_config = ConfigDict(frozen=True)

    employee_id: str
    shift_start: datetime
    kind: Literal["in", "out"]
    at: datetime


class Deviation(BaseModel):
    """Desvio plantado no ponto simulado (`data/demo/acompanhamento/ponto_desvios.json`)."""

    model_config = ConfigDict(frozen=True)

    id: str
    employee_id: str
    shift_start: datetime
    kind: Literal["falta", "atraso", "hora_extra"]
    minutes: int = 0


TriggerKind = Literal[
    "no_punch", "no_answer", "offer_expired", "overtime_near_limit", "overtime_limit", "overtime_needed", "weekly_check"
]


class Trigger(BaseModel):
    """Gatilho do varredor (SAIDA-AC-06). `ref` é o id do turno (`<employee_id>@<início ISO>`) ou da oferta."""

    model_config = ConfigDict(frozen=True)

    kind: TriggerKind
    employee_id: str | None = None
    ref: str
    observed: str
    threshold: str
    rule_ref: str

    @property
    def key(self) -> str:
        """Chave de idempotência: o mesmo gatilho (tipo + referência) só é tratado uma vez."""
        return f"{self.kind}:{self.ref}"


def shift_ref(shift: Shift) -> str:
    """Referência estável de um turno: `<employee_id>@<início ISO>`."""
    return f"{shift.employee_id}@{shift.start.isoformat()}"


class AtestadoFields(BaseModel):
    """O que o modelo devolve ao ler a comprovação. Schema fechado: sem CID, sem médico, sem texto livre."""

    model_config = ConfigDict(extra="forbid")

    legible: bool
    issued_on: date | None = None
    start_on: date | None = None
    days: int | None = Field(default=None, ge=1, le=30)
    patient_matches: bool | None = None
    has_crm: bool | None = None


Reason = Literal["data_nao_bate", "sem_data", "sem_crm", "nome_nao_bate", "ilegivel", "dias_fora_da_faixa"]
Verdict = Literal["valido", "inconsistente", "ilegivel"]


class AtestadoReading(AtestadoFields):
    """Leitura julgada: `verdict` e `reasons` são calculados em código (`rules/atestado.judge`), nunca pelo modelo."""

    verdict: Verdict
    reasons: list[Reason] = Field(default_factory=list)


ReplanReason = Literal["falta", "atraso", "no_punch", "overtime_limit"]


class ReplanRequest(BaseModel):
    """Pedido de replanejamento do acompanhamento à otimização (arquitetura, seções 4 e 8)."""

    id: str
    case_id: str
    window_start: datetime
    window_end: datetime
    absent_id: str
    reason: ReplanReason
    origin_trace_id: str | None = None


OfferStatus = Literal["enviada", "aceita", "recusada", "vencida"]


class Offer(BaseModel):
    id: str
    candidate_id: str
    rank: int  # 1 = o primeiro da ordem do `find_cover`
    status: OfferStatus = "enviada"
    sent_at: datetime
    deadline: datetime
    overtime_hours: Decimal
    added_cost: Decimal


CaseStatus = Literal[
    "aguardando_colaborador",
    "oferta_enviada",
    "aguardando_gestor",
    "coberto",
    "descoberto",
    "atraso_registrado",
    "decidido",
]
CaseKind = Literal["falta", "atraso"]


class Case(BaseModel):
    """Um caso do acompanhamento (tabela `track_case`). `run_id` do rastro: `track-<id>`."""

    id: str
    kind: CaseKind
    origin: Literal["aviso", "ponto"]
    employee_id: str
    shift: Shift
    status: CaseStatus
    created_at: datetime
    abono: Literal["provisorio", "nenhum"] = "nenhum"
    reading: AtestadoReading | None = None
    replan: ReplanRequest | None = None
    ranked: list[str] = Field(default_factory=list)  # ordem dos candidatos do `find_cover`
    offers: list[Offer] = Field(default_factory=list)
    exception_ids: list[str] = Field(default_factory=list)
    handled: list[str] = Field(default_factory=list)  # `Trigger.key` já tratados (idempotência)
    asked_at: datetime | None = None  # quando o agente perguntou ao colaborador (gatilho `no_punch`)
    closed_at: datetime | None = None

    @property
    def run_id(self) -> str:
        return f"track-{self.id}"


class ChannelMessage(BaseModel):
    """Mensagem do canal (RH-06). Entrada: `body` só no chat (C7b), já sem CID nem campo protegido (RN-06: o canal
    corta antes de gravar); as outras entradas guardam só metadados."""

    id: str
    case_id: str | None = None
    direction: Literal["in", "out"]
    party: str  # employee_id ou "gestor"
    template: str
    body: str | None = None
    has_text: bool = False
    attachment_media_type: str | None = None
    decision_ref: str | None = None  # id do `trace_event` da decisão que gerou a mensagem
    at: datetime


class TrackPolicy(BaseModel):
    """Parâmetros da política fictícia lidos por `rules/tracking_policy.py` (`pol_atraso`, `pol_oferta_turno`,
    `pol_hora_extra`, `pol_aviso_hora_extra_estourando`)."""

    model_config = ConfigDict(frozen=True)

    late_tolerance_min: int
    answer_deadline_min: int
    offer_deadline_min: int
    max_candidates: int
    overtime_weekly_limit_h: Decimal
    overtime_warn_pct: int
    late_cover_from_min: int | None = (
        None  # `pol_atraso.cobertura_a_partir_de_min`; `None` = atraso nunca abre cobertura
    )

    def late_opens_cover(self, minutes_late: int | None) -> bool:
        """O atraso abre a busca de cobertura (C7b, seção 5)? Sem limite na política ou sem minutos, nunca."""
        if self.late_cover_from_min is None or minutes_late is None:
            return False
        return minutes_late >= self.late_cover_from_min


# --- chat do colaborador (C7b) ------------------------------------------------------------------------------------

ChatIntent = Literal[
    "falta",
    "atraso",
    "aceitar_oferta",
    "recusar_oferta",
    "resposta_ponto_vou",
    "resposta_ponto_nao_vou",
    "consultar_escala",
    "consultar_caso",
    "outro",
]


class ChatInterpretation(BaseModel):
    """O que o modelo devolve ao classificar a mensagem livre. Schema fechado: só a intenção e dois campos; o modelo
    nunca escreve a resposta, nunca escolhe ferramenta nem id (C7b, seção 4)."""

    model_config = ConfigDict(extra="forbid")

    intent: ChatIntent
    day: date | None = None  # só para falta e atraso
    minutes_late: int | None = Field(default=None, ge=1, le=480)


class ChatContext(BaseModel):
    """Só dados da própria pessoa, montados pelo código, para o modelo resolver "amanhã" e "aceito"."""

    model_config = ConfigDict(frozen=True)

    today: date
    own_shift_days: list[date] = Field(default_factory=list)
    open_offer_days: list[date] = Field(default_factory=list)
    open_question_days: list[date] = Field(default_factory=list)


class Reply(BaseModel):
    """O que o `Tracker.message` devolve (SAIDA-AC-17): texto de template nosso, nunca do modelo."""

    template: str
    body: str
    case_id: str | None = None
    suggestions: list[str] = Field(default_factory=list)


class OfferView(BaseModel):
    offer_id: str
    candidate_id: str
    rank: int
    status: OfferStatus
    deadline: datetime


class CaseView(BaseModel):
    """O caso como sai do `Tracker` (SAIDA-AC-03). Sem texto livre, sem CID."""

    case_id: str
    status: CaseStatus
    kind: CaseKind
    employee_id: str
    day: date
    abono: Literal["provisorio", "nenhum"]
    reading: AtestadoReading | None = None
    offers: list[OfferView] = Field(default_factory=list)
    exception_ids: list[str] = Field(default_factory=list)

    @classmethod
    def of(cls, case: Case) -> CaseView:
        return cls(
            case_id=case.id,
            status=case.status,
            kind=case.kind,
            employee_id=case.employee_id,
            day=case.shift.start.date(),
            abono=case.abono,
            reading=case.reading,
            offers=[
                OfferView(offer_id=o.id, candidate_id=o.candidate_id, rank=o.rank, status=o.status, deadline=o.deadline)
                for o in case.offers
            ],
            exception_ids=list(case.exception_ids),
        )


class TrackMetrics(BaseModel):
    """Métricas derivadas do rastro (SAIDA-AC-12). Tempos em minutos **simulados**; custo `None` = não medido."""

    cases: int
    covered: int
    coverage_rate: float | None
    median_minutes_to_cover: float | None
    new_violations_total: int
    overtime_hours_added: Decimal
    atestado_reads: int
    cost_usd_total: Decimal | None
    latency_ms_p50: int | None
    latency_ms_max: int | None


class ToolRefusedError(Exception):
    """Ferramenta com efeito chamada sem o registro humano exigido (SAIDA-AC-16)."""

    def __init__(self, tool: str, reason: str) -> None:
        super().__init__(f"{tool}: {reason}")
        self.tool = tool
        self.reason = reason


class PunchUnavailableError(Exception):
    """O ponto simulado não respondeu (RX-12)."""
