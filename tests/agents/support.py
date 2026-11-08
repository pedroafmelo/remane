"""Apoio dos testes do agente da fatia: rede mínima sintética, falsos de LLM e montagem do agente.

Os testes podem importar as bordas (`ingest`, `llm`); só o código de `src/escalista/agents/` não pode.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from escalista.agents.optimizer.graph import OptimizerAgent
from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, LLMUnavailableError, Role, TraceEvent
from escalista.domain.ports import Repository, TraceSink
from escalista.domain.results import Approval
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Store
from escalista.ingest.csv_schedule import read_schedule_csv
from escalista.llm.prompts.justify import make_justifier
from escalista.rules.loader import load_rule_card
from tests.fakes import FixedClock, InMemoryRepository, ListTraceSink

WEEK = date(2027, 1, 11)  # segunda; semana da demo, já sob a EC 141
NOW = datetime(2027, 1, 8, 9, 30)
RULES_DIR = Path("data/regras")
DEMO_DIR = Path("data/demo")
FAKE_COST = Decimal("0.000321")
GOOD_JUSTIFICATION = {
    "summary": "A escala proposta respeita 42h semanais e 2 repousos, sem hora extra.",
    "items": [
        {"text": "Ninguém passa de 42h na semana.", "rule_refs": ["jornada_semanal_max"]},
        {"text": "Cada pessoa tem 2 dias de repouso.", "rule_refs": ["repouso_semanal"]},
    ],
}


def rule_card() -> RuleCard:
    return load_rule_card(RULES_DIR, WEEK)


# --- rede mínima (1 loja, 3 pessoas): resolve em milissegundos ---------------------------------------------------

TINY_STORES = [Store(id="L1", name="Loja Sintética Teste", opens=time(8), closes=time(22))]
TINY_EMPLOYEES = [
    Employee(id="E1", name="Ana Sintética", store_id="L1", job="Atendente", hourly_wage=Decimal("15.00"),
             contract_hours=44, sex="F"),
    Employee(id="E2", name="Bruno Sintético", store_id="L1", job="Atendente", hourly_wage=Decimal("15.00"),
             contract_hours=44, sex="M"),
    Employee(id="E3", name="Carla Sintética", store_id="L1", job="Caixa", hourly_wage=Decimal("16.00"),
             contract_hours=44, sex="F"),
]  # fmt: skip


def tiny_demand(required: int = 1) -> list[DemandSlot]:
    """Segunda a sexta, 10h às 14h, `required` pessoas por faixa de 30 min."""
    out: list[DemandSlot] = []
    for d in range(5):
        t = datetime.combine(WEEK + timedelta(days=d), time(10))
        while t.time() < time(14):
            out.append(DemandSlot(store_id="L1", day=t.date(), start=t.time(), required=required))
            t += timedelta(minutes=30)
    return out


def tiny_csv() -> bytes:
    """Regime antigo: E1 trabalha 6 dias de 8h (48h, 1 folga), o que viola as 42h e os 2 repousos."""
    lines = ["# SINTETICO - dados ficticios", "loja_id,pessoa_id,nome,data,inicio,fim"]
    for d in range(6):
        lines.append(f"L1,E1,Ana Sintética,{(WEEK + timedelta(days=d)).isoformat()},08:00,16:00")
    for d in range(5):
        lines.append(f"L1,E2,Bruno Sintético,{(WEEK + timedelta(days=d)).isoformat()},12:00,18:00")
    return ("\n".join(lines) + "\n").encode("utf-8")


# --- falsos de LLM -----------------------------------------------------------------------------------------------


class JustifyLLM:
    """Falso do cliente real: emite um `TraceEvent` por chamada com o `kind` pedido e um custo falso, como o
    `FeatherlessClient` faz. `fail=True` levanta RX-12; `args` troca a saída da ferramenta."""

    def __init__(self, sink: TraceSink, clock: FixedClock, *, fail: bool = False, args: Any = None) -> None:
        self._sink = sink
        self._clock = clock
        self._fail = fail
        self._args = GOOD_JUSTIFICATION if args is None else args
        self.calls: list[list[LLMMessage]] = []

    def complete(
        self,
        *,
        size: str,
        messages: list[LLMMessage],
        tool_schema: dict | None = None,
        run_id: str,
        parent_id: str | None = None,
        kind: str | None = None,
    ) -> LLMResult:
        self.calls.append(messages)
        if self._fail:
            raise LLMUnavailableError(
                ExceptionCard(code="RX-12", title="Modelo indisponível", reason="falha simulada", trace_id=parent_id)
            )
        event_id = f"llm-{len(self.calls)}"
        self._sink.emit(
            TraceEvent(id=event_id, run_id=run_id, parent_id=parent_id, kind=kind or "llm.call", at=self._clock.now(),
                       model="falso-pequeno", key_index=1, tokens_in=900, tokens_out=120, cost_usd=FAKE_COST,
                       latency_ms=15, payload={"cost_basis": "custo falso (teste)"})
        )  # fmt: skip
        return LLMResult(tool_args=self._args, model="falso-pequeno", key_index=1, cost_usd=FAKE_COST)


# --- montagem ----------------------------------------------------------------------------------------------------


class Harness:
    def __init__(
        self,
        *,
        stores: list[Store] = TINY_STORES,
        employees: list[Employee] = TINY_EMPLOYEES,
        demand: list[DemandSlot] | None = None,
        card: RuleCard | None = None,
        llm_fail: bool = False,
        llm_args: Any = None,
        time_limit_s: float = 10.0,
        repo: Repository | None = None,
        sink: TraceSink | None = None,
        list_events: Callable[[str], list[TraceEvent]] | None = None,
    ) -> None:
        self.repo = repo or InMemoryRepository()
        self.sink = sink or ListTraceSink()
        self._list_events = list_events
        self.clock = FixedClock(NOW)
        self.llm = JustifyLLM(self.sink, self.clock, fail=llm_fail, args=llm_args)
        self.employees = employees
        self.agent = OptimizerAgent(
            repo=self.repo,
            sink=self.sink,
            clock=self.clock,
            read_csv=lambda name, content: read_schedule_csv(
                name, content, employees=employees, stores=stores, week_start=WEEK
            ),
            justify=make_justifier(self.llm),
            list_events=self.events,
            card=card or rule_card(),
            stores=stores,
            employees=employees,
            demand=tiny_demand() if demand is None else demand,
            week_start=WEEK,
            seed=42,
            time_limit_s=time_limit_s,
            num_workers=1,
        )

    def events(self, run_id: str) -> list[TraceEvent]:
        if self._list_events is not None:
            return self._list_events(run_id)
        return [e for e in self.sink.events if e.run_id == run_id]

    def kinds(self, run_id: str) -> list[str]:
        return [e.kind for e in self.events(run_id)]

    def approval(self, version_id: str, *, role: Role = Role.GERENTE) -> Approval:
        return Approval(id=f"apr-{version_id}", version_id=version_id, approved_by="demo-gerente", role=role, at=NOW)
