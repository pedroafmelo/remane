"""Celular simulado (C7, seção 4.3): implementa a porta `Channel` gravando em `channel_message` (RH-06).

A caixa do celular lê daqui (sondagem de 3 s). **RN-06:** o texto livre do colaborador nunca é gravado; mensagem de
entrada só carrega metadados (`has_text`, tipo do anexo).
"""

from __future__ import annotations

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from escalista.domain.tracking import ChannelMessage
from escalista.store.tracking import ChannelMessageRow


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
        """Grava a mensagem. Levanta `ValueError` se for de entrada e trouxer `body` (RN-06)."""
        if message.direction == "in" and message.body is not None:
            raise ValueError("RN-06: o texto do colaborador nunca é gravado (mensagem de entrada com body)")
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
