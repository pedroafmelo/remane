"""Uso: uv run python -m escalista.synth --seed 42 --out data/demo
Arquivos de leitura do E2 e exemplo em grade: uv run python -m escalista.synth e2 --seed 42 --out data/demo
Cenário do acompanhamento (C7) e atestados: uv run python -m escalista.synth acompanhamento --seed 42 --out data/demo"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from escalista.synth.acompanhamento import gerar_acompanhamento
from escalista.synth.e2 import escrever_e2, gerar_e2
from escalista.synth.saida import escrever, gerar

DESCRICAO = {
    "e2": "Gera os arquivos de leitura do E2 e o exemplo em grade.",
    "acompanhamento": "Gera o cenário sintético do acompanhamento de escala (C7), o ponto simulado e os atestados.",
}


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    modo = argumentos[0] if argumentos and argumentos[0] in DESCRICAO else None
    if modo:
        argumentos = argumentos[1:]
    parser = argparse.ArgumentParser(
        prog="python -m escalista.synth" + (f" {modo}" if modo else ""),
        description=DESCRICAO.get(modo or "", "Gera os dados sintéticos da demo."),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True, help="pasta de saída, por exemplo data/demo")
    args = parser.parse_args(argumentos)
    if modo:
        gerados = gerar_e2(args.seed) if modo == "e2" else gerar_acompanhamento(args.seed)
        escrever_e2(gerados, args.out)  # grava bytes e cria as subpastas
        rotulo = "do E2" if modo == "e2" else "do acompanhamento"
        print(f"SINTETICO: {len(gerados)} arquivos {rotulo} gerados em {args.out} (seed {args.seed})")
        return 0
    arquivos = gerar(args.seed)
    escrever(arquivos, args.out)
    print(f"SINTETICO: {len(arquivos)} arquivos gerados em {args.out} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
