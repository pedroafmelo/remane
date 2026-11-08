"""Quadro guardado na confirmação da 1ª escala (plano da C6, seção 5.1): lojas, pessoas e padrão de demanda.

Cada confirmação acrescenta uma versão (`Repository.save_roster`); nada é sobrescrito. As semanas seguintes partem do
último quadro, sem novo upload.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from escalista.domain.reading import DemandPattern
from escalista.domain.schedule import Employee, Store


class Roster(BaseModel):
    version: int = Field(ge=1)
    stores: list[Store]
    employees: list[Employee]
    demand: list[DemandPattern]
    source_run_id: str
    confirmed_by: str  # id do usuário
    confirmed_at: datetime
