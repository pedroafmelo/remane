# IDEA-001 · Analista de recuperação de depósitos judiciais

Status: **arquivada** (o time decidiu mudar de ideia em 07/11/2026; motivo detalhado não informado, ver
[DEC-001](../../decisoes.md)). Última atualização: 2026-11-07 11:55.

Material completo, preservado (só com aviso de arquivamento no topo e links ajustados), em
[arquivo/ideia-001-recuperacao-depositos/](../../arquivo/ideia-001-recuperacao-depositos/):
[proposta](../../arquivo/ideia-001-recuperacao-depositos/proposta.md),
[arquitetura](../../arquivo/ideia-001-recuperacao-depositos/arquitetura.md),
[pesquisa](../../arquivo/ideia-001-recuperacao-depositos/pesquisa.md).

## Em uma frase

Um digital worker que lê a política do cliente, filtra e verifica um lote de depósitos judiciais, lê documentos, calcula
um score de recuperabilidade, trata exceções e deixa a minuta de pedido de alvará pronta; o advogado aprova só exceções e
atos jurídicos.

## O que tinha de forte (vale como régua para as novas ideias)

- Humano no loop **bem definido**: o agente prepara, o advogado decide e protocola.
- **Seis tipos de exceção** nomeados, cada um com motivo, evidência e recomendação.
- Métrica central clara: **decisões erradas sem revisão** (meta próxima de zero), além de taxa de intervenção e custo
  por processo.
- Estratégia de custo: filtrar antes de gastar, cascata de modelo pequeno para grande só na dúvida.
- Ideia de onboarding por documento de política, gerando um "cartão de regras" citado e aprovado uma vez.

## Pontos fracos e ressalvas registradas

- Totais de mercado variam entre reportagens e **não há número consolidado do que é realmente recuperável** [FATO, ver
  pesquisa].
- O mercado já é atendido por escritórios que cobram por êxito; o diferencial teria de ser custo por processo e autonomia
  medida.
- Domínio jurídico exige validação com advogado antes de codificar prazos como regra.
- Dados públicos cobrem status processual, mas não saldo, partes nem documentos; tudo ficaria sintético e simulado.
- Não havia fonte para percentual de success fee: tratar como hipótese.

## Reaproveitável em qualquer ideia nova

Padrões de [arquitetura](../../arquivo/ideia-001-recuperacao-depositos/arquitetura.md) e
[pesquisa](../../arquivo/ideia-001-recuperacao-depositos/pesquisa.md) que independem do domínio: roteamento por incerteza
(seguir sozinho quando há confiança, escalar quando não), cascata de modelos, auto-verificação de campos contra o texto
de origem, trace por execução, métricas de autonomia e a lista de armadilhas de pitch ("o que evitar").
