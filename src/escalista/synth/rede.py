"""Rede fictícia: 3 lojas e 60 pessoas (plano da C5, seção 4, D2). Tudo sintético."""

from __future__ import annotations

import random
from datetime import date, time
from decimal import Decimal

from escalista.domain.schedule import Employee, Store

SEMANA_INICIO = date(2027, 1, 11)  # segunda-feira da semana de referência
CONTRATO_HORAS = 44  # regime antigo, de onde vem a escala atual
LOJAS = (
    ("L1", "Loja Sintética Centro"),
    ("L2", "Loja Sintética Norte"),
    ("L3", "Loja Sintética Sul"),
)
PESSOAS_POR_LOJA = 20
# cargo, salário-hora fictício, peso no sorteio
CARGOS: tuple[tuple[str, Decimal, int], ...] = (
    ("Atendente", Decimal("11.50"), 10),
    ("Caixa", Decimal("12.20"), 5),
    ("Repositor", Decimal("11.80"), 3),
    ("Estoquista", Decimal("12.40"), 2),
)
PRIMEIROS = (
    "Ana",
    "Bruno",
    "Carla",
    "Diego",
    "Elisa",
    "Fábio",
    "Gabriela",
    "Hugo",
    "Iara",
    "João",
    "Karina",
    "Lucas",
    "Mariana",
    "Nelson",
    "Olívia",
    "Paulo",
    "Quitéria",
    "Rafael",
    "Sílvia",
    "Tiago",
    "Úrsula",
    "Vitor",
    "Wagner",
    "Yasmin",
    "Zé",
)
SOBRENOMES = (
    "Almeida",
    "Barros",
    "Cardoso",
    "Dantas",
    "Esteves",
    "Freitas",
    "Galvão",
    "Horta",
    "Ivo",
    "Junqueira",
    "Lacerda",
    "Monteiro",
    "Nogueira",
    "Oliveira",
    "Pacheco",
    "Quintela",
    "Rezende",
    "Siqueira",
    "Teixeira",
    "Vasconcelos",
)


def make_rede(rng: random.Random) -> tuple[list[Store], list[Employee]]:
    """Lojas abertas das 08h às 22h e 20 pessoas por loja. Nomes ganham o sufixo "(sintético)" para não se confundir
    com pessoas reais."""
    lojas = [Store(id=sid, name=nome, opens=time(8, 0), closes=time(22, 0)) for sid, nome in LOJAS]
    nomes = rng.sample([(p, s) for p in PRIMEIROS for s in SOBRENOMES], k=PESSOAS_POR_LOJA * len(LOJAS))
    pessoas: list[Employee] = []
    for indice, (loja, _) in enumerate(LOJAS):
        for posicao in range(PESSOAS_POR_LOJA):
            n = indice * PESSOAS_POR_LOJA + posicao
            primeiro, sobrenome = nomes[n]
            cargo, salario, _peso = rng.choices(CARGOS, weights=[c[2] for c in CARGOS])[0]
            pessoas.append(
                Employee(
                    id=f"P{n + 1:03d}",
                    name=f"{primeiro} {sobrenome} (sintético)",
                    store_id=loja,
                    job=cargo,
                    hourly_wage=salario,
                    contract_hours=CONTRATO_HORAS,
                    sex=rng.choice(["F", "M"]),
                )
            )
    return lojas, pessoas
