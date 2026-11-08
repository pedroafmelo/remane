"""Evals E2: leitura de escalas (plano da C6, seção 12; D5). Cada arquivo de `data/demo/e2/` mais o exemplo em grade.

    uv run python -m escalista.evals --suite e2                 # sem modelo: heurística (`guess_mapping`), DEC-039
    uv run python -m escalista.evals --suite e2 --with-model    # o mapeamento vem do modelo pequeno (chave, à mão)

Cadeia por arquivo: `read_tables` → mapeamento (heurística, ou `propose_mapping` com `check_mapping`) → `apply_mapping`
→ `verify_evidence` (e `resolve_identities` quando o gabarito traz `identity`). O resultado é comparado com o gabarito
(`<arquivo>.esperado.json`, formato em `data/demo/e2/README.md`).

Métricas por arquivo e no total, sem arredondar: turnos esperados, corretos (casados por pessoa + início + fim, ao
minuto), **inventados** (lidos que não estão no gabarito; precisa ser 0), perdidos, problemas apontados contra
`expected_issues`, RX-13 certo, evidência vazia, fonte do mapeamento, identidade (E2-08) e igualdade E2-09 = E2-02.
Grava `var/evals/e2-<timestamp>.json` e `var/evals/e2-latest.json`. Código de saída diferente de zero se algum arquivo
falhar ou se algum turno for inventado. Com modelo, registra por arquivo modelo, tokens, `cost_usd` (só o medido) e
latência, coletados dos eventos `llm.map_columns` do rastro; se o modelo falhar, a reserva (heurística) e o motivo.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time as wallclock
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from escalista.domain.contracts import LLMUnavailableError, TraceEvent
from escalista.domain.ports import LLMClient, TraceSink
from escalista.domain.reading import ColumnMapping
from escalista.domain.schedule import CsvIssue
from escalista.ingest.tables import TablesResult, read_tables
from escalista.rules.header_aliases import guess_mapping
from escalista.rules.identity import resolve_identities
from escalista.rules.mapping import MappingResult, apply_mapping, check_mapping, verify_evidence

SUITE = "e2"
SOURCE_HEURISTIC = "heuristica"
SOURCE_MODEL = "modelo"
SOURCE_FALLBACK = "heuristica (reserva)"
SOURCE_NONE = "nenhuma"
MODEL_EVENT_KIND = "llm.map_columns"
FAILURE_EVENT_KIND = "exception.raised"
DEMO_EXAMPLE = "escala_exemplo_grade.esperado.json"

ShiftKey = tuple[str, datetime, datetime]  # pessoa como escrita no arquivo, início, fim (ao minuto)
ClientFactory = Callable[[TraceSink], LLMClient]


class MemorySink:
    """`TraceSink` em memória: guarda os eventos do cliente para ler tokens, custo e latência de cada chamada."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class ModelUse:
    """O que o modelo gastou neste arquivo (medido nos eventos; `cost_usd` é `None` se faltar o custo de alguma
    chamada, nunca estimado)."""

    calls: int
    models: list[str]
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: Decimal | None
    latency_ms: int | None
    fell_back: bool
    fallback_reason: str | None
    same_as_heuristic: bool | None

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


@dataclass
class FileResult:
    id: str
    file: str
    expect: str
    source: str = SOURCE_NONE
    expected: int = 0
    correct: int = 0
    invented: int = 0
    lost: int = 0
    wrong_store: int = 0
    issues_expected: int = 0
    issues_found: int = 0  # dos esperados, quantos foram apontados
    issues_extra: int = 0  # apontados que o gabarito não prevê
    rx13_ok: bool | None = None  # só nos arquivos com gabarito RX-13
    evidence_problems: int = 0
    identity: dict[str, Any] | None = None  # só no gabarito com `identity`
    same_as: dict[str, Any] | None = None  # só no E2-09
    model: ModelUse | None = None
    elapsed_ms: int = 0
    error: str | None = None
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "arquivo": self.file,
            "esperado": self.expect,
            "fonte_mapeamento": self.source,
            "turnos_esperados": self.expected,
            "corretos": self.correct,
            "inventados": self.invented,
            "perdidos": self.lost,
            "loja_diferente": self.wrong_store,
            "problemas_esperados": self.issues_expected,
            "problemas_achados": self.issues_found,
            "problemas_extras": self.issues_extra,
            "rx13_certo": self.rx13_ok,
            "evidencia_com_problema": self.evidence_problems,
            "identidade": self.identity,
            "igual_ao": self.same_as,
            "tempo_ms": self.elapsed_ms,
            "erro": self.error,
            "falhas": self.failures,
            "passou": self.passed,
        }
        if self.model is not None:
            out["modelo"] = self.model.as_json()
        return out


# Gabarito ---------------------------------------------------------------------------------------------------------


def _minute(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(second=0, microsecond=0)


def _key(name: str, start: datetime, end: datetime) -> ShiftKey:
    return (name, start.replace(second=0, microsecond=0), end.replace(second=0, microsecond=0))


def _expected_keys(gold: dict[str, Any]) -> list[tuple[ShiftKey, str]]:
    return [((s["person_name"], _minute(s["start"]), _minute(s["end"])), s["store"]) for s in gold.get("shifts", [])]


def _obtained_keys(result: MappingResult | None) -> list[tuple[ShiftKey, str | None]]:
    if result is None:
        return []
    return [(_key(s.person_name, s.start, s.end), s.store) for s in result.shifts]


def _file_id(gabarito: Path) -> str:
    if gabarito.name == DEMO_EXAMPLE:
        return "EXEMPLO"
    stem = gabarito.name.removesuffix(".esperado.json")
    parts = stem.split("-")
    return f"{parts[0].upper()}-{parts[1]}" if len(parts) > 1 else stem.upper()


def discover(data_dir: Path) -> list[Path]:
    """Gabaritos do E2 em ordem estável (E2-01 ... E2-11d) e, por último, o do exemplo em grade da demo."""
    found = sorted((data_dir / "e2").glob("*.esperado.json"))
    example = data_dir / DEMO_EXAMPLE
    return [*found, example] if example.exists() else found


def _issue_matches(expected: dict[str, Any], issue: CsvIssue) -> bool:
    if issue.line != expected.get("line"):
        return False
    reason = issue.reason.casefold()
    kind = str(expected.get("kind", "")).casefold()
    if kind and kind not in reason:
        return False
    origin = expected.get("duplicate_of_line")
    return origin is None or f"linha {origin}" in reason


def _compare_issues(expected: list[dict[str, Any]], found: Sequence[CsvIssue]) -> tuple[int, int]:
    """(esperados achados, apontados sem correspondência no gabarito). Cada problema real casa com no máximo um."""
    free = list(found)
    hit = 0
    for item in expected:
        match = next((i for i in free if _issue_matches(item, i)), None)
        if match is not None:
            free.remove(match)
            hit += 1
    return hit, len(free)


# Identidade (E2-08) ------------------------------------------------------------------------------------------------


def _normalized(name: str) -> str:
    return " ".join(name.split()).casefold()


def _identity_check(gold_identity: dict[str, Any], gold: dict[str, Any], result: MappingResult) -> dict[str, Any]:
    ident = resolve_identities(result.shifts)
    want_merged = sorted(sorted(m["names"]) for m in gold_identity.get("merged_by_normalization", []))
    got_merged = sorted(sorted(m.names) for m in ident.merged)
    want_cards = Counter((c["kind"], frozenset(c["names"])) for c in gold_identity.get("cards", []))
    got_cards = Counter((c.kind, frozenset(c.names)) for c in ident.cards)
    kinds = Counter(c.kind for c in ident.cards)
    expected_people = len({_normalized(s["person_name"]) for s in gold.get("shifts", [])})
    auto_merges = max(0, expected_people - len(ident.people))
    ok = (
        want_merged == got_merged
        and want_cards == got_cards
        and auto_merges == gold_identity.get("auto_merge_by_similarity", 0)
    )
    return {
        "fusoes_esperadas": len(want_merged),
        "fusoes_obtidas": len(got_merged),
        "cartoes_por_tipo": dict(sorted(kinds.items())),
        "cartoes_esperados": len(gold_identity.get("cards", [])),
        "fusao_por_parecenca": auto_merges,
        "pessoas": len(ident.people),
        "pessoas_esperadas": expected_people,
        "bate_com_gabarito": ok,
    }


# Mapeamento: heurística ou modelo ---------------------------------------------------------------------------------


def _model_use(
    sink: MemorySink, run_id: str, fell_back: bool, reason: str | None, same_as_heuristic: bool | None
) -> ModelUse:
    events = [e for e in sink.events if e.run_id == run_id and e.kind in (MODEL_EVENT_KIND, FAILURE_EVENT_KIND)]
    complete = [e for e in events if e.kind == MODEL_EVENT_KIND]

    def total(values: list[int | None]) -> int | None:
        return None if not values or any(v is None for v in values) else sum(v for v in values if v is not None)

    costs = [e.cost_usd for e in events]
    cost = None if not costs or any(c is None for c in costs) else sum((c for c in costs if c is not None), Decimal(0))
    return ModelUse(
        calls=len(events),
        models=sorted({e.model for e in events if e.model}),
        tokens_in=total([e.tokens_in for e in complete]) if complete else None,
        tokens_out=total([e.tokens_out for e in complete]) if complete else None,
        cost_usd=cost,
        latency_ms=total([e.latency_ms for e in events]),
        fell_back=fell_back,
        fallback_reason=reason,
        same_as_heuristic=same_as_heuristic,
    )


def _fallback_reason(exc: LLMUnavailableError) -> str:
    card = exc.card
    tail = "; ".join(card.evidence[-1:]) if card.evidence else ""
    return f"{card.code}: {card.reason}" + (f" ({tail})" if tail else "")


def _choose_mapping(
    tables: TablesResult, name: str, client_factory: ClientFactory | None, sink: MemorySink
) -> tuple[ColumnMapping | None, str, ModelUse | None]:
    heuristic = guess_mapping(tables.tables)
    if client_factory is None:
        return heuristic, SOURCE_HEURISTIC if heuristic is not None else SOURCE_NONE, None
    from escalista.llm.prompts.map_columns import propose_mapping

    run_id = f"e2-{name}"
    try:
        mapping = propose_mapping(client_factory(sink), tables.tables, run_id=run_id, check=check_mapping)
    except LLMUnavailableError as exc:
        source = SOURCE_FALLBACK if heuristic is not None else SOURCE_NONE
        return heuristic, source, _model_use(sink, run_id, True, _fallback_reason(exc), None)
    same = None if heuristic is None else mapping == heuristic
    return mapping, SOURCE_MODEL, _model_use(sink, run_id, False, None, same)


# Um arquivo -------------------------------------------------------------------------------------------------------


def _evaluate(
    gabarito: Path, data_dir: Path, client_factory: ClientFactory | None, sink: MemorySink
) -> tuple[FileResult, MappingResult | None, dict[str, Any]]:
    gold = json.loads(gabarito.read_text(encoding="utf-8"))
    path = data_dir / gold["file"]
    res = FileResult(id=_file_id(gabarito), file=gold["file"], expect=gold["expect"])
    started = wallclock.perf_counter()
    result: MappingResult | None = None
    try:
        tables = read_tables(path.name, path.read_bytes())
        if tables.exception is None and tables.tables:
            mapping, res.source, res.model = _choose_mapping(tables, path.stem, client_factory, sink)
            result = apply_mapping(tables.tables, mapping) if mapping is not None else None
            if result is not None:
                res.evidence_problems = len(verify_evidence(tables.tables, result))
        _score(res, gold, tables, result)
    except Exception as exc:  # noqa: BLE001 - um arquivo que quebra a cadeia é falha dele, não aborta a suíte
        res.error = f"{type(exc).__name__}: {exc}"
        res.failures.append(f"erro: {res.error}")
    res.elapsed_ms = round((wallclock.perf_counter() - started) * 1000)
    return res, result, gold


def _score(res: FileResult, gold: dict[str, Any], tables: TablesResult, result: MappingResult | None) -> None:
    obtained = _obtained_keys(result)
    if gold["expect"] == "RX-13":
        res.rx13_ok = tables.exception is not None and not obtained
        if not res.rx13_ok:
            res.failures.append("RX-13 esperado: o arquivo foi lido ou devolveu turnos")
        res.invented = len(obtained)
        if res.invented:
            res.failures.append(f"{res.invented} turno(s) inventado(s) em arquivo ilegível")
        return

    expected = _expected_keys(gold)
    res.expected = len(expected)
    want = Counter(k for k, _ in expected)
    got = Counter(k for k, _ in obtained)
    matched = want & got
    res.correct = sum(matched.values())
    res.invented = sum((got - want).values())
    res.lost = sum((want - got).values())
    # Loja: entre os turnos casados, quantos trazem outra loja que a do gabarito.
    stores_want = Counter((k, s) for k, s in expected)
    stores_got = Counter((k, s) for k, s in obtained)
    res.wrong_store = res.correct - sum((stores_want & stores_got).values())

    if tables.exception is not None:
        res.failures.append(f"arquivo recusado ({tables.exception.code}) mas o gabarito espera turnos")
    if res.source == SOURCE_NONE and tables.exception is None:
        res.failures.append("nenhum mapeamento obtido")
    if res.invented:
        res.failures.append(f"{res.invented} turno(s) inventado(s)")
    if res.lost:
        res.failures.append(f"{res.lost} turno(s) perdido(s)")
    if res.wrong_store:
        res.failures.append(f"{res.wrong_store} turno(s) com a loja diferente do gabarito")
    if res.evidence_problems:
        res.failures.append(f"{res.evidence_problems} problema(s) em verify_evidence")

    issues = result.issues if result is not None else []
    wanted_issues = gold.get("expected_issues", [])
    res.issues_expected = len(wanted_issues)
    res.issues_found, res.issues_extra = _compare_issues(wanted_issues, issues)
    if res.issues_found != res.issues_expected or res.issues_extra:
        res.failures.append(
            f"problemas: {res.issues_found}/{res.issues_expected} esperados achados, {res.issues_extra} extra(s)"
        )

    if "identity" in gold and result is not None:
        res.identity = _identity_check(gold["identity"], gold, result)
        if not res.identity["bate_com_gabarito"]:
            res.failures.append("identidade diferente do gabarito")


def _same_as(results: dict[str, FileResult], shifts: dict[str, MappingResult | None], golds: dict[str, dict]) -> None:
    """E2-09 deve dar o mesmo resultado do arquivo de `same_as` (E2-02), com o nome de `renamed` trocado."""
    for file_id, gold in golds.items():
        target = gold.get("same_as")
        if not target:
            continue
        res = results[file_id]
        base_id = next((i for i, g in golds.items() if g["file"] == target), None)
        if base_id is None or shifts.get(base_id) is None or shifts.get(file_id) is None:
            res.same_as = {"arquivo": target, "igual": False, "motivo": "resultado de referência indisponível"}
            res.failures.append(f"sem resultado para comparar com {target}")
            continue
        renamed = gold.get("renamed", {})
        base = shifts[base_id]
        assert base is not None
        reference = Counter(_key(renamed.get(s.person_name, s.person_name), s.start, s.end) for s in base.shifts)
        current = shifts[file_id]
        assert current is not None
        obtained = Counter(_key(s.person_name, s.start, s.end) for s in current.shifts)
        same_mapping = base.mapping == current.mapping
        equal = reference == obtained and same_mapping
        res.same_as = {
            "arquivo": target,
            "igual": equal,
            "turnos_iguais": reference == obtained,
            "mapeamento_igual": same_mapping,
        }
        if not equal:
            res.failures.append(f"resultado diferente do de {target}")


# Suíte ------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SuiteRun:
    results: list[FileResult]
    report: dict[str, Any]
    path: Path
    table: str

    @property
    def invented(self) -> int:
        return sum(r.invented for r in self.results)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results) and self.invented == 0


def scoreboard(results: Sequence[FileResult]) -> str:
    return f"{sum(1 for r in results if r.passed)}/{len(results)}"


def run_files(
    data_dir: Path, *, client_factory: ClientFactory | None = None, sink: MemorySink | None = None
) -> list[FileResult]:
    memory = sink if sink is not None else MemorySink()
    results: dict[str, FileResult] = {}
    mapped: dict[str, MappingResult | None] = {}
    golds: dict[str, dict] = {}
    for gabarito in discover(data_dir):
        res, result, gold = _evaluate(gabarito, data_dir, client_factory, memory)
        results[res.id], mapped[res.id], golds[res.id] = res, result, gold
    _same_as(results, mapped, golds)
    return list(results.values())


def _sum_model(results: Sequence[FileResult]) -> dict[str, Any] | None:
    uses = [r.model for r in results if r.model is not None]
    if not uses:
        return None
    costs = [u.cost_usd for u in uses if u.calls]
    latencies = [u.latency_ms for u in uses if u.calls]
    return {
        "chamadas": sum(u.calls for u in uses),
        "arquivos_com_reserva": sum(1 for u in uses if u.fell_back),
        "tokens_entrada": sum(u.tokens_in or 0 for u in uses),
        "tokens_saida": sum(u.tokens_out or 0 for u in uses),
        "cost_usd": None
        if not costs or any(c is None for c in costs)
        else format(sum((c for c in costs if c is not None), Decimal(0)), "f"),
        "latencia_ms": None if not latencies or any(v is None for v in latencies) else sum(latencies),  # type: ignore[arg-type]
    }


def build_report(results: Sequence[FileResult], generated_at: datetime, *, with_model: bool) -> dict[str, Any]:
    shifts = [r for r in results if r.expect == "shifts"]
    rx13 = [r for r in results if r.expect == "RX-13"]
    report: dict[str, Any] = {
        "suite": SUITE,
        "gerado_em": generated_at.isoformat(timespec="seconds"),
        "modo": "com_modelo" if with_model else "sem_modelo",
        "placar": scoreboard(results),
        "totais": {
            "arquivos": len(results),
            "arquivos_ok": sum(1 for r in results if r.passed),
            "turnos_esperados": sum(r.expected for r in results),
            "corretos": sum(r.correct for r in results),
            "inventados": sum(r.invented for r in results),
            "perdidos": sum(r.lost for r in results),
            "problemas_esperados": sum(r.issues_expected for r in results),
            "problemas_achados": sum(r.issues_found for r in results),
            "problemas_extras": sum(r.issues_extra for r in results),
            "rx13_certos": f"{sum(1 for r in rx13 if r.rx13_ok)}/{len(rx13)}",
            "evidencia_com_problema": sum(r.evidence_problems for r in results),
            "arquivos_de_turnos": len(shifts),
        },
        "arquivos": [r.as_json() for r in results],
    }
    model_total = _sum_model(results)
    if model_total is not None:
        report["modelo"] = model_total
    return report


def format_table(results: Sequence[FileResult], report: dict[str, Any]) -> str:
    head = ("id", "arquivo", "esper.", "corretos", "inventados", "perdidos", "problemas", "RX-13", "fonte", "ok")
    rows: list[tuple[str, ...]] = []
    for r in results:
        problems = f"{r.issues_found}/{r.issues_expected}" + (f" +{r.issues_extra}" if r.issues_extra else "")
        rx = "-" if r.rx13_ok is None else ("sim" if r.rx13_ok else "NAO")
        rows.append(
            (
                r.id,
                Path(r.file).name,
                str(r.expected),
                str(r.correct),
                str(r.invented),
                str(r.lost),
                problems,
                rx,
                r.source,
                "ok" if r.passed else "FALHOU",
            )
        )
    widths = [max(len(head[i]), *(len(row[i]) for row in rows)) if rows else len(head[i]) for i in range(len(head))]

    def line(cells: Sequence[str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths, strict=True)).rstrip()

    out = [line(head), line(["-" * w for w in widths]), *(line(row) for row in rows)]
    for r in results:
        out.extend(f"  {r.id}: {why}" for why in r.failures)
        if r.identity is not None:
            out.append(f"  {r.id}: identidade {r.identity}")
        if r.same_as is not None:
            out.append(f"  {r.id}: igual a {r.same_as['arquivo']}: {r.same_as['igual']}")
        if r.model is not None:
            m = r.model
            cost = "n/medido" if m.cost_usd is None else f"US$ {format(m.cost_usd, 'f')}"
            fallback = f" | RESERVA: {m.fallback_reason}" if m.fell_back else ""
            out.append(
                f"  {r.id}: modelo {','.join(m.models) or '-'} | {m.calls} chamada(s) | tokens {m.tokens_in}/"
                f"{m.tokens_out} | {cost} | {m.latency_ms} ms{fallback}"
            )
    t = report["totais"]
    out.append("")
    out.append(
        f"Turnos: esperados {t['turnos_esperados']}, corretos {t['corretos']}, inventados {t['inventados']}, "
        f"perdidos {t['perdidos']}. Problemas: {t['problemas_achados']}/{t['problemas_esperados']} esperados achados, "
        f"{t['problemas_extras']} extra(s). RX-13 certo: {t['rx13_certos']}. Evidência com problema: "
        f"{t['evidencia_com_problema']}."
    )
    if "modelo" in report:
        m = report["modelo"]
        out.append(
            f"Modelo: {m['chamadas']} chamada(s), {m['arquivos_com_reserva']} arquivo(s) na reserva, tokens "
            f"{m['tokens_entrada']}/{m['tokens_saida']}, cost_usd {m['cost_usd']}, latência {m['latencia_ms']} ms."
        )
    out.append(f"Placar E2 ({report['modo']}): {report['placar']} arquivos")
    return "\n".join(out)


def write_report(report: dict[str, Any], out_dir: Path, generated_at: datetime) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{SUITE}-{generated_at:%Y%m%dT%H%M%S}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(path, out_dir / f"{SUITE}-latest.json")
    return path


def run_suite(
    out_dir: Path,
    *,
    data_dir: Path = Path("data/demo"),
    client_factory: ClientFactory | None = None,
    sink: MemorySink | None = None,
    now: Callable[[], datetime] = datetime.now,
) -> SuiteRun:
    """Roda a suíte. `client_factory` (recebe o `TraceSink` em memória) liga o modo com modelo; `None` é sem modelo."""
    results = run_files(data_dir, client_factory=client_factory, sink=sink)
    generated_at = now()
    report = build_report(results, generated_at, with_model=client_factory is not None)
    return SuiteRun(results, report, write_report(report, out_dir, generated_at), format_table(results, report))


def _real_client_factory() -> ClientFactory:
    """Cliente real da Featherless, como o smoke (`llm/smoke.py`): chaves e modelos vêm do ambiente/`.env`."""
    from escalista.clock.system import SystemClock
    from escalista.config import Settings
    from escalista.llm.client import FeatherlessClient

    settings = Settings()
    if not settings.featherless_keys:
        raise SystemExit("nenhuma chave da Featherless configurada (FEATHERLESS_API_KEY_1 a _4 no .env)")
    clock = SystemClock()
    return lambda sink: FeatherlessClient.from_settings(settings, trace_sink=sink, clock=clock)


def build_parser(prog: str = "escalista.evals") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="Evals E2 do Escalista: leitura de escalas")
    parser.add_argument("--with-model", action="store_true", help="mapeamento pelo modelo (usa a chave; custo medido)")
    parser.add_argument("--out", type=Path, default=Path("var/evals"), help="diretório do relatório JSON")
    parser.add_argument("--data", type=Path, default=Path("data/demo"), help="dados sintéticos da demo")
    return parser


def run_cli(args: argparse.Namespace, *, client_factory: ClientFactory | None = None) -> int:
    factory = client_factory
    if factory is None and args.with_model:
        factory = _real_client_factory()
    run = run_suite(args.out, data_dir=args.data, client_factory=factory)
    print(run.table)
    print(f"Relatório: {run.path} (e {run.path.with_name('e2-latest.json')})")
    return 0 if run.all_passed else 1
