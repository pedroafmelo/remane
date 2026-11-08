"""Ferramenta `publicar` e rastro dos passos (regra 5 da arquitetura, 2.1; RH-01; RN-01 a RN-03)."""

from __future__ import annotations

import time
from datetime import date, datetime
from decimal import Decimal

import pytest

from escalista.agents.optimizer.errors import PublishRefusedError
from escalista.agents.optimizer.tools import NO_MODEL, Tracer, publicar
from escalista.domain.contracts import Role
from escalista.domain.results import Approval, ScheduleVersion
from escalista.domain.schedule import Schedule
from tests.fakes import FixedClock, InMemoryRepository, ListTraceSink

RUN = "run-1"
WEEK = date(2027, 1, 11)
NOW = datetime(2027, 1, 8, 9, 30)
VERSION = "ver-1"


def _version(*, run_id: str = RUN, violations: int = 0, status: str = "draft") -> ScheduleVersion:
    return ScheduleVersion(id=VERSION, run_id=run_id, schedule=Schedule(week_start=WEEK, shifts=[]), status=status,
                           input_hash="abc", seed=42, violations_total=violations, created_at=NOW)  # fmt: skip


def _approval(*, version_id: str = VERSION, role: Role = Role.GERENTE) -> Approval:
    return Approval(id="apr-1", version_id=version_id, approved_by="demo-gerente", role=role, at=NOW)


@pytest.fixture
def sink() -> ListTraceSink:
    return ListTraceSink()


@pytest.fixture
def tracer(sink: ListTraceSink) -> Tracer:
    ids = iter(f"ev-{i}" for i in range(1, 100))
    return Tracer(sink, FixedClock(NOW), new_id=lambda: next(ids), list_events=lambda run_id: [])


@pytest.fixture
def repo() -> InMemoryRepository:
    r = InMemoryRepository()
    r.save_version(_version())
    return r


def _refused(sink: ListTraceSink) -> list:
    return [e for e in sink.events if e.kind == "schedule.publish_refused"]


# --- publicar ------------------------------------------------------------------------------------------------------


def test_publish_without_approval_is_refused(repo: InMemoryRepository, tracer: Tracer, sink: ListTraceSink) -> None:
    with pytest.raises(PublishRefusedError) as err:
        publicar(repo=repo, tracer=tracer, run_id=RUN, version_id=VERSION)

    assert "aprovação" in err.value.reason
    assert repo.get_version(VERSION).status == "draft"
    assert repo.latest_published() is None
    [event] = _refused(sink)
    assert event.run_id == RUN and event.cost_usd == Decimal(0)
    assert event.payload["reason"] == err.value.reason and event.payload["version_id"] == VERSION
    assert not [e for e in sink.events if e.kind == "schedule.publish"]


def test_publish_with_recorded_approval_publishes(
    repo: InMemoryRepository, tracer: Tracer, sink: ListTraceSink
) -> None:
    repo.record_approval(_approval())

    version = publicar(repo=repo, tracer=tracer, run_id=RUN, version_id=VERSION)

    assert version.status == "published"
    assert repo.latest_published().id == VERSION
    [event] = [e for e in sink.events if e.kind == "schedule.publish"]
    assert event.payload["version_id"] == VERSION and event.payload["approval_id"] == "apr-1"
    assert event.cost_usd == Decimal(0) and event.payload["cost_basis"] == NO_MODEL
    assert not _refused(sink)


def test_publish_reads_the_approval_in_the_tool_not_from_the_caller(repo: InMemoryRepository, tracer: Tracer) -> None:
    """Não há como passar a aprovação por argumento: a ferramenta só confia no que está gravado."""
    with pytest.raises(TypeError):
        publicar(repo=repo, tracer=tracer, run_id=RUN, version_id=VERSION, approval=_approval())  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("setup", "fragment"),
    [
        (lambda r: r.record_approval(_approval(role=Role.DP)), "papel"),
        (lambda r: r.record_approval(_approval(role=Role.COLABORADOR)), "papel"),
        (lambda r: (r.save_version(_version(run_id="outra")), r.record_approval(_approval())), "outra execução"),
        (lambda r: (r.save_version(_version(violations=3)), r.record_approval(_approval())), "violaç"),
        (lambda r: (r.save_version(_version(status="published")), r.record_approval(_approval())), "já publicada"),
    ],
    ids=["dp", "colaborador", "outra-execucao", "com-violacoes", "ja-publicada"],
)
def test_publish_refusals(repo, tracer, sink, setup, fragment) -> None:
    setup(repo)

    with pytest.raises(PublishRefusedError) as err:
        publicar(repo=repo, tracer=tracer, run_id=RUN, version_id=VERSION)

    assert fragment in err.value.reason
    assert len(_refused(sink)) == 1
    assert not [e for e in sink.events if e.kind == "schedule.publish"]


def test_publish_refuses_unknown_or_missing_version(tracer: Tracer, sink: ListTraceSink) -> None:
    repo = InMemoryRepository()
    for version_id in ("nao-existe", None):
        with pytest.raises(PublishRefusedError):
            publicar(repo=repo, tracer=tracer, run_id=RUN, version_id=version_id)
    assert len(_refused(sink)) == 2


def test_approval_recorded_for_another_version_does_not_count(repo: InMemoryRepository, tracer: Tracer) -> None:
    repo.record_approval(_approval(version_id="ver-2"))

    with pytest.raises(PublishRefusedError):
        publicar(repo=repo, tracer=tracer, run_id=RUN, version_id=VERSION)


# --- Tracer --------------------------------------------------------------------------------------------------------


def test_tracer_step_has_zero_cost_basis_latency_and_chain(tracer: Tracer, sink: ListTraceSink) -> None:
    t0 = time.perf_counter()
    time.sleep(0.005)
    first = tracer.step(RUN, "csv.validate", started=t0, payload={"rows": 3})
    second = tracer.step(RUN, "read.summary", payload={"ok": True})
    human = tracer.human(RUN, "read.confirmed")

    assert [e.id for e in sink.events] == ["ev-1", "ev-2", "ev-3"]
    assert first.parent_id is None and second.parent_id == "ev-1" and human.parent_id == "ev-2"
    assert all(e.cost_usd == Decimal(0) and e.payload["cost_basis"] == NO_MODEL for e in sink.events)
    assert first.latency_ms >= 5 and second.latency_ms == 0
    assert all(e.at == NOW for e in sink.events)
    assert first.payload["rows"] == 3 and human.payload["humano"] is True


def test_tracer_resumes_chain_from_stored_events(sink: ListTraceSink) -> None:
    stored = Tracer(sink, FixedClock(NOW), new_id=lambda: "ev-a", list_events=lambda run_id: []).step(RUN, "x")
    fresh = Tracer(sink, FixedClock(datetime(2027, 1, 9)), new_id=lambda: "ev-b", list_events=lambda r: [stored])

    assert fresh.step(RUN, "y").parent_id == "ev-a"


def test_tracer_rejects_personal_fields_in_payload(tracer: Tracer) -> None:
    for key in ("sex", "name", "nome"):
        with pytest.raises(ValueError):
            tracer.step(RUN, "x", payload={key: "F"})
