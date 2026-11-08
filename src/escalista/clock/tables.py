"""Tabela `demo_clock` (plano da C7, seção 4.4; contrato SAIDA-AC-01): uma linha só (`id = 1`) com o instante
simulado (`now`) e o ponto de partida (`base`). Horário de Brasília, sem fuso, como o resto do app."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from escalista.db import Base


class DemoClockRow(Base):
    __tablename__ = "demo_clock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # sempre 1
    now: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    base: Mapped[datetime] = mapped_column(DateTime, nullable=False)
