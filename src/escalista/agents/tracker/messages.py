"""Textos das mensagens do acompanhamento (RH-06): modelos fixos, sem modelo de linguagem no T1.

Cada mensagem de saída é texto nosso, montado aqui a partir de campos do caso. O texto do colaborador nunca entra
em nenhum modelo de mensagem (RN-06).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from escalista.domain.schedule import Shift

WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

TEMPLATES: dict[str, str] = {
    "recebido": "Recebi o seu aviso de falta em {turno}. Vou procurar quem cubra e aviso o gestor. Melhoras!",
    "atraso_recebido": "Recebi o seu aviso de atraso em {turno}. Já avisei o gestor.",
    "atraso_aviso": "{pessoa} avisou que vai se atrasar em {turno}. Registrei o atraso; nenhuma cobertura foi pedida.",
    "aviso_hora_extra": "A cobertura de {turno} precisa de hora extra: {hora_extra}. Nada muda sem a sua validação.",
    "oferta": "Você pode cobrir {turno}? {hora_extra_cap}. Responda até {prazo}.",
    "aceite_recebido": "Obrigado! Recebi o seu aceite para {turno}. O gestor vai validar e eu confirmo aqui.",
    "recusa_recebida": "Tudo bem, registrei que você não pode cobrir {turno}.",
    "cobertura_confirmada": "Confirmado: você cobre {turno}. A escala publicada já mostra o turno.",
    "falta_coberta": "O seu turno de {turno} está coberto. Bom descanso.",
    "pergunta": "Você não bateu o ponto às {hora} ({turno}). Você vem hoje?",
    "pedir_comprovacao": "Não consegui confirmar o seu atestado de {turno}. Pode mandar uma nova foto ou o PDF?",
}


def _hour(moment: datetime) -> str:
    return f"{moment.hour}" if moment.minute == 0 else f"{moment.hour}:{moment.minute:02d}"


def shift_label(shift: Shift) -> str:
    """'qua 13/01, 14–22h' (o padrão de horário do design system)."""
    d = shift.start
    return f"{WEEKDAYS[d.weekday()]} {d:%d/%m}, {_hour(shift.start)}–{_hour(shift.end)}h"


def overtime_label(hours: Decimal) -> str:
    return "sem hora extra" if hours == 0 else f"{hours.normalize():f}h extra".replace(".", ",")


def brl(value: Decimal) -> str:
    whole, cents = f"{value:.2f}".split(".")
    return f"R$ {int(whole):,}".replace(",", ".") + f",{cents}"


def first_name(name: str) -> str:
    return name.split()[0] if name.strip() else name


def render(template: str, *, shift: Shift, **fields: str) -> str:
    """Texto do modelo `template` com o turno já formatado. Campo ausente vira erro (modelo e chamada andam juntos)."""
    values = {"turno": shift_label(shift), **fields}
    if "hora_extra" in values:
        values.setdefault("hora_extra_cap", values["hora_extra"][:1].upper() + values["hora_extra"][1:])
    return TEMPLATES[template].format(**values)


def deadline_label(moment: datetime) -> str:
    return f"{moment:%H:%M}"
