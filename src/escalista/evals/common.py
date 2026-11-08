"""Harness comum dos evals (plano dos evals E3/E4, seção 4): um estilo só para o E1, o E3, o E4 e o comando all.

- `Scenario` declara a suíte, se usa modelo, o tier da C7 e os requisitos (`Requirement`: módulo e atributo que a
  saída da C7 entrega). Requisito ausente → `não executado (falta SAIDA-AC-NN (...))`, sem rodar o cenário.
- `NotRun` é o que o cenário levanta quando não pode afirmar nada (sem chave, teto, saída ausente, ainda não escrito).
- **Honestidade:** cenário com modelo só fica `passou`/`falhou` se o `Outcome.model` registra ao menos uma chamada a um
  modelo real (nome diferente de `"fake"` e não vazio). Senão o runner força `não executado (modelo não chamado)`.
- `BudgetedClient` aplica o teto de orçamento e de tempo da rodada com modelo (seção 9).
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import time
import time as wallclock
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from escalista.domain.contracts import LLMMessage, LLMResult, TraceEvent

if TYPE_CHECKING:
    from escalista.domain.ports import LLMClient
    from escalista.domain.rules import RuleCard
    from escalista.domain.schedule import DemandSlot, Employee, Store

PASSED = "passou"
FAILED = "falhou"
NOT_RUN = "não executado"
FAKE_MODEL = "fake"
FAILURE_EVENT_KIND = "exception.raised"

REASON_NO_FLAG = "sem --with-model"
REASON_NO_KEY = "sem chave"
REASON_NO_CALL = "modelo não chamado"
REASON_BUDGET = "teto de orçamento"
REASON_TIME = "tempo esgotado"

WEEK_START = date(2027, 1, 11)  # segunda; semana de referência da demo, já sob a EC 141


class NotRun(Exception):  # noqa: N818 - o nome é o status do relatório ("não executado"), não um erro
    """O cenário não pode afirmar nada: vira `não executado` com o motivo, nunca aprovado nem falha."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MemorySink:
    """`TraceSink` em memória: guarda os eventos do cliente para ler tokens, custo e latência de cada chamada."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class ModelUse:
    """O que o modelo gastou num cenário ou arquivo (medido nos eventos; `cost_usd` é `None` se faltar o custo de
    alguma chamada, nunca estimado). Os três últimos campos são do E2 (reserva da heurística)."""

    calls: int
    models: list[str]
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: Decimal | None
    latency_ms: int | None
    fell_back: bool = False
    fallback_reason: str | None = None
    same_as_heuristic: bool | None = None

    @property
    def real_model_called(self) -> bool:
        return self.calls > 0 and any(m and m != FAKE_MODEL for m in self.models)

    def as_json(self) -> dict[str, Any]:
        return {
            "chamadas": self.calls,
            "modelos": self.models,
            "tokens_entrada": self.tokens_in,
            "tokens_saida": self.tokens_out,
            "cost_usd": None if self.cost_usd is None else format(self.cost_usd, "f"),
            "latencia_ms": self.latency_ms,
            "reserva": self.fell_back,
            "motivo_reserva": self.fallback_reason,
            "igual_a_heuristica": self.same_as_heuristic,
        }


def _total(values: Sequence[int | None]) -> int | None:
    return None if not values or any(v is None for v in values) else sum(v for v in values if v is not None)


def model_use(sink: MemorySink, run_id: str, kinds: Sequence[str]) -> ModelUse:
    """Soma as chamadas de `run_id` cujos eventos são de `kinds` (sucesso) ou `exception.raised` (falha do cliente).
    Tokens só dos eventos de sucesso; custo e latência de todos. Faltou um custo, o total é `None` (não medido)."""
    wanted = set(kinds)
    events = [e for e in sink.events if e.run_id == run_id and (e.kind in wanted or e.kind == FAILURE_EVENT_KIND)]
    ok = [e for e in events if e.kind in wanted]
    costs = [e.cost_usd for e in events]
    cost = None if not costs or any(c is None for c in costs) else sum((c for c in costs if c is not None), Decimal(0))
    return ModelUse(
        calls=len(events),
        models=sorted({e.model for e in events if e.model}),
        tokens_in=_total([e.tokens_in for e in ok]) if ok else None,
        tokens_out=_total([e.tokens_out for e in ok]) if ok else None,
        cost_usd=cost,
        latency_ms=_total([e.latency_ms for e in events]),
    )


@dataclass
class EvalContext:
    """Entradas compartilhadas, lidas uma vez e só se algum cenário as pedir.

    `with_model` liga os cenários com modelo; `llm` é o cliente (já com o teto, `BudgetedClient`) ou `None` quando não
    há chave; `sink` recebe os eventos do cliente, de onde sai o `ModelUse` de cada cenário. `client_factory` monta um
    cliente que emite no sink pedido (e, na rodada real, também no sink compartilhado do teto): é o que os cenários
    que reaproveitam a cadeia do E2 (com o próprio `MemorySink`) usam."""

    data_dir: Path = Path("data/demo")
    rules_dir: Path = Path("data/regras")
    reference_date: date = WEEK_START
    with_model: bool = False
    llm: LLMClient | None = None
    sink: MemorySink = field(default_factory=MemorySink)
    client_factory: Callable[[Any], LLMClient] | None = None

    @cached_property
    def card(self) -> RuleCard:
        from escalista.rules.loader import load_rule_card

        return load_rule_card(self.rules_dir, self.reference_date)

    @cached_property
    def network(self) -> tuple[list[Store], list[Employee], list[DemandSlot]]:
        from escalista.ingest.demo_network import load_demo_network

        return load_demo_network(self.data_dir)


@dataclass(frozen=True)
class Outcome:
    """O que um cenário devolve: esperado e obtido em texto, o veredito e, se houver, o uso do modelo e métricas."""

    expected: str
    obtained: str
    passed: bool
    model: ModelUse | None = field(default=None, kw_only=True)
    metrics: dict[str, Any] | None = field(default=None, kw_only=True)
    reason: str | None = field(default=None, kw_only=True)  # por que passou ou falhou, quando não é óbvio


@dataclass(frozen=True)
class Requirement:
    """Saída da C7 de que o cenário depende: `module` importável e, se dado, `attr` (encadeado: `Tracker.message`)."""

    module: str
    attr: str | None
    saida: str

    def missing(self) -> bool:
        try:
            if importlib.util.find_spec(self.module) is None:
                return True
        except (ImportError, ValueError):
            return True
        if self.attr is None:
            return False
        try:
            obj: Any = importlib.import_module(self.module)
            for part in self.attr.split("."):
                obj = getattr(obj, part)
        except (ImportError, AttributeError):
            return True
        return False

    def reason(self) -> str:
        target = self.module + (f".{self.attr}" if self.attr else "")
        return f"falta {self.saida} ({target})"


@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    run: Callable[[EvalContext], Outcome]
    suite: str = field(default="e1", kw_only=True)
    uses_model: bool = field(default=False, kw_only=True)
    tier: str = field(default="atual", kw_only=True)
    requires: tuple[Requirement, ...] = field(default=(), kw_only=True)


@dataclass(frozen=True)
class ScenarioResult:
    id: str
    description: str
    expected: str
    obtained: str
    status: str
    elapsed_ms: int
    suite: str = "e1"
    uses_model: bool = False
    tier: str = "atual"
    model_executed: bool = False
    reason: str | None = None
    model: ModelUse | None = None
    metrics: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return self.status == PASSED

    def as_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "descricao": self.description,
            "esperado": self.expected,
            "obtido": self.obtained,
            "passou": self.passed,
            "tempo_ms": self.elapsed_ms,
            "status": self.status,
            "suite": self.suite,
            "usa_modelo": self.uses_model,
            "tier": self.tier,
            "motivo": self.reason,
        }
        if self.model is not None:
            out["modelo"] = self.model.as_json()
        if self.metrics is not None:
            out["metricas"] = self.metrics
        return out


def _gate(scenario: Scenario, ctx: EvalContext) -> str | None:
    """Motivo para não rodar, na ordem: saída da C7 ausente, modo sem modelo, sem chave."""
    for req in scenario.requires:
        if req.missing():
            return req.reason()
    if scenario.uses_model and not ctx.with_model:
        return REASON_NO_FLAG
    if scenario.uses_model and ctx.llm is None and ctx.client_factory is None:
        return REASON_NO_KEY
    return None


def run_one(scenario: Scenario, ctx: EvalContext) -> ScenarioResult:
    base = {
        "suite": scenario.suite,
        "uses_model": scenario.uses_model,
        "tier": scenario.tier,
    }
    blocked = _gate(scenario, ctx)
    if blocked is not None:
        return ScenarioResult(scenario.id, scenario.description, "", "", NOT_RUN, 0, reason=blocked, **base)
    t0 = wallclock.perf_counter()
    try:
        outcome = scenario.run(ctx)
    except NotRun as exc:
        elapsed = int((wallclock.perf_counter() - t0) * 1000)
        return ScenarioResult(scenario.id, scenario.description, "", "", NOT_RUN, elapsed, reason=exc.reason, **base)
    except Exception as exc:  # noqa: BLE001 - qualquer erro do cenário vira falha no placar
        outcome = Outcome(expected="cenário roda sem erro", obtained=f"erro: {type(exc).__name__}: {exc}", passed=False)
    elapsed = int((wallclock.perf_counter() - t0) * 1000)
    executed = scenario.uses_model and outcome.model is not None and outcome.model.real_model_called
    status, reason = (PASSED if outcome.passed else FAILED), outcome.reason
    if scenario.uses_model and not executed:
        status, reason = NOT_RUN, REASON_NO_CALL
    return ScenarioResult(
        scenario.id,
        scenario.description,
        outcome.expected,
        outcome.obtained,
        status,
        elapsed,
        model_executed=executed,
        reason=reason,
        model=outcome.model,
        metrics=outcome.metrics,
        **base,
    )


def run_scenarios(scenarios: Sequence[Scenario], ctx: EvalContext | None = None) -> list[ScenarioResult]:
    """Roda os cenários em ordem. Exceção num cenário é falha dele (com a causa); `NotRun` é `não executado`."""
    ctx = ctx if ctx is not None else EvalContext()
    return [run_one(s, ctx) for s in scenarios]


def write_report(report: dict, out_dir: Path, generated_at: datetime, suite: str = "e1") -> Path:
    """Grava `<suite>-<timestamp>.json` e `<suite>-latest.json` em `out_dir`; devolve o primeiro."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{suite}-{generated_at:%Y%m%dT%H%M%S}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(path, out_dir / f"{suite}-latest.json")
    return path


def status_label(r: ScenarioResult) -> str:
    if r.status == PASSED:
        return "passou"
    if r.status == FAILED:
        return "FALHOU"
    return f"não executado ({r.reason})"


def render(results: Sequence[ScenarioResult]) -> str:
    """Tabela: uma linha por cenário com `passou` / `FALHOU` / `não executado (motivo)`; falhas detalhadas no fim."""
    rows = [(r.id, r.suite, "sim" if r.uses_model else "não", r.tier, status_label(r), r.description) for r in results]
    head = ("cenário", "suíte", "modelo", "tier", "resultado", "descrição")
    widths = [max(len(head[i]), *(len(row[i]) for row in rows)) if rows else len(head[i]) for i in range(len(head))]

    def line(cells: Sequence[str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths, strict=True)).rstrip()

    out = [line(head), line(["-" * w for w in widths]), *(line(row) for row in rows)]
    for r in results:
        if r.status == FAILED:
            out += ["", f"FALHA {r.id}: {r.description}", f"  esperado: {r.expected}", f"  obtido:   {r.obtained}"]
    return "\n".join(out)


# Orçamento ----------------------------------------------------------------------------------------------------------

# Premissa da guarda (não é custo medido): preço declarado do modelo `small` na Featherless, em US$ por 1M de tokens
# (plano dos evals E3/E4, F11). Só entra quando um evento vem sem `cost_usd`; o relatório segue dizendo "não medido".
GUARD_PRICE_IN_PER_M = Decimal("0.17")
GUARD_PRICE_OUT_PER_M = Decimal("0.25")
MILLION = Decimal(1_000_000)


class TeeSink:
    """Repassa cada evento a vários sinks (o do cenário e o compartilhado do teto), sem repetir o mesmo sink."""

    def __init__(self, *sinks: Any) -> None:
        self._sinks = list({id(s): s for s in sinks}.values())

    def emit(self, event: TraceEvent) -> None:
        for sink in self._sinks:
            sink.emit(event)


class BudgetedClient:
    """`LLMClient` com teto: antes de cada chamada, se o gasto (soma do `cost_usd` medido no sink; tokens × preço
    declarado nos eventos sem custo) chegou ao teto, ou o tempo passou de `max_seconds`, levanta `NotRun`."""

    def __init__(
        self,
        inner: Any,
        sink: MemorySink,
        ceiling_usd: Decimal,
        *,
        price_in_per_m: Decimal = GUARD_PRICE_IN_PER_M,
        price_out_per_m: Decimal = GUARD_PRICE_OUT_PER_M,
        max_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        started_at: float | None = None,
    ) -> None:
        self._inner = inner
        self._sink = sink
        self.ceiling_usd = ceiling_usd
        self._price_in = price_in_per_m
        self._price_out = price_out_per_m
        self._max_seconds = max_seconds
        self._clock = clock
        self._started = clock() if started_at is None else started_at

    def spent_usd(self) -> Decimal:
        total = Decimal(0)
        for e in self._sink.events:
            if e.cost_usd is not None:
                total += e.cost_usd
            else:  # premissa da guarda: tokens × preço declarado
                total += Decimal(e.tokens_in or 0) * self._price_in / MILLION
                total += Decimal(e.tokens_out or 0) * self._price_out / MILLION
        return total

    def complete(
        self,
        *,
        size: str,
        messages: list[LLMMessage],
        tool_schema: dict[str, Any] | None = None,
        run_id: str,
        parent_id: str | None = None,
        kind: str | None = None,
    ) -> LLMResult:
        if self.spent_usd() >= self.ceiling_usd:
            raise NotRun(REASON_BUDGET)
        if self._max_seconds is not None and self._clock() - self._started >= self._max_seconds:
            raise NotRun(REASON_TIME)
        extra = {"kind": kind} if kind is not None else {}
        return self._inner.complete(
            size=size, messages=messages, tool_schema=tool_schema, run_id=run_id, parent_id=parent_id, **extra
        )
