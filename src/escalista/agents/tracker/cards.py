"""Cartões de exceção do acompanhamento (plano da C7, seção 8): `COBERTURA`, os da política e o RX-12.

O mapeamento das entradas de `excecoes_demo` é o mesmo de `api/excecoes.py::policy_card` (reimplementado aqui:
`agents` não importa `api`). O decisor é sempre o gestor (DEC-044) e o prazo é `agora + prazo_min`.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from escalista.agents.tracker.messages import brl, first_name, overtime_label, shift_label
from escalista.domain.contracts import ExceptionCard, ExceptionOption, Role
from escalista.domain.schedule import Shift

UNCOVERED_LABEL = "Deixar o turno descoberto"
COVER_DEADLINE_MIN = 30
READING_DEADLINE_MIN = 1440
COVER_RETRY_LABEL = "Tentar a busca de novo"
READING_RETRY_LABEL = "Pedir o atestado de novo"


def policy_card(raw: dict[str, Any], now: datetime, evidence: list[str]) -> ExceptionCard:
    """Cartão a partir de uma entrada de `excecoes_demo` (os campos espelham o `ExceptionCard`)."""
    vetoed = [f"Opção vedada: {v}" for v in raw.get("opcoes_vedadas", [])]
    return ExceptionCard(
        code=raw["code"],
        title=raw["titulo"],
        reason=raw["motivo"],
        decider=Role.GESTOR,
        deadline=now + timedelta(minutes=raw["prazo_min"]),
        evidence=[*evidence, *vetoed, f"Fonte: {raw['fonte']}"],
        options=[ExceptionOption(label=o["rotulo"], effect=o["efeito"]) for o in raw["opcoes"]],
        recommendation=raw.get("recomendacao"),
        if_no_answer=raw.get("sem_resposta"),
    )


def option_label(raw: dict[str, Any] | None, index: int) -> str | None:
    """Rótulo da opção `index` de uma entrada da política (ou `None` se não existir)."""
    options = (raw or {}).get("opcoes", [])
    return options[index]["rotulo"] if 0 <= index < len(options) else None


def rx12_reading_card(now: datetime, shift: Shift) -> ExceptionCard:
    """RX-12 da leitura do atestado: o fluxo segue com o abono provisório; nada é publicado."""
    return ExceptionCard(
        code="RX-12",
        title=f"Leitura do atestado indisponível · {shift_label(shift)}",
        reason="O leitor do atestado não respondeu. O abono segue provisório e a busca de cobertura continua.",
        decider=Role.GESTOR,
        deadline=now + timedelta(minutes=READING_DEADLINE_MIN),
        evidence=["Falha do leitor registrada no rastro do caso.", "Abono provisório até a sua confirmação."],
        options=[
            ExceptionOption(
                label="Seguir com o abono provisório", effect="O abono segue provisório até você confirmar."
            ),
            ExceptionOption(
                label=READING_RETRY_LABEL,
                effect="O agente pede ao colaborador o PDF de novo, com a mensagem registrada (RH-06).",
            ),
        ],
        recommendation="Seguir com o abono provisório.",
        if_no_answer="O abono segue provisório. Nunca há recusa automática.",
    )


def rx12_cover_card(now: datetime, shift: Shift, store: str) -> ExceptionCard:
    """RX-12 da busca de cobertura: nada é oferecido nem publicado até a sua decisão."""
    return ExceptionCard(
        code="RX-12",
        title=f"Busca de cobertura indisponível · {shift_label(shift)}",
        reason="A busca de quem cubra a falta falhou. Nenhuma oferta saiu e a escala publicada não mudou.",
        decider=Role.GESTOR,
        deadline=now + timedelta(minutes=COVER_DEADLINE_MIN),
        evidence=[f"Turno: {shift_label(shift)}, {store}", "Falha registrada no rastro do caso."],
        options=[
            ExceptionOption(label=COVER_RETRY_LABEL, effect="O agente refaz a busca e oferece ao primeiro da lista."),
            ExceptionOption(label=UNCOVERED_LABEL, effect="A escala publicada não muda."),
        ],
        recommendation=COVER_RETRY_LABEL,
        if_no_answer="O turno segue sem cobertura; nada é publicado.",
    )


def rx12_punch_card(now: datetime, reason: str) -> ExceptionCard:
    """RX-12 do ponto simulado: a varredura não inventa gatilho; nada muda até o ponto voltar."""
    return ExceptionCard(
        code="RX-12",
        title="Ponto simulado indisponível",
        reason="A varredura não conseguiu ler o ponto. Nenhum gatilho foi disparado sem as batidas.",
        decider=Role.GESTOR,
        deadline=now + timedelta(minutes=COVER_DEADLINE_MIN),
        evidence=[f"Falha: {reason}", "Registrada no rastro da varredura (track-sweep)."],
        options=[
            ExceptionOption(
                label="Tentar de novo na próxima varredura", effect="O agente lê o ponto no próximo avanço."
            ),
            ExceptionOption(label="Seguir sem o ponto", effect="Faltas só entram por aviso do colaborador."),
        ],
        recommendation="Tentar de novo na próxima varredura.",
        if_no_answer="A varredura segue tentando; nada é feito sem as batidas.",
    )


def cobertura_card(
    *,
    now: datetime,
    shift: Shift,
    store: str,
    absent_name: str,
    cover_name: str,
    cover_job: str,
    overtime_hours: Decimal,
    added_cost: Decimal,
    evaluated: int | None,
    eligible: int | None,
) -> ExceptionCard:
    """O colega aceitou: o gestor valida sempre antes de a escala mudar (plano da C7, seção 7)."""
    overtime = overtime_label(overtime_hours)
    validate = f"Validar: {cover_name} cobre · {overtime} · +{brl(added_cost)}"
    searched = (
        f"Avaliados {evaluated} colegas de folga; o verificador aprovou {eligible}."
        if evaluated is not None
        else "Candidatos aprovados pelo verificador, sem violação nova."
    )
    return ExceptionCard(
        code="COBERTURA",
        title=f"Cobertura: {cover_name} aceitou · {shift_label(shift)}",
        reason=(
            f"{first_name(absent_name)} avisou que vai faltar. Ofereci o turno pela ordem da busca e "
            f"{first_name(cover_name)} aceitou. A escala só muda com a sua validação."
        ),
        decider=Role.GESTOR,
        deadline=now + timedelta(minutes=COVER_DEADLINE_MIN),
        evidence=[
            f"Turno: {shift_label(shift)}, {store}",
            searched,
            f"Custo adicional: +{brl(added_cost)} ({overtime}), pela mesma função de custo do antes e depois.",
        ],
        options=[
            ExceptionOption(
                label=validate,
                effect=f"{cover_job}. A escala é republicada com o turno reatribuído, com a sua aprovação.",
            ),
            ExceptionOption(
                label="Recusar e oferecer ao próximo",
                effect="A oferta aceita é desfeita e o próximo da lista recebe a oferta.",
            ),
            ExceptionOption(label=UNCOVERED_LABEL, effect="A escala publicada não muda."),
        ],
        recommendation=f"{validate}: nenhuma violação nova no verificador.",
        if_no_answer="Nada é publicado sem a sua decisão; o turno segue sem cobertura.",
    )
