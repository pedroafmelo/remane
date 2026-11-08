"""Tabelas `run_state`, `schedule_version`, `approval` (plano da C5, seção 3.2) e `roster_version` (C6, seção 5.2).

O modelo pydantic inteiro fica em `data` (JSON, `model_dump(mode="json")`, `Decimal` como texto: sem perda). As demais
colunas existem só para busca e ordenação. `publish_seq` é a ordem de publicação (não depende do relógio, que na demo
pode ficar parado ou voltar); `NULL` significa "nunca publicada". Sem chave estrangeira entre as tabelas, de
propósito: a porta não exige que a versão exista antes da aprovação.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from escalista.db import Base


class RunStateRow(Base):
    __tablename__ = "run_state"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    phase: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version_id: Mapped[str | None] = mapped_column(String, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ScheduleVersionRow(Base):
    __tablename__ = "schedule_version"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # horário de Brasília, sem fuso
    published_at: Mapped[datetime | None] = mapped_column(DateTime)  # idem
    publish_seq: Mapped[int | None] = mapped_column(Integer, unique=True)  # ordem de publicação
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ApprovalRow(Base):
    __tablename__ = "approval"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    version_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)  # uma aprovação por versão
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # horário de Brasília, sem fuso
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class RosterVersionRow(Base):
    """Quadro guardado: uma linha por confirmação, nunca atualizada. O mais recente é a maior `version`."""

    __tablename__ = "roster_version"

    version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # horário de Brasília, sem fuso
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
