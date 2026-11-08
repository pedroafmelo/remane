"""Relógio de demo persistido (porta `Clock`; plano da C7, seção 4.4; contrato SAIDA-AC-01).

O tempo simulado só anda pelos botões (`advance`) e volta ao início por `reset`. Fica na tabela `demo_clock`, para
sobreviver a reinícios do processo e ser o mesmo para todas as requisições. Horário de Brasília, sem fuso (naive).
A tabela é registrada no `Base` ao importar este módulo (convenção de `escalista.db`) e, por garantia, criada aqui
mesmo se ainda não existir, para o relógio funcionar com ou sem `init_db`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from escalista.clock.tables import DemoClockRow

# Quarta da semana da demo (DEMO_WEEK_START = 2027-01-11), 5 min antes do turno das 14h: o `no_punch` desse turno
# cai em dois "+15 min" (contrato SAIDA-AC-01, v1.1).
DEMO_CLOCK_BASE = datetime(2027, 1, 13, 13, 55)
_ROW_ID = 1


class DemoClock:
    def __init__(self, engine: Engine, *, base: datetime = DEMO_CLOCK_BASE) -> None:
        if base.tzinfo is not None:
            raise ValueError("base deve ser horário de Brasília sem fuso (naive)")
        self._engine = engine
        self._base = base
        DemoClockRow.__table__.create(engine, checkfirst=True)

    def _row(self, session: Session) -> DemoClockRow:
        """A linha única; criada com `base` na primeira leitura."""
        row = session.get(DemoClockRow, _ROW_ID)
        if row is None:
            row = DemoClockRow(id=_ROW_ID, now=self._base, base=self._base)
            session.add(row)
        return row

    def now(self) -> datetime:
        with Session(self._engine) as session, session.begin():
            return self._row(session).now

    def advance(self, minutes: int) -> datetime:
        """Avança o tempo simulado `minutes` minutos (> 0) e devolve o novo instante."""
        if minutes <= 0:
            raise ValueError("minutes deve ser positivo: o relógio de demo só anda para a frente (use reset)")
        with Session(self._engine) as session, session.begin():
            row = self._row(session)
            row.now = row.now + timedelta(minutes=minutes)
            return row.now

    def reset(self) -> datetime:
        """Volta o tempo simulado ao início (`base`) e devolve esse instante."""
        with Session(self._engine) as session, session.begin():
            row = self._row(session)
            row.now = self._base
            row.base = self._base
            return row.now
