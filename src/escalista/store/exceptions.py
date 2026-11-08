"""Fila de exceções do gestor (FT-04): tabela `exception_item` e o repositório mínimo dela.

Como nas outras tabelas, o modelo inteiro fica em `data` (JSON); `status`, `code` e `created_at` existem para busca e
ordenação. `add` é idempotente pelo `id` (a semente do RX-01 pode rodar a cada subida do app).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Engine, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from escalista.db import Base
from escalista.domain.contracts import ExceptionCard, Role


class Decision(BaseModel):
    """O ato humano: qual opção, quem (conta e papel), quando e o que foi feito por causa dela."""

    option_index: int
    label: str
    by: str
    role: Role
    at: datetime
    outcome: str


class ExceptionItem(BaseModel):
    id: str
    status: Literal["open", "decided"] = "open"
    created_at: datetime
    card: ExceptionCard
    # origem: {"kind": "regras"} ou {"kind": "falta", "run_id", "version_id", "employee_id", "shift", "candidates"}
    source: dict[str, Any] = Field(default_factory=dict)
    decision: Decision | None = None


class ExceptionItemRow(Base):
    __tablename__ = "exception_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # horário de Brasília, sem fuso
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ExceptionStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, item: ExceptionItem) -> bool:
        """Grava o item se o `id` ainda não existe. Devolve se gravou."""
        with Session(self._engine) as session, session.begin():
            if session.get(ExceptionItemRow, item.id) is not None:
                return False
            session.add(
                ExceptionItemRow(
                    id=item.id,
                    status=item.status,
                    code=item.card.code,
                    created_at=item.created_at,
                    data=item.model_dump(mode="json"),
                )
            )
            return True

    def save(self, item: ExceptionItem) -> None:
        with Session(self._engine) as session, session.begin():
            row = session.get(ExceptionItemRow, item.id)
            if row is None:
                raise KeyError(item.id)
            row.status, row.data = item.status, item.model_dump(mode="json")

    def get(self, item_id: str) -> ExceptionItem | None:
        with Session(self._engine) as session:
            row = session.get(ExceptionItemRow, item_id)
            return None if row is None else ExceptionItem.model_validate(row.data)

    def list(self) -> list[ExceptionItem]:
        """Abertas primeiro (mais antigas antes), depois as decididas (mais recentes antes)."""
        with Session(self._engine) as session:
            rows = session.scalars(select(ExceptionItemRow).order_by(ExceptionItemRow.created_at)).all()
            items = [ExceptionItem.model_validate(r.data) for r in rows]
        open_ = [i for i in items if i.status == "open"]
        decided = sorted((i for i in items if i.decision), key=lambda i: i.decision.at, reverse=True)  # type: ignore[union-attr]
        return open_ + decided
