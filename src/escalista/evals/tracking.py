"""Montagem comum dos cenários do E3/E4 sobre o acompanhamento (C7): gabaritos, política, `Tracker`, superfícies.

Regras (plano dos evals E3/E4, seções 6 a 8):

- Sem HTTP; SQLite em memória; `StepClock`; `ScriptedLLM` por nome de ferramenta. Nada de `tests/`.
- **Gabarito não circular:** instantes, ordens e veredictos esperados vêm **literais** dos JSON da C7
  (`data/demo/acompanhamento/cenario.esperado.json` e `atestados/*.esperado.json`, SAIDA-AC-15); números da política
  vêm do `TrackPolicy` (`rules.tracking_policy.load_track_policy`). Nunca se chama `detect`, `find_cover` nem `judge`
  para saber o esperado.
- Arquivo de gabarito ausente → `NotRun("falta SAIDA-AC-15 (...)")`: a saída não existe, o cenário não afirma nada.

**Gabarito do cenário** (`cenario.esperado.json`, formato no README da pasta, C7 D1): `{synthetic, seed, week_start,
demo_clock, policy, schedule_violations, cases}`; cada caso traz `id` (`PL-NN` plantado, `DV-NN` desvio do ponto),
`origin`, `employee_id`, `shift_start`, `trigger`, `fires_at`, `not_before`, `no_answer`, `ranked`,
`first_without_overtime`, `overtime_needed`, `expect_rx05`, `new_violations` e, no caso com aviso, `offers` (instantes
literais de cada oferta e do RX-06).
"""

from __future__ import annotations

import io
import json
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from escalista.evals.common import EvalContext, NotRun
from escalista.evals.fakes import ScriptedLLM, StepClock

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from escalista.domain.contracts import TraceEvent

TRACK_DIR = Path("acompanhamento")
SCENARIO_EXPECTED = TRACK_DIR / "cenario.esperado.json"
SCENARIO_DATA = TRACK_DIR / "cenario_folga.json"
ATESTADOS = TRACK_DIR / "atestados"
SAIDA_15 = "SAIDA-AC-15"

# Contrato, SAIDA-AC-01 (v1.1): `reset` volta a qua 13/01/2027 13:55 [PROPOSTA da C7]. O gabarito pode trazer o seu.
DEMO_RESET = datetime(2027, 1, 13, 13, 55)

# Superfícies em que o padrão de CID vale: as mesmas do `scrub` da C7 (contrato, seção 4, linha "Execução C7, 09:47",
# item 4): eventos `track.*` e `channel_message`. Nas outras, só os valores plantados (literais) contam.
TRACK_PATTERN_SURFACES = {"track.*", "channel_message"}
READ_KIND = "track.llm.read_atestado"
EXPECT_FIELDS = ("legible", "issued_on", "start_on", "days", "patient_matches", "has_crm", "verdict", "reasons")
READ_FIELDS = EXPECT_FIELDS[:6]  # o que o modelo devolve (`AtestadoFields`); `verdict` e `reasons` são do código


# --- gabaritos ------------------------------------------------------------------------------------------------------


def _load_json(path: Path, what: str) -> Any:
    if not path.exists():
        raise NotRun(f"falta {SAIDA_15} ({what})")
    return json.loads(path.read_text(encoding="utf-8"))


def pick(node: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in node:
            return node[name]
    return default


def as_dt(value: Any) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


def as_day(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)
    return date.fromisoformat(text[:10])


def scenario_expected(ctx: EvalContext) -> dict[str, Any]:
    return _load_json(ctx.data_dir / SCENARIO_EXPECTED, str(SCENARIO_EXPECTED))


def scenario_data(ctx: EvalContext) -> dict[str, Any]:
    return _load_json(ctx.data_dir / SCENARIO_DATA, str(SCENARIO_DATA))


def cases(gab: dict[str, Any]) -> list[dict[str, Any]]:
    return list(gab.get("cases", []))


def case(gab: dict[str, Any], case_id: str) -> dict[str, Any]:
    for c in cases(gab):
        if c.get("id") == case_id:
            return c
    raise NotRun(f"falta {SAIDA_15} (caso {case_id} no gabarito)")


def punch_cases(gab: dict[str, Any], kinds: set[str]) -> list[dict[str, Any]]:
    """Casos que nascem do ponto simulado (`origin = ponto`) com gatilho em `kinds`: os desvios plantados."""
    return [c for c in cases(gab) if c.get("origin") == "ponto" and c.get("trigger") in kinds]


def reported_case(gab: dict[str, Any]) -> dict[str, Any]:
    """O caso com aviso do colaborador e loja com folga (ofertas com instantes literais)."""
    for c in cases(gab):
        if c.get("offers") and c.get("ranked") and not c.get("expect_rx05"):
            return c
    raise NotRun(f"falta {SAIDA_15} (caso com aviso e ofertas no gabarito)")


def rx05_cases(gab: dict[str, Any]) -> list[dict[str, Any]]:
    found = [c for c in cases(gab) if c.get("expect_rx05") is True]
    if not found:
        raise NotRun(f"falta {SAIDA_15} (caso sem substituto, RX-05, no gabarito)")
    return found


def falta_from_punch(gab: dict[str, Any]) -> dict[str, Any]:
    for c in punch_cases(gab, {"no_punch"}):
        if c.get("kind") == "falta" and c.get("no_answer"):
            return c
    raise NotRun(f"falta {SAIDA_15} (falta plantada no ponto, com no_answer, no gabarito)")


def case_day(c: dict[str, Any]) -> date:
    return as_day(c["shift_start"])


@dataclass(frozen=True)
class Atestado:
    file: str
    data: bytes
    media_type: str
    expected_day: date
    employee_name: str
    expect: dict[str, Any]
    planted: list[str]


def atestado(ctx: EvalContext, prefix: str) -> Atestado:
    folder = ctx.data_dir / ATESTADOS
    gabs = sorted(folder.glob(f"{prefix}*.esperado.json")) if folder.exists() else []
    if not gabs:
        raise NotRun(f"falta {SAIDA_15} ({ATESTADOS}/{prefix}*.esperado.json)")
    body = json.loads(gabs[0].read_text(encoding="utf-8"))
    name = str(body.get("file") or gabs[0].name.removesuffix(".esperado.json"))
    path = folder / Path(name).name
    if not path.exists():
        raise NotRun(f"falta {SAIDA_15} ({ATESTADOS}/{Path(name).name})")
    media = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}[path.suffix.lower()]
    planted = body.get("planted_cid") or []
    return Atestado(
        file=path.name,
        data=path.read_bytes(),
        media_type=media,
        expected_day=as_day(body["expected_day"]),
        employee_name=str(body["employee_name"]),
        expect=dict(body["expect"]),
        planted=[str(p) for p in (planted if isinstance(planted, list) else [planted])],
    )


def scripted_fields(at: Atestado) -> dict[str, Any]:
    """Resposta do falso: os campos de leitura do gabarito (sem `verdict`/`reasons`, que o código calcula)."""
    return {k: at.expect[k] for k in READ_FIELDS if k in at.expect}


def field_score(reading: Any, expect: dict[str, Any]) -> tuple[int, int, list[str]]:
    """Campos do gabarito iguais na leitura (datas comparadas em ISO; `reasons` como conjunto). Devolve os errados
    pelo **nome** do campo, nunca pelo valor."""
    got = reading.model_dump(mode="json") if hasattr(reading, "model_dump") else dict(reading)
    wrong = []
    for key, want in expect.items():
        have = got.get(key)
        same = sorted(have or []) == sorted(want or []) if key == "reasons" else have == want
        if not same:
            wrong.append(key)
    return len(expect) - len(wrong), len(expect), wrong


# --- política -------------------------------------------------------------------------------------------------------


def track_policy(ctx: EvalContext) -> Any:
    from escalista.rules.tracking_policy import load_track_policy

    return load_track_policy(ctx.rules_dir / "politica" / "politica_ficticia.yaml")


def policy_options(ctx: EvalContext, code: str) -> list[str]:
    """Rótulos das opções do cartão `code` em `excecoes_demo` (lidos do YAML, a fonte; não do código testado)."""
    import yaml

    raw = yaml.safe_load((ctx.rules_dir / "politica" / "politica_ficticia.yaml").read_text(encoding="utf-8"))
    for item in raw.get("excecoes_demo", []):
        if item.get("code") == code:
            return [str(o["rotulo"]) for o in item.get("opcoes", [])]
    return []


# --- o Tracker ------------------------------------------------------------------------------------------------------


@dataclass
class Rig:
    tracker: Any
    engine: Engine
    clock: StepClock
    llm: Any
    log: io.StringIO = field(default_factory=io.StringIO)

    def at(self, moment: datetime) -> Any:
        """Leva o relógio a `moment` (só para a frente) e roda o varredor nesse instante."""
        if moment < self.clock.now():
            raise ValueError(f"o relógio não volta: {self.clock.now()} -> {moment}")
        self.clock.advance(moment - self.clock.now())
        return self.tracker.run_sweep(moment)

    def events(self, run_id: str | None = None) -> list[TraceEvent]:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from escalista.audit.sink import _to_event
        from escalista.audit.tables import TraceEventRow

        stmt = select(TraceEventRow).order_by(TraceEventRow.seq)
        if run_id is not None:
            stmt = stmt.where(TraceEventRow.run_id == run_id)
        with Session(self.engine) as session:
            return [_to_event(row) for row in session.scalars(stmt)]

    def open_cards(self, code: str | None = None, case_id: str | None = None) -> list[Any]:
        """Cartões abertos na fila do gestor: `tracker.desk.queue()` (contrato) ou, sem a mesa no `Tracker`, a tabela
        `exception_item` do mesmo engine (código real da C7 em `d7be9fc`: o `Tracker` só tem a porta `open`)."""
        desk = getattr(self.tracker, "desk", None)
        if desk is not None:
            items = list(desk.queue().open)
        else:
            from escalista.store.exceptions import ExceptionStore

            items = [i for i in ExceptionStore(self.engine).list() if i.status == "open"]
        if code is not None:
            items = [i for i in items if i.card.code == code]
        if case_id is not None:
            items = [i for i in items if i.source.get("case_id") == case_id]
        return items

    def decide(self, item: Any, option_index: int) -> Any:
        """Decisão do gestor: pela mesa (contrato) ou por `Tracker.on_decision` (código real da C7)."""
        from escalista.api.accounts import SEEDED_ACCOUNTS
        from escalista.domain.contracts import Role

        gestor = next(a for a in SEEDED_ACCOUNTS if a.role == Role.GESTOR)
        desk = getattr(self.tracker, "desk", None)
        if desk is not None:
            return desk.decide(item.id, option_index, gestor)
        return self.tracker.on_decision(
            case_id=item.source.get("case_id"),
            code=item.card.code,
            option_index=option_index,
            approver_id=gestor.id,
            role=gestor.role,
        )

    def tracer(self) -> Any:
        """Um `Tracer` sobre o `trace_event` do mesmo engine (para chamar as ferramentas do portão direto)."""
        from escalista.agents.optimizer.tools import Tracer
        from escalista.audit.sink import SqlTraceSink

        sink = SqlTraceSink(self.engine)
        return Tracer(sink, self.clock, new_id=lambda: uuid.uuid4().hex, list_events=sink.list_events)

    def rows(self, table: str) -> list[dict[str, Any]]:
        from sqlalchemy import text

        with self.engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(text(f'SELECT * FROM "{table}"'))]  # noqa: S608

    def published_version(self) -> Any:
        from escalista.store.sql_repository import SqlRepository

        return SqlRepository(self.engine).latest_published()


def memory_engine() -> Engine:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def build(ctx: EvalContext, *, llm: Any = None, start: datetime | None = None, **kwargs: Any) -> Rig:
    """`build_tracker` (SAIDA-AC-02) com SQLite em memória, `StepClock` e o `LLMClient` dado (falso, por padrão)."""
    from escalista.api.tracker_wiring import build_tracker

    gab = scenario_expected(ctx)  # sem gabarito, o cenário não afirma nada
    begin = start or (as_dt(gab["demo_clock"]) if "demo_clock" in gab else DEMO_RESET)
    clock = StepClock(begin)
    engine = memory_engine()
    llm = llm if llm is not None else ScriptedLLM()
    tracker = build_tracker(engine=engine, clock=clock, llm=llm, scenario="folga", data_dir=ctx.data_dir, **kwargs)
    return Rig(tracker=tracker, engine=engine, clock=clock, llm=llm)


def attachment(at: Atestado) -> Any:
    from escalista.domain.tracking import Attachment

    return Attachment(data=at.data, media_type=at.media_type, filename=at.file)


def employee_by_name(ctx: EvalContext, name: str) -> str:
    for e in scenario_data(ctx).get("employees", []):
        if e.get("name") == name:
            return str(e["id"])
    raise NotRun(f"falta {SAIDA_15} (pessoa do atestado no cenario_folga.json)")


def trigger_keys(result: Any) -> list[tuple[str, str | None, str]]:
    return [(t.kind, t.employee_id, t.ref) for t in result.triggers]


# --- vazamento ------------------------------------------------------------------------------------------------------


@contextmanager
def capture_root_log(buffer: io.StringIO) -> Iterator[None]:
    """Handler na raiz, nível DEBUG, durante o cenário (log do acompanhamento como superfície do vazamento)."""
    handler = logging.StreamHandler(buffer)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def surfaces(rig: Rig, *, returns: dict[str, Any], llm_messages: list[Any]) -> dict[str, str]:
    """Superfícies nomeadas: cada tabela (todas as colunas, todas as linhas), `trace_event` por `kind` (os `track.*`
    com o próprio nome, para o padrão de CID valer neles), o log capturado, os retornos e as mensagens ao modelo."""
    from sqlalchemy import inspect

    blobs: dict[str, str] = {}
    for table in inspect(rig.engine).get_table_names():
        rows = rig.rows(table)
        if table == "trace_event":
            for row in rows:
                kind = str(row.get("kind"))
                name = kind if kind.startswith("track.") else f"trace_event.{kind}"
                blobs[name] = blobs.get(name, "") + "\n" + " ".join(_text(v) for v in row.values())
        else:
            blobs[table] = "\n".join(" ".join(_text(v) for v in row.values()) for row in rows)
    blobs["log"] = rig.log.getvalue()
    for name, value in returns.items():
        dumped = value.model_dump_json() if hasattr(value, "model_dump_json") else json.dumps(value, default=str)
        blobs[f"retorno.{name}"] = dumped
    blobs["llm.mensagens"] = "\n".join(_text(getattr(m, "content", m)) for m in llm_messages)
    return blobs


def leaks(blobs: dict[str, str], planted: list[str]) -> list[Any]:
    from escalista.audit.protected import find_leaks

    return find_leaks(blobs, planted, pattern_surfaces=TRACK_PATTERN_SURFACES)


def describe_leaks(found: list[Any]) -> str:
    """Superfície e tipo, nunca o valor."""
    return ", ".join(f"{leak.surface} ({leak.kind})" for leak in found) or "nenhum"


class Recording:
    """Embrulha um `LLMClient` e guarda as mensagens que saem para o modelo (superfície do vazamento)."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.messages: list[Any] = []
        self.calls = 0

    def complete(self, *, size: str, messages: list[Any], tool_schema: Any = None, run_id: str,
                 parent_id: str | None = None, kind: str | None = None) -> Any:  # fmt: skip
        self.calls += 1
        self.messages.extend(messages)
        extra = {"kind": kind} if kind is not None else {}
        return self.inner.complete(
            size=size, messages=messages, tool_schema=tool_schema, run_id=run_id, parent_id=parent_id, **extra
        )


def all_llm_messages(llm: Any) -> list[Any]:
    if isinstance(llm, Recording):
        return list(llm.messages)
    calls = getattr(llm, "calls", [])
    return [m for c in calls if isinstance(c, dict) for m in c.get("messages", [])]


def at_minutes(moment: datetime, minutes: int) -> datetime:
    return moment + timedelta(minutes=minutes)
