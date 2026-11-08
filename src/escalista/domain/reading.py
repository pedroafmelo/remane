"""Contratos da leitura por agente (plano da C6, seção 5.1): tabela crua, mapeamento de colunas, evidência por célula,
identidade das pessoas, padrão de demanda, capacidade e a confirmação humana.

Só forma: aplicar o mapeamento, conferir evidência e inferir demanda é das tarefas A1 a A3 (`rules/`).
Os schemas que o modelo preenche (`ColumnMapping` e seus itens) têm `extra="forbid"`.
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Weekday = Literal["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


class RawTable(BaseModel):
    """Uma aba ou página do arquivo, com as células já como texto (data ISO `2027-01-11`, hora `08:00`)."""

    name: str
    rows: list[list[str]]


class ColumnRef(BaseModel):
    """Coluna apontada pelo modelo: o índice (a partir de 0) e o texto literal da célula do cabeçalho."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    header: str


class ShiftCode(BaseModel):
    """Código de turno de uma escala em grade (ex.: `M` = 07:00 às 15:00). `evidence` é o trecho literal da legenda."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=8)
    start: time | None = None
    end: time | None = None
    off: bool = False  # folga
    evidence: str | None = None


class DayColumn(BaseModel):
    """Coluna de um dia, numa escala em grade: pela data ou só pelo dia da semana."""

    model_config = ConfigDict(extra="forbid")

    col: ColumnRef
    day: date | None = None
    weekday: Weekday | None = None


class ColumnMapping(BaseModel):
    """Mapeamento devolvido pelo modelo (nó 1) ou pela heurística. O modelo nunca devolve linhas: só diz onde estão
    os dados.

    `date`, `start`, `end` e `shift` servem ao layout `long`; `day_columns` e `shift_codes`, ao `grid`.
    """

    model_config = ConfigDict(extra="forbid")

    table: int = Field(ge=0)
    header_row: int = Field(ge=0)
    layout: Literal["long", "grid"]
    person: ColumnRef
    person_code: ColumnRef | None = None  # matrícula
    store: ColumnRef | None = None
    date: ColumnRef | None = None
    start: ColumnRef | None = None
    end: ColumnRef | None = None
    shift: ColumnRef | None = None
    day_columns: list[DayColumn] = Field(default_factory=list)
    date_order: Literal["dmy", "ymd", "mdy"] = "dmy"
    shift_codes: list[ShiftCode] = Field(default_factory=list)
    wage: ColumnRef | None = None
    notes: ColumnRef | None = None


class CellRef(BaseModel):
    """Uma célula: índice da tabela, da linha e da coluna (a partir de 0)."""

    table: int = Field(ge=0)
    row: int = Field(ge=0)
    col: int = Field(ge=0)


class ShiftEvidence(BaseModel):
    """De onde saiu o turno `shift_index` da escala lida: as células e o texto delas (invariante 1)."""

    shift_index: int = Field(ge=0)
    cells: list[CellRef]
    raw: list[str]


class IdentityCard(BaseModel):
    """Dúvida de identidade levada ao gestor (seção 7). Nunca há fusão automática."""

    id: str
    kind: Literal["homonimo", "grafia_parecida", "sem_par_no_quadro"]
    names: list[str]
    rows: list[CellRef]
    suggestion: Literal["mesma", "distintas"]
    reason: str


class DemandPattern(BaseModel):
    """Pessoas necessárias numa loja, num dia da semana (0 = segunda) e numa faixa de 30 min."""

    store_id: str
    weekday: int = Field(ge=0, le=6)
    start: time
    required: int = Field(ge=0)


class CapacityCheck(BaseModel):
    """Conta antes do solver: a demanda cabe no quadro? `max_fitting_pct` é a cobertura máxima que cabe."""

    demand_person_hours: Decimal
    capacity_person_hours: Decimal
    fits: bool
    max_fitting_pct: int = Field(ge=0)


class IdentityAnswer(BaseModel):
    """Resposta do gestor a um `IdentityCard`: mesma pessoa ou não."""

    card_id: str
    same: bool


CoveragePct = Annotated[int, Field(ge=50, le=120)]


class ConfirmInput(BaseModel):
    """O que o gestor confirma ou corrige na parada humana depois da leitura (ato humano)."""

    coverage_pct: dict[str, CoveragePct] = Field(default_factory=dict)  # por loja; ausente = 100
    hourly_wage_default: Decimal | None = Field(default=None, gt=0)
    planned_week_start: date | None = None  # segunda-feira; só na 1ª escala
    note: str = Field(default="", max_length=500)
    identity: list[IdentityAnswer] = Field(default_factory=list)

    @model_validator(mode="after")
    def _week_starts_on_monday(self) -> Self:
        if self.planned_week_start is not None and self.planned_week_start.weekday() != 0:
            raise ValueError("planned_week_start deve ser uma segunda-feira")
        return self
