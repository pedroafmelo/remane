"""Relógio de demo persistido (C7 A1; contrato SAIDA-AC-01)."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.pool import StaticPool

from escalista.clock.demo import DEMO_CLOCK_BASE, DemoClock
from escalista.clock.tables import DemoClockRow
from escalista.db import init_db
from escalista.domain.ports import Clock


def memory_engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_default_base_is_wednesday_of_the_demo_week():
    assert DEMO_CLOCK_BASE == datetime(2027, 1, 13, 13, 55)
    assert DEMO_CLOCK_BASE.weekday() == 2  # quarta


def test_demo_clock_satisfies_port_and_starts_at_base():
    clock = DemoClock(memory_engine())
    assert isinstance(clock, Clock)
    assert clock.now() == datetime(2027, 1, 13, 13, 55)
    assert clock.now().tzinfo is None


def test_now_creates_the_single_row_with_base():
    engine = memory_engine()
    base = datetime(2027, 1, 11, 8, 0)
    DemoClock(engine, base=base).now()
    with engine.connect() as conn:
        rows = conn.execute(select(DemoClockRow.id, DemoClockRow.now, DemoClockRow.base)).all()
    assert rows == [(1, base, base)]


def test_advance_moves_forward_and_persists_across_instances():
    engine = memory_engine()
    first = DemoClock(engine)
    assert first.advance(15) == datetime(2027, 1, 13, 14, 10)
    assert first.advance(60 * 24) == datetime(2027, 1, 14, 14, 10)
    assert DemoClock(engine).now() == datetime(2027, 1, 14, 14, 10)


def test_advance_persists_in_a_file_database(tmp_path):
    url = f"sqlite:///{tmp_path}/app.db"
    DemoClock(create_engine(url)).advance(30)
    assert DemoClock(create_engine(url)).now() == datetime(2027, 1, 13, 14, 25)


@pytest.mark.parametrize("minutes", [0, -15])
def test_advance_rejects_non_positive_minutes(minutes):
    clock = DemoClock(memory_engine())
    with pytest.raises(ValueError):
        clock.advance(minutes)
    assert clock.now() == DEMO_CLOCK_BASE


def test_reset_goes_back_to_base():
    clock = DemoClock(memory_engine())
    clock.advance(60 * 24 * 7)
    assert clock.reset() == datetime(2027, 1, 13, 13, 55)
    assert clock.now() == datetime(2027, 1, 13, 13, 55)


def test_reset_without_a_row_creates_it():
    assert DemoClock(memory_engine()).reset() == DEMO_CLOCK_BASE


def test_table_is_registered_for_init_db():
    import escalista.clock.demo  # noqa: F401 (registra a tabela)

    engine = memory_engine()
    init_db(engine)
    assert "demo_clock" in inspect(engine).get_table_names()


def test_clock_creates_its_table_even_without_init_db():
    engine = memory_engine()
    DemoClock(engine).advance(15)
    assert "demo_clock" in inspect(engine).get_table_names()
