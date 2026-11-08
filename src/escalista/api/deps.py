"""Dependências FastAPI de acesso: quem está na sessão e se o papel dele pode chamar a rota (RF-30, DEC-017).

A proteção é aqui, na rota; a SPA só esconde botões. Cada rota protegida entra na matriz de `tests/api/test_access.py`.
"""

from collections.abc import Callable

from fastapi import HTTPException, Request, status

from escalista.api.accounts import Account, account_by_id
from escalista.domain.contracts import Role

SESSION_ACCOUNT_KEY = "account_id"


def current_account(request: Request) -> Account:
    """A conta da sessão. Sem sessão, cookie adulterado ou conta desconhecida: 401."""
    account = account_by_id(request.session.get(SESSION_ACCOUNT_KEY))
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sessão ausente ou inválida")
    return account


def require_role(*roles: Role) -> Callable[[Request], Account]:
    """Dependência que exige sessão (401) com um dos `roles` (403). Uso: `Depends(require_role(Role.GESTOR))`."""
    if not roles:
        raise ValueError("require_role precisa de ao menos um papel")
    allowed = frozenset(roles)

    def dependency(request: Request) -> Account:
        account = current_account(request)
        if account.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="papel sem acesso a esta rota")
        return account

    return dependency
