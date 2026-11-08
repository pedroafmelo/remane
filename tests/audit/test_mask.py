"""Máscara do `payload` do rastro (RN-06, RN-08): o valor de uma chave nunca sai, nem aninhado, nem em texto livre."""

import json
from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import BaseModel, SecretStr

from escalista.audit.mask import REDACTED, Masker, redact, redact_payload, redact_text

SENTINEL = "rc_SENTINELA_NAO_VAZAR"


def dumped(value) -> str:
    return json.dumps(value, ensure_ascii=False)


# --- campos com nome sensível -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "api_key",
        "apiKey",
        "API_KEY",
        "x-api-key",
        "apikey",
        "featherless_api_key_1",
        "authorization",
        "Authorization",
        "proxy-authorization",
        "secret",
        "client_secret",
        "session_secret",
        "langfuse_secret_key",
        "password",
        "passwd",
        "token",
        "access_token",
        "refreshToken",
        "private_key",
        "cookie",
        "credentials",
        "senha",
        "segredo_cliente",
    ],
)
def test_sensitive_field_names_are_redacted(name):
    out = redact_payload({name: "valor-qualquer-123"})
    assert out == {name: REDACTED}


@pytest.mark.parametrize(
    "name",
    ["key_index", "tokens_in", "tokens_out", "max_tokens", "total_tokens", "featherless_keys", "rule_ref", "author"],
)
def test_harmless_field_names_are_kept(name):
    assert redact_payload({name: 3}) == {name: 3}


def test_sensitive_field_redacts_whole_subtree_but_keeps_none():
    out = redact_payload({"authorization": {"scheme": "Bearer", "value": "abc"}, "api_key": None})
    assert out == {"authorization": REDACTED, "api_key": None}


# --- padrões de valor em texto livre ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        f"falhou com a chave {SENTINEL} agora",
        f"Authorization: Bearer {SENTINEL}",
        f"bearer {SENTINEL}",
        f"https://api.exemplo/v1?api_key={SENTINEL}&x=1",
        f'{{"api_key": "{SENTINEL}"}}',
        f"token={SENTINEL}",
        f"password: {SENTINEL}",
        f"senha={SENTINEL}",
        f"https://usuario:{SENTINEL}@host.exemplo/db",
    ],
)
def test_sentinel_in_free_text_is_removed(text):
    out = redact_text(text)
    assert SENTINEL not in out
    assert "SENTINELA" not in out
    assert REDACTED in out


@pytest.mark.parametrize(
    "secret",
    [
        "rc_0123456789abcdef",
        "sk-proj-AbCdEf0123456789",
        "sk-lf-1234abcd-5678",
        "pk-lf-1234abcd-5678",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJh",
        "ghp_" + "a1" * 12,
        "AKIA" + "ABCDEFGHIJKLMNOP",
    ],
)
def test_known_key_formats_are_removed(secret):
    assert secret not in redact_text(f"valor: {secret} fim")


def test_text_without_secrets_is_unchanged():
    text = "Escala da loja 3 respeita RX-12 e a regra lei/ec-141 §2; 50 tokens; custo 0.000120 USD; src_x."
    assert redact_text(text) == text


def test_literal_known_secrets_are_removed_whatever_the_format():
    weird = "zz9-chave-sem-prefixo-conhecido"
    out = redact_payload({"msg": f"usei {weird}", "lista": [weird]}, known_secrets=[SecretStr(weird)])
    assert weird not in dumped(out)


def test_short_known_secrets_are_ignored_to_avoid_blanking_text():
    assert redact_text("abc def", known_secrets=["a"]) == "abc def"


# --- estrutura ----------------------------------------------------------------------------------------------------


def test_recurses_into_dicts_lists_and_tuples_and_dict_keys():
    payload = {
        "nivel1": {"nivel2": [{"headers": {"Authorization": f"Bearer {SENTINEL}"}}, (f"x {SENTINEL}",)]},
        f"chave {SENTINEL}": 1,
    }
    out = redact_payload(payload)
    assert SENTINEL not in dumped(out)
    assert out["nivel1"]["nivel2"][0]["headers"]["Authorization"] == REDACTED


def test_output_is_json_serializable_and_input_is_not_mutated():
    class Modelo(BaseModel):
        api_key: str
        n: int

    payload = {
        "custo": Decimal("0.000120"),
        "quando": datetime(2026, 11, 7, 9, 30),
        "conjunto": {"b"},
        "modelo": Modelo(api_key=SENTINEL, n=2),
        "erro": RuntimeError(f"401 para {SENTINEL}"),
        "segredo": SecretStr(SENTINEL),
        "bytes": SENTINEL.encode(),
    }
    original = dict(payload)
    out = redact_payload(payload)
    text = dumped(out)
    assert SENTINEL not in text and "SENTINELA" not in text
    assert out["custo"] == "0.000120"
    assert out["quando"] == "2026-11-07T09:30:00"
    assert out["conjunto"] == ["b"]
    assert out["modelo"] == {"api_key": REDACTED, "n": 2}
    assert payload == original


def test_scalars_pass_through():
    assert redact(None) is None
    assert redact(True) is True
    assert redact(7) == 7
    assert redact(1.5) == 1.5


def test_deep_nesting_is_truncated_not_crashing():
    payload: dict = {}
    node = payload
    for _ in range(200):
        node["x"] = {}
        node = node["x"]
    node["x"] = SENTINEL
    assert SENTINEL not in dumped(redact_payload(payload))


def test_cycles_do_not_hang():
    a: list = []
    a.append(a)
    redact_payload({"a": a})


def test_masker_repr_never_shows_known_secrets():
    masker = Masker([SecretStr(SENTINEL), "outra-chave-literal"])
    assert SENTINEL not in repr(masker) and "outra-chave-literal" not in repr(masker)
    assert masker.text("outra-chave-literal") == REDACTED
