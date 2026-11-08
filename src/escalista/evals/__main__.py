"""Uso:
uv run python -m escalista.evals [--suite all|e3|e4] [--with-model] [--budget-usd 1.00] [--max-seconds N]
                                 [--out var/evals] [--data data/demo] [--rules data/regras] [--snapshot DIR]
uv run python -m escalista.evals --suite e1 [--out var/evals] [--data data/demo] [--rules data/regras]
uv run python -m escalista.evals --suite e2 [--with-model] [--out var/evals] [--data data/demo]

Sem `--suite` é `all`. `--suite e1` e `--suite e2` mantêm o relatório e os códigos 0/1 de antes; o all, o e3 e o e4
usam 0 (todos rodaram e passaram), 1 (algum falhou) e 3 (nenhum falhou, mas algum não executado).
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str]) -> int:
    pick = argparse.ArgumentParser(prog="escalista.evals", add_help=False)
    pick.add_argument("--suite", choices=["e1", "e2", "e3", "e4", "all"])
    chosen, rest = pick.parse_known_args(argv)
    if chosen.suite == "e2":
        from escalista.evals import e2

        return e2.run_cli(e2.build_parser().parse_args(rest))
    if chosen.suite == "e1":
        from escalista.evals import e1

        return e1.main(argv)
    from escalista.evals import suite_all

    return suite_all.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
