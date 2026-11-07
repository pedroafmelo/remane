# Regras de jornada (entrada do cartão de regras)

Última atualização: 2026-11-07 15:20. Entrada do cartão de regras ([RF-01](../../docs/requisitos.md)) e da política
parametrizável ([RF-22](../../docs/requisitos.md)). Enquanto a leitura de PDF (RF-20, cortável) não existir, as regras entram
por estes arquivos YAML.

## Camadas

| Pasta | O que contém | Origem | Situação |
|---|---|---|---|
| [lei/](lei/) | Normas públicas: EC 141 ([ec141.yaml](lei/ec141.yaml)); CLT, Lei 10.101/2000 e incisos do art. 7º da CF ([clt.yaml](lei/clt.yaml)) | Texto oficial (Planalto) | Os dois conferidos por Claude contra o Planalto em 07/11; falta leitura do time |
| [convencao/](convencao/) | Convenção coletiva **fictícia** da demo | Escrita pelo time | vazia |
| [politica/](politica/) | Política **fictícia** da empresa da demo: o que a lei e a convenção deixam em aberto | Escrita pelo time | vazia |

Ordem entre as camadas: a política nunca afrouxa a lei. **Conflito entre convenção e emenda: em aberto** (conflito 2 em
[requisitos.md](../../docs/requisitos.md)). Até lá, a regra fica pendente para o DP e não é decidida no código.

## Convenções dos arquivos

- Cada regra tem `id` estável, `fonte` (artigo ou cláusula) e, quando muda no tempo, vigência (`de` e `ate`).
- Status de cada regra (RN-09): `conferida` (lida na fonte oficial por alguém do time), `interpretacao` (leitura nossa) ou
  `pendente`. **Nenhuma interpretação aparece na tela como certa.** Conferência feita só pelo agente não basta para
  `conferida`: a regra fica `interpretacao` até alguém do time ler o artigo.
- `pendente` vale quando o trecho não foi achado, o artigo diverge, falta um valor ou a conclusão depende de conta nossa
  (por exemplo, a data exata dos marcos).
- `verificacao`: quem leu, onde, quando e o resultado ("confere" ou "diverge: o quê"). Divergência não é corrigida em
  silêncio: a regra fica `pendente` até alguém do time decidir.
- `acao` das `excecoes` tem só dois valores:
  - `escalar`: o agente não decide; vai para a fila de um humano, junto com a fonte;
  - `verificar_convencao`: o agente procura a cláusula na convenção; se ela não prevê, aplica a regra padrão e registra.
  Detalhes em texto livre vão no campo `nota`.
- Os cálculos derivados (divisor, salário-hora, custo) ficam no código, não no YAML.
- A convenção e a política são 100% fictícias e não reproduzem documento de empresa nem de cliente (clean room). Isso precisa
  aparecer como sintético na submissão.

## Pontos em aberto

- As 42h contra o limite de 8h por dia, e se a convenção fictícia permite passar de 8h: pergunta 13 de
  [estado-do-projeto.md](../../docs/estado-do-projeto.md).
- A data exata dos marcos (15 ou 16/12): `marcos.status: pendente` em [ec141.yaml](lei/ec141.yaml).
