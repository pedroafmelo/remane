"""Máscara do `payload` do rastro (RN-06, RN-08): o valor de uma chave nunca vai a banco, log ou trace.

Três camadas, todas aplicadas antes de gravar:
1. **Nome do campo:** um campo com nome sensível (`api_key`, `authorization`, `secret`, `password`, `token`, ...) tem o
   valor inteiro trocado por `REDACTED`, seja texto, número, lista ou dicionário.
2. **Padrão do valor:** em qualquer texto (inclusive nomes de campo e mensagens de erro), formatos de chave conhecidos
   (`rc_...`, `sk-...`, `Bearer ...`, JWT, `api_key=...`, senha em URL) viram `REDACTED`.
3. **Valores literais:** quem conhece as chaves configuradas (`known_secrets`) remove o valor exato, qualquer que seja o
   formato.

A saída é sempre serializável em JSON (Decimal e datetime viram texto) e a entrada nunca é alterada. A máscara erra
para o lado de esconder: um campo inofensivo com nome parecido (por exemplo `token_count`) também é mascarado.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, SecretBytes, SecretStr

REDACTED = "[REDACTED]"
MAX_DEPTH = 32
MIN_KNOWN_SECRET_LEN = 4

# Palavras (depois de separar snake_case, kebab-case e camelCase) que tornam o nome de um campo sensível.
_SENSITIVE_WORDS = frozenset(
    {
        "apikey",
        "authorization",
        "auth",
        "bearer",
        "secret",
        "secrets",
        "password",
        "passwd",
        "pwd",
        "passphrase",
        "senha",
        "segredo",
        "token",  # singular: `tokens_in`, `max_tokens` são contagens e ficam
        "jwt",
        "cookie",
        "credential",
        "credentials",
        "privatekey",
    }
)
# `key` só é sensível ao lado de um destes (`api_key`, `private_key`); `key_index` e `featherless_keys` ficam.
_KEY_QUALIFIERS = frozenset({"api", "private", "secret", "access", "auth", "client", "signing", "encryption", "master"})
_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def _redact_name_value(match: re.Match[str]) -> str:
    """Mantém `nome=` (ou `"nome": "`) e troca só o valor."""
    return match.group(0)[: match.end(1) - match.start(0)] + REDACTED


_NAME = (
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|client[_-]?secret"
    r"|token|secret|password|passwd|pwd|senha)"
)
_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]], ...] = (
    # Cabeçalho inteiro até o fim da linha: `Authorization: Bearer xyz` -> `Authorization: [REDACTED]`.
    (re.compile(r"(?i)(?<![A-Za-z0-9])((?:proxy-)?authorization[\"']?\s*[:=]\s*)[^\r\n]+"), rf"\1{REDACTED}"),
    # `nome=valor`, `nome: valor`, `"nome": "valor"` (query string, JSON em texto, log).
    (re.compile(rf"(?i)(?<![A-Za-z0-9]){_NAME}([\"']?\s*[:=]\s*[\"']?)[^\s\"'&,;}}]+"), _redact_name_value),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*"), f"Bearer {REDACTED}"),
    (re.compile(r"\bBasic\s+[A-Za-z0-9+/]{4,}=*"), f"Basic {REDACTED}"),
    (re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]+@"), f"{REDACTED}@"),  # senha em URL
    (re.compile(r"(?<![A-Za-z0-9])rc_[A-Za-z0-9_\-]+"), REDACTED),  # Featherless
    (re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{4,}"), REDACTED),  # OpenAI, Langfuse (sk-lf-)
    (re.compile(r"(?<![A-Za-z0-9])pk-lf-[A-Za-z0-9_\-]+"), REDACTED),  # Langfuse, chave pública
    (re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), REDACTED),  # JWT
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), REDACTED),  # GitHub
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), REDACTED),  # AWS
)


def is_sensitive_name(name: str) -> bool:
    words = {w.lower() for w in _WORDS.findall(name)}
    if words & _SENSITIVE_WORDS:
        return True
    return "key" in words and bool(words & _KEY_QUALIFIERS)


def _prepare_known(known_secrets: Iterable[str | SecretStr] | None) -> tuple[str, ...]:
    values = (s.get_secret_value() if isinstance(s, SecretStr) else s for s in known_secrets or ())
    return tuple(sorted({v for v in values if v and len(v) >= MIN_KNOWN_SECRET_LEN}, key=len, reverse=True))


def _scrub(text: str, known: tuple[str, ...]) -> str:
    for secret in known:
        text = text.replace(secret, REDACTED)
    for pattern, replacement in _TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_text(text: str, *, known_secrets: Iterable[str | SecretStr] | None = None) -> str:
    """Remove de um texto livre os valores de chave conhecidos e os formatos de chave reconhecíveis."""
    return Masker(known_secrets).text(text)


def _redact(value: Any, known: tuple[str, ...], depth: int, seen: frozenset[int]) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _scrub(value, known)
    if isinstance(value, SecretStr | SecretBytes):
        return REDACTED
    if isinstance(value, bytes | bytearray | memoryview):
        return f"[BYTES {len(value)}]"  # nunca decodifica: pode ser imagem ou chave
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Enum):
        return _redact(value.value, known, depth, seen)
    if depth >= MAX_DEPTH or id(value) in seen:
        return "[TRUNCATED]"
    seen = seen | {id(value)}
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            name = str(k)
            hidden = is_sensitive_name(name) and v is not None
            out[_scrub(name, known)] = REDACTED if hidden else _redact(v, known, depth + 1, seen)
        return out
    if isinstance(value, list | tuple | set | frozenset):
        items = sorted(value, key=repr) if isinstance(value, set | frozenset) else value
        return [_redact(v, known, depth + 1, seen) for v in items]
    return _scrub(str(value), known)  # exceções e objetos quaisquer: o texto, já mascarado


class Masker:
    """Máscara com os valores literais das chaves configuradas (camada 3). O `repr` nunca mostra esses valores."""

    def __init__(self, known_secrets: Iterable[str | SecretStr] | None = None) -> None:
        self._known = _prepare_known(known_secrets)

    def __repr__(self) -> str:
        return f"Masker(known_secrets={len(self._known)})"

    def text(self, text: str) -> str:
        return _scrub(text, self._known)

    def value(self, value: Any) -> Any:
        return _redact(value, self._known, 0, frozenset())

    def payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        out = self.value(dict(payload))
        assert isinstance(out, dict)
        return out


def redact(value: Any, *, known_secrets: Iterable[str | SecretStr] | None = None) -> Any:
    """Versão mascarada e serializável em JSON de `value` (recursiva em dicionários, listas e modelos pydantic)."""
    return Masker(known_secrets).value(value)


def redact_payload(
    payload: Mapping[str, Any], *, known_secrets: Iterable[str | SecretStr] | None = None
) -> dict[str, Any]:
    """Máscara do `payload` de um `TraceEvent` antes de gravar."""
    return Masker(known_secrets).payload(payload)
