# SINTETICO: dados de demonstração do Escalista

**SINTETICO - dados ficticios.** Nenhuma pessoa, loja ou escala aqui é real. Os nomes têm o sufixo "(sintético)", as
lojas se chamam "Loja Sintética", e os salários são valores inventados. Estes arquivos foram gerados pelo nosso código
(`escalista.synth`), com seed fixa, e não vieram de nenhum cliente nem empregador.

## Como são gerados

```
uv run python -m escalista.synth --seed 42 --out data/demo
```

- **Seed:** `42`. A mesma seed gera os mesmos bytes. `tests/synth/` confere isso e também confere que estes arquivos
  são os da seed 42.
- **Semana de referência:** segunda 11/01/2027 a domingo 17/01/2027.
- **Código:** `src/escalista/synth/` (`rede.py`, `demanda.py`, `escalas.py`, `saida.py`).

## Arquivos

| Arquivo | O que é | Uso |
|---|---|---|
| `lojas.json` | 3 lojas, abertas das 08h às 22h. Valida com `TypeAdapter(list[Store])`. | Solver, verificador, tela |
| `pessoas.json` | 60 pessoas (20 por loja), com cargo, salário-hora fictício, `contract_hours=44`, `sex` e `profile="padrao"`. Valida com `TypeAdapter(list[Employee])`. | Solver (usa `sex`); a API nunca devolve `sex` (RN-13) |
| `demanda.json` | Demanda por faixa de 30 min, de seg a dom, por loja (588 faixas). Valida com `TypeAdapter(list[DemandSlot])`. | Solver (cobertura) |
| `escala_atual.csv` | Escala atual, no regime de 44h e 1 folga: 6 dias por pessoa, alguns dias de 9h30 a 10h (hora extra). Julgada pelas regras novas, **tem violações**. | Tela "antes" |
| `escala_defeito.csv` | Escala com 5 defeitos de leitura plantados (um de cada tipo). A lista exata está em `defeitos_plantados.json`. | Validação de leitura (RF-04, RX-13) |
| `defeitos_plantados.json` | `[{"line", "field", "reason"}]`. `line` é o número da linha física no arquivo (1-based, contando a marca e o cabeçalho). | Teste do validador |
| `escala_violacoes.csv` | Escala **válida para leitura**, com violações plantadas e conhecidas. As outras pessoas ficam dentro de todas as regras. | Teste do verificador (RN-04: meta 0 violações não detectadas) |
| `violacoes_plantadas.json` | `[{"rule_id", "kind", "employee_id", "day"}]`, a lista completa e exata das violações de `escala_violacoes.csv`. `kind` repete o `rule_id` (o tipo da primitiva). `day` é `null` nas regras de semana. | Gabarito do verificador |

Os turnos estão em CSV longo (DEC-036), um turno por linha. O `escala_violacoes.csv` e o `escala_atual.csv` começam com a
marca `# SINTETICO - dados ficticios`, e o cabeçalho vem na linha 2.

## Formato do CSV longo

Cabeçalho exato, nesta ordem: `loja_id,pessoa_id,nome,data,inicio,fim`.

- `data`: `AAAA-MM-DD`, o dia em que o turno **começa**.
- `inicio` e `fim`: `HH:MM`.
- **Turno que vira a noite:** se `fim` é menor que `inicio`, o turno termina no dia seguinte. Ex.: `2027-01-13,16:00,00:00`
  é das 16h de quarta às 0h de quinta (8h). A duração é `fim - inicio` com a virada de dia.
- Linha de comentário: só a primeira linha, `# SINTETICO - dados ficticios`. Os leitores devem ignorá-la.

Observação: a loja fecha às 22h, e o turno da quarta de `escala_violacoes.csv` passa da meia-noite de propósito, para
testar a leitura do turno noturno e a interjornada. Horário de loja não é primitiva da fatia.

## Regras que as escalas exercitam

Valores das regras novas, da fatia (plano da C5, seção 3.1): `jornada_semanal_max` 42h, `jornada_diaria_max` 8h,
`interjornada_min` 11h, `repouso_semanal` 2 dias por semana.

Em `escala_violacoes.csv`, as violações plantadas são (ver `violacoes_plantadas.json`):

| Regra | Pessoas | Dias |
|---|---|---|
| `jornada_semanal_max` | P001 (45h), P003 (46h40) | semana |
| `repouso_semanal` | P001, P002, P003 | semana (1 folga) |
| `jornada_diaria_max` | P004 (9h na segunda), P005 (10h na quarta) | 11/01 e 13/01 |
| `interjornada_min` | P006 (10h entre seg e ter), P007 (8h entre o turno noturno de qua e qui) | 12/01 e 14/01 |

P002 faz exatamente 42h, o que não viola o limite. A regra semanal só é quebrada com mais de 42h, e com 5 dias de até
8h isso não acontece sem uma segunda violação. Por isso, as pessoas com semana acima de 42h também têm folga a menos.

## Demanda e capacidade

- Demanda total: 1.742 pessoa-horas na semana (3 lojas).
- Capacidade: 60 pessoas × 40h = 2.400 pessoa-horas. Com 2 folgas e no máximo 8h por dia, a pessoa não passa de 40h na
  semana, mesmo com o limite de 42h. Sobra cerca de 27% de folga no total, e a loja mais carregada (L3) usa cerca de 80%.
- Teste: `pedidas <= 0,85 × 60 × 42` (2.142), e também `<= 0,85 × 60 × 40` (2.040).

Isto é uma conta de capacidade, e não prova que existe escala viável com 0 violações. Essa prova é do solver.

## Como os dados foram feitos

- Nomes: combinações de nomes e sobrenomes comuns com o sufixo "(sintético)". Ninguém real está aqui.
- `escala_atual.csv`: 6 dias por pessoa (uma folga sorteada), turnos de 7h20 ou 8h, e 8 pessoas com um dia de 9h30 ou 10h.
  Não é calibrada para cobrir a demanda: serve para mostrar o "antes" e as violações.
- Os turnos de `escala_violacoes.csv` e de `escala_defeito.csv` vêm de um padrão novo e compatível (5 dias, folga no
  domingo, turnos de 7h ou 8h, 12h de descanso no mínimo), com as 7 pessoas planejadas e os 5 defeitos alterados em cima.
