"""Uso:
uv run python -m escalista.evals --suite e1 [--out var/evals] [--data data/demo] [--rules data/regras]
uv run python -m escalista.evals --suite e2 [--with-model] [--out var/evals] [--data data/demo]
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str]) -> int:
    pick = argparse.ArgumentParser(prog="escalista.evals", add_help=False)
    pick.add_argument("--suite", choices=["e1", "e2"])
    chosen, rest = pick.parse_known_args(argv)
    if chosen.suite == "e2":
        from escalista.evals import e2

        return e2.run_cli(e2.build_parser().parse_args(rest))
    from escalista.evals import e1

    return e1.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
