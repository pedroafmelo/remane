"""Adaptador da porta `ExceptionQueue` (vista do agente) sobre o `ExceptionStore` do gestor (C7, tarefa B1)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from escalista.domain.contracts import ExceptionCard
from escalista.domain.ports import Clock
from escalista.store.exceptions import ExceptionItem, ExceptionStore


class ExceptionStoreQueue:
    """Abre itens na fila do gestor com origem `{"kind": "track", ...}`; o prazo vem do relógio injetado."""

    def __init__(self, store: ExceptionStore, clock: Clock, *, new_id: Callable[[], str] = lambda: uuid4().hex) -> None:
        self._store = store
        self._clock = clock
        self._new_id = new_id

    def open(self, card: ExceptionCard, source: dict[str, Any]) -> str:
        item = ExceptionItem(
            id=f"exc-{self._new_id()[:12]}",
            created_at=self._clock.now(),
            card=card,
            source={**source, "kind": "track"},
        )
        self._store.add(item)
        return item.id
