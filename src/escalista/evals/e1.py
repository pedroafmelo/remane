"""Evals E1: 10 cenários sem modelo, num comando (plano da C5, D5; RN-04, RX-02, RX-13).

    uv run python -m escalista.evals --suite e1

Cada cenário monta a entrada, chama o código real (leitura do CSV, verificador, solver, custo) e compara com o
esperado. Grava `var/evals/e1-<timestamp>.json` e `var/evals/e1-latest.json`, imprime a tabela e o placar **real**
(`N/10`, sem arredondar). Código de saída diferente de zero se algum cenário falhar. Nenhum modelo é chamado: custo 0
de modelo; o tempo de cada cenário é o medido.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time as wallclock
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import cached_property
from pathlib import Path

from escalista.domain.results import SolveRequest
from escalista.domain.rules import RuleCard
from escalista.domain.schedule import DemandSlot, Employee, Schedule, Shift, Store
from escalista.ingest.csv_schedule import read_schedule_csv
from escalista.ingest.demo_network import load_demo_network
from escalista.rules.loader import load_rule_card
from escalista.solver.cost import compute_metrics
from escalista.solver.model import solve
from escalista.verifier import coverage_gaps, verify

WEEK_START = date(2027, 1, 11)  # segunda; semana de referência da demo, já sob a EC 141
SOLVER_SEED = 42
SOLVER_TIME_LIMIT_S = 60.0
SOLVER_WORKERS = 1

WEEKLY, DAILY, REST_GAP, WEEKLY_REST = (
    "jornada_semanal_max",
    "jornada_diaria_max",
    "interjornada_min",
    "repouso_semanal",
)


@dataclass(frozen=True)
class Outcome:
    """O que um cenário devolve: esperado e obtido em texto, e o veredito."""

    expected: str
    obtained: str
    passed: bool


@dataclass(frozen=True)
class ScenarioResult:
    id: str
    description: str
    expected: str
    obtained: str
    passed: bool
    elapsed_ms: int

    def as_json(self) -> dict:
        return {
            "id": self.id,
            "descricao": self.description,
            "esperado": self.expected,
            "obtido": self.obtained,
            "passou": self.passed,
            "tempo_ms": self.elapsed_ms,
        }


@dataclass
class EvalContext:
    """Entradas compartilhadas, lidas uma vez e só se algum cenário as pedir."""

    data_dir: Path = Path("data/demo")
    rules_dir: Path = Path("data/regras")
    reference_date: date = WEEK_START

    @cached_property
    def card(self) -> RuleCard:
        return load_rule_card(self.rules_dir, self.reference_date)

    @cached_property
    def network(self) -> tuple[list[Store], list[Employee], list[DemandSlot]]:
        return load_demo_network(self.data_dir)


@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    run: Callable[[EvalContext], Outcome]


# Auxiliares -------------------------------------------------------------------------------------------------------


def _shift(day: int, start: str, hours: float, employee: str = "P001", store: str = "L1") -> Shift:
    begin = datetime.combine(WEEK_START + timedelta(days=day), time.fromisoformat(start))
    return Shift(employee_id=employee, store_id=store, start=begin, end=begin + timedelta(hours=hours))


def _schedule(*shifts: Shift) -> Schedule:
    return Schedule(week_start=WEEK_START, shifts=list(shifts))


def _by_kind(violations: list) -> dict[str, int]:
    return dict(sorted(Counter(v.kind for v in violations).items()))


def _outcome(expected: str, obtained: str, passed: bool) -> Outcome:
    return Outcome(expected=expected, obtained=obtained, passed=passed)


def _primitive_outcome(ctx: EvalContext, kind: str, bad: Schedule, control: Schedule, what: str) -> Outcome:
    """Escala com a violação: exatamente 1 do tipo `kind`, citando a fonte da regra. Controle no limite: 0 do tipo."""
    found = [v for v in verify(bad, ctx.card).violations if v.kind == kind]
    ok = [v for v in verify(control, ctx.card).violations if v.kind == kind]
    cites_source = bool(found) and all(v.source for v in found)
    passed = len(found) == 1 and cites_source and not ok
    obtained = f"{len(found)} violação de {kind} ({found[0].detail if found else '-'}); controle no limite: {len(ok)}"
    return _outcome(f"1 violação de {kind} ({what}) com a fonte citada; controle no limite: 0", obtained, passed)


# Cenários 1 a 5: uma primitiva cada --------------------------------------------------------------------------------


def _s01_weekly(ctx: EvalContext) -> Outcome:
    bad = _schedule(*(_shift(d, "08:00", 7) for d in range(5)), _shift(5, "08:00", 8))  # 43h
    control = _schedule(*(_shift(d, "08:00", 7) for d in range(6)))  # 42h exatas
    return _primitive_outcome(ctx, WEEKLY, bad, control, "43h contra o limite de 42h")


def _s02_daily(ctx: EvalContext) -> Outcome:
    bad = _schedule(_shift(0, "08:00", 9))
    control = _schedule(_shift(0, "08:00", 8))
    return _primitive_outcome(ctx, DAILY, bad, control, "9h contra o limite de 8h")


def _s03_rest_gap(ctx: EvalContext) -> Outcome:
    bad = _schedule(_shift(0, "14:00", 8), _shift(1, "08:00", 8))  # termina 22h, volta 08h: 10h
    control = _schedule(_shift(0, "14:00", 8), _shift(1, "10:00", 8))  # 12h exatas (pol_interjornada; a CLT pede 11h)
    return _primitive_outcome(ctx, REST_GAP, bad, control, "10h de descanso contra o mínimo de 12h")


def _s04_weekly_rest(ctx: EvalContext) -> Outcome:
    bad = _schedule(*(_shift(d, "08:00", 7) for d in range(6)))  # 6 dias: 1 repouso
    control = _schedule(*(_shift(d, "08:00", 7) for d in range(5)))  # 5 dias: 2 repousos
    return _primitive_outcome(ctx, WEEKLY_REST, bad, control, "1 repouso contra o mínimo de 2")


def _s05_coverage(ctx: EvalContext) -> Outcome:
    demand = [
        DemandSlot(
            store_id="L1",
            day=WEEK_START,
            start=(datetime(2027, 1, 11, 8) + timedelta(minutes=30 * i)).time(),
            required=2,
        )
        for i in range(4)
    ]
    schedule = _schedule(
        _shift(0, "08:00", 1)
    )  # 1 pessoa das 08h às 09h; falta 1 nas 2 primeiras faixas e 2 nas outras
    _, employees, _ = ctx.network
    report = verify(schedule, ctx.card)
    gaps = coverage_gaps(schedule, demand)
    metrics = compute_metrics(schedule, employees, demand, ctx.card, violations=report.total)
    missing = sorted((g.start.strftime("%H:%M"), g.required) for g in gaps)
    expected_missing = [("08:00", 1), ("08:30", 1), ("09:00", 2), ("09:30", 2)]
    passed = (
        report.total == 0
        and missing == expected_missing
        and metrics.uncovered_slots == 4
        and metrics.coverage_pct == 25.0
    )
    return _outcome(
        "0 violações (cobertura não é violação); 4 faixas com falta (08:00 1, 08:30 1, 09:00 2, 09:30 2); "
        "cobertura 25,0%",
        f"{report.total} violações; faixas com falta {missing}; "
        f"{metrics.uncovered_slots} faixas descobertas na métrica; cobertura {metrics.coverage_pct}%",
        passed,
    )


# Cenário 6: a escala enviada, em 44h, julgada sob 42h -------------------------------------------------------------

EXPECTED_ATUAL = {WEEKLY: 60, WEEKLY_REST: 60, REST_GAP: 30, DAILY: 8}  # medido em 2026-11-07 sobre data/demo


def _s06_current_schedule(ctx: EvalContext) -> Outcome:
    stores, employees, _ = ctx.network
    content = (ctx.data_dir / "escala_atual.csv").read_bytes()
    read = read_schedule_csv("escala_atual.csv", content, employees=employees, stores=stores, week_start=WEEK_START)
    if read.schedule is None or read.exception is not None:
        code = read.exception.code if read.exception else "sem escala"
        return _outcome("escala_atual.csv legível e julgada sob 42h", f"leitura falhou ({code})", False)
    report = verify(read.schedule, ctx.card)
    kinds = _by_kind(report.violations)
    expected_kinds = dict(sorted(EXPECTED_ATUAL.items()))
    passed = report.total == sum(EXPECTED_ATUAL.values()) and kinds == expected_kinds
    return _outcome(
        f"{sum(EXPECTED_ATUAL.values())} violações sob 42h: {expected_kinds}",
        f"{report.total} violações: {kinds}",
        passed,
    )


# Cenário 7: demanda acima da capacidade -> RX-02 (vindo do solver) -----------------------------------------------


def _s07_rx02(ctx: EvalContext) -> Outcome:
    # 2 pessoas, demanda de 3 pessoas das 08h às 16h nos 7 dias = 168 pessoa-horas. Capacidade de cada pessoa:
    # mín(42h, 5 dias x 8h) = 40h; 2 x 40 = 80h. Faltam 88 pessoa-horas; 88 ÷ 40 = 2,2 -> contratar 3.
    store = Store(id="S1", name="Loja de teste", opens=time(8), closes=time(22))
    employees = [
        Employee(id=f"E{i}", name=f"E{i}", store_id="S1", job="caixa", hourly_wage=Decimal("10.00"),
                 contract_hours=42, sex="F")
        for i in (1, 2)
    ]  # fmt: skip
    demand = [
        DemandSlot(store_id="S1", day=WEEK_START + timedelta(days=d), start=time(8 + h // 2, 30 * (h % 2)), required=3)
        for d in range(7)
        for h in range(16)
    ]
    result = solve(
        SolveRequest(
            card=ctx.card, stores=[store], employees=employees, demand=demand, week_start=WEEK_START,
            seed=SOLVER_SEED, time_limit_s=30.0, num_workers=1,
        )
    )  # fmt: skip
    missing_h = sum(u.required for u in result.uncovered) / 2
    exc = result.exception
    evidence = " | ".join(exc.evidence) if exc else ""
    violations = verify(result.schedule, ctx.card).total if result.schedule else -1
    passed = (
        exc is not None and exc.code == "RX-02" and missing_h == 88 and "contratar 3" in evidence and violations == 0
    )
    return _outcome(
        "RX-02 do solver: faltam 88 pessoa-horas, 88 ÷ 40 h = 2,2 -> contratar 3; escala parcial com 0 violações",
        f"exceção {exc.code if exc else None}; faltam {missing_h:g} pessoa-horas; "
        f"{'contratar 3' if 'contratar 3' in evidence else 'sem a conta de contratação'}; "
        f"escala parcial com {violations} violações",
        passed,
    )


# Cenário 8: CSV com defeito -> RX-13 --------------------------------------------------------------------------------


def _s08_defective_csv(ctx: EvalContext) -> Outcome:
    stores, employees, _ = ctx.network
    planted = json.loads((ctx.data_dir / "defeitos_plantados.json").read_text(encoding="utf-8"))
    expected = sorted((d["line"], d["field"]) for d in planted)
    read = read_schedule_csv(
        "escala_defeito.csv",
        (ctx.data_dir / "escala_defeito.csv").read_bytes(),
        employees=employees, stores=stores, week_start=WEEK_START,
    )  # fmt: skip
    found = sorted((i.line, i.field) for i in read.summary.issues)
    code = read.exception.code if read.exception else None
    passed = code == "RX-13" and found == expected and not read.summary.ok
    return _outcome(
        f"RX-13 com as {len(expected)} linhas plantadas (linha, campo): {expected}",
        f"exceção {code}; {len(found)} problemas (linha, campo): {found}",
        passed,
    )


# Cenário 9: a escala otimizada da demo ----------------------------------------------------------------------------


def _s09_optimized_demo(ctx: EvalContext) -> Outcome:
    stores, employees, demand = ctx.network
    result = solve(
        SolveRequest(
            card=ctx.card, stores=stores, employees=employees, demand=demand, week_start=WEEK_START,
            seed=SOLVER_SEED, time_limit_s=SOLVER_TIME_LIMIT_S, num_workers=SOLVER_WORKERS,
        )
    )  # fmt: skip
    if result.schedule is None:
        return _outcome(
            "escala otimizada com 0 violações e cobertura 100%", f"solver sem escala ({result.status})", False
        )
    report = verify(result.schedule, ctx.card)
    gaps = coverage_gaps(result.schedule, demand)
    metrics = compute_metrics(result.schedule, employees, demand, ctx.card, violations=report.total)
    passed = (
        result.status in ("optimal", "feasible")
        and report.total == 0
        and not gaps
        and metrics.coverage_pct == 100.0
        and result.exception is None
    )
    return _outcome(
        "solver (seed 42, 1 thread): 0 violações pelo verificador independente, 0 faixas descobertas, cobertura 100%",
        f"status {result.status}; {report.total} violações; {len(gaps)} faixas descobertas; "
        f"cobertura {metrics.coverage_pct}%; custo {metrics.total_cost}; solver {result.wall_ms} ms",
        passed,
    )


# Cenário 10: turno que vira a noite e a interjornada ----------------------------------------------------------------


def _s10_overnight(ctx: EvalContext) -> Outcome:
    stores, employees, _ = ctx.network
    person = next(e for e in employees if e.id == "P001")

    def read(next_start: str, next_end: str) -> Schedule | None:
        rows = [
            "loja_id,pessoa_id,nome,data,inicio,fim",
            f"{person.store_id},{person.id},{person.name},2027-01-13,16:00,00:00",  # quarta 16h até quinta 0h
            f"{person.store_id},{person.id},{person.name},2027-01-14,{next_start},{next_end}",
        ]
        return read_schedule_csv(
            "noturno.csv", "\n".join(rows).encode(), employees=employees, stores=stores, week_start=WEEK_START
        ).schedule

    bad, control = read("08:00", "16:00"), read("12:00", "20:00")  # controle: 12h exatas (pol_interjornada)
    if bad is None or control is None:
        return _outcome("CSV do turno noturno legível", "leitura falhou", False)
    night = bad.shifts[0]
    ends_next_day = night.end == datetime(2027, 1, 14, 0, 0) and night.end - night.start == timedelta(hours=8)
    found = [v for v in verify(bad, ctx.card).violations if v.kind == REST_GAP]
    ok = [v for v in verify(control, ctx.card).violations if v.kind == REST_GAP]
    passed = ends_next_day and len(found) == 1 and found[0].employee_id == person.id and not ok
    return _outcome(
        "turno 16:00-00:00 termina na quinta (8h); recomeço às 08:00 = 8h de descanso -> 1 violação; "
        "às 12:00 = 12h (mínimo da política) -> 0",
        f"fim do turno {night.end:%d/%m %H:%M}; {len(found)} violação ({found[0].detail if found else '-'}); "
        f"controle às 12:00: {len(ok)}",
        passed,
    )


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("E1-01", "Primitiva: jornada semanal acima de 42h", _s01_weekly),
    Scenario("E1-02", "Primitiva: jornada diária acima de 8h", _s02_daily),
    Scenario("E1-03", "Primitiva: interjornada abaixo de 12h", _s03_rest_gap),
    Scenario("E1-04", "Primitiva: menos de 2 repousos na semana", _s04_weekly_rest),
    Scenario("E1-05", "Cobertura é métrica, não violação", _s05_coverage),
    Scenario("E1-06", "Escala enviada em 44h julgada sob 42h tem violações", _s06_current_schedule),
    Scenario("E1-07", "Demanda acima da capacidade vira RX-02 com a conta de contratação", _s07_rx02),
    Scenario("E1-08", "CSV com defeito vira RX-13 com as linhas plantadas", _s08_defective_csv),
    Scenario("E1-09", "Escala otimizada da demo: 0 violações e cobertura 100%", _s09_optimized_demo),
    Scenario("E1-10", "Turno que vira a noite e a interjornada", _s10_overnight),
)


# Runner e relatório -----------------------------------------------------------------------------------------------


def run_scenarios(
    scenarios: tuple[Scenario, ...] | list[Scenario], ctx: EvalContext | None = None
) -> list[ScenarioResult]:
    """Roda os cenários em ordem. Exceção dentro de um cenário é falha dele (com a causa), não aborta o resto."""
    ctx = ctx if ctx is not None else EvalContext()
    results = []
    for scenario in scenarios:
        t0 = wallclock.perf_counter()
        try:
            outcome = scenario.run(ctx)
        except Exception as exc:  # noqa: BLE001 - qualquer erro do cenário vira falha no placar
            outcome = Outcome(
                expected="cenário roda sem erro", obtained=f"erro: {type(exc).__name__}: {exc}", passed=False
            )
        elapsed_ms = int((wallclock.perf_counter() - t0) * 1000)
        results.append(
            ScenarioResult(
                scenario.id, scenario.description, outcome.expected, outcome.obtained, outcome.passed, elapsed_ms
            )
        )
    return results


def scoreboard(results: list[ScenarioResult]) -> str:
    return f"{sum(r.passed for r in results)}/{len(results)}"


def build_report(results: list[ScenarioResult], generated_at: datetime, suite: str = "e1") -> dict:
    return {
        "suite": suite,
        "gerado_em": generated_at.isoformat(timespec="seconds"),
        "modelo": "nenhum (suíte sem chamada de modelo)",
        "placar": scoreboard(results),
        "passaram": sum(r.passed for r in results),
        "total": len(results),
        "tempo_total_ms": sum(r.elapsed_ms for r in results),
        "cenarios": [r.as_json() for r in results],
    }


def write_report(report: dict, out_dir: Path, generated_at: datetime, suite: str = "e1") -> Path:
    """Grava `<suite>-<timestamp>.json` e `<suite>-latest.json` em `out_dir`; devolve o primeiro."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{suite}-{generated_at:%Y%m%dT%H%M%S}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(path, out_dir / f"{suite}-latest.json")
    return path


def render_table(results: list[ScenarioResult]) -> str:
    width = max((len(r.description) for r in results), default=10)
    lines = [f"{'cenário':<7}  {'resultado':<9}  {'tempo':>9}  {'descrição':<{width}}"]
    lines.append("-" * len(lines[0]))
    for r in results:
        lines.append(
            f"{r.id:<7}  {'passou' if r.passed else 'FALHOU':<9}  {r.elapsed_ms:>6} ms  {r.description:<{width}}"
        )
    failed = [r for r in results if not r.passed]
    for r in failed:
        lines += ["", f"FALHA {r.id}: {r.description}", f"  esperado: {r.expected}", f"  obtido:   {r.obtained}"]
    lines += ["", f"Placar: {scoreboard(results)}"]
    return "\n".join(line.rstrip() for line in lines)


@dataclass
class SuiteRun:
    results: list[ScenarioResult]
    report: dict
    path: Path
    table: str = field(init=False)

    def __post_init__(self) -> None:
        self.table = render_table(self.results)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


def run_suite(
    out_dir: Path,
    *,
    scenarios: tuple[Scenario, ...] | list[Scenario] | None = None,
    ctx: EvalContext | None = None,
    now: Callable[[], datetime] = datetime.now,
) -> SuiteRun:
    results = run_scenarios(SCENARIOS if scenarios is None else scenarios, ctx)
    generated_at = now()
    report = build_report(results, generated_at)
    return SuiteRun(results, report, write_report(report, out_dir, generated_at))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="escalista.evals", description="Evals do Escalista (sem modelo)")
    parser.add_argument("--suite", choices=["e1"], required=True)
    parser.add_argument("--out", type=Path, default=Path("var/evals"), help="diretório do relatório JSON")
    parser.add_argument("--data", type=Path, default=Path("data/demo"), help="dados sintéticos da demo")
    parser.add_argument("--rules", type=Path, default=Path("data/regras"), help="regras em YAML")
    args = parser.parse_args(argv)

    run = run_suite(args.out, ctx=EvalContext(data_dir=args.data, rules_dir=args.rules))
    print(run.table)
    print(f"Relatório: {run.path} (e {run.path.with_name('e1-latest.json')})")
    return 0 if run.all_passed else 1
