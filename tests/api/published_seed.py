"""Uma escala publicada sintética da loja L1 (sem solver), gravada direto no repositório, para as rotas de exceção.

Pessoas da L1 em ordem de id, em três grupos: i % 3 == 0 de manhã (08-16h) de segunda a sexta; i % 3 == 1 à tarde
(14-22h) de quarta a domingo; i % 3 == 2 de manhã só segunda, terça e quinta. Assim P001 (5 turnos, o colaborador
da demo) tem cobertura na quarta (o terceiro grupo está de folga) e nenhuma na segunda (só o segundo grupo está de
folga, e cobrir daria 6 dias e 48h).
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import Engine

from escalista.domain.contracts import Role
from escalista.domain.results import Approval, ScheduleVersion
from escalista.domain.schedule import Schedule, Shift
from escalista.ingest.demo_network import load_demo_network
from escalista.store.sql_repository import SqlRepository

WEEK = date(2027, 1, 11)
RUN_ID = "run-semeada-publicada"
VERSION_ID = "ver-semeada-publicada"
GROUPS = {0: ([0, 1, 2, 3, 4], 8), 1: ([2, 3, 4, 5, 6], 14), 2: ([0, 1, 3], 8)}


def seeded_schedule() -> Schedule:
    _, employees, _ = load_demo_network(Path("data/demo"))
    l1 = sorted((e for e in employees if e.store_id == "L1"), key=lambda e: e.id)
    shifts = []
    for i, e in enumerate(l1):
        days, hour = GROUPS[i % 3]
        for d in days:
            begin = datetime.combine(WEEK + timedelta(days=d), time(hour))
            shifts.append(Shift(employee_id=e.id, store_id="L1", start=begin, end=begin + timedelta(hours=8)))
    return Schedule(week_start=WEEK, shifts=shifts)


def seed_published(engine: Engine) -> ScheduleVersion:
    repo = SqlRepository(engine)
    now = datetime(2027, 1, 8, 9, 0)
    version = ScheduleVersion(
        id=VERSION_ID,
        run_id=RUN_ID,
        schedule=seeded_schedule(),
        status="draft",
        input_hash="semente",
        seed=42,
        violations_total=0,
        created_at=now,
    )
    repo.save_version(version)
    repo.record_approval(
        Approval(id="apr-semente", version_id=VERSION_ID, approved_by="demo-gestor", role=Role.GESTOR, at=now)
    )
    repo.mark_published(VERSION_ID, now)
    return version
