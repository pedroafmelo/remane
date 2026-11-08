"""Sessão por cookie assinado e rotas de acesso (RF-29, RF-30, arquitetura seção 11).

A sessão é o `SessionMiddleware` do Starlette: JSON em base64 assinado com `itsdangerous` (`TimestampSigner`), cookie
`HttpOnly` e `SameSite=Lax`. Só guarda o id da conta. O segredo vem de `Settings.session_secret` e nunca é logado;
sem ele, o app gera um segredo efêmero (as sessões caem a cada reinício).
"""

import logging
import secrets

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from escalista.api.accounts import Account, demo_account_for
from escalista.api.deps import SESSION_ACCOUNT_KEY, require_role
from escalista.config import Settings
from escalista.domain.contracts import Role

log = logging.getLogger("escalista")

SESSION_COOKIE = "escalista_session"
SESSION_MAX_AGE_S = 8 * 60 * 60


class Me(BaseModel):
    id: str
    nome: str
    papel: Role

    @classmethod
    def of(cls, account: Account) -> "Me":
        return cls(id=account.id, nome=account.name, papel=account.role)


def install_auth(app: FastAPI, settings: Settings) -> None:
    """Liga o middleware de sessão e as rotas de acesso ao app."""
    if settings.session_secret is not None:
        secret = settings.session_secret.get_secret_value()
    else:
        secret = secrets.token_urlsafe(32)
        log.warning("SESSION_SECRET ausente: usando segredo efêmero; as sessões caem a cada reinício")
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie=SESSION_COOKIE,
        max_age=SESSION_MAX_AGE_S,
        same_site="lax",
        https_only=False,  # execução local por http (DEC-034); ligar ao hospedar com https
    )
    app.include_router(_router(settings))


def _router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/demo/{papel}", response_model=Me)
    def demo_login(papel: str, request: Request) -> Me:
        """Cria sessão como a conta semeada do papel. Só com `DEMO_MODE=1`; senão, 404 (a rota "não existe")."""
        if not settings.demo_mode or papel not in Role._value2member_map_:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        account = demo_account_for(Role(papel))
        request.session.clear()
        request.session[SESSION_ACCOUNT_KEY] = account.id
        return Me.of(account)

    @router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request) -> Response:
        request.session.clear()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/api/me", response_model=Me)
    def me(account: Account = Depends(require_role(*Role))) -> Me:  # noqa: B008
        return Me.of(account)

    return router
