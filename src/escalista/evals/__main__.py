"""Uso: uv run python -m escalista.evals --suite e1 [--out var/evals] [--data data/demo] [--rules data/regras]"""

from __future__ import annotations

import sys

from escalista.evals.e1 import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
