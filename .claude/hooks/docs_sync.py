#!/usr/bin/env python3
"""Hooks de documentação viva do projeto.

Uso (configurado em .claude/settings.json):
  docs_sync.py session-start   imprime contagem regressiva dos marcos e avisos de documentação defasada
  docs_sync.py stop            bloqueia UMA vez o fim do turno se o código mudou e a documentação não

Regras de defasagem (comparação por data de modificação):
  1. Algo em src/, tests/ ou pyproject.toml é mais novo que docs/estado-do-projeto.md
     -> registrar a mudança no estado do projeto.
  2. pyproject.toml é mais novo que docs/declaracao-ferramentas.md
     -> declarar dependências, modelos e APIs novos (a submissão exige essa lista).

Para silenciar um aviso, atualize o arquivo de documentação correspondente (ele passa a ser o mais novo).
Só usa a biblioteca padrão. Nunca falha o fluxo do agente: qualquer erro inesperado vira saída vazia.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
BRT = timezone(timedelta(hours=-3))  # Recife

MARCOS = [
    ("Início do hacking", datetime(2026, 11, 7, 10, 30, tzinfo=BRT)),
    ("Encerramento do dia 1", datetime(2026, 11, 7, 17, 0, tzinfo=BRT)),
    ("PRAZO DE SUBMISSÃO", datetime(2026, 11, 8, 13, 0, tzinfo=BRT)),
    ("Demo Day (pitch de 3 min)", datetime(2026, 11, 8, 16, 0, tzinfo=BRT)),
    ("Premiação", datetime(2026, 11, 8, 17, 30, tzinfo=BRT)),
]

ESTADO = ROOT / "docs" / "estado-do-projeto.md"
FERRAMENTAS = ROOT / "docs" / "declaracao-ferramentas.md"
CODE_PATHS = [ROOT / "src", ROOT / "tests", ROOT / "pyproject.toml"]
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", ".DS_Store"}


def _mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def _newest_code_change() -> tuple[float, str]:
    newest, name = 0.0, ""
    for base in CODE_PATHS:
        files = [base] if base.is_file() else base.rglob("*") if base.is_dir() else []
        for f in files:
            if not f.is_file() or IGNORED_PARTS & set(f.parts) or f.suffix == ".pyc":
                continue
            t = f.stat().st_mtime
            if t > newest:
                newest, name = t, str(f.relative_to(ROOT))
    return newest, name


def drift() -> list[str]:
    """Lista de avisos de documentação defasada (vazia se tudo em dia)."""
    avisos: list[str] = []
    code_t, code_name = _newest_code_change()
    if code_t and code_t > _mtime(ESTADO):
        avisos.append(
            f"O código mudou ({code_name}) depois da última atualização de docs/estado-do-projeto.md. "
            "Registre a mudança no estado do projeto (seção 'Registro de atualizações' e o que mais tiver mudado)."
        )
    pyproject_t = _mtime(ROOT / "pyproject.toml")
    if pyproject_t and pyproject_t > _mtime(FERRAMENTAS):
        avisos.append(
            "pyproject.toml mudou depois de docs/declaracao-ferramentas.md. Declare dependências, modelos, APIs e "
            "serviços de terceiros novos (a submissão exige a lista completa)."
        )
    return avisos


def session_start() -> None:
    agora = datetime.now(BRT)
    linhas = [f"[docs vivas] Agora: {agora:%d/%m/%Y %H:%M} (Recife)."]
    futuros = [(n, t) for n, t in MARCOS if t > agora]
    for nome, t in futuros[:3]:
        falta = t - agora
        horas, resto = divmod(int(falta.total_seconds()), 3600)
        linhas.append(f"  - {nome}: {t:%d/%m %H:%M} (faltam {horas}h{resto // 60:02d})")
    if not futuros:
        linhas.append("  - Todos os marcos do evento já passaram.")
    linhas.append("Leia CLAUDE.md e docs/estado-do-projeto.md antes de agir. Mantenha as docs em dia (ver 'Documentação viva').")
    for aviso in drift():
        linhas.append(f"ATENÇÃO: {aviso}")
    print("\n".join(linhas))


def stop() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    if payload.get("stop_hook_active"):  # já bloqueou uma vez neste ciclo: não entrar em loop
        return
    avisos = drift()
    if avisos:
        print(json.dumps({"decision": "block", "reason": "Documentação viva defasada. " + " ".join(avisos)}))


def main() -> None:
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if comando == "session-start":
            session_start()
        elif comando == "stop":
            stop()
    except Exception:  # noqa: BLE001 - hook nunca deve quebrar a sessão
        pass


if __name__ == "__main__":
    main()
