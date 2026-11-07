# Regras de jornada (entrada do cartão de regras)

Última atualização: 2026-11-07 14:15. Entrada do cartão de regras ([RF-01](../../docs/requisitos.md)) e da política
parametrizável ([RF-22](../../docs/requisitos.md)). Enquanto a leitura de PDF (RF-20, cortável) não existir, as regras entram
por estes arquivos YAML.

## Camadas

| Pasta | O que contém | Origem | Situação |
|---|---|---|---|
| [lei/](lei/) | Normas públicas: EC 141 ([ec141.yaml](lei/ec141.yaml)); CLT e ECA depois | Texto oficial (Planalto) | `ec141.yaml` entrou em 07/11; falta conferir |
| [convencao/](convencao/) | Convenção coletiva **fictícia** da demo | Escrita pelo time | vazia |
| [politica/](politica/) | Política **fictícia** da empresa da demo: o que a lei e a convenção deixam em aberto | Escrita pelo time | vazia |

Ordem entre as camadas: a política nunca afrouxa a lei. **Conflito entre convenção e emenda: em aberto** (conflito 2 em
[requisitos.md](../../docs/requisitos.md)). Até lá, a regra fica pendente para o DP e não é decidida no código.

## Convenções dos arquivos

- Cada regra tem `id` estável, `fonte` (artigo ou cláusula) e, quando muda no tempo, vigência (`de` e `ate`).
- Status de cada regra (RN-09): `conferida` (lida na fonte oficial por alguém do time), `interpretacao` (leitura nossa) ou
  `pendente`. **Nenhuma interpretação aparece na tela como certa.**
- `excecoes` não são decididas pelo agente: viram fila para um humano, junto com a fonte.
- Os cálculos derivados (divisor, salário-hora, custo) ficam no código, não no YAML.
- A convenção e a política são 100% fictícias e não reproduzem documento de empresa nem de cliente (clean room). Isso precisa
  aparecer como sintético na submissão.
