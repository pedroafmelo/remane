from datetime import UTC, datetime

import pytest

from tests.fakes import FakeLLMClient, FixedClock, ListTraceSink


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 11, 7, 12, 0, tzinfo=UTC))


@pytest.fixture
def trace_sink() -> ListTraceSink:
    return ListTraceSink()


@pytest.fixture
def llm() -> FakeLLMClient:
    return FakeLLMClient()
