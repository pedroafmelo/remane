"""`ExceptionStore`: remoção dos itens de uma origem (o "Reiniciar" da demo apaga só os cartões do acompanhamento)."""

from datetime import datetime

from sqlalchemy import create_engine

from escalista.db import init_db
from escalista.domain.contracts import ExceptionCard, Role
from escalista.store.exceptions import ExceptionItem, ExceptionStore

NOW = datetime(2027, 1, 13, 13, 55)


def item(item_id: str, kind: str) -> ExceptionItem:
    card = ExceptionCard(code="RX-05", title="t", reason="r", decider=Role.GESTOR, evidence=[], options=[])
    return ExceptionItem(id=item_id, created_at=NOW, card=card, source={"kind": kind})


def test_remove_by_source_kind_drops_only_that_origin():
    engine = create_engine("sqlite://")
    init_db(engine)
    store = ExceptionStore(engine)
    for i, kind in enumerate(["track", "regras", "track", "falta"]):
        store.add(item(f"i{i}", kind))
    assert store.remove_by_source_kind("track") == 2
    assert sorted(i.id for i in store.list()) == ["i1", "i3"]
    assert store.remove_by_source_kind("track") == 0
