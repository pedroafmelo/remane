"""Benchmark do solver na instância 60 × 7 de `data/demo/` (plano da C5, A2; G3).

    uv run python -m escalista.solver.bench --seed 42 [--threads 1 8] [--time-limit 30] [--data data/demo]

Roda o mesmo `solve` com 1 thread e com várias, imprime e grava em `var/bench/solver_seed<seed>.json` o tempo de
parede, o status, o custo (pela mesma `compute_metrics` de `cost.py`), as faixas descobertas e o tamanho do modelo.

O `solver` é núcleo e não importa `escalista.rules`: o cartão daqui é montado à mão por `bench_rule_card`, com os
valores das 5 primitivas da fatia, e `tests/solver/test_bench.py` confere que ele bate com o cartão carregado de
`data/regras/` na mesma data.
"""

from __future__ import annotations

import argparse
import json
import platform
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter

from escalista.domain.results import SolveRequest
from escalista.domain.rules import Rule, RuleCard, RuleLayer, RuleStatus
from escalista.domain.schedule import DemandSlot, Employee, Store
from escalista.solver.cost import compute_metrics
from escalista.solver.model import ModelStats, solve

WEEK_START = date(2027, 1, 11)
PRIMITIVE_KINDS = (
    "jornada_semanal_max",
    "jornada_diaria_max",
    "interjornada_min",
    "repouso_semanal",
    "adicional_hora_extra",
)


def bench_rule_card(reference_date: date = WEEK_START) -> RuleCard:
    """Cartão explícito com as 5 primitivas (EC 141, convenção e política fictícias), sem ler `data/regras/`."""

    def lei(kind: str, **params: float) -> Rule:
        return Rule(
            id=kind,
            kind=kind,
            layer=RuleLayer.LEI,
            params=params,
            status=RuleStatus.INTERPRETACAO,
            source="benchmark: valor da EC 141 copiado de data/regras/lei (conferido em tests/solver/test_bench.py)",
        )

    return RuleCard(
        reference_date=reference_date,
        rules=[
            lei("jornada_semanal_max", hours=42),
            lei("jornada_diaria_max", hours=8),
            lei("repouso_semanal", days=2),
            Rule(
                id="pol_interjornada",
                kind="interjornada_min",
                layer=RuleLayer.POLITICA,
                params={"hours": 12},
                status=RuleStatus.INTERPRETACAO,
                source="benchmark: política fictícia de data/regras/politica (a CLT pede 11h)",
            ),
            Rule(
                id="cct_adicional_hora_extra",
                kind="adicional_hora_extra",
                layer=RuleLayer.CONVENCAO,
                params={"percent": 60},
                status=RuleStatus.INTERPRETACAO,
                source="benchmark: convenção fictícia de data/regras/convencao",
            ),
        ],
    )


def load_demo(data_dir: Path) -> tuple[list[Store], list[Employee], list[DemandSlot]]:
    stores = TypeAdapter(list[Store]).validate_json((data_dir / "lojas.json").read_bytes())
    employees = TypeAdapter(list[Employee]).validate_json((data_dir / "pessoas.json").read_bytes())
    demand = TypeAdapter(list[DemandSlot]).validate_json((data_dir / "demanda.json").read_bytes())
    return stores, employees, demand


def run_once(
    stores: list[Store],
    employees: list[Employee],
    demand: list[DemandSlot],
    *,
    seed: int,
    threads: int,
    time_limit_s: float,
) -> dict:
    card = bench_rule_card()
    req = SolveRequest(
        card=card,
        stores=stores,
        employees=employees,
        demand=demand,
        week_start=WEEK_START,
        seed=seed,
        time_limit_s=time_limit_s,
        num_workers=threads,
    )
    stats = ModelStats()
    result = solve(req, stats)
    row: dict = {
        "threads": threads,
        "time_limit_s": time_limit_s,
        "wall_ms": result.wall_ms,
        "status": result.status,
        "store_status": stats.store_status,
        "uncovered_slots": len(result.uncovered),
        "uncovered_person_hours": sum(u.required for u in result.uncovered) / 2,
        "num_vars": stats.num_vars,
        "num_constraints": stats.num_constraints,
        "catalog_size": stats.catalog_size,
        "solver_wall_s": stats.solver_wall_s,
        "input_hash": result.input_hash,
        "rx02": result.exception.code if result.exception else None,
    }
    if result.schedule is not None:
        m = compute_metrics(result.schedule, employees, demand, card, violations=0)
        row |= {
            "shifts": len(result.schedule.shifts),
            "total_cost": str(m.total_cost),
            "regular_hours": str(m.regular_hours),
            "overtime_hours": str(m.overtime_hours),
            "coverage_pct": m.coverage_pct,
        }
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark do solver CP-SAT na instância 60 × 7 de data/demo.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, nargs="+", default=[1, 8])
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--data", type=Path, default=Path("data/demo"))
    parser.add_argument("--out", type=Path, default=Path("var/bench"))
    args = parser.parse_args(argv)

    stores, employees, demand = load_demo(args.data)
    runs = []
    for threads in args.threads:
        row = run_once(stores, employees, demand, seed=args.seed, threads=threads, time_limit_s=args.time_limit)
        runs.append(row)
        print(
            f"threads={threads:<2} status={row['status']:<8} wall={row['wall_ms'] / 1000:.2f}s "
            f"custo=R$ {row.get('total_cost', '-')} cobertura={row.get('coverage_pct', '-')}% "
            f"faixas_descobertas={row['uncovered_slots']} ({row['uncovered_person_hours']} pessoa-horas) "
            f"vars={row['num_vars']} restricoes={row['num_constraints']} lojas={row['store_status']}"
        )

    report = {
        "seed": args.seed,
        "week_start": WEEK_START.isoformat(),
        "instance": {"stores": len(stores), "employees": len(employees), "demand_slots": len(demand)},
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "runs": runs,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"solver_seed{args.seed}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"gravado em {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
