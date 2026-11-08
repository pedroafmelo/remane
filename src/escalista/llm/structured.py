"""Saída estruturada como ferramenta (arquitetura, seção 7): o schema pydantic vira a ferramenta que o modelo é
obrigado a chamar; os argumentos são validados com o mesmo modelo.

- Schema: `model_json_schema()` com os `$ref`/`$defs` **resolvidos no lugar** (a Featherless não documenta suporte a
  `$defs`, então a ferramenta sai autocontida) e sem `title` de schema. `$ref` recursivo não é suportado.
- Reenvio: ferramenta ausente, JSON inválido, validação do pydantic ou validação extra (`validate`) falhando reenvia
  a conversa com o motivo anexado, até `MAX_RESENDS` (2) vezes, ou seja, no máximo 3 chamadas. Depois disso,
  `LLMUnavailableError` com cartão RX-12. Falha do cliente (`LLMUnavailableError`) propaga como está.
- **Nunca devolve texto livre no lugar:** o `content` da resposta é ignorado; só `tool_args` validado vira resultado.
- O motivo do reenvio não repete o valor recusado (só o caminho do campo e a mensagem), para não ecoar dado no prompt.
- O rastro de cada chamada é do cliente (`kind` pedido); aqui não há evento próprio.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from escalista.domain.contracts import ExceptionCard, LLMMessage, LLMUnavailableError
from escalista.domain.ports import LLMClient

MAX_RESENDS = 2
RX12 = "RX-12"
_MAX_ERROR_CHARS = 600
_NO_TOOL_ERROR = "você não chamou a ferramenta, ou os argumentos não são um objeto JSON válido"


def tool_schema_for(
    model: type[BaseModel], *, name: str | None = None, description: str | None = None
) -> dict[str, Any]:
    """Ferramenta no formato OpenAI para o modelo pydantic, sem `$defs` (referências resolvidas no lugar)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    parameters = _inline(schema, defs, ())
    return {
        "type": "function",
        "function": {
            "name": name or _snake(model.__name__),
            "description": description or (inspect.getdoc(model) or model.__name__),
            "parameters": parameters,
        },
    }


def call_structured[M: BaseModel](
    client: LLMClient,
    model: type[M],
    *,
    messages: list[LLMMessage],
    run_id: str,
    parent_id: str | None = None,
    tool_name: str | None = None,
    tool_description: str | None = None,
    size: Literal["small", "large"] = "small",
    kind: str | None = None,
    validate: Callable[[M], None] | None = None,
    what: str = "saída estruturada",
) -> M:
    """Chama o modelo com a ferramenta forçada e devolve a instância validada de `model`.

    `validate` roda depois do pydantic e levanta `ValueError` com o motivo (vai ao modelo no reenvio).
    `kind` só é repassado se o cliente aceitar (o `FeatherlessClient` aceita; o falso dos testes, não).
    """
    tool = tool_schema_for(model, name=tool_name, description=tool_description)
    extra = {"kind": kind} if kind and _accepts_kind(client) else {}
    conversation = list(messages)
    errors: list[str] = []
    for _ in range(MAX_RESENDS + 1):
        result = client.complete(
            size=size, messages=conversation, tool_schema=tool, run_id=run_id, parent_id=parent_id, **extra
        )
        checked = _check(result.tool_args, model, validate)
        if not isinstance(checked, str):
            return checked
        error = checked
        errors.append(error)
        conversation = [
            *messages,
            LLMMessage(
                role="user",
                content=(
                    f"Sua resposta anterior foi recusada: {error}. "
                    f"Chame a ferramenta `{tool['function']['name']}` de novo, corrigindo esse problema."
                ),
            ),
        ]
    raise LLMUnavailableError(_card(what, errors, run_id, parent_id))


def _check[M: BaseModel](args: dict[str, Any] | None, model: type[M], validate: Callable[[M], None] | None) -> M | str:
    if args is None:
        return _NO_TOOL_ERROR
    try:
        value = model.model_validate(args)
    except ValidationError as exc:
        return _clip("argumentos inválidos: " + "; ".join(_describe(e) for e in exc.errors()))
    if validate is not None:
        try:
            validate(value)
        except ValueError as exc:
            return _clip(str(exc) or "validação recusou a resposta")
    return value


def _describe(error: Any) -> str:
    where = ".".join(str(p) for p in error["loc"]) or "(raiz)"
    return f"{where}: {error['msg']}"


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_ERROR_CHARS else text[: _MAX_ERROR_CHARS - 1] + "…"


def _card(what: str, errors: list[str], run_id: str, parent_id: str | None) -> ExceptionCard:
    return ExceptionCard(
        code=RX12,
        title="Modelo de linguagem não entregou uma resposta válida",
        reason=f"O modelo não produziu {what} válida em {len(errors)} tentativas (1 chamada e {MAX_RESENDS} reenvios).",
        evidence=[f"tentativa {i}: {e}" for i, e in enumerate(errors, start=1)],
        recommendation="Tentar de novo; se persistir, conferir o modelo pequeno e a ferramenta no teste de fumaça.",
        if_no_answer="O passo que depende do modelo fica sem texto do modelo; nenhum texto é inventado.",
        trace_id=parent_id or run_id,
    )


def _accepts_kind(client: Any) -> bool:
    try:
        params = inspect.signature(client.complete).parameters
    except (TypeError, ValueError):
        return False
    return "kind" in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _inline(node: Any, defs: dict[str, Any], seen: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        return [_inline(item, defs, seen) for item in node]
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if isinstance(ref, str):
        key = ref.removeprefix("#/$defs/")
        if key in seen:
            raise ValueError(f"schema recursivo não suportado: {key}")
        extra = {k: v for k, v in node.items() if k != "$ref"}
        return {**_inline(defs[key], defs, (*seen, key)), **_inline(extra, defs, seen)}
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "title":
            continue
        # `properties` mapeia nomes de campo (um campo pode se chamar "title"): inline em cada valor, sem filtrar chaves
        if key == "properties" and isinstance(value, dict):
            out[key] = {name: _inline(sub, defs, seen) for name, sub in value.items()}
        else:
            out[key] = _inline(value, defs, seen)
    return out
