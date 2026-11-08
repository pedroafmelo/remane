"""Tabela `trace_event` (plano da C5, seção 3.3): as colunas do `TraceEvent` v0, mais `seq`, só de ordenação.

`seq` existe porque `at` vem do relógio (o de demo pode ficar parado ou voltar) e `id` não é ordenável: a ordem de
gravação é a única ordem confiável dentro de um `run_id`. Não faz parte do contrato e nunca sai em `TraceEvent`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from escalista.db import Base


class TraceEventRow(Base):
    __tablename__ = "trace_event"
    __table_args__ = (
        CheckConstraint("key_index IS NULL OR key_index BETWEEN 1 AND 4", name="ck_trace_event_key_index"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # horário de Brasília, sem fuso
    rule_ref: Mapped[str | None] = mapped_column(String)
    message_ref: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    key_index: Mapped[int | None] = mapped_column(Integer)  # índice da chave (1 a 4), nunca o valor
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6, asdecimal=True))  # só o medido
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)  # já redigido (RN-06)
