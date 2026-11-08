"""Pool de chaves da Featherless: failover em ordem e semáforo de concorrência (DEC-025, arquitetura, seção 7).

Regras de failover, por requisição HTTP (o pool não conhece o modelo; o modelo reserva é decisão do cliente):

- **401, 402, 403, 429 → próxima chave, em ordem.** Erro da conta: chave não reconhecida (401), saldo (402; o status
  de saldo zerado é [NÃO ENCONTRADO] na doc), modelo não desbloqueado na conta (403), limite de concorrência (429).
- **400 → falha direto, sem trocar.** Modelo frio (doc da Featherless): outra chave não esquenta o modelo.
- **404 → falha direto, sem trocar.** Modelo não encontrado.
- **5xx, conexão ou tempo esgotado → mesma chave**, até `retries_on_transient` (3) novas tentativas, com espera curta:
  para o 503 "no valid executor" a doc pede repetir a mesma chamada.
- **Outro 4xx → falha direto.** Erro do pedido.

Esgotar chaves, tentativas ou semáforo levanta `PoolExhaustedError` com motivo legível: só o índice da chave e o
status HTTP, nunca o valor da chave nem o corpo da resposta (que pode ecoar o cabeçalho). O cliente faz disso o RX-12.

**Semáforo:** `threading.Semaphore` do pool, segurado só durante cada requisição HTTP (não na espera entre tentativas).
Tamanho: `featherless_concurrency_units` ou `DEFAULT_CONCURRENCY = 2` `[PROPOSTA]`: o teto do plano do evento é
[NÃO ENCONTRADO]; 2 cabe uma chamada do modelo grande (2 unidades) ou duas do pequeno (1 unidade). Passar do teto
devolve 429, que troca de chave; o semáforo evita chegar lá.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, TypeVar

import openai
from pydantic import SecretStr

from escalista.audit.mask import Masker

log = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_CONCURRENCY = 2
DEFAULT_RETRIES_ON_TRANSIENT = 3
DEFAULT_BACKOFF_S: tuple[float, ...] = (0.5, 1.0, 2.0)
DEFAULT_ACQUIRE_TIMEOUT_S = 120.0

SWITCH_KEY_STATUSES = frozenset({401, 402, 403, 429})
MODEL_STATUSES = frozenset({400, 404})  # problema do modelo: o cliente pode tentar o modelo reserva

_STATUS_TEXT = {
    400: "modelo frio ou pedido recusado",
    401: "chave não reconhecida",
    402: "saldo insuficiente",
    403: "modelo não desbloqueado nesta conta",
    404: "modelo não encontrado",
    429: "limite de concorrência da conta",
    500: "erro interno da Featherless",
    503: "sem capacidade para o modelo",
}


class Action(StrEnum):
    SWITCH_KEY = "switch_key"
    RETRY_SAME_KEY = "retry_same_key"
    FAIL = "fail"


FailureKind = Literal["keys", "model", "request", "busy"]


@dataclass(frozen=True)
class Attempt:
    """Uma requisição HTTP tentada. Só índice e status: nunca o valor da chave nem o corpo da resposta."""

    key_index: int
    status: int | None  # None: sem resposta HTTP (conexão, tempo esgotado)
    outcome: str  # "ok", "switch_key", "retry_same_key", "fail"
    detail: str
    latency_ms: int

    def describe(self) -> str:
        code = self.status if self.status is not None else "sem resposta"
        return f"chave {self.key_index}: {code} ({self.detail})"


class PoolExhaustedError(Exception):
    """Nenhuma chave respondeu. `kind`: `keys` (todas recusaram), `model` (modelo frio, ausente ou sem capacidade),
    `request` (erro do pedido) ou `busy` (semáforo local cheio)."""

    def __init__(self, kind: FailureKind, reason: str, attempts: Sequence[Attempt]) -> None:
        super().__init__(reason)
        self.kind: FailureKind = kind
        self.reason = reason
        self.attempts = list(attempts)


def classify(exc: BaseException) -> tuple[Action, int | None, str]:
    """O que fazer com uma falha da chamada: (ação, status HTTP ou None, motivo curto sem segredo)."""
    if isinstance(exc, openai.APIStatusError):
        status = exc.status_code
        detail = _STATUS_TEXT.get(status, "erro HTTP")
        if status in SWITCH_KEY_STATUSES:
            return Action.SWITCH_KEY, status, detail
        if status >= 500:
            return Action.RETRY_SAME_KEY, status, detail
        return Action.FAIL, status, detail
    if isinstance(exc, openai.APITimeoutError):
        return Action.RETRY_SAME_KEY, None, "tempo esgotado"
    if isinstance(exc, openai.APIConnectionError):
        return Action.RETRY_SAME_KEY, None, "falha de conexão"
    return Action.FAIL, None, type(exc).__name__


class KeyPool:
    """Chaves em ordem de prioridade (`Settings.featherless_keys`), failover e semáforo. `repr` só mostra índices."""

    def __init__(
        self,
        keys: Sequence[tuple[int, SecretStr]],
        *,
        concurrency: int | None = None,
        retries_on_transient: int = DEFAULT_RETRIES_ON_TRANSIENT,
        backoff_s: Sequence[float] = DEFAULT_BACKOFF_S,
        sleep: Callable[[float], None] = time.sleep,
        acquire_timeout_s: float | None = DEFAULT_ACQUIRE_TIMEOUT_S,
        perf_counter: Callable[[], float] = time.perf_counter,
    ) -> None:
        indices = [i for i, _ in keys]
        if len(set(indices)) != len(indices):
            raise ValueError("índices de chave repetidos")
        size = DEFAULT_CONCURRENCY if concurrency is None else concurrency
        if size < 1:
            raise ValueError("concorrência precisa ser >= 1")
        if retries_on_transient < 0:
            raise ValueError("retries_on_transient precisa ser >= 0")
        self._keys = list(keys)
        self._concurrency = size
        self._semaphore = threading.Semaphore(size)
        self._retries = retries_on_transient
        self._backoff = tuple(backoff_s) or (0.0,)
        self._sleep = sleep
        self._acquire_timeout = acquire_timeout_s
        self._perf_counter = perf_counter
        self._masker = Masker([key for _, key in self._keys])

    def __repr__(self) -> str:
        return f"KeyPool(keys={self.indices}, concurrency={self._concurrency}, retries_on_transient={self._retries})"

    @property
    def indices(self) -> list[int]:
        return [i for i, _ in self._keys]

    @property
    def concurrency(self) -> int:
        return self._concurrency

    def redact(self, text: str) -> str:
        """Defesa em profundidade: remove de um texto os valores das chaves do pool e formatos de chave conhecidos."""
        return self._masker.text(text)

    @contextmanager
    def _slot(self) -> Iterator[bool]:
        timeout = self._acquire_timeout
        acquired = self._semaphore.acquire() if timeout is None else self._semaphore.acquire(timeout=timeout)
        try:
            yield acquired
        finally:
            if acquired:
                self._semaphore.release()

    def _elapsed_ms(self, start: float) -> int:
        return max(0, round((self._perf_counter() - start) * 1000))

    def run(self, send: Callable[[int, SecretStr], T]) -> tuple[T, int, list[Attempt]]:
        """Chama `send(índice, chave)` com failover. Devolve (resultado, índice da chave que respondeu, tentativas).

        `send` lê o valor só com `chave.get_secret_value()` ao montar o cabeçalho e levanta a exceção do SDK `openai`
        em caso de erro. Exceções que não são do SDK sobem como estão (erro de programação, não de modelo).
        """
        attempts: list[Attempt] = []
        if not self._keys:
            raise PoolExhaustedError("keys", "nenhuma chave da Featherless configurada", attempts)
        for position, (index, key) in enumerate(self._keys):
            has_next = position + 1 < len(self._keys)
            transient_failures = 0
            while True:
                start = self._perf_counter()
                with self._slot() as acquired:
                    if not acquired:
                        reason = (
                            f"fila local do modelo cheia por {self._acquire_timeout:g} s "
                            f"(concorrência {self._concurrency})"
                        )
                        log.warning("featherless: %s", reason)
                        raise PoolExhaustedError("busy", reason, attempts)
                    try:
                        result = send(index, key)
                    except openai.OpenAIError as exc:
                        action, status, detail = classify(exc)
                    else:
                        attempts.append(Attempt(index, 200, "ok", "resposta recebida", self._elapsed_ms(start)))
                        return result, index, attempts
                latency = self._elapsed_ms(start)
                if action is Action.RETRY_SAME_KEY and transient_failures < self._retries:
                    attempts.append(Attempt(index, status, Action.RETRY_SAME_KEY, detail, latency))
                    delay = self._backoff[min(transient_failures, len(self._backoff) - 1)]
                    transient_failures += 1
                    log.warning(
                        "featherless: chave %d devolveu %s (%s); nova tentativa %d de %d na mesma chave",
                        index, status, detail, transient_failures, self._retries,
                    )  # fmt: skip
                    self._sleep(delay)
                    continue
                if action is Action.SWITCH_KEY:
                    attempts.append(Attempt(index, status, Action.SWITCH_KEY, detail, latency))
                    log.warning(
                        "featherless: chave %d devolveu %s (%s); %s",
                        index, status, detail, "trocando para a próxima chave" if has_next else "sem mais chaves",
                    )  # fmt: skip
                    break
                attempts.append(Attempt(index, status, Action.FAIL, detail, latency))
                log.warning("featherless: chave %d devolveu %s (%s); sem troca de chave", index, status, detail)
                raise PoolExhaustedError(_failure_kind(action, status), _reason(attempts), attempts)
        raise PoolExhaustedError("keys", _reason(attempts), attempts)


def _failure_kind(action: Action, status: int | None) -> FailureKind:
    if action is Action.RETRY_SAME_KEY or status in MODEL_STATUSES:
        return "model"
    return "request"


def _reason(attempts: Sequence[Attempt]) -> str:
    """Resumo legível das tentativas, agrupando repetições na mesma chave e status."""
    parts: list[str] = []
    for attempt in attempts:
        text = attempt.describe()
        if parts and parts[-1].startswith(text):
            head, _, count = parts[-1].partition(" × ")
            parts[-1] = f"{head} × {int(count or 1) + 1}"
        else:
            parts.append(text)
    return "; ".join(parts)
