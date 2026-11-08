"""Script de fumaça com transporte HTTP falso: sem rede, sem `.env`, chaves sentinela que nunca podem vazar."""

import json
import logging

import httpx2
import pytest

from escalista.config import Settings
from escalista.llm import smoke

SENTINELS = {1: "rc_SENTINELA_NAO_VAZAR_1", 2: "", 3: "rc_SENTINELA_NAO_VAZAR_3"}
BY_VALUE = {v: k for k, v in SENTINELS.items() if v}
SMALL, LARGE = "modelo/pequeno", "modelo/grande"


def tool_completion(model: str, *, cost: float | None = 0.000123, args: str | None = None) -> dict:
    args = args if args is not None else json.dumps({"resposta": "Recife", "confianca": 95})
    usage: dict = {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60}
    if cost is not None:
        usage["cost"] = cost
    return {
        "id": "cmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "c1", "type": "function", "function": {"name": "responder", "arguments": args}}
                    ],
                },
            }
        ],
        "usage": usage,
    }


class FakeFeatherless:
    """`behavior`: índice da chave -> status de erro (int) ou função modelo -> corpo de sucesso."""

    def __init__(self, behavior) -> None:
        self.behavior = behavior
        self.calls: list[tuple[int | None, str]] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        key = request.headers["authorization"].removeprefix("Bearer ")
        index = BY_VALUE.get(key)
        model = json.loads(request.content)["model"]
        self.calls.append((index, model))
        step = self.behavior[index]
        if isinstance(step, int):
            return httpx2.Response(step, json={"error": {"message": f"erro {step} para a chave {key}"}})
        return httpx2.Response(200, json=step(model))

    @property
    def keys(self) -> list[int | None]:
        return [i for i, _ in self.calls]


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


def run_smoke(settings, behavior, argv=()):
    server = FakeFeatherless(behavior)
    code = smoke.run(
        list(argv),
        settings=settings,
        http_client=httpx2.Client(transport=httpx2.MockTransport(server)),
        sleep=lambda _s: None,
    )
    return code, server


def assert_no_secret(*texts: str) -> None:
    for text in texts:
        assert "SENTINELA" not in text
        for value in SENTINELS.values():
            assert not value or value not in text


def test_one_line_per_key_with_right_index(settings, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    code, server = run_smoke(settings, {1: 401, 3: tool_completion})
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    key_lines = [line for line in lines if line.startswith("chave ")]
    assert code == 0
    assert len(key_lines) == 2 and server.calls == [(1, SMALL), (3, SMALL)]  # a chave 2 vazia não é chamada
    assert key_lines[0].startswith(f"chave 1 | {SMALL} | falha (HTTP 401) | custo não informado | ")
    assert key_lines[0].endswith(" ms | ferramenta: não")
    assert key_lines[1].startswith(f"chave 3 | {SMALL} | ok | custo US$ 0.000123 | ")
    assert key_lines[1].endswith(" ms | ferramenta: sim")
    assert not any(line.startswith("chave 2") for line in lines)
    assert lines[-1].startswith(
        "resumo: 1 de 2 chamadas ok | chaves ok: [3] de [1, 3] | custo total medido US$ 0.000123"
    )
    assert_no_secret(captured.out, captured.err, caplog.text)


def test_keys_are_isolated_no_failover(settings, capsys):
    # a chave 1 falha com 401, mas o script não pode trocar para a 3 dentro da chamada da 1
    _, server = run_smoke(settings, {1: 401, 3: 401})
    assert server.keys == [1, 3]
    capsys.readouterr()


def test_large_flag_adds_the_large_model_per_key(settings, capsys):
    code, server = run_smoke(settings, {1: tool_completion, 3: tool_completion}, ["--large"])
    out = capsys.readouterr().out
    assert code == 0
    assert server.calls == [(1, SMALL), (1, LARGE), (3, SMALL), (3, LARGE)]
    assert out.count("ferramenta: sim") == 4
    assert "resumo: 4 de 4 chamadas ok | chaves ok: [1, 3] de [1, 3] | custo total medido US$ 0.000492" in out


def test_missing_cost_and_tool_are_reported_honestly(settings, capsys):
    bad_tool = lambda model: tool_completion(model, cost=None, args='{"resposta": "Recife"}')  # noqa: E731
    code, _ = run_smoke(settings, {1: bad_tool, 3: 429})
    out = capsys.readouterr().out
    assert code == 0
    assert f"chave 1 | {SMALL} | ok | custo não informado | " in out
    assert "ferramenta: não" in out.splitlines()[0]
    assert "chave 3 | modelo/pequeno | falha (HTTP 429)" in out
    assert "1 chamada(s) ok sem custo informado" in out


def test_exit_code_nonzero_when_all_fail(settings, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    code, server = run_smoke(settings, {1: 401, 3: 402})
    captured = capsys.readouterr()
    assert code == 1
    assert "falha (HTTP 401)" in captured.out and "falha (HTTP 402)" in captured.out
    assert "resumo: 0 de 2 chamadas ok | chaves ok: nenhuma de [1, 3]" in captured.out
    assert server.keys == [1, 3]
    assert_no_secret(captured.out, captured.err, caplog.text)


def test_exit_code_nonzero_without_keys(monkeypatch, capsys):
    for i in (1, 2, 3, 4):
        monkeypatch.delenv(f"FEATHERLESS_API_KEY_{i}", raising=False)
    code, server = run_smoke(Settings(_env_file=None), {})
    assert code == 1 and server.calls == []
    assert "nenhuma chave" in capsys.readouterr().out


def test_dry_run_does_not_touch_the_transport(settings, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    code, server = run_smoke(settings, {1: tool_completion, 3: tool_completion}, ["--dry-run"])
    captured = capsys.readouterr()
    assert code == 0 and server.calls == []
    assert "[1, 3]" in captured.out
    assert SMALL in captured.out and LARGE in captured.out
    assert_no_secret(captured.out, captured.err, caplog.text)


def test_message_content_is_never_printed(settings, capsys):
    run_smoke(settings, {1: tool_completion, 3: tool_completion})
    out = capsys.readouterr().out
    assert "Pernambuco" not in out and "Recife" not in out
