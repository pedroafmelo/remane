"""Uso: uv run python -m escalista.synth --seed 42 --out data/demo
Arquivos de leitura do E2 e exemplo em grade: uv run python -m escalista.synth e2 --seed 42 --out data/demo"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from escalista.synth.e2 import escrever_e2, gerar_e2
from escalista.synth.saida import escrever, gerar


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    e2 = bool(argumentos) and argumentos[0] == "e2"
    if e2:
        argumentos = argumentos[1:]
    parser = argparse.ArgumentParser(
        prog="python -m escalista.synth" + (" e2" if e2 else ""),
        description="Gera os arquivos de leitura do E2 e o exemplo em grade."
        if e2
        else "Gera os dados sintéticos da demo.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True, help="pasta de saída, por exemplo data/demo")
    args = parser.parse_args(argumentos)
    if e2:
        arquivos_e2 = gerar_e2(args.seed)
        escrever_e2(arquivos_e2, args.out)
        print(f"SINTETICO: {len(arquivos_e2)} arquivos do E2 gerados em {args.out} (seed {args.seed})")
        return 0
    arquivos = gerar(args.seed)
    escrever(arquivos, args.out)
    print(f"SINTETICO: {len(arquivos)} arquivos gerados em {args.out} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
