"""Campos protegidos do acompanhamento, num lugar só (RN-06, SAIDA-AC-13 v1.1).

CID, diagnóstico, texto livre do colaborador, imagem e anexo nunca vão ao rastro, a tabela, a log nem ao modelo (no
caminho PDF). Este módulo é a única fonte da lista e das três operações sobre ela:

- `strip_cid(text)`: corta o CID do texto do atestado **antes** de ir ao modelo.
- `scrub(payload, kind=...)`: aplicado pelo `SqlTraceSink` antes de gravar. Por **nome de campo** em todo evento; pelo
  **padrão de CID** só em `track.*` e `channel_message`, porque o padrão também casa referência de célula de planilha
  (`B12`) que a evidência da leitura do E2 cita (achado da sessão B no contrato com os evals).
- `find_leaks(...)`: usado pelos testes de vazamento e pelos evals; diz **onde** vazou, nunca o valor.

Só biblioteca padrão: os evals e o teste de privacidade importam sem puxar o resto do sistema.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

REDACTED = "[REDACTED]"  # o mesmo texto de `audit.mask.REDACTED`
CID_REMOVED = "[CID removido]"

PROTECTED_KEYS: frozenset[str] = frozenset(
    {
        "cid",
        "cid10",
        "diagnostico",
        "diagnóstico",
        "text",
        "texto",
        "texto_livre",
        "raw_text",
        "image",
        "imagem",
        "attachment",
        "anexo",
        "medico",
        "médico",
    }
)

# CID-10: letra (sem U, reservada), dois dígitos e subcategoria opcional. Casa também `B12` de planilha: ver `scrub`.
CID_PATTERN: re.Pattern[str] = re.compile(r"\b[A-TV-Z][0-9]{2}(?:\.[0-9])?\b")

# Rótulo (`CID:`, `CID-10:`, `CID 10`, `cid10 =`) e o valor que vem depois dele, na mesma linha, em qualquer caixa.
# `(?![A-Za-z0-9])` evita casar `Cidade`; o valor começa por letra para `CID 10` não virar rótulo `CID` + valor `10`.
_CID_LABEL = re.compile(
    r"(?i)(?<![A-Za-z0-9])(cid(?:[ \t]*-?[ \t]*10)?(?![A-Za-z0-9])[ \t]*[:=\-]?[ \t]*)[^\W\d_]\w*(?:\.\w+)*"
)

# Prefixos de `kind` (e superfícies) em que o padrão de CID vale: o acompanhamento e as mensagens do canal.
_PATTERN_KINDS = ("track.",)
_PATTERN_SURFACES = frozenset({"channel_message"})


def strip_cid(text: str) -> str:
    """Troca por `[CID removido]` o valor depois de um rótulo de CID e todo código no formato CID-10."""
    text = _CID_LABEL.sub(lambda m: m.group(1) + CID_REMOVED, text)
    return CID_PATTERN.sub(CID_REMOVED, text)


def _applies_pattern(kind: str) -> bool:
    return kind.startswith(_PATTERN_KINDS) or kind in _PATTERN_SURFACES


def _is_protected(name: str) -> bool:
    return name.lower() in PROTECTED_KEYS


def _scrub(value: Any, pattern: bool) -> Any:
    if isinstance(value, str):
        return strip_cid(value) if pattern else value
    if isinstance(value, Mapping):
        out: dict[Any, Any] = {}
        for key, item in value.items():
            name = strip_cid(key) if pattern and isinstance(key, str) else key
            out[name] = REDACTED if isinstance(key, str) and _is_protected(key) else _scrub(item, pattern)
        return out
    if isinstance(value, list | tuple):
        return [_scrub(item, pattern) for item in value]
    return value


def scrub(payload: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    """Cópia de `payload` sem campos protegidos e, em `track.*` e `channel_message`, sem CID em texto algum.

    O valor de uma chave de `PROTECTED_KEYS` (nome sem distinção de caixa, em qualquer nível) vira `[REDACTED]` em todo
    `kind`. Fora do acompanhamento, nada mais muda: `célula B12` na evidência do `llm.map_columns` fica intacta.
    """
    out = _scrub(payload, _applies_pattern(kind))
    assert isinstance(out, dict)
    return out


@dataclass(frozen=True)
class Leak:
    """Onde vazou (`surface`) e como foi achado. Nunca carrega o valor vazado."""

    surface: str
    kind: Literal["planted", "pattern"]


def _in_pattern_surfaces(surface: str, pattern_surfaces: set[str]) -> bool:
    return any(surface.startswith(name[:-1]) if name.endswith("*") else surface == name for name in pattern_surfaces)


def find_leaks(blobs: dict[str, str], planted: list[str], *, pattern_surfaces: set[str]) -> list[Leak]:
    """Superfícies (nome -> texto) que contêm um valor plantado (sem caixa) ou, nas de `pattern_surfaces`, um CID.

    `pattern_surfaces` aceita nome exato ou prefixo terminado em `*` (`"track.*"`). Lista vazia: nada vazou.
    """
    needles = [p.lower() for p in planted if p]
    leaks: list[Leak] = []
    for surface, blob in blobs.items():
        lowered = blob.lower()
        if any(needle in lowered for needle in needles):
            leaks.append(Leak(surface, "planted"))
        if _in_pattern_surfaces(surface, pattern_surfaces) and CID_PATTERN.search(blob):
            leaks.append(Leak(surface, "pattern"))
    return leaks
