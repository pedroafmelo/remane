"""Contas semeadas da demo (RF-29, arquitetura seção 11): uma por papel, todas fictícias.

Na fatia (C5) ficam em código, sem banco e sem senha: só o login de demo (`POST /auth/demo/{papel}`) as usa.
Contas com senha (`hashlib.scrypt`) e persistência entram em camada posterior.
"""

from dataclasses import dataclass

from escalista.domain.contracts import Role


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    role: Role


SEEDED_ACCOUNTS: tuple[Account, ...] = (
    Account(id="demo-gestor", name="Gestora Fictícia (demo)", role=Role.GESTOR),
    Account(id="demo-colaborador", name="Colaboradora Fictícia (demo)", role=Role.COLABORADOR),
)

_BY_ID = {a.id: a for a in SEEDED_ACCOUNTS}
_BY_ROLE = {a.role: a for a in SEEDED_ACCOUNTS}


def account_by_id(account_id: object) -> Account | None:
    return _BY_ID.get(account_id) if isinstance(account_id, str) else None


def demo_account_for(role: Role) -> Account:
    return _BY_ROLE[role]
