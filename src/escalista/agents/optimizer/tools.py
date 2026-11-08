"""Ferramentas e portas injetadas do agente de otimização (arquitetura, seções 2.1 e 4).

- As bordas entram como callables tipados só com contratos de `escalista.domain` (`ReadCsv`, `Justifier`,
  `ListEvents`): `agents` não importa `ingest`, `llm` nem `audit`.
- `Tracer`: um `TraceEvent` por passo, com `cost_usd = 0` e `payload.cost_basis` nos passos sem modelo, latência
  medida com `time.perf_counter`, carimbo pelo `Clock` e `parent_id` encadeado no passo anterior da execução.
- `publicar`: a única ferramenta com efeito da fatia. **Lê a aprovação no próprio código** (`repo.get_approval`) e
  recusa sem ela (regra 5 da arquitetura, 2.1; RH-01). Não aceita aprovação por argumento, de propósito.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from escalista.agents.optimizer.errors import PublishRefusedError
from escalista.domain.contracts import ExceptionCard, Role, TraceEvent
from escalista.domain.ports import Clock, Repository, TraceSink
from escalista.domain.results import Comparison, Justification, ScheduleVersion, ViolationReport
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, ReadSummary, Schedule

NO_MODEL = "sem chamada de modelo"
PUBLISHER_ROLES: frozenset[Role] = frozenset({Role.GESTOR})  # RH-01: o gerente aprova e publica
PERSONAL_KEYS = frozenset({"sex", "sexo", "name", "nome"})  # RN-13 e minimização: nada disso vai ao rastro


# --- bordas injetadas --------------------------------------------------------------------------------------------


class ReadResult(Protocol):
    """Resultado da leitura do CSV (o `CsvReadResult` de `ingest` satisfaz). `exception` não nulo é RX-13."""

    @property
    def schedule(self) -> Schedule | None: ...

    @property
    def summary(self) -> ReadSummary: ...

    @property
    def exception(self) -> ExceptionCard | None: ...


ReadCsv = Callable[[str, bytes], ReadResult]
"""`(file_name, content) -> ReadResult`. Já ligado às pessoas, às lojas e à semana planejada."""

ListEvents = Callable[[str], list[TraceEvent]]
"""`run_id -> eventos em ordem` (por exemplo `SqlTraceSink.list_events`)."""


class Justifier(Protocol):
    """Justificativa pelo modelo pequeno (o cliente real emite o evento `llm.justify` com o custo medido).

    Levanta `LLMUnavailableError` (cartão RX-12) quando o modelo falha ou insiste em `rule_ref` fora do cartão."""

    def __call__(
        self,
        *,
        card: RuleCard,
        comparison: Comparison,
        report: ViolationReport,
        status: str,
        uncovered: list[DemandSlot],
        run_id: str,
        parent_id: str | None = None,
    ) -> Justification: ...


# --- rastro --------------------------------------------------------------------------------------------------------


class Tracer:
    """Emite os eventos dos passos sem modelo e mantém a cadeia `parent_id` por execução.

    Sem a cadeia em memória (processo reiniciado), retoma do último evento gravado (`list_events`)."""

    def __init__(self, sink: TraceSink, clock: Clock, *, new_id: Callable[[], str], list_events: ListEvents) -> None:
        self._sink = sink
        self._clock = clock
        self._new_id = new_id
        self._list_events = list_events
        self._last: dict[str, str] = {}

    def now(self) -> datetime:
        return self._clock.now()

    def parent(self, run_id: str) -> str | None:
        if run_id not in self._last:
            stored = self._list_events(run_id)
            if not stored:
                return None
            self._last[run_id] = stored[-1].id
        return self._last[run_id]

    def follow(self, run_id: str, event_id: str) -> None:
        """Encadeia o próximo passo num evento emitido por outra borda (por exemplo o `llm.justify`)."""
        self._last[run_id] = event_id

    def step(
        self,
        run_id: str,
        kind: str,
        *,
        started: float | None = None,
        payload: dict[str, Any] | None = None,
        rule_ref: str | None = None,
    ) -> TraceEvent:
        """Passo sem modelo: `cost_usd = 0`, `cost_basis`, latência medida desde `started` (`perf_counter`)."""
        latency_ms = 0 if started is None else max(0, round((time.perf_counter() - started) * 1000))
        body = {**(payload or {}), "cost_basis": NO_MODEL}
        _reject_personal(body)
        event = TraceEvent(
            id=self._new_id(),
            run_id=run_id,
            parent_id=self.parent(run_id),
            kind=kind,
            at=self._clock.now(),
            rule_ref=rule_ref,
            cost_usd=Decimal(0),
            latency_ms=latency_ms,
            payload=body,
        )
        self._sink.emit(event)
        self._last[run_id] = event.id
        return event

    def human(self, run_id: str, kind: str, *, payload: dict[str, Any] | None = None) -> TraceEvent:
        """Ato humano registrado (confirmação, aprovação): sem modelo e sem latência de máquina."""
        return self.step(run_id, kind, payload={**(payload or {}), "humano": True})


def _reject_personal(value: Any) -> None:
    if isinstance(value, dict):
        bad = PERSONAL_KEYS & set(value)
        if bad:
            raise ValueError(f"campo pessoal no payload do rastro (RN-13): {sorted(bad)}")
        for item in value.values():
            _reject_personal(item)
    elif isinstance(value, list | tuple):
        for item in value:
            _reject_personal(item)


# --- publicar ------------------------------------------------------------------------------------------------------


def publicar(
    *,
    repo: Repository,
    tracer: Tracer,
    run_id: str,
    version_id: str | None,
    allowed_roles: Iterable[Role] = PUBLISHER_ROLES,
) -> ScheduleVersion:
    """Publica a versão **só** com aprovação humana gravada no `Repository`, lida aqui.

    Recusa (evento `schedule.publish_refused` e `PublishRefusedError`) se: a versão não existe ou é de outra
    execução; não há aprovação gravada para ela; a aprovação gravada é de outra versão ou de papel sem permissão;
    a versão já foi publicada; o verificador achou violação na versão. Com tudo certo: `mark_published` e evento
    `schedule.publish`. Devolve a versão publicada, relida do `Repository`.
    """
    started = time.perf_counter()
    version = repo.get_version(version_id) if version_id else None
    approval = repo.get_approval(version_id) if version is not None else None
    roles = frozenset(allowed_roles)

    reason: str | None = None
    if version is None:
        reason = "versão da escala não encontrada"
    elif version.run_id != run_id:
        reason = "a versão é de outra execução"
    elif approval is None:
        reason = "aprovação humana não encontrada para esta versão"
    elif approval.version_id != version.id:
        reason = "a aprovação gravada é de outra versão"
    elif approval.role not in roles:
        reason = f"papel sem permissão para publicar: {approval.role.value}"
    elif version.status == "published":
        reason = "a versão já publicada não é publicada de novo"
    elif version.violations_total > 0:
        reason = f"o verificador achou {version.violations_total} violações nesta versão"

    if reason is not None:
        tracer.step(
            run_id,
            "schedule.publish_refused",
            started=started,
            payload={
                "reason": reason,
                "version_id": version_id,
                "approval_id": approval.id if approval else None,
                "role": approval.role.value if approval else None,
            },
        )
        raise PublishRefusedError(reason)

    assert version is not None and approval is not None  # garantido pelas recusas acima
    repo.mark_published(version.id, tracer.now())
    published = repo.get_version(version.id) or version.model_copy(update={"status": "published"})
    tracer.step(
        run_id,
        "schedule.publish",
        started=started,
        payload={
            "version_id": version.id,
            "approval_id": approval.id,
            "approved_by": approval.approved_by,
            "role": approval.role.value,
            "input_hash": version.input_hash,
            "violations_total": version.violations_total,
        },
    )
    return published
