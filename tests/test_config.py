"""Configuração: lê o pool de chaves e nunca expõe o valor de uma chave (RN-08, DEC-025).

Sempre `Settings(_env_file=None)` com `monkeypatch`: estes testes nunca leem o `.env` real.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from escalista.config import Settings

SENTINEL = "rc_SENTINELA_NAO_VAZAR"
ALL_VARS = [
    *(f"FEATHERLESS_API_KEY_{i}" for i in range(1, 5)),
    "FEATHERLESS_BASE_URL", "FEATHERLESS_MODEL_SMALL", "FEATHERLESS_MODEL_LARGE",
    "FEATHERLESS_MODEL_SMALL_FALLBACK", "FEATHERLESS_MODEL_LARGE_FALLBACK",
    "FEATHERLESS_CONCURRENCY_UNITS", "FEATHERLESS_DAILY_BUDGET_USD", "DEMO_MODE", "SESSION_SECRET",
    "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "DATABASE_URL", "WEB_DIST_DIR",
]  # fmt: skip


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ALL_VARS:
        monkeypatch.delenv(name, raising=False)


def make(monkeypatch, **env) -> Settings:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_defaults_without_any_variable(monkeypatch):
    s = make(monkeypatch)
    assert s.featherless_keys == []
    assert s.demo_mode is False
    assert s.featherless_base_url == "https://api.featherless.ai/v1"
    assert s.featherless_model_small == "Qwen/Qwen3.5-9B"
    assert s.featherless_model_large == "google/gemma-4-31B-it"
    assert s.database_url == "sqlite:///./var/escalista.db"
    assert s.web_dist_dir == "web/dist"


def test_keys_are_ordered_and_keep_their_index_when_one_is_empty(monkeypatch):
    s = make(monkeypatch, FEATHERLESS_API_KEY_1="rc_a", FEATHERLESS_API_KEY_2="", FEATHERLESS_API_KEY_3="rc_c")
    assert [(i, k.get_secret_value()) for i, k in s.featherless_keys] == [(1, "rc_a"), (3, "rc_c")]


def test_empty_values_fall_back_to_defaults_and_none(monkeypatch):
    s = make(monkeypatch, FEATHERLESS_MODEL_SMALL="", FEATHERLESS_DAILY_BUDGET_USD="", FEATHERLESS_CONCURRENCY_UNITS="")
    assert s.featherless_model_small == "Qwen/Qwen3.5-9B"
    assert s.featherless_daily_budget_usd is None and s.featherless_concurrency_units is None


def test_numeric_fields_are_typed(monkeypatch):
    s = make(monkeypatch, FEATHERLESS_DAILY_BUDGET_USD="2.5", FEATHERLESS_CONCURRENCY_UNITS="4", DEMO_MODE="1")
    assert s.featherless_daily_budget_usd == Decimal("2.5") and s.featherless_concurrency_units == 4
    assert s.demo_mode is True


def secrets_env(monkeypatch, **extra):
    env = {f"FEATHERLESS_API_KEY_{i}": f"{SENTINEL}_{i}" for i in range(1, 5)}
    env |= {"SESSION_SECRET": f"{SENTINEL}_sessao", "LANGFUSE_SECRET_KEY": f"{SENTINEL}_lf"}
    return make(monkeypatch, **env, **extra)


def test_secret_values_never_appear_in_repr_str_json_or_summary(monkeypatch):
    s = secrets_env(monkeypatch)
    shown = [repr(s), str(s), s.model_dump_json(), repr(s.model_dump()), str(s.summary()), repr(s.featherless_keys)]
    for text in shown:
        assert SENTINEL not in text
    assert s.summary()["featherless_keys"] == [1, 2, 3, 4]
    assert s.featherless_keys[1][1].get_secret_value() == f"{SENTINEL}_2"  # o valor só sai por get_secret_value()


def test_validation_error_does_not_leak_secrets(monkeypatch):
    with pytest.raises(ValidationError) as excinfo:
        secrets_env(monkeypatch, FEATHERLESS_CONCURRENCY_UNITS="abc")
    assert SENTINEL not in str(excinfo.value) and SENTINEL not in repr(excinfo.value)
    assert "abc" not in str(excinfo.value)  # hide_input_in_errors
