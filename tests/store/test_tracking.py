"""`SqlTrackRepository` e `ExceptionStoreQueue` (C7, B1): mesmo comportamento do falso `InMemoryTrackRepository`."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from escalista.db import init_db, make_engine
from escalista.domain.contracts import ExceptionCard
from escalista.domain.ports import ExceptionQueue, TrackRepository
from escalista.domain.schedule import Shift
from escalista.domain.tracking import AtestadoReading, Case, Offer, ReplanRequest
from escalista.store.exceptions import ExceptionStore
from escalista.store.track_queue import ExceptionStoreQueue
from escalista.store.tracking import ChannelMessageRow, SqlTrackRepository, TrackCaseRow
from tests.fakes import FixedClock, InMemoryTrackRepository

T0 = datetime(2027, 1, 13, 13, 55)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    init_db(eng)
    return eng


@pytest.fixture(params=["memory", "sql"])
def repo(request, engine) -> TrackRepository:
    return InMemoryTrackRepository() if request.param == "memory" else SqlTrackRepository(engine)


def make_case(case_id: str = "c1", *, created_at: datetime = T0, status="aguardando_colaborador") -> Case:
    shift = Shift(employee_id="e1", store_id="s1", start=datetime(2027, 1, 13, 14), end=datetime(2027, 1, 13, 22))
    return Case(
        id=case_id, kind="falta", origin="aviso", employee_id="e1", shift=shift, status=status, created_at=created_at
    )


def full_case() -> Case:
    case = make_case("full", status="oferta_enviada")
    case.abono = "provisorio"
    case.reading = AtestadoReading(
        legible=True,
        issued_on=T0.date(),
        start_on=T0.date(),
        days=2,
        patient_matches=True,
        has_crm=True,
        verdict="valido",
    )
    case.replan = ReplanRequest(
        id="r1", case_id="full", window_start=T0, window_end=T0 + timedelta(hours=8), absent_id="e1", reason="falta"
    )
    case.ranked = ["e2", "e3"]
    case.offers = [
        Offer(
            id="o1",
            candidate_id="e2",
            rank=1,
            sent_at=T0,
            deadline=T0 + timedelta(minutes=30),
            overtime_hours=Decimal("1.50"),
            added_cost=Decimal("37.25"),
        )
    ]
    case.handled = ["no_punch:e1@2027-01-13T14:00:00"]
    case.asked_at = T0
    return case


def test_implements_port(engine):
    assert isinstance(SqlTrackRepository(engine), TrackRepository)


def test_round_trip_with_offers_and_reading(repo):
    case = full_case()
    repo.save_case(case)
    assert repo.get_case("full") == case
    assert repo.get_case("nao-existe") is None


def test_save_case_updates_existing(repo):
    repo.save_case(make_case("c1"))
    updated = make_case("c1", status="coberto")
    repo.save_case(updated)
    assert repo.get_case("c1").status == "coberto"
    assert len(repo.list_cases()) == 1


def test_list_cases_ordered_by_created_at_then_id(repo):
    repo.save_case(make_case("b", created_at=T0))
    repo.save_case(make_case("a", created_at=T0))
    repo.save_case(make_case("z", created_at=T0 - timedelta(hours=1)))
    assert [c.id for c in repo.list_cases()] == ["z", "a", "b"]


def test_status_column_follows_updates(engine):
    repo = SqlTrackRepository(engine)
    repo.save_case(make_case("c1"))
    repo.save_case(make_case("c1", status="decidido"))
    with Session(engine) as session:
        row = session.scalars(select(TrackCaseRow)).one()
        assert (row.status, row.kind, row.employee_id) == ("decidido", "falta", "e1")


def test_reset_clears_cases_and_messages(engine):
    repo = SqlTrackRepository(engine)
    repo.save_case(make_case("c1"))
    with Session(engine) as session, session.begin():
        session.add(
            ChannelMessageRow(
                id="m1",
                seq=1,
                case_id="c1",
                direction="out",
                party="e1",
                template="t",
                body="oi",
                has_text=False,
                attachment_media_type=None,
                decision_ref=None,
                at=T0,
            )
        )
    repo.reset()
    assert repo.list_cases() == []
    with Session(engine) as session:
        assert session.scalars(select(ChannelMessageRow)).all() == []


def test_tables_created_by_init_db(engine):
    assert {"track_case", "channel_message"} <= set(inspect(engine).get_table_names())


def card(code: str = "COBERTURA") -> ExceptionCard:
    return ExceptionCard(code=code, title="t", reason="r")


def test_exception_queue_opens_track_item(engine):
    store = ExceptionStore(engine)
    queue = ExceptionStoreQueue(store, FixedClock(T0), new_id=lambda: "abcdef0123456789")
    assert isinstance(queue, ExceptionQueue)
    item_id = queue.open(card(), {"case_id": "c1", "kind": "outro"})
    assert item_id == "exc-abcdef012345"
    item = store.get(item_id)
    assert item is not None
    assert item.created_at == T0
    assert item.status == "open"
    assert item.card.code == "COBERTURA"
    assert item.source == {"case_id": "c1", "kind": "track"}


def test_exception_queue_default_ids_are_unique(engine):
    store = ExceptionStore(engine)
    queue = ExceptionStoreQueue(store, FixedClock(T0))
    ids = {queue.open(card(), {}) for _ in range(5)}
    assert len(ids) == 5
    assert all(i.startswith("exc-") and len(i) == 16 for i in ids)
