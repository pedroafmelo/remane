# Regras de jornada (entrada do cartão de regras)

Última atualização: 2026-11-08 00:05. Entrada do cartão de regras ([RF-01](../../docs/requisitos.md)) e da política
parametrizável ([RF-22](../../docs/requisitos.md)). Enquanto a leitura de PDF (RF-20, cortável) não existir, as regras entram
por estes arquivos YAML.

## Camadas

| Pasta | O que contém | Origem | Situação |
|---|---|---|---|
| [lei/](lei/) | Normas públicas: EC 141 ([ec141.yaml](lei/ec141.yaml)); CLT, Lei 10.101/2000 e incisos do art. 7º da CF ([clt.yaml](lei/clt.yaml)) | Texto oficial (Planalto) | Os dois conferidos por Claude contra o Planalto em 07/11; falta leitura do time |
| [convencao/](convencao/) | Convenção coletiva **fictícia** da demo ([cct_comercio_ficticia.yaml](convencao/cct_comercio_ficticia.yaml)) | Escrita por Claude a pedido de Pedro Veloso | 8 cláusulas, 1 conflito com a EC (RX-01) e 1 cláusula ambígua (RX-11) plantados |
| [politica/](politica/) | Política **fictícia** da empresa da demo: o que a lei e a convenção deixam em aberto ([politica_ficticia.yaml](politica/politica_ficticia.yaml)) | Escrita por Claude a pedido de Pedro Veloso | 11 parâmetros (2 `[PROPOSTA]`) e as 3 exceções da demo (RX-01, RX-05, RX-08) |

Ordem entre as camadas: a política só restringe a lei e a convenção, nunca afrouxa. **Quando duas camadas conflitam, o
agente aplica a mais restritiva de forma provisória e abre exceção ao DP** (P1 de [produto.md](../../docs/produto.md);
conflito 2 de [requisitos.md](../../docs/requisitos.md)).

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

- As 42h contra o limite de 8h por dia (pergunta 17 de [estado-do-projeto.md](../../docs/estado-do-projeto.md)): na demo, a
  convenção fictícia permite até 9h por dia a partir de 16/12/2026 (`cct_jornada_diaria_ampliada`).
- Itens `proposta: true` da política (aviso de necessidade de hora extra e reotimização semanal) esperam decisão do time.

## Campos da convenção e da política

- `restringe`, `amplia` e `resolve` apontam para o `id` da regra de `lei/` que a cláusula ou o item ajusta. A convenção só
  `amplia` o que a lei deixa ampliar; a política só `restringe`.
- `demo` (só na convenção): o que foi plantado de propósito para a demo e para os evals (`plantado` e `esperado`). Não é regra:
  o motor não lê esse campo.
- `nao_preve` (só na convenção): o que ela não trata. Nesse caso valem a lei e a exceção correspondente.
- `proposta: true` (só na política): `[PROPOSTA]` do agente, à espera de decisão do time.
- `excecoes_demo` (só na política): as 3 exceções da demo, com os campos do `ExceptionCard` de
  `src/escalista/domain/contracts.py`. O mapeamento está no comentário do arquivo. `custo_base` diz como o código calcula o
  custo: `hora_extra`, `remanejamento` ou `nenhum`. `opcoes_vedadas` lista o que o agente nunca oferece.
- Prazos em minutos de relógio simulado.
- A data exata dos marcos (15 ou 16/12): `marcos.status: pendente` em [ec141.yaml](lei/ec141.yaml).
