"""Demanda por faixa de 30 min, de segunda a domingo (plano da C5, seção 4, D2). Sintética, com picos plausíveis."""

from __future__ import annotations

import random
from datetime import time, timedelta

from escalista.domain.schedule import DemandSlot, Store
from escalista.synth.rede import PESSOAS_POR_LOJA, SEMANA_INICIO

# pessoas no piso por faixa de 30 min, antes dos ajustes (almoço e fim de tarde são os picos)
FATOR_DIA = (0.85, 0.90, 0.95, 1.00, 1.15, 1.30, 1.20)  # seg a dom: fim de semana mais forte
FATOR_LOJA = {"L1": 1.00, "L2": 0.90, "L3": 1.10}
# teto de pessoas simultâneas por faixa, como fração da equipe da loja: nenhum pico pede mais do que a equipe, com
# folgas e interjornada, consegue cobrir. Sem o teto, os picos de L1 e L3 (11 e 12 de 20) deixavam 9,5 h descobertas.
TETO_FRACAO_EQUIPE = 0.40


def _base(minuto: int) -> int:
    hora = minuto // 60
    if hora < 10:
        return 3  # abertura
    if hora < 12:
        return 5
    if hora < 14:
        return 7  # almoço
    if hora < 17:
        return 5
    if hora < 20:
        return 8  # fim de tarde
    return 5  # fechamento


def make_demanda(rng: random.Random, lojas: list[Store]) -> list[DemandSlot]:
    """Uma linha por loja, por dia e por faixa de 30 min entre a abertura e o fechamento. Tudo com `required >= 1`."""
    demanda: list[DemandSlot] = []
    for loja in lojas:
        teto = max(1, int(TETO_FRACAO_EQUIPE * PESSOAS_POR_LOJA))
        for dia in range(7):
            data = SEMANA_INICIO + timedelta(days=dia)
            for minuto in range(loja.opens.hour * 60, loja.closes.hour * 60, 30):
                valor = _base(minuto) * FATOR_DIA[dia] * FATOR_LOJA.get(loja.id, 1.0)
                ruido = rng.uniform(0.92, 1.08)  # sempre sorteado: o RNG compartilhado avança igual com ou sem teto
                requerido = max(1, min(round(valor * ruido), teto))
                demanda.append(
                    DemandSlot(
                        store_id=loja.id,
                        day=data,
                        start=time(minuto // 60, minuto % 60),
                        required=requerido,
                    )
                )
    return demanda
