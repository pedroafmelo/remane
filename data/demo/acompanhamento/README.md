# SINTÉTICO: cenário do acompanhamento de escala (FT-03)

**SINTÉTICO — documento fictício.** Nenhuma pessoa, loja, ponto ou atestado aqui é real. Os nomes têm o sufixo
"(sintético)". Tudo foi gerado pelo nosso código (`escalista.synth`), com seed fixa, e não veio de nenhum cliente nem
empregador. O ponto é **simulado**: não há relógio de ponto.

## Como gerar

```
uv run python -m escalista.synth acompanhamento --seed 42 --out data/demo
```

Seed `42`. Rodar duas vezes dá os mesmos bytes (`git diff --exit-code data/demo/acompanhamento` fica limpo).
Código: `src/escalista/synth/acompanhamento.py` e `ponto.py`. Semana: seg 11/01/2027 a dom 17/01/2027.

## Arquivos

| Arquivo | O que é |
|---|---|
| `cenario_folga.json` | `{synthetic, week_start, stores, employees, shifts}`: 3 lojas, 17 pessoas e a escala da semana, com **0 violações** no verificador (cartão de `data/regras/` em 11/01/2027). Valida com `Store`, `Employee` e `Shift` de `escalista.domain.schedule` (`stores` traz também `opens` e `closes`). |
| `ponto_desvios.json` | `{synthetic, deviations: [Deviation]}` (`escalista.domain.tracking.Deviation`): a falta da Carla (`DV-01`), o atraso de 25 min do Bruno (`DV-02`) e a hora extra do Nelson em 5 dias (`DV-03` a `DV-07`, T2). Lido por `escalista.synth.ponto.load_deviations`. |
| `cenario.esperado.json` | O gabarito, descrito abaixo. |

## As três lojas

| Loja | Falta plantada | O que a busca de cobertura (`find_cover`) devolve |
|---|---|---|
| L1 Centro (a da demo, **com folga**) | **Ana (sintético)**, qui 14/01 14:00–22:00 (`PL-01`); **Carla (sintético)**, qua 13/01 14:00–22:00 (`DV-01`) | Ana: 3 candidatos, o 1º **sem hora extra** (pessoas de meio período, contrato de 24 h, que folgam nesse dia). Carla: 4 candidatos |
| L2 Norte | Iara, sex 15/01 08:00–16:00 (`PL-02`) | nenhum candidato (ver "Limite conhecido") |
| L3 Sul | Olívia, sáb 16/01 14:00–22:00 (`PL-03`) | nenhum colega livre no dia (`evaluated` 0): RX-05 |

O relógio de demo começa em qua 13/01/2027 13:55. A Ana avisa nesse instante; a falta da Carla aparece no ponto às 14:10.

## Formato do gabarito `cenario.esperado.json`

`{synthetic, seed, week_start, demo_clock, policy, schedule_violations, cases}`. `policy` repete os números da política
fictícia que geraram os instantes (`pol_atraso`, `pol_oferta_turno`, `pol_hora_extra`). Cada item de `cases`:

| Campo | Conteúdo |
|---|---|
| `id`, `origin`, `deviation_id` | `PL-NN` (plantada) ou `DV-NN` (desvio do ponto); `origin` = `relato_do_colaborador`, `ponto` ou `plantada` |
| `kind`, `employee_id`, `shift_start`, `shift_end` | o desvio e o turno atingido (ISO, sem fuso, horário de Brasília) |
| `trigger`, `rule_ref` | o gatilho esperado do varredor (`no_punch`, `overtime_near_limit`, `overtime_limit`) e a regra de onde vem o número |
| `fires_at` | **instante literal** em que o gatilho deve disparar: início + `tolerancia_min` (10) |
| `not_before` | **instante literal** em que ele ainda **não** pode ter disparado: início + 9 min |
| `no_answer` | pergunta em `fires_at`; `fires_at` e `not_before` da resposta: pergunta + 15 e + 14 (RX-09) |
| `offers` | só quando há aviso do colaborador (`reported_at`): cada oferta tem `sent_at`, `deadline` (envio + 20 min) e `offer_expired_not_before`; `rx06_at` = aviso + 20 min por candidato ofertado (até 3: + 60 min), `rx06_not_before` = 1 min antes |
| `evaluated`, `ranked`, `ranked_names` | quantos colegas a busca avaliou e a **ordem** dos aprovados (ids), saída do `find_cover` |
| `first_without_overtime`, `overtime_needed`, `expect_rx05`, `new_violations` | o 1º candidato sem hora extra; se todos exigem hora extra; se não há candidato (RX-05); violações novas da cobertura (sempre 0) |

Os instantes são **aritmética sobre a política**, escrita pelo gerador sem chamar o varredor (PEDIDO-EV-20): um eval que
compara o varredor com este arquivo não é circular. Nos casos de hora extra (T2): `cumulative_minutes`,
`threshold_minutes` (80% de 6 h = 288 min; 100% = 360 min) e `fires_at` na batida de saída que cruza o limiar.

O ponto simulado (`escalista.synth.ponto.SimulatedPunchSource`) deriva as batidas da escala corrente: `in` no início, `out`
no fim; o desvio casa por (`employee_id`, `shift_start`), então um turno reatribuído a quem cobre tem batidas normais.

## Limite conhecido: a hora extra e o `find_cover`

O pedido original era uma falta, na loja 2, em que **só** há candidatos com hora extra. Com o cartão de regras atual isso é
impossível numa escala verificada: hora extra exige mais de 8 h no dia ou mais de 42 h na semana, e as duas coisas são
violações do verificador (e passar de 42 h em turnos de 8 h exige 6 dias de trabalho, contra o repouso de 2 dias). O
`find_cover` só aceita cobertura sem violação nova, então `overtime_hours` é sempre 0 e `overtime_needed` nunca é verdadeiro.
A loja 2 fica, portanto, como "ninguém cobre dentro das regras" (RX-05). Mudar isso pede decisão do time sobre o
`find_cover` ou sobre o cartão (por exemplo, aceitar até a hora extra da política, `pol_hora_extra`).
