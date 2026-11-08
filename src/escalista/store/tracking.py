"""Tabelas `track_case` e `channel_message` (C7, seção 4.1 e 4.3) e o repositório `SqlTrackRepository`.

Como em `exception_item`, o `Case` inteiro fica em `data` (`model_dump(mode="json")`, `Decimal` como texto: sem perda);
`status`, `kind`, `employee_id` e `created_at` existem para busca e ordenação. Em `channel_message`, `seq` é a ordem de
gravação (não depende do relógio, que na demo avança aos saltos). Sem chave estrangeira, como nas demais tabelas.
RN-06: nenhuma coluna guarda texto livre do colaborador; `body` só existe nas mensagens de saída (texto nosso).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Engine, Integer, String, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from escalista.db import Base
from escalista.domain.tracking import Case


class TrackCaseRow(Base):
    __tablename__ = "track_case"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    employee_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # horário de Brasília, sem fuso
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ChannelMessageRow(Base):
    __tablename__ = "channel_message"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)  # ordem de gravação
    case_id: Mapped[str | None] = mapped_column(String, index=True)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    party: Mapped[str] = mapped_column(String, nullable=False, index=True)
    template: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str | None] = mapped_column(String)  # só saída (RN-06)
    has_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attachment_media_type: Mapped[str | None] = mapped_column(String)
    decision_ref: Mapped[str | None] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SqlTrackRepository:
    """Satisfaz a porta `TrackRepository`."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_case(self, case: Case) -> None:
        """Insere o caso ou atualiza o que já existe com o mesmo `id`."""
        with Session(self._engine) as session, session.begin():
            row = session.get(TrackCaseRow, case.id)
            if row is None:
                row = TrackCaseRow(id=case.id)
                session.add(row)
            row.status, row.kind, row.employee_id = case.status, case.kind, case.employee_id
            row.created_at, row.data = case.created_at, case.model_dump(mode="json")

    def get_case(self, case_id: str) -> Case | None:
        with Session(self._engine) as session:
            row = session.get(TrackCaseRow, case_id)
            return None if row is None else Case.model_validate(row.data)

    def list_cases(self) -> list[Case]:
        """Em ordem de `created_at` e, no empate, de `id`."""
        with Session(self._engine) as session:
            rows = session.scalars(select(TrackCaseRow).order_by(TrackCaseRow.created_at, TrackCaseRow.id)).all()
            return [Case.model_validate(r.data) for r in rows]

    def reset(self) -> None:
        """Apaga todos os casos e todas as mensagens do canal ("Reiniciar" da demo)."""
        with Session(self._engine) as session, session.begin():
            session.execute(delete(TrackCaseRow))
            session.execute(delete(ChannelMessageRow))
