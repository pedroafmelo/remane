"""Teste de fumaça das chaves da Featherless: cada chave, isolada, com o modelo pequeno (e o grande com `--large`).

COMO RODAR (na raiz do repositório, com o `.env` preenchido; o script lê as chaves de lá):

    uv run python -m escalista.llm.smoke              # modelo pequeno, uma chamada curta por chave
    uv run python -m escalista.llm.smoke --large      # também o modelo grande (mais lento e mais caro)
    uv run python -m escalista.llm.smoke --dry-run    # não chama a rede: só lista índices de chave e modelos

Cada chamada é curta, em português, com uma ferramenta forçada (`{"resposta": str, "confianca": int}`). O pool de cada
chamada tem **uma única chave** (mantendo o índice do `.env`): sem failover, sem modelo reserva, para saber o que cada
chave faz sozinha. A saída é **uma linha por chave e modelo**:

    chave <índice> | <modelo> | ok/falha (<código ou tipo>) | custo US$ <valor ou "não informado"> | <n> ms
        | ferramenta: sim/não

(na tela é uma linha só, sem a quebra acima.)

- **chave <índice>**: o número da variável `FEATHERLESS_API_KEY_<índice>`. O valor da chave nunca é impresso.
- **modelo**: o modelo chamado (do `.env` ou do padrão de `config.py`).
- **ok/falha**: `ok`, ou `falha (HTTP 401)` (chave recusada), `falha (HTTP 402)` (sem saldo), `falha (HTTP 403)` (modelo
  não desbloqueado na conta), `falha (HTTP 429)` (limite de concorrência), `falha (HTTP 400)` (modelo frio),
  `falha (sem resposta)` (conexão ou tempo esgotado) ou `falha (<TipoDoErro>)` (erro inesperado do script).
- **custo US$**: o `usage.cost` devolvido pela Featherless, medido; `não informado` se a resposta não trouxe o campo
  (nunca é estimado).
- **ms**: latência da chamada, incluindo novas tentativas em 5xx e conexão.
- **ferramenta**: `sim` se o modelo chamou a ferramenta com argumentos que passam no schema; `não` caso contrário
  (modelo sem suporte a ferramentas) ou se a chamada falhou.

No fim vem o resumo (chamadas ok, chaves ok e custo total medido). O código de saída é 0 se ao menos uma chamada
funcionou e 1 se nenhuma funcionou (ou se não há chave configurada). O conteúdo das mensagens também não é impresso.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TextIO

from pydantic import BaseModel, SecretStr, ValidationError

from escalista.audit.mask import Masker
from escalista.clock.system import SystemClock
from escalista.config import Settings
from escalista.domain.contracts import LLMMessage, LLMUnavailableError, TraceEvent
from escalista.llm.client import FeatherlessClient, ModelChoice, Size
from escalista.llm.pool import KeyPool
from escalista.llm.structured import tool_schema_for

NOT_REPORTED = "não informado"
RUN_ID = "smoke"
_SIZES: dict[Size, str] = {"small": "featherless_model_small", "large": "featherless_model_large"}


class Resposta(BaseModel):
    """Resposta curta de teste."""

    resposta: str
    confianca: int


_MESSAGES = [
    LLMMessage(role="system", content="Você é um assistente objetivo. Responda sempre em português."),
    LLMMessage(
        role="user",
        content="Qual é a capital de Pernambuco? Use a ferramenta para responder, com a confiança de 0 a 100.",
    ),
]


@dataclass(frozen=True)
class Outcome:
    key_index: int
    model: str
    ok: bool
    status: str  # "ok" ou "falha (...)"
    cost_usd: Decimal | None
    latency_ms: int | None
    tool_ok: bool


class _CollectSink:
    """Guarda os eventos do cliente em memória, só para ler o código HTTP e a latência de uma falha."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


def _failure_status(events: Sequence[TraceEvent]) -> tuple[str, int | None]:
    event = events[-1] if events else None
    attempts = (event.payload or {}).get("attempts") if event is not None else None
    last = attempts[-1] if attempts else None
    if last is None:
        return "falha (sem resposta)", event.latency_ms if event else None
    code = f"HTTP {last['status']}" if last.get("status") is not None else "sem resposta"
    return f"falha ({code})", event.latency_ms


def probe(
    index: int,
    key: SecretStr,
    size: Size,
    settings: Settings,
    *,
    http_client: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Outcome:
    """Uma chamada curta com ferramenta, usando só esta chave e só o modelo principal (sem reserva)."""
    model = getattr(settings, _SIZES[size])
    sink = _CollectSink()
    models = {s: ModelChoice(getattr(settings, name)) for s, name in _SIZES.items()}
    pool = KeyPool([(index, key)], concurrency=settings.featherless_concurrency_units, sleep=sleep)
    client = FeatherlessClient(
        pool=pool,
        models=models,
        trace_sink=sink,
        clock=SystemClock(),
        base_url=settings.featherless_base_url,
        http_client=http_client,
    )
    try:
        result = client.complete(
            size=size, messages=_MESSAGES, tool_schema=tool_schema_for(Resposta, name="responder"), run_id=RUN_ID
        )
    except LLMUnavailableError:
        status, latency = _failure_status(sink.events)
        return Outcome(index, model, False, status, None, latency, False)
    except Exception as exc:  # noqa: BLE001 - o script de fumaça relata qualquer falha em vez de abortar
        return Outcome(index, model, False, f"falha ({type(exc).__name__})", None, None, False)
    try:
        Resposta.model_validate(result.tool_args)
        tool_ok = True
    except ValidationError:
        tool_ok = False
    return Outcome(index, result.model, True, "ok", result.cost_usd, result.latency_ms, tool_ok)


def format_line(outcome: Outcome) -> str:
    cost = "não informado" if outcome.cost_usd is None else f"US$ {format(outcome.cost_usd, 'f')}"
    latency = "n/d" if outcome.latency_ms is None else str(outcome.latency_ms)
    tool = "sim" if outcome.tool_ok else "não"
    return (
        f"chave {outcome.key_index} | {outcome.model} | {outcome.status} | custo {cost} | {latency} ms | "
        f"ferramenta: {tool}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m escalista.llm.smoke", description="Fumaça das chaves da Featherless, uma por vez."
    )
    parser.add_argument("--large", action="store_true", help="também chama o modelo grande")
    parser.add_argument("--dry-run", action="store_true", help="não chama a rede: lista chaves e modelos")
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    http_client: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
    out: TextIO | None = None,
) -> int:
    """Executa a fumaça e devolve o código de saída (0: alguma chamada ok; 1: nenhuma)."""
    args = _parser().parse_args(argv)
    cfg = settings if settings is not None else Settings()
    stream = out if out is not None else sys.stdout
    keys = cfg.featherless_keys
    mask = Masker([key for _, key in keys])

    def say(text: str) -> None:
        print(mask.text(text), file=stream)

    sizes: list[Size] = ["small", "large"] if args.large else ["small"]
    if args.dry_run:
        say("dry-run: nenhuma chamada de rede")
        say(f"chaves configuradas (índices): {cfg.summary()['featherless_keys']}")
        say(f"modelo pequeno: {cfg.featherless_model_small}")
        say(f"modelo grande: {cfg.featherless_model_large}" + ("" if args.large else " (só com --large)"))
        return 0
    if not keys:
        say("nenhuma chave da Featherless configurada (FEATHERLESS_API_KEY_1 a _4 no .env)")
        return 1

    outcomes: list[Outcome] = []
    for index, key in keys:
        for size in sizes:
            outcome = probe(index, key, size, cfg, http_client=http_client, sleep=sleep)
            outcomes.append(outcome)
            say(format_line(outcome))

    ok = [o for o in outcomes if o.ok]
    keys_ok = sorted({o.key_index for o in ok})
    measured = [o.cost_usd for o in outcomes if o.cost_usd is not None]
    total = format(sum(measured, Decimal(0)), "f")
    unmeasured = len(ok) - len([o for o in ok if o.cost_usd is not None])
    note = f" ({unmeasured} chamada(s) ok sem custo informado)" if unmeasured else ""
    say(
        f"resumo: {len(ok)} de {len(outcomes)} chamadas ok | chaves ok: {keys_ok or 'nenhuma'} "
        f"de {[i for i, _ in keys]} | custo total medido US$ {total}{note}"
    )
    return 0 if ok else 1


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    sys.exit(run())


if __name__ == "__main__":
    main()
