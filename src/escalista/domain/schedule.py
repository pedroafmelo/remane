"""Contratos da rede, da demanda, da escala e da leitura do CSV (plano da C5, seção 3.1).

Datas e horas sem fuso (horário de Brasília implícito, dado sintético). Dinheiro e horas somadas em `Decimal`.
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, NaiveDatetime, model_validator


class Store(BaseModel):
    id: str
    name: str
    opens: time
    closes: time


Profile = Literal["padrao", "aprendiz", "menor"]


class Employee(BaseModel):
    """`sex` existe só para as regras que dependem dele. RN-13: nunca vai à tela, à API do gestor nem ao trace;
    para sair do núcleo, use `EmployeePublic.from_employee`."""

    id: str
    name: str
    store_id: str
    job: str  # cargo
    hourly_wage: Decimal
    contract_hours: int
    sex: Literal["F", "M"]
    profile: Profile = "padrao"


class EmployeePublic(BaseModel):
    """Os campos de `Employee` sem `sex` (RN-13, DEC-039). Não herda de `Employee`, de propósito: assim um
    `Employee` nunca passa por `EmployeePublic` e não vaza `sex` numa resposta."""

    id: str
    name: str
    store_id: str
    job: str
    hourly_wage: Decimal
    contract_hours: int
    profile: Profile = "padrao"

    @classmethod
    def from_employee(cls, employee: Employee) -> EmployeePublic:
        return cls(**employee.model_dump(exclude={"sex"}))


class DemandSlot(BaseModel):
    store_id: str
    day: date
    start: time  # início da faixa de 30 min
    required: int


class Shift(BaseModel):
    """Turno que vira a noite termina no dia seguinte."""

    employee_id: str
    store_id: str
    start: NaiveDatetime
    end: NaiveDatetime

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end deve ser posterior a start")
        return self


class Schedule(BaseModel):
    week_start: date  # segunda-feira
    shifts: list[Shift]

    @model_validator(mode="after")
    def _week_starts_on_monday(self) -> Self:
        if self.week_start.weekday() != 0:
            raise ValueError("week_start deve ser uma segunda-feira")
        return self


class CsvIssue(BaseModel):
    line: int
    field: str | None = None
    reason: str


class ReadSummary(BaseModel):
    """Resumo da leitura do CSV (RF-23), mostrado ao gestor antes de otimizar."""

    file_name: str
    rows: int
    employees: int
    stores: int
    week_start: date | None
    total_hours: Decimal
    issues: list[CsvIssue]
    ok: bool
