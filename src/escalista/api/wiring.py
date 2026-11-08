"""Ligação da API ao agente da fatia (plano da C5, seção 4: C2 e C4).

`SliceAgentC6` (o `SliceAgent` mais a continuidade da C6) é o que as rotas de `routes_runs.py` consomem. `build_agent`
liga o agente LangGraph da I1 (`OptimizerSliceAgent`, que traduz os erros do agente nos daqui) com o rastro e o
repositório em SQL e o cliente Featherless. O `FakeSliceAgent` (respostas fixas) fica só para os testes de rota,
injetado em `create_app(agent=...)`.

Divisão de responsabilidades:
- A API cuida do transporte: sessão e papel (`require_role`), tamanho do arquivo (413) e tipo (CSV, XLSX ou PDF, pela
  extensão e pelos bytes iniciais; fora disso, cartão RX-13). O agente recebe só arquivos com até `MAX_UPLOAD_BYTES` e
  de um tipo aceito; decodificar (UTF-8 e afins) é do leitor do agente, que devolve RX-13 quando não consegue.
- A API monta o `Approval` (o ato humano) com o id e o papel da sessão; o agente o grava e só então chama `publicar`,
  que confere a aprovação **no código** e recusa sem ela (`PublishRefusedError` vira 403).
- Nada que o agente devolve à API carrega `sex` (RN-13): pessoas saem só como `EmployeePublic`.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fastapi import Request
from sqlalchemy import Engine

from escalista.config import Settings
from escalista.domain.contracts import ExceptionCard, TraceEvent
from escalista.domain.ports import Clock, LLMClient, TraceSink
from escalista.domain.reading import ConfirmInput
from escalista.domain.results import Approval, RunState, ScheduleVersion
from escalista.domain.roster import Roster
from escalista.domain.schedule import EmployeePublic, Schedule

if TYPE_CHECKING:
    from escalista.domain.rules import RuleCard

log = logging.getLogger("escalista")

MAX_UPLOAD_BYTES = 1024 * 1024  # 1 MB (MiB): acima disso, 413
DEFAULT_DEMO_FILES_DIR = "data/demo"
DEFAULT_RULES_DIR = "data/regras"
DEMO_WEEK_START = date(2027, 1, 11)  # a semana da demo (11 a 17/01/2027), já sob as 42h e os 2 repousos da EC 141
BRT = timezone(timedelta(hours=-3), "BRT")  # sem horário de verão desde 2019


@runtime_checkable
class SliceAgent(Protocol):
    """O agente da fatia (otimização: ler, confirmar, otimizar, verificar, comparar, justificar, publicar).

    Todo `run_id` desconhecido levanta `RunNotFoundError`, exceto em `get_run`, `get_schedule`, `employees` e `trace`,
    que devolvem `None` ou lista vazia. Uma chamada fora da fase esperada levanta `RunPhaseError`.
    """

    def start_run(self, file_name: str, content: bytes) -> RunState:
        """Cria a execução, valida o CSV e devolve o resumo da leitura (RF-04, RF-23).

        `content` já vem com até `MAX_UPLOAD_BYTES` e de um tipo aceito pela API (CSV, XLSX ou PDF, extensão e bytes
        iniciais coerentes); a codificação **não** é conferida na API. Devolve a fase `awaiting_confirm` com
        `summary.ok`, ou `failed` com o cartão RX-13 (e `summary.issues` com a linha de cada erro), inclusive para um
        CSV que não decodifica.
        """
        ...

    def confirm(self, run_id: str, data: ConfirmInput | None = None) -> RunState:
        """O gestor confirmou (e talvez corrigiu) o resumo: otimiza, verifica, compara e justifica. Fase
        `awaiting_approval` (com `comparison`, `report`, `justification` e `version_id`) ou `failed` com o cartão
        (RX-02, RX-12). Exige a fase `awaiting_confirm`.

        `data` é o ato humano da parada (cobertura-alvo, salário-hora, semana, identidade, pedido em texto); `None`
        equivale a `ConfirmInput()` (tudo no padrão). Na 1ª escala, a confirmação grava o `Roster`."""
        ...

    def get_run(self, run_id: str) -> RunState | None: ...

    def get_schedule(self, run_id: str) -> Schedule | None:
        """A grade proposta (otimizada) da execução; `None` antes de otimizar."""
        ...

    def employees(self, run_id: str) -> list[EmployeePublic]:
        """As pessoas da escala da execução, sem `sex` (RN-13), para a grade mostrar nomes."""
        ...

    def approve(self, run_id: str, approval: Approval) -> RunState:
        """Grava a aprovação humana e publica a versão. Fase `published`.

        Exige a fase `awaiting_approval`. Se `publicar` recusar (sem aprovação gravada, versão ou papel errado),
        levanta `PublishRefusedError` e registra `schedule.publish_refused` no rastro."""
        ...

    def published(self) -> ScheduleVersion | None:
        """A última versão publicada, ou `None`."""
        ...

    def trace(self, run_id: str) -> list[TraceEvent]:
        """Os eventos do rastro da execução, em ordem; cada um com `cost_usd` (0 nos passos sem modelo)."""
        ...


@runtime_checkable
class SliceAgentC6(SliceAgent, Protocol):
    """O `SliceAgent` com a continuidade da C6 (planejar a próxima semana sem upload e ler o quadro). É o que as rotas
    consomem.

    Os dois métodos ficam num protocolo à parte só enquanto o `OptimizerAgent` da frente B não os tem (B4a): o teste
    `tests/agents/test_graph.py::test_agent_satisfies_the_api_protocol` confere `isinstance(agente, SliceAgent)`, e
    pôr os métodos no `SliceAgent` o quebraria antes da hora. Quando a B4a entregar, os dois protocolos podem virar um.
    """

    def start_next_week(self) -> RunState:
        """Planeja a semana seguinte à última publicada, sem upload (modo `continuidade`): o "antes" é a publicada
        deslocada 7 dias, e o quadro e a demanda são os do último `Roster`. Devolve a fase `awaiting_confirm`.
        Sem versão publicada ou sem quadro, levanta `RunPhaseError` ("envie a primeira escala")."""
        ...

    def roster(self) -> Roster | None:
        """O último quadro confirmado, ou `None`. A API só o expõe com as pessoas como `EmployeePublic` (RN-13)."""
        ...


class SliceAgentError(Exception):
    """Base dos erros que o agente devolve à API."""


class RunNotFoundError(SliceAgentError):
    """`run_id` desconhecido. A API responde 404."""


class RunPhaseError(SliceAgentError):
    """A execução não está na fase que a operação exige. A API responde 409."""


class PublishRefusedError(SliceAgentError):
    """`publicar` recusou (RH-01). A API responde 403 com o motivo e, se houver, o cartão."""

    def __init__(self, reason: str, card: ExceptionCard | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.card = card


LLMFactory = Callable[[TraceSink, Clock], LLMClient]
"""`(sink, clock) -> cliente do modelo`. O cliente real emite o `llm.justify` no `sink`; os testes injetam um falso."""


def build_agent(
    settings: Settings, *, engine: Engine | None = None, llm_factory: LLMFactory | None = None
) -> SliceAgentC6:
    """Liga o agente real: `SqlTraceSink`, `SqlRepository`, relógio do sistema e o cliente Featherless.

    `engine` e `llm_factory` existem para os testes (SQLite em memória e falso de LLM); em produção ficam `None`
    (banco de `settings.database_url` e cliente da Featherless com as chaves do ambiente; sem chave, RX-12)."""
    import escalista.audit.tables  # noqa: F401 (registra a tabela antes do init_db)
    import escalista.store.sql_repository  # noqa: F401 (idem)
    from escalista.agents.optimizer.graph import OptimizerAgent
    from escalista.api.optimizer_adapter import OptimizerSliceAgent
    from escalista.audit.sink import SqlTraceSink
    from escalista.clock.system import SystemClock
    from escalista.db import init_db, make_engine
    from escalista.ingest.csv_schedule import read_schedule_csv
    from escalista.ingest.demo_network import load_demo_network
    from escalista.llm.client import FeatherlessClient
    from escalista.llm.prompts.justify import make_justifier
    from escalista.rules.loader import load_rule_card
    from escalista.store.sql_repository import SqlRepository

    engine = engine or make_engine(settings.database_url)
    init_db(engine)
    sink = SqlTraceSink(engine, known_secrets=[key for _, key in settings.featherless_keys])
    clock = SystemClock()
    if llm_factory is not None:
        client = llm_factory(sink, clock)
    else:  # sem chave, o cliente sobe e `complete` levanta RX-12 (testado), sem inventar texto
        client = FeatherlessClient.from_settings(settings, trace_sink=sink, clock=clock)
    card: RuleCard = load_rule_card(Path(DEFAULT_RULES_DIR), DEMO_WEEK_START)
    stores, employees, demand = load_demo_network(Path(DEFAULT_DEMO_FILES_DIR))
    read_csv = functools.partial(read_schedule_csv, employees=employees, stores=stores, week_start=DEMO_WEEK_START)
    agent = OptimizerAgent(
        repo=SqlRepository(engine),
        sink=sink,
        clock=clock,
        read_csv=read_csv,
        justify=make_justifier(client),
        list_events=sink.list_events,
        card=card,
        stores=stores,
        employees=employees,
        demand=demand,
        week_start=DEMO_WEEK_START,
    )
    log.info(
        "agente da fatia: OptimizerAgent (LangGraph), semana %s, chaves: %d",
        DEMO_WEEK_START,
        len(settings.featherless_keys),
    )
    return OptimizerSliceAgent(agent)


def now_brt() -> datetime:
    """Agora no horário de Brasília, sem fuso (os contratos usam datas sem fuso)."""
    return datetime.now(BRT).replace(tzinfo=None)


# --- dependências FastAPI (os testes trocam por `app.dependency_overrides`) ---


def get_agent(request: Request) -> SliceAgentC6:
    return request.app.state.agent


def get_demo_files_dir(request: Request) -> Path:
    return Path(request.app.state.demo_files_dir)
