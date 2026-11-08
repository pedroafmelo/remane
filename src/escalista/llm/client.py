"""`FeatherlessClient`: porta `LLMClient` sobre o SDK `openai` apontado para a Featherless (arquitetura, seção 7).

- `size` escolhe o modelo (`small` ou `large`). Se o principal falhar por problema do modelo (frio, ausente, sem
  capacidade) e houver reserva configurada, tenta o reserva com o mesmo pool.
- `tool_schema` vira ferramenta forçada (`tools` + `tool_choice` com o nome da função); `tool_args` é o JSON dos
  argumentos. Se o modelo não chamar a ferramenta ou mandar JSON inválido, `tool_args=None` e o motivo vai ao `payload`:
  quem valida e reenvia é a saída estruturada (B3), não este cliente.
- Custo: `usage.cost` em USD, como a Featherless documenta [FATO, featherless.ai/docs/request-pricing-and-credits],
  vira `cost_usd` (`Decimal`). Sem o campo, `cost_usd=None` e `payload.cost_basis` diz que não foi medido. Nunca estima.
- Rastro: **um `TraceEvent` por chamada** no `TraceSink` injetado: o `kind` pedido (padrão `llm.call`) no sucesso, ou
  `exception.raised` com RX-12 na falha. Leva modelo, índice da chave (nunca o valor), tokens, custo, latência e as
  tentativas. O conteúdo das mensagens não vai ao rastro (RN-06); quem precisar dele grava o próprio evento, redigido.
- Chave: o SDK recebe um valor de mentira; a chave real entra só no cabeçalho `Authorization` de cada requisição, lida
  do `SecretStr` naquele momento. As novas tentativas automáticas do SDK ficam desligadas (`max_retries=0`): quem
  decide é o pool.
"""

from __future__ import annotations

import json
import logging
import math
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import partial
from typing import Any, Literal, NoReturn

import openai
from pydantic import SecretStr

from escalista.config import Settings
from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMResult, LLMUnavailableError, TraceEvent
from escalista.domain.ports import Clock, TraceSink
from escalista.llm.pool import Attempt, KeyPool, PoolExhaustedError

log = logging.getLogger(__name__)

Size = Literal["small", "large"]

DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.2
DEFAULT_EVENT_KIND = "llm.call"
EXCEPTION_KIND = "exception.raised"
RX12 = "RX-12"
# Valor de mentira para o SDK: a chave real vai só no cabeçalho de cada requisição (não fica guardada no SDK).
_SDK_PLACEHOLDER_KEY = "featherless-key-per-request"

COST_MEASURED = "usage.cost da resposta da Featherless (USD, medido)"
COST_MISSING = "resposta sem usage.cost: custo não medido"
COST_INVALID = "usage.cost inválido na resposta: custo não medido"
COST_FAILED = "chamada falhou sem resposta válida: custo não medido"


@dataclass(frozen=True)
class ModelChoice:
    primary: str
    fallback: str | None = None

    def candidates(self) -> list[str]:
        return [self.primary] if not self.fallback or self.fallback == self.primary else [self.primary, self.fallback]


class FeatherlessClient:
    """Cliente da Featherless (porta `LLMClient`). Para montar a partir da configuração, use `from_settings`."""

    def __init__(
        self,
        *,
        pool: KeyPool,
        models: Mapping[Size, ModelChoice],
        trace_sink: TraceSink,
        clock: Clock,
        base_url: str,
        http_client: Any | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_tokens: int | None = DEFAULT_MAX_TOKENS,
        temperature: float | None = DEFAULT_TEMPERATURE,
        extra_body: Mapping[str, Any] | None = None,
        event_kind: str = DEFAULT_EVENT_KIND,
        perf_counter: Callable[[], float] = time.perf_counter,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        missing = {"small", "large"} - set(models)
        if missing:
            raise ValueError(f"modelos sem configuração: {sorted(missing)}")
        self._pool = pool
        self._models = dict(models)
        self._sink = trace_sink
        self._clock = clock
        self._base_url = base_url
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._extra_body = dict(extra_body) if extra_body else None
        self._event_kind = event_kind
        self._perf_counter = perf_counter
        self._new_id = id_factory
        self._sdk = openai.OpenAI(
            api_key=_SDK_PLACEHOLDER_KEY,
            base_url=base_url,
            timeout=timeout_s,
            max_retries=0,
            http_client=http_client,
        )

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        trace_sink: TraceSink,
        clock: Clock,
        http_client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        **kwargs: Any,
    ) -> FeatherlessClient:
        pool = KeyPool(settings.featherless_keys, concurrency=settings.featherless_concurrency_units, sleep=sleep)
        models: dict[Size, ModelChoice] = {
            "small": ModelChoice(settings.featherless_model_small, settings.featherless_model_small_fallback),
            "large": ModelChoice(settings.featherless_model_large, settings.featherless_model_large_fallback),
        }
        return cls(
            pool=pool,
            models=models,
            trace_sink=trace_sink,
            clock=clock,
            base_url=settings.featherless_base_url,
            http_client=http_client,
            **kwargs,
        )

    def __repr__(self) -> str:
        models = {size: choice.candidates() for size, choice in self._models.items()}
        return f"FeatherlessClient(base_url={self._base_url!r}, models={models!r}, pool={self._pool!r})"

    def complete(
        self,
        *,
        size: Size,
        messages: list[LLMMessage],
        tool_schema: dict[str, Any] | None = None,
        run_id: str,
        parent_id: str | None = None,
        kind: str | None = None,
    ) -> LLMResult:
        """Uma chamada ao modelo. Levanta `LLMUnavailableError` (RX-12) se nenhuma chave ou modelo responder.

        `kind` (fora da porta, opcional): tipo do evento de sucesso, por exemplo `llm.justify`; padrão `event_kind`.
        """
        if size not in self._models:
            raise ValueError(f"size inválido: {size!r}")
        tool = _normalize_tool(tool_schema) if tool_schema is not None else None
        event_kind = kind or self._event_kind
        start = self._perf_counter()
        all_attempts: list[dict[str, Any]] = []
        failure: PoolExhaustedError | None = None
        model = self._models[size].primary
        for model in self._models[size].candidates():
            request = self._request(model, messages, tool)
            try:
                response, key_index, attempts = self._pool.run(partial(self._send, request))
            except PoolExhaustedError as exc:
                all_attempts += _attempts_payload(model, exc.attempts)
                failure = exc
                if exc.kind != "model":
                    break  # trocar de modelo não resolve chave, pedido ou fila local
                continue
            all_attempts += _attempts_payload(model, attempts)
            return self._success(
                response, event_kind, size, model, key_index, tool, all_attempts, run_id, parent_id, start
            )
        assert failure is not None
        self._fail(failure, size, model, all_attempts, run_id, parent_id, start, event_kind)

    # --- requisição -----------------------------------------------------------------------------------------------

    def _request(self, model: str, messages: Sequence[LLMMessage], tool: dict[str, Any] | None) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if self._max_tokens is not None:
            request["max_tokens"] = self._max_tokens
        if self._temperature is not None:
            request["temperature"] = self._temperature
        if tool is not None:
            request["tools"] = [tool]
            request["tool_choice"] = {"type": "function", "function": {"name": tool["function"]["name"]}}
        if self._extra_body:
            request["extra_body"] = self._extra_body
        return request

    def _send(self, request: dict[str, Any], _index: int, key: SecretStr) -> Any:
        headers = {"Authorization": f"Bearer {key.get_secret_value()}"}
        return self._sdk.chat.completions.create(**request, extra_headers=headers)

    # --- sucesso --------------------------------------------------------------------------------------------------

    def _success(
        self,
        response: Any,
        event_kind: str,
        size: Size,
        model: str,
        key_index: int,
        tool: dict[str, Any] | None,
        attempts: list[dict[str, Any]],
        run_id: str,
        parent_id: str | None,
        start: float,
    ) -> LLMResult:
        latency_ms = self._elapsed_ms(start)
        usage = getattr(response, "usage", None)
        tokens_in = _int_or_none(getattr(usage, "prompt_tokens", None))
        tokens_out = _int_or_none(getattr(usage, "completion_tokens", None))
        cost_usd, cost_basis = _measured_cost(usage)
        choice = response.choices[0] if getattr(response, "choices", None) else None
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        tool_args, tool_note = _tool_args(message, tool) if tool is not None else (None, None)
        payload: dict[str, Any] = {
            "size": size,
            "model_requested": self._models[size].primary,
            "fallback_used": model != self._models[size].primary,
            "cost_basis": cost_basis,
            "finish_reason": getattr(choice, "finish_reason", None),
            "attempts": attempts,
        }
        if tool is not None:
            payload["tool"] = tool["function"]["name"]
            payload["tool_args_ok"] = tool_args is not None
            if tool_note:
                payload["tool_args_error"] = tool_note
        self._emit(
            kind=event_kind,
            run_id=run_id,
            parent_id=parent_id,
            model=model,
            key_index=key_index,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            payload=payload,
        )
        return LLMResult(
            content=content,
            tool_args=tool_args,
            model=model,
            key_index=key_index,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

    # --- falha (RX-12) --------------------------------------------------------------------------------------------

    def _fail(
        self,
        failure: PoolExhaustedError,
        size: Size,
        model: str,
        attempts: list[dict[str, Any]],
        run_id: str,
        parent_id: str | None,
        start: float,
        event_kind: str,
    ) -> NoReturn:
        latency_ms = self._elapsed_ms(start)
        reason = self._pool.redact(_failure_reason(failure, size, attempts))
        last_key = attempts[-1]["key_index"] if attempts else None
        event_id = self._new_id()
        card = ExceptionCard(
            code=RX12,
            title="Modelo de linguagem indisponível",
            reason=reason,
            evidence=[self._pool.redact(_describe(a)) for a in attempts],
            recommendation=_recommendation(failure),
            if_no_answer="O passo que depende do modelo fica sem texto do modelo; nenhum texto é inventado.",
            trace_id=event_id,
        )
        self._emit(
            event_id=event_id,
            kind=EXCEPTION_KIND,
            run_id=run_id,
            parent_id=parent_id,
            model=model,
            key_index=last_key,
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
            latency_ms=latency_ms,
            payload={
                "code": RX12,
                "reason": reason,
                "failure": failure.kind,
                "requested_kind": event_kind,
                "size": size,
                "cost_basis": COST_FAILED,
                "attempts": attempts,
            },
        )
        log.warning("featherless: RX-12 em run_id=%s (%s)", run_id, failure.kind)
        raise LLMUnavailableError(card) from None

    # --- apoio ----------------------------------------------------------------------------------------------------

    def _emit(self, *, event_id: str | None = None, **fields: Any) -> None:
        self._sink.emit(TraceEvent(id=event_id or self._new_id(), at=self._clock.now(), **fields))

    def _elapsed_ms(self, start: float) -> int:
        return max(0, round((self._perf_counter() - start) * 1000))


def _normalize_tool(tool_schema: Mapping[str, Any]) -> dict[str, Any]:
    """Aceita a ferramenta no formato OpenAI (`{"type": "function", "function": {...}}`) ou só a função."""
    function = tool_schema.get("function") if tool_schema.get("type") == "function" else tool_schema
    if not isinstance(function, Mapping) or not isinstance(function.get("name"), str) or not function["name"]:
        raise ValueError("tool_schema precisa ter o nome da função (`name`)")
    return {"type": "function", "function": dict(function)}


def _tool_args(message: Any, tool: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    calls = getattr(message, "tool_calls", None) or []
    name = tool["function"]["name"]
    call = next((c for c in calls if getattr(getattr(c, "function", None), "name", None) == name), None)
    if call is None:
        return None, "o modelo não chamou a ferramenta"
    raw = call.function.arguments
    try:
        args = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return None, "argumentos da ferramenta não são JSON válido"
    if not isinstance(args, dict):
        return None, "argumentos da ferramenta não são um objeto JSON"
    return args, None


def _measured_cost(usage: Any) -> tuple[Decimal | None, str]:
    """`usage.cost` (USD) -> `Decimal`. O SDK guarda campos extras do `usage`; ausente ou inválido vira `None`."""
    if usage is None:
        return None, COST_MISSING
    raw = getattr(usage, "cost", None)
    if raw is None:
        extra = getattr(usage, "model_extra", None) or {}
        raw = extra.get("cost")
    if raw is None:
        return None, COST_MISSING
    if isinstance(raw, bool) or not isinstance(raw, int | float | str | Decimal):
        return None, COST_INVALID
    if isinstance(raw, float) and not math.isfinite(raw):
        return None, COST_INVALID
    try:
        cost = Decimal(str(raw))
    except InvalidOperation:
        return None, COST_INVALID
    if not cost.is_finite() or cost < 0:
        return None, COST_INVALID
    return cost, COST_MEASURED


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _attempts_payload(model: str, attempts: Sequence[Attempt]) -> list[dict[str, Any]]:
    return [
        {
            "model": model,
            "key_index": a.key_index,
            "status": a.status,
            "outcome": str(a.outcome),
            "detail": a.detail,
            "latency_ms": a.latency_ms,
        }
        for a in attempts
    ]


def _describe(attempt: Mapping[str, Any]) -> str:
    status = attempt["status"] if attempt["status"] is not None else "sem resposta"
    return f"{attempt['model']} · chave {attempt['key_index']}: {status} ({attempt['detail']})"


def _failure_reason(failure: PoolExhaustedError, size: Size, attempts: Sequence[Mapping[str, Any]]) -> str:
    headline = {
        "keys": "nenhuma chave da Featherless aceitou a chamada",
        "model": "o modelo não respondeu (frio, ausente ou sem capacidade)",
        "request": "a Featherless recusou o pedido",
        "busy": "o limite local de chamadas simultâneas não liberou a tempo",
    }[failure.kind]
    detail = "; ".join(_describe(a) for a in attempts) if attempts else failure.reason
    return f"Modelo {size}: {headline}. {detail}."


def _recommendation(failure: PoolExhaustedError) -> str:
    return {
        "keys": "Conferir no painel da Featherless a validade, o saldo e o desbloqueio do modelo de cada chave; "
        "tentar de novo depois.",
        "model": "Tentar de novo em alguns minutos ou configurar um modelo reserva para este papel.",
        "request": "Revisar o pedido (mensagens e ferramenta); o erro não é da chave.",
        "busy": "Tentar de novo quando as chamadas em andamento terminarem.",
    }[failure.kind]
