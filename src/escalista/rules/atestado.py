"""Julgamento da comprovação (plano da C7, seção 4.7; contrato SAIDA-AC-05), **puro**.

O modelo só lê os campos (`AtestadoFields`); `verdict` e `reasons` saem daqui, em código, a partir dos campos e do dia
da falta. Regras, nesta ordem fixa das razões:

- ilegível → `verdict="ilegivel"`, `reasons=["ilegivel"]` (os campos lidos seguem no retorno, sem outro julgamento);
- sem data (nem emissão nem início) → `sem_data`;
- com data, o dia esperado fora da janela `[início ou emissão, + (dias ou 1) - 1]` → `data_nao_bate`;
- `has_crm is False` → `sem_crm`;
- `patient_matches is False` → `nome_nao_bate`.

`None` em `has_crm` ou `patient_matches` é "não deu para ver", não uma falha: não gera razão. `dias_fora_da_faixa`
fica reservado: o schema de `AtestadoFields` já barra `days` fora de 1..30.

Nenhuma razão leva a recusa: `inconsistente` vira RX-08 ao gestor, e o abono segue provisório (RH-03).
"""

from __future__ import annotations

from datetime import date, timedelta

from escalista.domain.tracking import AtestadoFields, AtestadoReading, Reason


def judge(fields: AtestadoFields, *, expected_day: date) -> AtestadoReading:
    if not fields.legible:
        return AtestadoReading(**fields.model_dump(), verdict="ilegivel", reasons=["ilegivel"])

    reasons: list[Reason] = []
    first_day = fields.start_on or fields.issued_on
    if first_day is None:
        reasons.append("sem_data")
    else:
        last_day = first_day + timedelta(days=(fields.days or 1) - 1)
        if not first_day <= expected_day <= last_day:
            reasons.append("data_nao_bate")
    if fields.has_crm is False:
        reasons.append("sem_crm")
    if fields.patient_matches is False:
        reasons.append("nome_nao_bate")

    return AtestadoReading(**fields.model_dump(), verdict="inconsistente" if reasons else "valido", reasons=reasons)
