import logging

from fastapi.testclient import TestClient

from escalista.api.app import create_app
from escalista.config import Settings

SENTINEL = "rc_SENTINELA_NAO_VAZAR"


def make_settings(tmp_path, **extra) -> Settings:
    return Settings(
        _env_file=None, database_url=f"sqlite:///{tmp_path}/app.db", web_dist_dir=str(tmp_path / "dist"), **extra
    )


def test_health_ok(tmp_path):
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["db"] == "ok" and "version" in body


def test_health_and_startup_log_never_show_key_values(tmp_path, caplog):
    keys = {f"featherless_api_key_{i}": f"{SENTINEL}_{i}" for i in range(1, 5)}
    with caplog.at_level(logging.DEBUG):
        client = TestClient(create_app(make_settings(tmp_path, session_secret=f"{SENTINEL}_s", **keys)))
        text = client.get("/health").text
    assert SENTINEL not in text and SENTINEL not in caplog.text
    assert client.get("/health").json()["featherless_keys"] == [1, 2, 3, 4]
