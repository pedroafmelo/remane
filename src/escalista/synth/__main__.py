"""Uso: uv run python -m escalista.synth --seed 42 --out data/demo
Arquivos de leitura do E2 e exemplo em grade: uv run python -m escalista.synth e2 --seed 42 --out data/demo
Arquivo adversário do E4-02: uv run python -m escalista.synth e4 --seed 42 --out data/demo
Cenário do acompanhamento (C7) e atestados: uv run python -m escalista.synth acompanhamento --seed 42 --out data/demo"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from escalista.synth.acompanhamento import gerar_acompanhamento
from escalista.synth.e2 import escrever_e2, gerar_e2
from escalista.synth.e4 import gerar_e4
from escalista.synth.saida import escrever, gerar

DESCRICAO = {
    "e2": "Gera os arquivos de leitura do E2 e o exemplo em grade.",
    "e4": "Gera o arquivo de escala com injeção do E4-02 e o gabarito.",
    "acompanhamento": "Gera o cenário sintético do acompanhamento de escala (C7), o ponto simulado e os atestados.",
}
GERADORES = {"e2": gerar_e2, "e4": gerar_e4, "acompanhamento": gerar_acompanhamento}
ROTULOS = {"e2": "do E2", "e4": "do E4", "acompanhamento": "do acompanhamento"}


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
        gerados = GERADORES[modo](args.seed)
        escrever_e2(gerados, args.out)  # grava bytes e cria as subpastas
        print(f"SINTETICO: {len(gerados)} arquivos {ROTULOS[modo]} gerados em {args.out} (seed {args.seed})")
        return 0
    arquivos = gerar(args.seed)
    escrever(arquivos, args.out)
    print(f"SINTETICO: {len(arquivos)} arquivos gerados em {args.out} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
