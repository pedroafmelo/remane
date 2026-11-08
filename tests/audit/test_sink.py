"""`SqlTraceSink`: grava o `TraceEvent` mascarado e o lê de volta por `run_id`, em ordem (RN-01 a RN-03)."""

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import SecretStr
from sqlalchemy import inspect, text

from escalista.audit.mask import REDACTED
from escalista.audit.sink import SqlTraceSink
from escalista.db import init_db, make_engine
from escalista.domain.contracts import TraceEvent
from escalista.domain.ports import TraceSink

SENTINEL = "rc_SENTINELA_NAO_VAZAR"
AT = datetime(2026, 11, 7, 9, 30)


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    init_db(eng)
    return eng


def event(id_: str, run_id: str = "run-1", **kw) -> TraceEvent:
    return TraceEvent(id=id_, run_id=run_id, kind=kw.pop("kind", "solver.run"), at=kw.pop("at", AT), **kw)


def test_table_has_trace_event_columns_and_indexes(engine):
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("trace_event")}
    assert set(TraceEvent.model_fields) <= cols
    indexed = {col for ix in insp.get_indexes("trace_event") for col in ix["column_names"]}
    assert {"run_id", "kind"} <= indexed
    assert insp.get_pk_constraint("trace_event")["constrained_columns"] == ["id"]


def test_sink_satisfies_port(engine):
    assert isinstance(SqlTraceSink(engine), TraceSink)


def test_roundtrip_keeps_every_field_and_decimal_cost(engine):
    sink = SqlTraceSink(engine)
    original = event(
        "e1",
        parent_id="e0",
        kind="llm.justify",
        rule_ref="lei/ec-141#art2",
        message_ref="msg-7",
        model="Qwen/Qwen3.5-9B",
        key_index=3,
        tokens_in=812,
        tokens_out=95,
        cost_usd=Decimal("0.000123"),
        latency_ms=1450,
        payload={"cost_basis": "usage.cost", "itens": [1, 2], "ok": True},
    )
    sink.emit(original)
    [back] = sink.list_events("run-1")
    assert back == original
    assert isinstance(back.cost_usd, Decimal) and back.cost_usd == Decimal("0.000123")


def test_cost_zero_and_none_roundtrip(engine):
    sink = SqlTraceSink(engine)
    sink.emit(event("a", cost_usd=Decimal("0"), payload={"cost_basis": "sem chamada de modelo"}))
    sink.emit(event("b"))
    a, b = sink.list_events("run-1")
    assert a.cost_usd == Decimal("0") and isinstance(a.cost_usd, Decimal)
    assert b.cost_usd is None and b.payload == {}


def test_list_events_filters_by_run_and_keeps_emission_order_even_with_same_timestamp(engine):
    sink = SqlTraceSink(engine)
    for id_, run in [("z", "run-1"), ("x", "run-2"), ("a", "run-1"), ("m", "run-1")]:
        sink.emit(event(id_, run_id=run))  # mesmo `at` (relógio de demo parado) e ids fora de ordem alfabética
    assert [e.id for e in sink.list_events("run-1")] == ["z", "a", "m"]
    assert [e.id for e in sink.list_events("run-2")] == ["x"]
    assert sink.list_events("nao-existe") == []


def test_aware_timestamp_is_stored_as_brasilia_naive(engine):
    sink = SqlTraceSink(engine)
    sink.emit(event("e1", at=datetime(2026, 11, 7, 12, 0, tzinfo=UTC)))
    [back] = sink.list_events("run-1")
    assert back.at == datetime(2026, 11, 7, 9, 0)


def test_payload_is_masked_before_storage(engine):
    sink = SqlTraceSink(engine)
    sink.emit(event("e1", payload={"api_key": "qualquer", "nota": "ok"}))
    [back] = sink.list_events("run-1")
    assert back.payload == {"api_key": REDACTED, "nota": "ok"}


def test_key_value_never_in_trace_or_log(engine, caplog):
    """RN-08: sentinela em todo canto do evento; ela não aparece no banco, no log (nem no eco SQL) nem na volta."""
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.INFO, logger="sqlalchemy.engine")  # eco SQL com os parâmetros: também não pode vazar
    literal = "zz9-chave-sem-prefixo-conhecido"
    sink = SqlTraceSink(engine, known_secrets=[SecretStr(literal)])
    sink.emit(
        event(
            "e1",
            kind="llm.justify",
            key_index=2,
            message_ref=f"msg {SENTINEL}",
            rule_ref=f"token={SENTINEL}",
            payload={
                "api_key": SENTINEL,
                "request": {
                    "headers": {"Authorization": f"Bearer {SENTINEL}"},
                    "url": f"https://h/v1?api_key={SENTINEL}",
                },
                "erro": f"401 Unauthorized para a chave {SENTINEL} ({literal})",
                "tentativas": [{"key": 1, "detalhe": SENTINEL}, {"key": 2, "detalhe": literal}],
                f"campo-{SENTINEL}": 1,
            },
        )
    )
    with engine.connect() as conn:
        stored = repr(conn.execute(text("SELECT * FROM trace_event")).all())
    events = sink.list_events("run-1")
    read_back = json.dumps([e.model_dump(mode="json") for e in events], ensure_ascii=False)
    assert "sqlalchemy.engine" in {r.name.rsplit(".", 1)[0] for r in caplog.records}, (
        "o eco SQL deveria ter sido capturado"
    )
    for where in (stored, read_back, caplog.text, repr(sink)):
        assert SENTINEL not in where
        assert "SENTINELA" not in where
        assert literal not in where
    assert events[0].key_index == 2  # só o índice da chave


# --- campos protegidos (RN-06, SAIDA-AC-13 v1.1) ----------------------------------------------------------------


def stored_payloads(engine) -> str:
    with engine.connect() as conn:
        return repr(conn.execute(text("SELECT payload FROM trace_event")).all())


def test_track_event_is_stored_without_cid(engine):
    sink = SqlTraceSink(engine)
    sink.emit(event("e1", kind="track.atestado.read", payload={"text": "CID J11 febre", "nota": "J11.1"}))
    [back] = sink.list_events("run-1")
    assert back.payload["text"] == REDACTED
    assert "J11" not in json.dumps(back.payload) and "J11" not in stored_payloads(engine)
    assert "febre" not in stored_payloads(engine)


def test_non_track_event_keeps_cell_reference(engine):
    sink = SqlTraceSink(engine)
    sink.emit(event("e1", kind="llm.map_columns", payload={"evidence": "célula B12"}))
    [back] = sink.list_events("run-1")
    assert back.payload == {"evidence": "célula B12"}


@pytest.mark.parametrize("kind", ["solver.run", "llm.map_columns", "track.case.closed"])
def test_protected_key_is_redacted_in_any_kind(engine, kind):
    sink = SqlTraceSink(engine)
    sink.emit(event("e1", kind=kind, payload={"cid": "Z99", "nested": {"CID": "Z99"}}))
    [back] = sink.list_events("run-1")
    assert back.payload == {"cid": REDACTED, "nested": {"CID": REDACTED}}
