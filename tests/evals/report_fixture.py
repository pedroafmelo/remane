"""Relatório `all` sintético, com a forma da seção 4 de `docs/planos/evals-e3-e4.md` (só para testes).

Os números aqui são de teste, não medidos: nenhum testa o produto, só o transporte (retrato, rota, tela).
"""

from __future__ import annotations

import copy
from typing import Any

_REPORT: dict[str, Any] = {
    "suite": "all",
    "gerado_em": "2026-11-08T10:30:00-03:00",
    "git_sha": "abc1234",
    "modo": "sem_modelo",
    "dados": "sintéticos",
    "contagem": {
        "cenarios": 30,
        "sem_modelo": 20,
        "com_modelo": 10,
        "executados": 21,
        "passaram": 21,
        "falharam": 0,
        "nao_executados": 9,
        "com_modelo_executados": 1,
    },
    "dec_019": {
        "sem_modelo": {"meta": 20, "existem": 20, "passaram": 20},
        "com_modelo": {"meta": 10, "existem": 10, "executados": 1, "passaram": 1},
    },
    "rn04": {
        "violacoes_nao_detectadas": {
            "plantadas": 14,
            "detectadas": 14,
            "nao_detectadas": 0,
            "falsos_positivos": 0,
            "fontes": ["E1-01", "E1-11"],
        },
        "cobertura": {"escala_demo_pct": 97.5, "casos_cobertos": None},
        "custo_contra_planilha": {
            "antes_brl": "1000.00",
            "depois_brl": "900.00",
            "fonte": "compute_metrics, dados sintéticos",
        },
        "acerto_atestado": {"campos_certos": None, "campos": None, "n_atestados": 0, "status": "não medido"},
    },
    "modelo": {"chamadas": 0, "cost_usd": None, "latencia_ms_p50": None, "latencia_ms_max": None, "teto_usd": 1.0},
    "suites": {
        "e1": {"cenarios": 11, "passaram": 11, "falharam": 0, "nao_executados": 0},
        "e2": {"cenarios": 10, "passaram": 10, "falharam": 0, "nao_executados": 0},
        "e3": {"cenarios": 6, "passaram": 0, "falharam": 0, "nao_executados": 6},
        "e4": {"cenarios": 3, "passaram": 0, "falharam": 0, "nao_executados": 3},
    },
    "cenarios": [
        {
            "id": "E1-01",
            "suite": "e1",
            "descricao": "Interjornada de 11 h",
            "usa_modelo": False,
            "tier": "atual",
            "status": "passou",
            "esperado": "1 violação",
            "obtido": "1 violação",
            "motivo": None,
            "tempo_ms": 12,
            "modelo": None,
        },
        {
            "id": "E3-01",
            "suite": "e3",
            "descricao": "Atestado lido e aplicado",
            "usa_modelo": True,
            "tier": "T1",
            "status": "não executado",
            "esperado": "campos do gabarito",
            "obtido": None,
            "motivo": "falta SAIDA-AC-15",
            "tempo_ms": None,
            "modelo": None,
        },
    ],
}


def sample_report() -> dict[str, Any]:
    """Cópia nova a cada chamada: o teste pode mexer sem afetar os outros."""
    return copy.deepcopy(_REPORT)
