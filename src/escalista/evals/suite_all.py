"""Comando único dos evals (plano dos evals E3/E4, seção 4): `--suite all|e3|e4`, relatório all e códigos de saída.

    uv run python -m escalista.evals                                   # = --suite all, sem modelo
    uv run python -m escalista.evals --suite all --with-model --budget-usd 1.00 [--max-seconds 900]
    uv run python -m escalista.evals --suite all --snapshot data/evals # grava também o retrato do link público

Códigos: 0 = todos rodaram e passaram; 1 = algum falhou (ou turno inventado no E2); 3 = nenhum falhou, mas algum
`não executado`; 2 = erro de argumento (`argparse`). O E2 entra no all com uma linha por arquivo (sem modelo); com
`--with-model`, o E2 roda de novo com o modelo **só como medição** (`medicoes.e2_com_modelo`), sem contar cenários.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from escalista.evals import common, e1, e2, e3, e4
from escalista.evals.common import (
    FAILED,
    NOT_RUN,
    PASSED,
    BudgetedClient,
    EvalContext,
    MemorySink,
    ScenarioResult,
)

SUITES = ("e1", "e2", "e3", "e4")
DEC_019_META = {"sem_modelo": 20, "com_modelo": 10}
NOT_MEASURED = "não medido"
MEASURED = "medido"
EXIT_OK, EXIT_FAILED, EXIT_NOT_RUN = 0, 1, 3

ClientFactory = Callable[[Any], Any]  # recebe o `TraceSink` em memória, devolve um `LLMClient`


def before_snapshot(report: dict[str, Any]) -> None:
    """Gancho chamado antes de gravar o retrato público. A checagem de vazamento (`find_leaks`) é da tarefa E6."""


def git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


# E2 no all: uma linha por arquivo ---------------------------------------------------------------------------------


def e2_rows(results: Sequence[e2.FileResult]) -> list[ScenarioResult]:
    rows = []
    for r in results:
        obtained = (
            f"{r.correct}/{r.expected} turnos corretos, {r.invented} inventados, {r.lost} perdidos"
            if r.expect != "RX-13"
            else f"RX-13 {'certo' if r.rx13_ok else 'errado'}, {r.invented} inventados"
        )
        if r.failures:
            obtained += "; " + "; ".join(r.failures)
        rows.append(
            ScenarioResult(
                r.id,
                f"Leitura de {Path(r.file).name}",
                "turnos do gabarito, 0 inventados" if r.expect != "RX-13" else "RX-13, 0 turnos",
                obtained,
                PASSED if r.passed else FAILED,
                r.elapsed_ms,
                suite="e2",
            )
        )
    return rows


# Métricas do RN-04 ------------------------------------------------------------------------------------------------


def _sum_metric(results: Sequence[ScenarioResult], key: str, fields: Sequence[str]) -> tuple[dict[str, Any], list]:
    found = [(r, r.metrics[key]) for r in results if r.metrics and key in r.metrics and r.status != NOT_RUN]
    totals: dict[str, Any] = {f: (sum(m.get(f, 0) for _, m in found) if found else None) for f in fields}
    return totals, [r.id for r, _ in found]


def rn04_metrics(results: Sequence[ScenarioResult]) -> dict[str, Any]:
    """As quatro métricas do RN-04 (plano, seção 5), somadas das `metrics` que os cenários devolvem
    (`rn04.violacoes`, `rn04.cobertura`, `rn04.custo`, `rn04.atestado`). Sem fonte: `status = "não medido"`."""
    viol, viol_src = _sum_metric(results, "rn04.violacoes", ("plantadas", "detectadas", "falsos_positivos"))
    if viol_src:
        viol["nao_detectadas"] = viol["plantadas"] - viol["detectadas"]
    else:
        viol["nao_detectadas"] = None
    cov = [r.metrics["rn04.cobertura"] for r in results if r.metrics and "rn04.cobertura" in r.metrics]
    cost = [r.metrics["rn04.custo"] for r in results if r.metrics and "rn04.custo" in r.metrics]
    reading, reading_src = _sum_metric(
        [r for r in results if r.model_executed], "rn04.atestado", ("campos_certos", "campos")
    )
    return {
        "violacoes_nao_detectadas": {
            **viol,
            "fontes": viol_src,
            "status": MEASURED if viol_src else NOT_MEASURED,
        },
        "cobertura": {
            "escala_demo_pct": next((c.get("escala_demo_pct") for c in cov if "escala_demo_pct" in c), None),
            "casos_cobertos": next((c.get("casos_cobertos") for c in cov if "casos_cobertos" in c), None),
            "status": MEASURED if cov else NOT_MEASURED,
        },
        "custo_contra_planilha": {
            "antes_brl": cost[0].get("antes_brl") if cost else None,
            "depois_brl": cost[0].get("depois_brl") if cost else None,
            "fonte": "compute_metrics, dados sintéticos",
            "status": MEASURED if cost else NOT_MEASURED,
        },
        "acerto_atestado": {
            **reading,
            "n_atestados": len(reading_src),
            "status": MEASURED if reading_src else NOT_MEASURED,
        },
    }


# Relatório --------------------------------------------------------------------------------------------------------


def model_block(sink: MemorySink, ceiling: Decimal) -> dict[str, Any]:
    """Custo e latência medidos de todas as chamadas da rodada (eventos do cliente no sink compartilhado)."""
    events = sink.events
    costs = [e.cost_usd for e in events]
    latencies = [e.latency_ms for e in events if e.latency_ms is not None]
    cost = None if not costs or any(c is None for c in costs) else sum((c for c in costs if c is not None), Decimal(0))
    return {
        "chamadas": len(events),
        "cost_usd": None if cost is None else format(cost, "f"),
        "latencia_ms_p50": statistics.median(latencies) if latencies else None,
        "latencia_ms_max": max(latencies) if latencies else None,
        "teto_usd": format(ceiling, "f"),
    }


def _board(rows: Sequence[ScenarioResult]) -> dict[str, Any]:
    ran = [r for r in rows if r.status != NOT_RUN]
    return {
        "cenarios": len(rows),
        "passaram": sum(r.status == PASSED for r in rows),
        "falharam": sum(r.status == FAILED for r in rows),
        "nao_executados": len(rows) - len(ran),
        "placar": f"{sum(r.status == PASSED for r in rows)}/{len(rows)}",
    }


def count(results: Sequence[ScenarioResult]) -> dict[str, int]:
    return {
        "cenarios": len(results),
        "sem_modelo": sum(not r.uses_model for r in results),
        "com_modelo": sum(r.uses_model for r in results),
        "executados": sum(r.status != NOT_RUN for r in results),
        "passaram": sum(r.status == PASSED for r in results),
        "falharam": sum(r.status == FAILED for r in results),
        "nao_executados": sum(r.status == NOT_RUN for r in results),
        "com_modelo_executados": sum(r.uses_model and r.model_executed for r in results),
    }


def build_report(
    results: Sequence[ScenarioResult],
    generated_at: datetime,
    *,
    suite: str,
    with_model: bool,
    model: dict[str, Any],
    e2_report: dict[str, Any] | None = None,
    measurements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    no_model = [r for r in results if not r.uses_model]
    with_m = [r for r in results if r.uses_model]
    suites: dict[str, Any] = {}
    for name in SUITES:
        rows = [r for r in results if r.suite == name]
        if rows or suite == "all":
            suites[name] = _board(rows)
    if e2_report is not None and "e2" in suites:
        suites["e2"]["totais"] = e2_report["totais"]
    report: dict[str, Any] = {
        "suite": suite,
        "gerado_em": generated_at.isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "modo": "com_modelo" if with_model else "sem_modelo",
        "dados": "sintéticos",
        "contagem": count(results),
        "dec_019": {
            "sem_modelo": {
                "meta": DEC_019_META["sem_modelo"],
                "existem": len(no_model),
                "passaram": sum(r.status == PASSED for r in no_model),
            },
            "com_modelo": {
                "meta": DEC_019_META["com_modelo"],
                "existem": len(with_m),
                "executados": sum(r.model_executed for r in with_m),
                "passaram": sum(r.status == PASSED for r in with_m),
            },
        },
        "rn04": rn04_metrics(results),
        "modelo": model,
        "suites": suites,
        "cenarios": [r.as_json() for r in results],
    }
    if measurements:
        report["medicoes"] = measurements
    return report


def _fmt(value: Any) -> str:
    return NOT_MEASURED if value is None else str(value)


def _ms(value: Any) -> str:
    return NOT_MEASURED if value is None else f"{value} ms"


def _reading(at: dict[str, Any]) -> str:
    if not at["n_atestados"]:
        return NOT_MEASURED
    return f"{at['campos_certos']}/{at['campos']} campos (n={at['n_atestados']})"


def footer(report: dict[str, Any]) -> str:
    c = report["contagem"]
    rn = report["rn04"]
    v, cov, cost, at = (
        rn["violacoes_nao_detectadas"],
        rn["cobertura"],
        rn["custo_contra_planilha"],
        rn["acerto_atestado"],
    )
    m = report["modelo"]
    lines = [
        f"{c['cenarios']} cenários ({c['sem_modelo']} sem modelo, {c['com_modelo']} com modelo); executados "
        f"{c['executados']} (com modelo: {c['com_modelo_executados']}); passaram {c['passaram']}; falharam "
        f"{c['falharam']}; não executados {c['nao_executados']}",
        "RN-04 (dados sintéticos):",
        f"  violações não detectadas: {_fmt(v['nao_detectadas'])}"
        + (f" (de {v['plantadas']} plantadas; falsos positivos {v['falsos_positivos']})" if v["fontes"] else ""),
        f"  cobertura: escala da demo {_fmt(cov['escala_demo_pct'])}; casos {_fmt(cov['casos_cobertos'])}",
        f"  custo contra a planilha: antes {_fmt(cost['antes_brl'])}, depois {_fmt(cost['depois_brl'])}",
        "  acerto na leitura do atestado: "
        + (
            f"{at['campos_certos']}/{at['campos']} campos (n={at['n_atestados']})"
            if at["n_atestados"]
            else NOT_MEASURED
        ),
        f"Modelo: {m['chamadas']} chamada(s); custo {('US$ ' + m['cost_usd']) if m['cost_usd'] else NOT_MEASURED}; "
        f"latência p50 {_ms(m['latencia_ms_p50'])}, máx {_ms(m['latencia_ms_max'])}; teto US$ {m['teto_usd']}",
    ]
    return "\n".join(lines)


def exit_code(results: Sequence[ScenarioResult]) -> int:
    if any(r.status == FAILED for r in results):
        return EXIT_FAILED
    if any(r.status == NOT_RUN for r in results):
        return EXIT_NOT_RUN
    return EXIT_OK


# Comando ----------------------------------------------------------------------------------------------------------


def build_parser(prog: str = "escalista.evals") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="Evals do Escalista (comando único)")
    parser.add_argument("--suite", choices=["e1", "e2", "e3", "e4", "all"], default="all")
    parser.add_argument("--with-model", action="store_true", help="roda os cenários com modelo (chave; custo medido)")
    parser.add_argument("--budget-usd", type=Decimal, default=Decimal("1.00"), help="teto da rodada com modelo")
    parser.add_argument("--max-seconds", type=float, default=None, help="teto de tempo da rodada com modelo")
    parser.add_argument("--out", type=Path, default=Path("var/evals"), help="diretório do relatório JSON")
    parser.add_argument("--data", type=Path, default=Path("data/demo"), help="dados sintéticos da demo")
    parser.add_argument("--rules", type=Path, default=Path("data/regras"), help="regras em YAML")
    parser.add_argument("--snapshot", type=Path, default=None, help="grava DIR/evals-latest.json (só com all)")
    return parser


def _client(args: argparse.Namespace, sink: MemorySink, client_factory: ClientFactory | None) -> BudgetedClient | None:
    """Cliente com teto, ou `None` (sem `--with-model`, ou sem chave: os com modelo saem `não executado`)."""
    if not args.with_model:
        return None
    factory = client_factory
    if factory is None:
        try:
            factory = e2._real_client_factory()
        except SystemExit:
            return None
    return BudgetedClient(factory(sink), sink, args.budget_usd, max_seconds=args.max_seconds)


def main(
    argv: list[str], *, client_factory: ClientFactory | None = None, now: Callable[[], datetime] = datetime.now
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.snapshot is not None and args.suite != "all":
        parser.error("--snapshot só com --suite all")
    sink = MemorySink()
    llm = _client(args, sink, client_factory)
    ctx = EvalContext(data_dir=args.data, rules_dir=args.rules, with_model=args.with_model, llm=llm, sink=sink)

    picked = SUITES if args.suite == "all" else (args.suite,)
    results: list[ScenarioResult] = []
    e2_report: dict[str, Any] | None = None
    measurements: dict[str, Any] = {}
    for name in picked:
        if name == "e2":
            files = e2.run_files(args.data)
            e2_report = e2.build_report(files, now(), with_model=False)
            results += e2_rows(files)
            if llm is not None:
                with_model = e2.run_files(args.data, client_factory=lambda _sink: llm, sink=sink)
                rep = e2.build_report(with_model, now(), with_model=True)
                measurements["e2_com_modelo"] = {
                    "placar": rep["placar"],
                    "totais": rep["totais"],
                    "modelo": rep.get("modelo"),
                }
            continue
        module = {"e1": e1, "e3": e3, "e4": e4}[name]
        results += common.run_scenarios(module.SCENARIOS, ctx)

    generated_at = now()
    report = build_report(
        results,
        generated_at,
        suite=args.suite,
        with_model=args.with_model,
        model=model_block(sink, args.budget_usd),
        e2_report=e2_report,
        measurements=measurements,
    )
    path = common.write_report(report, args.out, generated_at, suite=args.suite)
    print(common.render(results))
    print()
    print(footer(report))
    print(f"Relatório: {path} (e {path.with_name(f'{args.suite}-latest.json')})")
    if args.snapshot is not None:
        before_snapshot(report)
        args.snapshot.mkdir(parents=True, exist_ok=True)
        (args.snapshot / "evals-latest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return exit_code(results)
