"""Uso: uv run python -m escalista.synth --seed 42 --out data/demo
Arquivos de leitura do E2 e exemplo em grade: uv run python -m escalista.synth e2 --seed 42 --out data/demo
Arquivo adversário do E4-02: uv run python -m escalista.synth e4 --seed 42 --out data/demo"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from escalista.synth.e2 import escrever_e2, gerar_e2
from escalista.synth.e4 import escrever_e4, gerar_e4
from escalista.synth.saida import escrever, gerar


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    sub = argumentos[0] if argumentos and argumentos[0] in ("e2", "e4") else None
    e2 = sub == "e2"
    if sub:
        argumentos = argumentos[1:]
    descricoes = {
        "e2": "Gera os arquivos de leitura do E2 e o exemplo em grade.",
        "e4": "Gera o arquivo de escala com injeção do E4-02 e o gabarito.",
        None: "Gera os dados sintéticos da demo.",
    }
    parser = argparse.ArgumentParser(
        prog="python -m escalista.synth" + (f" {sub}" if sub else ""), description=descricoes[sub]
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True, help="pasta de saída, por exemplo data/demo")
    args = parser.parse_args(argumentos)
    if e2:
        arquivos_e2 = gerar_e2(args.seed)
        escrever_e2(arquivos_e2, args.out)
        print(f"SINTETICO: {len(arquivos_e2)} arquivos do E2 gerados em {args.out} (seed {args.seed})")
        return 0
    if sub == "e4":
        arquivos_e4 = gerar_e4(args.seed)
        escrever_e4(arquivos_e4, args.out)
        print(f"SINTETICO: {len(arquivos_e4)} arquivos do E4 gerados em {args.out} (seed {args.seed})")
        return 0
    arquivos = gerar(args.seed)
    escrever(arquivos, args.out)
    print(f"SINTETICO: {len(arquivos)} arquivos gerados em {args.out} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
