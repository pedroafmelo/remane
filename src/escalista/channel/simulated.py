"""Celular simulado (C7, seção 4.3): implementa a porta `Channel` gravando em `channel_message` (RH-06).

A caixa do celular lê daqui (sondagem de 3 s). **RN-06 (revisto na C7b):** CID, imagem e dado de saúde nunca são
gravados. O texto do chat (`template="chat"`) é guardado, para a conversa aparecer ao recarregar, mas só **depois**
do corte de CID (`audit.protected.strip_cid_any_case`), feito aqui, na única porta de gravação. As outras mensagens
de entrada só carregam metadados (`has_text`, tipo do anexo): `body` nelas é recusado.
"""

from __future__ import annotations

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from escalista.audit.protected import strip_cid_any_case
from escalista.domain.tracking import ChannelMessage
from escalista.store.tracking import ChannelMessageRow

CHAT_TEMPLATE = "chat"


def _to_row(message: ChannelMessage, seq: int) -> ChannelMessageRow:
    return ChannelMessageRow(
        id=message.id,
        seq=seq,
        case_id=message.case_id,
        direction=message.direction,
        party=message.party,
        template=message.template,
        body=message.body,
        has_text=message.has_text,
        attachment_media_type=message.attachment_media_type,
        decision_ref=message.decision_ref,
        at=message.at,
    )


def _to_message(row: ChannelMessageRow) -> ChannelMessage:
    return ChannelMessage(
        id=row.id,
        case_id=row.case_id,
        direction=row.direction,  # type: ignore[arg-type]
        party=row.party,
        template=row.template,
        body=row.body,
        has_text=row.has_text,
        attachment_media_type=row.attachment_media_type,
        decision_ref=row.decision_ref,
        at=row.at,
    )


class SimulatedPhone:
    """Satisfaz a porta `Channel`. A ordem de leitura é a de gravação (`seq`), não a de `at`."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def send(self, message: ChannelMessage) -> None:
        """Grava a mensagem. Entrada do chat: `body` já sem CID. Outra entrada com `body`: `ValueError` (RN-06)."""
        if message.direction == "in" and message.body is not None:
            if message.template != CHAT_TEMPLATE:
                raise ValueError("RN-06: só o texto do chat é gravado (mensagem de entrada com body)")
            message = message.model_copy(update={"body": strip_cid_any_case(message.body)})
        with Session(self._engine) as session, session.begin():
            last = session.scalar(select(func.max(ChannelMessageRow.seq)))
            session.add(_to_row(message, (last or 0) + 1))

    def inbox(self, party: str) -> list[ChannelMessage]:
        with Session(self._engine) as session:
            stmt = select(ChannelMessageRow).where(ChannelMessageRow.party == party).order_by(ChannelMessageRow.seq)
            return [_to_message(r) for r in session.scalars(stmt)]

    def all_messages(self) -> list[ChannelMessage]:
        with Session(self._engine) as session:
            stmt = select(ChannelMessageRow).order_by(ChannelMessageRow.seq)
            return [_to_message(r) for r in session.scalars(stmt)]
