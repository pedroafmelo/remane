"""Uso: uv run python -m escalista.synth --seed 42 --out data/demo"""

from __future__ import annotations

import argparse
from pathlib import Path

from escalista.synth.saida import escrever, gerar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m escalista.synth", description="Gera os dados sintéticos da demo.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True, help="pasta de saída, por exemplo data/demo")
    args = parser.parse_args(argv)
    arquivos = gerar(args.seed)
    escrever(arquivos, args.out)
    print(f"SINTETICO: {len(arquivos)} arquivos gerados em {args.out} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
