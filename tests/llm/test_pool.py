"""`KeyPool`: failover em ordem, novas tentativas na mesma chave e semáforo, sem rede (erros do SDK `openai`)."""

import threading
import time

import httpx2
import openai
import pytest
from pydantic import SecretStr

from escalista.llm.pool import DEFAULT_CONCURRENCY, KeyPool, PoolExhaustedError

KEYS = [(1, SecretStr("rc_SENTINELA_NAO_VAZAR_1")), (2, SecretStr("rc_SENTINELA_NAO_VAZAR_2"))]
REQUEST = httpx2.Request("POST", "https://featherless.test/v1/chat/completions")


def status_error(status: int) -> openai.APIStatusError:
    response = httpx2.Response(status, request=REQUEST, json={"error": {"message": "falha"}})
    return openai.APIStatusError("falha", response=response, body=None)


def scripted(*steps):
    """`send` falso: cada passo é um status (levanta o erro do SDK) ou "ok"."""
    queue = list(steps)
    calls: list[int] = []

    def send(index: int, key: SecretStr):
        calls.append(index)
        step = queue.pop(0)
        if step == "ok":
            return f"resposta da chave {index}"
        if step == "conn":
            raise openai.APIConnectionError(request=REQUEST)
        raise status_error(step)

    return send, calls


def make_pool(**kw) -> KeyPool:
    kw.setdefault("sleep", lambda _s: None)
    return KeyPool(KEYS, **kw)


def test_switch_statuses_go_to_next_key_in_order():
    for status in (401, 402, 403, 429):
        send, calls = scripted(status, "ok")
        result, index, attempts = make_pool().run(send)
        assert (result, index, calls) == ("resposta da chave 2", 2, [1, 2])
        assert [a.outcome for a in attempts] == ["switch_key", "ok"]


def test_transient_retries_same_key_three_times_with_backoff_then_fails():
    sleeps: list[float] = []
    send, calls = scripted(503, 503, 503, 503)
    with pytest.raises(PoolExhaustedError) as err:
        make_pool(sleep=sleeps.append, backoff_s=(0.1, 0.2, 0.4)).run(send)
    assert calls == [1, 1, 1, 1]
    assert sleeps == [0.1, 0.2, 0.4]
    assert err.value.kind == "model"
    assert "chave 1: 503" in err.value.reason and "× 4" in err.value.reason


def test_connection_error_is_retried_on_same_key():
    send, calls = scripted("conn", "ok")
    _, index, _ = make_pool().run(send)
    assert (index, calls) == (1, [1, 1])


def test_400_fails_without_switch_or_retry():
    send, calls = scripted(400)
    with pytest.raises(PoolExhaustedError) as err:
        make_pool().run(send)
    assert calls == [1]
    assert err.value.kind == "model"


def test_other_4xx_is_request_error():
    send, calls = scripted(422)
    with pytest.raises(PoolExhaustedError) as err:
        make_pool().run(send)
    assert (calls, err.value.kind) == ([1], "request")


def test_all_keys_rejected_is_keys_failure():
    send, calls = scripted(401, 429)
    with pytest.raises(PoolExhaustedError) as err:
        make_pool().run(send)
    assert calls == [1, 2]
    assert err.value.kind == "keys"
    assert err.value.reason == "chave 1: 401 (chave não reconhecida); chave 2: 429 (limite de concorrência da conta)"


def test_empty_pool_fails_without_calling():
    with pytest.raises(PoolExhaustedError) as err:
        KeyPool([]).run(lambda i, k: pytest.fail("não devia chamar"))
    assert err.value.kind == "keys"


def test_non_sdk_exception_propagates():
    def send(index, key):
        raise RuntimeError("bug")

    with pytest.raises(RuntimeError):
        make_pool().run(send)


def test_default_concurrency_and_repr_without_values():
    pool = KeyPool(KEYS)
    assert pool.concurrency == DEFAULT_CONCURRENCY
    assert pool.indices == [1, 2]
    assert "SENTINELA" not in repr(pool)
    assert pool.redact("eco: rc_SENTINELA_NAO_VAZAR_2") == "eco: [REDACTED]"


def test_semaphore_limits_concurrency():
    pool = make_pool(concurrency=2)
    lock = threading.Lock()
    in_flight = 0
    peak = 0

    def send(index, key):
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        time.sleep(0.02)
        with lock:
            in_flight -= 1
        return "ok"

    threads = [threading.Thread(target=pool.run, args=(send,)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert 1 <= peak <= 2


def test_full_semaphore_times_out_as_busy():
    pool = make_pool(concurrency=1, acquire_timeout_s=0.01)
    entered, release = threading.Event(), threading.Event()

    def slow(index, key):
        entered.set()
        release.wait(5)
        return "ok"

    holder = threading.Thread(target=pool.run, args=(slow,))
    holder.start()
    entered.wait(5)
    try:
        with pytest.raises(PoolExhaustedError) as err:
            pool.run(lambda i, k: "ok")
        assert err.value.kind == "busy"
    finally:
        release.set()
        holder.join()


def test_duplicate_indices_rejected():
    with pytest.raises(ValueError):
        KeyPool([KEYS[0], KEYS[0]])
