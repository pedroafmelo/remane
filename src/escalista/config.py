"""Configuração por variáveis de ambiente (`.env` ignorado pelo git). Nunca imprime o valor de uma chave (RN-08).

Chaves são `SecretStr`: `repr`, `str` e `model_dump_json` as mascaram, e `hide_input_in_errors` evita que um erro
de validação as cite. O valor só sai por `get_secret_value()`, dentro do cliente LLM. Para log, use só `summary()`.
"""

from decimal import Decimal
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore", hide_input_in_errors=True)

    # Pool de chaves da Featherless (DEC-025): a ordem é a prioridade.
    featherless_api_key_1: SecretStr | None = None
    featherless_api_key_2: SecretStr | None = None
    featherless_api_key_3: SecretStr | None = None
    featherless_api_key_4: SecretStr | None = None
    featherless_base_url: str = "https://api.featherless.ai/v1"
    featherless_model_small: str = "Qwen/Qwen3.5-9B"
    featherless_model_large: str = "google/gemma-4-31B-it"
    # Foto do atestado (C7 T2): DEC-020 escolheu este modelo para a foto, mas ele **nunca foi testado com imagem** na
    # Featherless; se não aceitar imagem, a leitura cai em RX-12 (abono provisório). Sem reserva configurada.
    featherless_model_vision: str = "Qwen/Qwen3.5-9B"
    featherless_model_small_fallback: str | None = None
    featherless_model_large_fallback: str | None = None
    featherless_concurrency_units: int | None = None
    featherless_daily_budget_usd: Decimal | None = None

    # App (arquitetura.md, seção 11)
    demo_mode: bool = False
    session_secret: SecretStr | None = None

    # Tracing (Langfuse local)
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str | None = None

    # Banco e SPA
    database_url: str = "sqlite:///./var/escalista.db"
    web_dist_dir: str = "web/dist"

    @property
    def featherless_keys(self) -> list[tuple[int, SecretStr]]:
        """Chaves preenchidas, em ordem de prioridade, mantendo o índice (a chave 3 continua sendo a 3)."""
        slots = [
            self.featherless_api_key_1,
            self.featherless_api_key_2,
            self.featherless_api_key_3,
            self.featherless_api_key_4,
        ]
        return [(i, key) for i, key in enumerate(slots, start=1) if key is not None]

    def summary(self) -> dict[str, Any]:
        """Única visão da configuração que pode ir a log ou a `/health`: índices e flags, nunca valores."""
        return {
            "featherless_keys": [i for i, _ in self.featherless_keys],
            "demo_mode": self.demo_mode,
            "langfuse": bool(self.langfuse_base_url),
        }
