"""O retrato do relatório de evals (`data/evals/evals-latest.json`) como a área Impacto o lê (E6).

O arquivo é gerado por `uv run python -m escalista.evals --suite all --snapshot data/evals` e commitado, porque `var/`
não vai à imagem. O modelo é tolerante: campos novos passam (`extra="allow"`) e quase tudo é opcional, para que um
relatório mais novo ou mais pobre não derrube a tela. Sem arquivo, ou com arquivo ilegível, a resposta é
`{"status": "sem_relatorio"}`: nunca um erro.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

DEFAULT_SNAPSHOT_PATH = "data/evals/evals-latest.json"
SNAPSHOT_ENV = "EVALS_SNAPSHOT_PATH"


class _Open(BaseModel):
    model_config = ConfigDict(extra="allow")


class EvalsCounts(_Open):
    cenarios: int | None = None
    sem_modelo: int | None = None
    com_modelo: int | None = None
    executados: int | None = None
    passaram: int | None = None
    falharam: int | None = None
    nao_executados: int | None = None
    com_modelo_executados: int | None = None


class EvalsReport(_Open):
    status: Literal["ok"] = "ok"
    suite: str | None = None
    gerado_em: str | None = None
    git_sha: str | None = None
    modo: str | None = None
    dados: str | None = None
    comando: str | None = None
    privacidade: str | None = None
    contagem: EvalsCounts
    dec_019: dict[str, Any] | None = None
    rn04: dict[str, Any] | None = None
    modelo: dict[str, Any] | None = None
    suites: dict[str, dict[str, Any]] | None = None
    cenarios: list[dict[str, Any]] | None = None


class EvalsMissing(BaseModel):
    status: Literal["sem_relatorio"] = "sem_relatorio"


def snapshot_path() -> Path:
    return Path(os.environ.get(SNAPSHOT_ENV) or DEFAULT_SNAPSHOT_PATH)


def load_evals() -> EvalsReport | EvalsMissing:
    try:
        raw = json.loads(snapshot_path().read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return EvalsMissing()
        raw.pop("status", None)
        return EvalsReport.model_validate(raw)
    except (OSError, ValueError, ValidationError):
        return EvalsMissing()
