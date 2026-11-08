"""Acesso: sessão por cookie assinado, login de demo e matriz rota × papel (RF-29, RF-30, DEC-017; arquitetura, 11).

A matriz `ROUTES` é a fonte única de quem pode chamar cada rota protegida. Para proteger uma rota nova
(C2: `/api/runs...`, `/api/schedules/published`, `/api/demo/files/{nome}`), acrescente uma linha: o teste
parametrizado prova 401 sem sessão, 403 com cada papel não permitido e sucesso com cada papel permitido.

Sempre `Settings(_env_file=None)` com `monkeypatch`: estes testes nunca leem o `.env` real.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from escalista.api.accounts import SEEDED_ACCOUNTS
from escalista.api.app import create_app
from escalista.api.auth import SESSION_COOKIE
from escalista.api.deps import require_role
from escalista.config import Settings
from escalista.domain.contracts import Role

SENTINEL = "rc_SENTINELA_NAO_VAZAR"
ALL_ROLES = frozenset(Role)


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    roles: frozenset[Role]
    ok_status: int = 200
    request: dict[str, Any] = field(default_factory=dict)  # json, files, data... para o caso de sucesso

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


ROUTES: list[Route] = [
    Route("GET", "/api/me", ALL_ROLES),
]

CASES_FORBIDDEN = [(r, role) for r in ROUTES for role in Role if role not in r.roles]
CASES_ALLOWED = [(r, role) for r in ROUTES for role in r.roles]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DEMO_MODE", "SESSION_SECRET", "DATABASE_URL", "WEB_DIST_DIR"):
        monkeypatch.delenv(name, raising=False)


def make_client(tmp_path, *, demo_mode: bool = True, secret: str | None = f"{SENTINEL}_sessao") -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/app.db",
        web_dist_dir=str(tmp_path / "dist"),
        demo_mode=demo_mode,
        session_secret=secret,
    )
    return TestClient(create_app(settings))


def login(client: TestClient, role: Role) -> None:
    response = client.post(f"/auth/demo/{role.value}")
    assert response.status_code == 200, response.text


def call(client: TestClient, route: Route, **request) -> Any:
    return client.request(route.method, route.path, **request)


# --- matriz rota × papel ---


@pytest.mark.parametrize("route", ROUTES, ids=str)
def test_without_session_is_401(tmp_path, route):
    assert call(make_client(tmp_path), route).status_code == 401


@pytest.mark.parametrize(("route", "role"), CASES_FORBIDDEN, ids=lambda x: str(x))
def test_wrong_role_is_403(tmp_path, route, role):
    client = make_client(tmp_path)
    login(client, role)
    assert call(client, route).status_code == 403


@pytest.mark.parametrize(("route", "role"), CASES_ALLOWED, ids=lambda x: str(x))
def test_allowed_role_succeeds(tmp_path, route, role):
    client = make_client(tmp_path)
    login(client, role)
    assert call(client, route, **route.request).status_code == route.ok_status


def test_every_api_route_is_in_the_matrix(tmp_path):
    """Rota nova em `/api` sem linha na matriz reprova: ninguém esquece de declarar quem pode chamá-la."""
    app = make_client(tmp_path).app
    declared = {(r.method, r.path) for r in ROUTES}
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/"):
            for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}:
                assert (method, path) in declared, f"{method} {path} sem linha em ROUTES"


@pytest.mark.parametrize("role", list(Role), ids=str)
def test_require_role_on_a_gerente_only_route(tmp_path, role):
    """Enquanto a matriz só tem `/api/me` (todos os papéis), o 403 é provado numa rota de teste só do gerente."""
    client = make_client(tmp_path)
    client.app.add_api_route("/probe/gerente", lambda: {"ok": True}, dependencies=[Depends(require_role(Role.GERENTE))])
    assert client.get("/probe/gerente").status_code == 401
    login(client, role)
    assert client.get("/probe/gerente").status_code == (200 if role == Role.GERENTE else 403)


def test_require_role_needs_at_least_one_role():
    with pytest.raises(ValueError):
        require_role()


# --- login de demo, /api/me e logout ---


def test_seeded_accounts_cover_the_three_roles_and_are_fictitious():
    assert {a.role for a in SEEDED_ACCOUNTS} == ALL_ROLES
    assert all("fictíci" in a.name.lower() for a in SEEDED_ACCOUNTS)


@pytest.mark.parametrize("role", list(Role), ids=str)
def test_demo_login_creates_session_as_seeded_account(tmp_path, role):
    client = make_client(tmp_path)
    response = client.post(f"/auth/demo/{role.value}")
    assert response.status_code == 200
    account = next(a for a in SEEDED_ACCOUNTS if a.role == role)
    expected = {"id": account.id, "nome": account.name, "papel": role.value}
    assert response.json() == expected
    assert client.get("/api/me").json() == expected


def test_demo_login_is_404_when_demo_mode_is_off(tmp_path):
    client = make_client(tmp_path, demo_mode=False)
    for role in Role:
        response = client.post(f"/auth/demo/{role.value}")
        assert response.status_code == 404, role
        assert SESSION_COOKIE not in response.cookies
    assert client.get("/api/me").status_code == 401


def test_demo_login_with_unknown_role_is_404(tmp_path):
    client = make_client(tmp_path)
    assert client.post("/auth/demo/admin").status_code == 404
    assert client.get("/api/me").status_code == 401


def test_session_cookie_is_httponly_and_samesite_lax(tmp_path):
    response = make_client(tmp_path).post("/auth/demo/gerente")
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie


def test_logout_ends_the_session(tmp_path):
    client = make_client(tmp_path)
    login(client, Role.GERENTE)
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/api/me").status_code == 401
    assert client.post("/auth/logout").status_code == 204  # idempotente, sem sessão também


def test_tampered_cookie_is_401(tmp_path):
    client = make_client(tmp_path)
    login(client, Role.COLABORADOR)
    value = client.cookies[SESSION_COOKIE]
    payload, rest = value.split(".", 1)
    forged = make_client(tmp_path)
    forged.cookies.set(SESSION_COOKIE, payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB") + "." + rest)
    assert forged.get("/api/me").status_code == 401


def test_cookie_signed_with_another_secret_is_401(tmp_path):
    import base64
    import json

    payload = base64.b64encode(json.dumps({"account_id": SEEDED_ACCOUNTS[0].id}).encode())
    forged_value = TimestampSigner("outro-segredo").sign(payload).decode()
    client = make_client(tmp_path)
    client.cookies.set(SESSION_COOKIE, forged_value)
    assert client.get("/api/me").status_code == 401


def test_me_and_cookie_never_carry_the_secret(tmp_path, caplog):
    with caplog.at_level(logging.DEBUG):
        client = make_client(tmp_path)
        login_response = client.post("/auth/demo/gerente")
        me = client.get("/api/me")
    assert set(me.json()) == {"id", "nome", "papel"}
    for text in (me.text, login_response.text, login_response.headers["set-cookie"], caplog.text):
        assert SENTINEL not in text


def test_without_configured_secret_sessions_still_work(tmp_path):
    """Sem `SESSION_SECRET`, o app gera um segredo efêmero (sessões caem no restart) em vez de assinar com um fixo."""
    client = make_client(tmp_path, secret=None)
    login(client, Role.GERENTE)
    assert client.get("/api/me").json()["papel"] == "gerente"
    other = make_client(tmp_path, secret=None)
    other.cookies.set(SESSION_COOKIE, client.cookies[SESSION_COOKIE])
    assert other.get("/api/me").status_code == 401
