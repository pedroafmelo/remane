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
    # RF-27 (DEC-060): sem turno; `observado` e `limite` vêm do gatilho.
    "hora_extra_80": (
        "Aviso de hora extra: {pessoa} já tem {observado} (a política avisa em {limite}). "
        "Ainda dá para ajustar os próximos turnos."
    ),
    "hora_extra_limite": (
        "Você passou do limite de hora extra: {observado}, acima do {limite} da política. "
        "Avisei o gestor; ele decide os próximos passos."
    ),
    "hora_extra_limite_gestor": (
        "{pessoa} passou do limite de hora extra: {observado}, acima do {limite} da política. "
        "Abri um cartão para você decidir; nada muda na escala sem você."
    ),
    # C7b: atraso acima do limite da política abre a busca de cobertura, como a falta.
    "atraso_recebido_cobertura": (
        "Recebi o seu aviso de atraso de {minutos} min em {turno}. Pela política, vou procurar quem cubra e avisei o "
        "gestor."
    ),
    "atraso_aviso_cobertura": (
        "{pessoa} avisou atraso de {minutos} min em {turno}. Pela política, comecei a busca de cobertura; a escala só "
        "muda com a sua validação."
    ),
    # C7b: respostas do chat. Texto nosso; o modelo só classifica e nunca escreve aqui.
    "chat_fora_escopo": "Só posso ajudar com falta, atraso, atestado, hora extra e a sua escala.",
    "chat_nao_entendi": (
        'Não entendi. Pode escrever de outro jeito? Por exemplo: "amanhã não vou", "vou me atrasar 40 min" ou '
        '"qual é a minha escala?".'
    ),
    "chat_recusa": "{motivo}",
    "chat_escala": "Seus turnos nesta semana: {dias}.",
    "chat_caso": "{estado}",
}

# Motivos fixos da recusa no chat (`track.chat.refused {reason}` → texto ao colaborador).
CHAT_REFUSAL_TEXT: dict[str, str] = {
    "sem_oferta": "Não há oferta de cobertura aberta para você agora.",
    "oferta_ambigua": 'Você tem mais de uma oferta aberta. Diga o dia, por exemplo "aceito a de quinta".',
    "sem_pergunta": "Não há pergunta minha esperando a sua resposta agora.",
    "dia_invalido": "Não achei turno seu nesse dia. Seus turnos nesta semana: {dias}.",
    "sem_dia": "Para qual dia? Seus turnos nesta semana: {dias}.",
    "acao_recusada": "Não consegui registrar: {motivo}.",
}

CASE_STATE_TEXT: dict[str, str] = {
    "aguardando_colaborador": "O seu caso de {turno} espera a sua resposta.",
    "oferta_enviada": "O seu aviso de {turno}: ofereci o turno a um colega e espero a resposta.",
    "aguardando_gestor": "O seu aviso de {turno} está com o gestor para decidir.",
    "coberto": "O seu turno de {turno} está coberto.",
    "descoberto": "O seu turno de {turno} ficou descoberto, por decisão do gestor.",
    "atraso_registrado": "O seu atraso em {turno} está registrado.",
    "decidido": "O gestor já decidiu o seu caso de {turno}.",
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


def render(template: str, *, shift: Shift | None = None, **fields: str) -> str:
    """Texto do modelo `template` com o turno já formatado. Campo ausente vira erro (modelo e chamada andam juntos)."""
    values = {**({"turno": shift_label(shift)} if shift is not None else {}), **fields}
    if "hora_extra" in values:
        values.setdefault("hora_extra_cap", values["hora_extra"][:1].upper() + values["hora_extra"][1:])
    return TEMPLATES[template].format(**values)


def deadline_label(moment: datetime) -> str:
    return f"{moment:%H:%M}"
