"""`FeatherlessClient` com transporte HTTP falso: sem rede, sem `.env`, chaves sentinela que nunca podem vazar."""

import base64
import json
import logging
from datetime import datetime
from decimal import Decimal

import httpx2
import pytest
from sqlalchemy import text as sql

from escalista.audit.sink import SqlTraceSink
from escalista.config import Settings
from escalista.db import init_db, make_engine
from escalista.domain.contracts import ImagePart, LLMMessage, LLMUnavailableError, TextPart
from escalista.domain.ports import LLMClient
from escalista.llm.client import COST_MEASURED, COST_MISSING, FeatherlessClient
from tests.fakes import FixedClock, ListTraceSink

SENTINELS = {i: f"rc_SENTINELA_NAO_VAZAR_{i}" for i in (1, 2, 3)}
BY_VALUE = {v: k for k, v in SENTINELS.items()}
SMALL, LARGE, SMALL_FB = "modelo/pequeno", "modelo/grande", "modelo/pequeno-reserva"
MESSAGES = [LLMMessage(role="user", content="Explique a troca de turno.")]
TOOL = {
    "name": "registrar_justificativa",
    "description": "Justificativa estruturada",
    "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]},
}


def completion(model: str, *, content="ok", cost=0.000123, tool_args: str | None = None) -> dict:
    message: dict = {"role": "assistant", "content": content}
    if tool_args is not None:
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": TOOL["name"], "arguments": tool_args}}
            ],
        }
    usage: dict = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    if cost is not None:
        usage["cost"] = cost
    return {
        "id": "cmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": usage,
    }


class FakeFeatherless:
    """Servidor falso: cada passo é um status de erro (int) ou um corpo de sucesso (dict). Registra chave e corpo."""

    def __init__(self, *steps) -> None:
        self.steps = list(steps)
        self.calls: list[dict] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        key = request.headers["authorization"].removeprefix("Bearer ")
        body = json.loads(request.content)
        self.calls.append({"key_index": BY_VALUE.get(key), "model": body["model"], "body": body})
        step = self.steps.pop(0)
        if isinstance(step, int):
            # o corpo de erro ecoa a chave, como um servidor descuidado: nada disso pode chegar ao rastro ou ao log
            return httpx2.Response(step, json={"error": {"message": f"erro {step} para a chave {key}"}})
        return httpx2.Response(200, json=step)

    @property
    def keys(self) -> list[int | None]:
        return [c["key_index"] for c in self.calls]


@pytest.fixture
def settings(monkeypatch) -> Settings:
    for name in ("API_KEY_4", "MODEL_SMALL_FALLBACK", "MODEL_LARGE_FALLBACK", "CONCURRENCY_UNITS"):
        monkeypatch.delenv(f"FEATHERLESS_{name}", raising=False)
    for i, value in SENTINELS.items():
        monkeypatch.setenv(f"FEATHERLESS_API_KEY_{i}", value)
    monkeypatch.setenv("FEATHERLESS_BASE_URL", "https://featherless.test/v1")
    monkeypatch.setenv("FEATHERLESS_MODEL_SMALL", SMALL)
    monkeypatch.setenv("FEATHERLESS_MODEL_LARGE", LARGE)
    return Settings(_env_file=None)


@pytest.fixture
def sink() -> ListTraceSink:
    return ListTraceSink()


@pytest.fixture
def make(settings, sink):
    def build(server: FakeFeatherless, cfg: Settings | None = None, **kw) -> FeatherlessClient:
        kw.setdefault("sleep", lambda _s: None)
        return FeatherlessClient.from_settings(
            cfg or settings,
            trace_sink=sink,
            clock=FixedClock(datetime(2026, 11, 8, 9, 0)),
            http_client=httpx2.Client(transport=httpx2.MockTransport(server)),
            **kw,
        )

    return build


def call(client: FeatherlessClient, **kw):
    kw.setdefault("size", "small")
    return client.complete(messages=MESSAGES, run_id="run-1", parent_id="evt-0", **kw)


def test_client_satisfies_port(make):
    assert isinstance(make(FakeFeatherless()), LLMClient)


@pytest.mark.parametrize(
    ("steps", "expected_keys", "outcome"),
    [
        ([401, completion(SMALL)], [1, 2], 2),  # 401 troca de chave
        ([429, completion(SMALL)], [1, 2], 2),  # 429 troca de chave
        ([401, 429, completion(SMALL)], [1, 2, 3], 3),  # em ordem
        ([400], [1], "RX-12"),  # 400: modelo frio, não troca nem repete
        ([503, completion(SMALL)], [1, 1], 1),  # 503: repete na mesma chave
        ([503, 503, 503, 503], [1, 1, 1, 1], "RX-12"),  # 1 + 3 novas tentativas, sem trocar de chave
    ],
)
def test_401_429_switch_key_400_503_do_not(make, steps, expected_keys, outcome):
    server = FakeFeatherless(*steps)
    client = make(server)
    if outcome == "RX-12":
        with pytest.raises(LLMUnavailableError) as err:
            call(client)
        assert err.value.card.code == "RX-12"
    else:
        assert call(client).key_index == outcome
    assert server.keys == expected_keys
    assert server.steps == []


def test_llm_failure_yields_rx12_not_text(make, sink):
    server = FakeFeatherless(401, 429, 401)
    with pytest.raises(LLMUnavailableError) as err:
        call(make(server))
    card = err.value.card
    assert card.code == "RX-12"
    assert "chave 1: 401" in card.reason and "chave 2: 429" in card.reason and "chave 3: 401" in card.reason
    assert card.recommendation and card.if_no_answer
    assert len(card.evidence) == 3
    [event] = sink.events
    assert event.kind == "exception.raised"
    assert event.payload["code"] == "RX-12"
    assert event.payload["failure"] == "keys"
    assert event.payload["requested_kind"] == "llm.call"
    assert card.trace_id == event.id
    assert (event.run_id, event.parent_id, event.key_index) == ("run-1", "evt-0", 3)
    assert event.cost_usd is None and "não medido" in event.payload["cost_basis"]
    assert not [e for e in sink.events if e.kind == "llm.call"]


def test_key_value_never_in_trace_or_log(make, sink, caplog):
    caplog.set_level(logging.DEBUG)
    server = FakeFeatherless(401, 429, 503, completion(SMALL), 401, 429, 401)
    client = make(server)
    result = call(client)
    with pytest.raises(LLMUnavailableError) as err:
        call(client)
    # o teste só vale se as chaves de fato saíram nos cabeçalhos
    assert server.keys == [1, 2, 3, 3, 1, 2, 3]
    exposed = [
        caplog.text,
        repr(client),
        str(client),
        repr(vars(client)),
        repr(client._sdk.api_key),
        result.model_dump_json(),
        str(err.value),
        repr(err.value),
        err.value.card.model_dump_json(),
        *(e.model_dump_json() for e in sink.events),
    ]
    for text in exposed:
        for value in SENTINELS.values():
            assert value not in text
        assert "SENTINELA" not in text
    assert [e.key_index for e in sink.events] == [3, 3]


def test_usage_cost_becomes_decimal_and_one_event_per_call(make, sink):
    server = FakeFeatherless(completion(SMALL, cost=0.000123), 429, completion(SMALL, cost=0.0005))
    client = make(server)
    first = call(client)
    second = call(client, kind="llm.justify")
    assert first.cost_usd == Decimal("0.000123") and isinstance(first.cost_usd, Decimal)
    assert (first.tokens_in, first.tokens_out, first.model, first.key_index) == (120, 30, SMALL, 1)
    assert first.latency_ms is not None and first.latency_ms >= 0
    assert second.cost_usd == Decimal("0.0005") and second.key_index == 2
    assert [e.kind for e in sink.events] == ["llm.call", "llm.justify"]
    event = sink.events[0]
    assert (event.cost_usd, event.tokens_in, event.tokens_out, event.model) == (Decimal("0.000123"), 120, 30, SMALL)
    assert event.payload["cost_basis"] == COST_MEASURED
    assert (event.run_id, event.parent_id) == ("run-1", "evt-0")
    assert [a["outcome"] for a in sink.events[1].payload["attempts"]] == ["switch_key", "ok"]
    assert "Explique" not in json.dumps(event.payload)  # conteúdo das mensagens fica fora do rastro


def test_missing_cost_is_none_not_estimated(make, sink):
    result = call(make(FakeFeatherless(completion(SMALL, cost=None))))
    assert result.cost_usd is None
    assert sink.events[0].cost_usd is None
    assert sink.events[0].payload["cost_basis"] == COST_MISSING


def test_size_picks_model_and_sdk_does_not_retry_on_its_own(make):
    server = FakeFeatherless(completion(LARGE))
    assert call(make(server), size="large").model == LARGE
    assert server.calls[0]["model"] == LARGE
    assert make(FakeFeatherless())._sdk.max_retries == 0


def test_tool_schema_forces_function_and_parses_args(make, sink):
    server = FakeFeatherless(completion(SMALL, tool_args='{"texto": "cobre a falta de sábado"}'))
    result = call(make(server), tool_schema=TOOL)
    body = server.calls[0]["body"]
    assert body["tools"] == [{"type": "function", "function": TOOL}]
    assert body["tool_choice"] == {"type": "function", "function": {"name": TOOL["name"]}}
    assert result.tool_args == {"texto": "cobre a falta de sábado"}
    assert sink.events[0].payload["tool"] == TOOL["name"] and sink.events[0].payload["tool_args_ok"] is True


def test_invalid_tool_json_returns_none_for_caller_to_resend(make, sink):
    result = call(make(FakeFeatherless(completion(SMALL, tool_args="{nao é json"))), tool_schema=TOOL)
    assert result.tool_args is None
    assert sink.events[0].payload["tool_args_error"] == "argumentos da ferramenta não são JSON válido"


def test_tool_schema_without_name_is_programming_error(make):
    with pytest.raises(ValueError):
        call(make(FakeFeatherless()), tool_schema={"parameters": {}})


def test_fallback_model_on_cold_primary(make, settings, sink, monkeypatch):
    monkeypatch.setenv("FEATHERLESS_MODEL_SMALL_FALLBACK", SMALL_FB)
    server = FakeFeatherless(400, completion(SMALL_FB))
    result = call(make(server, Settings(_env_file=None)))
    assert [c["model"] for c in server.calls] == [SMALL, SMALL_FB]
    assert result.model == SMALL_FB
    assert sink.events[0].payload["fallback_used"] is True


def test_key_failures_do_not_try_fallback_model(make, monkeypatch):
    monkeypatch.setenv("FEATHERLESS_MODEL_SMALL_FALLBACK", SMALL_FB)
    server = FakeFeatherless(401, 401, 401)
    with pytest.raises(LLMUnavailableError):
        call(make(server, Settings(_env_file=None)))
    assert {c["model"] for c in server.calls} == {SMALL}


def test_no_keys_yields_rx12(make, monkeypatch, sink):
    for i in SENTINELS:
        monkeypatch.delenv(f"FEATHERLESS_API_KEY_{i}")
    server = FakeFeatherless()
    with pytest.raises(LLMUnavailableError) as err:
        call(make(server, Settings(_env_file=None)))
    assert "nenhuma chave" in err.value.card.reason
    assert server.calls == []
    assert [e.kind for e in sink.events] == ["exception.raised"]


def test_concurrency_units_from_settings(make, monkeypatch):
    monkeypatch.setenv("FEATHERLESS_CONCURRENCY_UNITS", "3")
    assert make(FakeFeatherless(), Settings(_env_file=None))._pool.concurrency == 3


def test_events_persist_in_sql_trace_sink_without_key_values(settings):
    engine = make_engine("sqlite://")
    init_db(engine)
    sql_sink = SqlTraceSink(engine, known_secrets=[key for _, key in settings.featherless_keys])
    client = FeatherlessClient.from_settings(
        settings,
        trace_sink=sql_sink,
        clock=FixedClock(datetime(2026, 11, 8, 9, 0)),
        http_client=httpx2.Client(transport=httpx2.MockTransport(FakeFeatherless(401, completion(SMALL), 400))),
        sleep=lambda _s: None,
    )
    call(client)
    with pytest.raises(LLMUnavailableError):
        call(client)
    events = sql_sink.list_events("run-1")
    assert [(e.kind, e.key_index) for e in events] == [("llm.call", 2), ("exception.raised", 1)]
    assert events[0].cost_usd == Decimal("0.000123")
    with engine.connect() as conn:
        dump = json.dumps([list(row) for row in conn.execute(sql("SELECT * FROM trace_event"))], default=str)
    assert "SENTINELA" not in dump


# --- foto do atestado (C7 T2, A5): partes de imagem e modelo de visão ---------------------------------------------

VISION = "modelo/visao"
IMAGE = b"\x89PNG\r\n\x1a\n" + b"PIXELS-DA-FOTO-NAO-VAZAR" * 40
IMAGE_B64 = base64.b64encode(IMAGE).decode("ascii")
PHOTO = [
    LLMMessage(role="system", content="Leia o atestado."),
    LLMMessage(role="user", content=[TextPart(text="Colaborador: Ana"), ImagePart(media_type="image/png", data=IMAGE)]),
]


def test_request_converts_parts_to_openai_format_in_memory(make):
    request = make(FakeFeatherless())._request("m", PHOTO, None)
    assert request["messages"] == [
        {"role": "system", "content": "Leia o atestado."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Colaborador: Ana"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{IMAGE_B64}"}},
            ],
        },
    ]


def test_request_keeps_plain_text_content_as_string(make):
    request = make(FakeFeatherless())._request("m", MESSAGES, None)
    assert request["messages"] == [{"role": "user", "content": "Explique a troca de turno."}]


def test_vision_model_comes_from_settings(settings, monkeypatch, make):
    assert Settings(_env_file=None).featherless_model_vision == "Qwen/Qwen3.5-9B"  # DEC-020; nunca testado com imagem
    monkeypatch.setenv("FEATHERLESS_MODEL_VISION", VISION)
    server = FakeFeatherless(completion(VISION))
    result = call(make(server, Settings(_env_file=None)), size="vision")
    assert result.model == VISION and server.calls[0]["model"] == VISION


def test_image_goes_only_to_the_provider_never_to_trace_or_log(make, sink, caplog, monkeypatch):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("FEATHERLESS_MODEL_VISION", VISION)
    server = FakeFeatherless(completion(VISION, tool_args='{"texto": "ok"}'), 400)
    client = make(server, Settings(_env_file=None))
    client.complete(size="vision", messages=PHOTO, tool_schema=TOOL, run_id="run-1", kind="track.llm.read_atestado")
    with pytest.raises(LLMUnavailableError) as err:
        client.complete(size="vision", messages=PHOTO, run_id="run-1", kind="track.llm.read_atestado")
    # controle positivo: a imagem chegou ao provedor como data URI
    sent = server.calls[0]["body"]["messages"][1]["content"][1]["image_url"]["url"]
    assert sent == f"data:image/png;base64,{IMAGE_B64}"
    exposed = [
        caplog.text,
        repr(client),
        str(err.value),
        err.value.card.model_dump_json(),
        *(e.model_dump_json() for e in sink.events),
        repr(PHOTO),
    ]
    for text in exposed:
        assert "PIXELS-DA-FOTO" not in text
        assert IMAGE_B64[:40] not in text
        assert "data:image" not in text
    # o rastro registra só o tamanho em bytes e o tipo da imagem
    ok, failed = sink.events
    assert ok.kind == "track.llm.read_atestado" and failed.kind == "exception.raised"
    assert ok.payload["images"] == [{"media_type": "image/png", "bytes": len(IMAGE)}]
    assert failed.payload["images"] == [{"media_type": "image/png", "bytes": len(IMAGE)}]


def test_text_only_calls_have_no_images_in_payload(make, sink):
    call(make(FakeFeatherless(completion(SMALL))))
    assert "images" not in sink.events[0].payload


def test_redacted_messages_describe_images_without_content():
    from escalista.llm.client import redacted_messages

    assert redacted_messages(PHOTO) == [
        {"role": "system", "content": "Leia o atestado."},
        {"role": "user", "content": ["Colaborador: Ana", f"[imagem omitida, {len(IMAGE)} bytes]"]},
    ]
