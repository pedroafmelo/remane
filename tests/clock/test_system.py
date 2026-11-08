from datetime import UTC, datetime, timedelta

from escalista.clock.system import SystemClock, to_brasilia_naive
from escalista.domain.ports import Clock


def test_system_clock_satisfies_port_and_is_naive_brasilia():
    clock = SystemClock()
    assert isinstance(clock, Clock)
    now = clock.now()
    assert now.tzinfo is None
    expected = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=3)
    assert abs(now - expected) < timedelta(seconds=5)


def test_to_brasilia_naive():
    assert to_brasilia_naive(datetime(2026, 11, 7, 12, 0, tzinfo=UTC)) == datetime(2026, 11, 7, 9, 0)
    assert to_brasilia_naive(datetime(2026, 11, 7, 9, 0)) == datetime(2026, 11, 7, 9, 0)
