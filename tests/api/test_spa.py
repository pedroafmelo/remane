import pytest
from fastapi.testclient import TestClient

from escalista.api.app import create_app
from escalista.config import Settings


@pytest.fixture
def dist(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html><body>Escalista · dados sintéticos</body></html>", encoding="utf-8")
    (root / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (root / "favicon.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("fora do dist", encoding="utf-8")
    return root


def client_for(tmp_path, dist_dir) -> TestClient:
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/app.db", web_dist_dir=str(dist_dir))
    return TestClient(create_app(settings))


def test_root_and_client_routes_serve_index(tmp_path, dist):
    client = client_for(tmp_path, dist)
    for path in ("/", "/gerente", "/gerente/escala/42"):
        response = client.get(path)
        assert response.status_code == 200 and "dados sintéticos" in response.text, path


def test_assets_and_root_files_are_served(tmp_path, dist):
    client = client_for(tmp_path, dist)
    assert client.get("/assets/app.js").text == "console.log('ok')"
    assert client.get("/favicon.svg").status_code == 200


def test_health_still_wins_over_the_spa_fallback(tmp_path, dist):
    assert client_for(tmp_path, dist).get("/health").json()["status"] == "ok"


def test_unknown_api_path_is_a_json_404(tmp_path, dist):
    response = client_for(tmp_path, dist).get("/api/nao-existe")
    assert response.status_code == 404 and response.headers["content-type"].startswith("application/json")


def test_path_traversal_does_not_leave_the_dist(tmp_path, dist):
    client = client_for(tmp_path, dist)
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt"):
        assert "fora do dist" not in client.get(path).text, path


def test_without_build_the_api_still_works_and_root_is_404(tmp_path):
    client = client_for(tmp_path, tmp_path / "nao-existe")
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 404
