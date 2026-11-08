"""`SqlTraceSink`: implementa a porta `TraceSink` sobre a tabela `trace_event` (RN-01 a RN-03, arquitetura, seção 9).

Antes de gravar, o `payload` passa pela máscara (`audit.mask`) e as colunas de texto também (defesa em profundidade:
elas deveriam carregar só referências). O log registra só `kind`, `run_id` e `id`, nunca o `payload`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from escalista.audit.mask import Masker
from escalista.audit.tables import TraceEventRow
from escalista.clock.system import to_brasilia_naive
from escalista.domain.contracts import TraceEvent

log = logging.getLogger(__name__)


class SqlTraceSink:
    """Grava cada `TraceEvent` mascarado. `known_secrets`: valores das chaves configuradas, removidos literalmente.

    Exemplo: `SqlTraceSink(engine, known_secrets=[key for _, key in settings.featherless_keys])`. Crie a tabela com
    `init_db(engine)` depois de importar este módulo.
    """

    def __init__(self, engine: Engine, *, known_secrets: Iterable[str | SecretStr] | None = None) -> None:
        self._engine = engine
        self._mask = Masker(known_secrets)

    def __repr__(self) -> str:
        return f"SqlTraceSink({self._engine.url.render_as_string(hide_password=True)!r}, {self._mask!r})"

    def emit(self, event: TraceEvent) -> None:
        text = self._mask.text
        opt = lambda value: None if value is None else text(value)  # noqa: E731
        row = TraceEventRow(
            id=text(event.id),
            run_id=text(event.run_id),
            parent_id=opt(event.parent_id),
            kind=text(event.kind),
            at=to_brasilia_naive(event.at),
            rule_ref=opt(event.rule_ref),
            message_ref=opt(event.message_ref),
            model=opt(event.model),
            key_index=event.key_index,
            tokens_in=event.tokens_in,
            tokens_out=event.tokens_out,
            cost_usd=event.cost_usd,
            latency_ms=event.latency_ms,
            payload=self._mask.payload(event.payload),
        )
        ident = (row.kind, row.run_id, row.id)  # já mascarados; o objeto expira no commit
        with Session(self._engine) as session, session.begin():
            row.seq = (session.scalar(select(func.max(TraceEventRow.seq))) or 0) + 1
            session.add(row)
        log.debug("trace_event gravado: kind=%s run_id=%s id=%s", *ident)

    def list_events(self, run_id: str) -> list[TraceEvent]:
        """Eventos de um `run_id`, na ordem em que foram gravados."""
        stmt = select(TraceEventRow).where(TraceEventRow.run_id == run_id).order_by(TraceEventRow.seq)
        with Session(self._engine) as session:
            return [_to_event(row) for row in session.scalars(stmt)]


def _to_event(row: TraceEventRow) -> TraceEvent:
    return TraceEvent(
        id=row.id,
        run_id=row.run_id,
        parent_id=row.parent_id,
        kind=row.kind,
        at=row.at,
        rule_ref=row.rule_ref,
        message_ref=row.message_ref,
        model=row.model,
        key_index=row.key_index,
        tokens_in=row.tokens_in,
        tokens_out=row.tokens_out,
        cost_usd=row.cost_usd,
        latency_ms=row.latency_ms,
        payload=row.payload or {},
    )
