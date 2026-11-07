# Critérios de decisão: filtros e rubrica

Última atualização: 2026-11-07 11:55. Base: guia oficial, seções 3, 4 e 8
([guia-converge-challenge.md](../guia-converge-challenge.md)). Os critérios oficiais podem mudar até o início do evento,
com aviso no WhatsApp: se mudarem, atualize este arquivo.

## 1. Filtros eliminatórios (sim ou não)

Uma resposta "não" elimina a ideia. Registre o motivo no backlog.

| # | Filtro | Pergunta |
|---|---|---|
| G1 | **IA central, agente que entrega trabalho** | Um agente conduz o processo e entrega resultado feito, não só responde perguntas? O uso de IA é obrigatório e central (guia, seção 5) |
| G2 | **Cabe em ~11 h** | Um time de 2 a 4 consegue ter o **fluxo mínimo ponta a ponta** funcionando em cerca de 6 h de construção, deixando o resto para exceções, medição e submissão? |
| G3 | **Dados sintéticos honestos** | Dá para gerar dados críveis e declarar que são sintéticos, sem perder o sentido da demo? |
| G4 | **Jurado testa sozinho** | Um jurado usa por link público, sem setup pesado, com dados pré-carregados e vê o agente trabalhando? |
| G5 | **Clean room** | A ideia, os dados e os critérios são 100% nossos, sem apoio em material de empregador ou cliente de qualquer integrante? |
| G6 | **Humano nos atos de consequência** | Os atos sensíveis (irreversíveis, financeiros, a terceiros) têm aprovação humana definida? |
| G7 | **Custo mensurável** | Dá para medir custo e latência por execução com o crédito disponível (US$ 25 por pessoa na Featherless) e compará-lo ao trabalho manual? |

## 2. Rubrica (4 critérios, pesos iguais, nota de 1 a 5, total de 4 a 20)

| Critério (guia, seção 8) | 1 · fraco | 3 · razoável | 5 · forte |
|---|---|---|---|
| **A. Protótipo e aderência** | Demo seria um script ou chat; o agente só responde | Fluxo ponta a ponta com 1 ou 2 exceções tratadas; rastro parcial | Fecha o processo, trata exceções com contexto pronto para o humano, rastro auditável, custo e ganho medidos, funciona fora da demo |
| **B. Viabilidade como startup** | Dor genérica, sem comprador claro | Comprador plausível, mercado estimado sem âncora, concorrente principal ignorado | Dor urgente e frequente, quem paga e de qual orçamento identificado, mercado em faixa com fonte, alternativa de hoje e concorrência mapeadas, caminho de crescimento |
| **C. Criatividade e originalidade** | Já existe igual e todo mundo faz | Ângulo conhecido com execução diferente | Ângulo novo no problema, no cliente ou no modelo de ganho, que faz a banca dizer "não tinha pensado nisso" |
| **D. Pitch** | Precisa de contexto para entender | Problema e solução claros, potencial de mercado vago | Em 3 minutos: problema sentido, demo ao vivo convincente, números medidos, modelo de negócio e próximo passo |

**Risco de execução** (baixo, médio, alto) **não entra no total**: é desempate e alerta. Considere domínio do time, dependências
externas, quantidade de peças novas e o risco de a demo falhar.

Regras de pontuação:

- Toda nota tem **uma frase de justificativa** e cada afirmação vem rotulada **[FATO]** (com fonte), **[INFERÊNCIA]** ou
  **[HIPÓTESE]**. Sem informação suficiente, a nota fica `?` e o que falta é anotado. Não chutar.
- Pontuem **juntos**; se houver discordância de 2 pontos ou mais, discutam o motivo antes de fazer média.
- Reavalie quando surgir fato novo (pesquisa, conversa com possível cliente, limitação técnica).

## 3. Perguntas-guia (do guia, seção 4)

**Problema.** É dor latente em mercado grande ou incômodo pontual? É urgente (já gastam tempo, dinheiro ou energia para evitar)?
Quem sofre, com que frequência e quanto custa não resolver? Se a resposta é "seria legal ter", é feature, não problema.

**Oportunidade.** Qual o tamanho do mercado (mesmo estimado, com âncora)? O que está mudando (crescimento, consolidação,
regulação)? Como a concorrência se posiciona, **incluindo como o cliente resolve hoje sem você** (planilha, processo manual,
consultoria)?

**Why now.** O que existe agora que não existia há dois anos? Se o problema é antigo, por que ninguém resolveu? A janela
está aberta, ou é cedo ou tarde demais?

**Técnica.** *Confiabilidade:* o que o agente faz quando a ferramenta falha, a API não responde ou a instrução é ambígua?
*Medição:* quais métricas e evals mostram que vai bem? *Custo e latência:* quanto custa cada execução, em tempo e tokens, e
isso vence o processo manual? *Autonomia com auditoria:* o rastro explica o porquê de cada ação?

## 4. Perguntas duras (pré-mortem de jurado e VC)

Use no passo 4 de [como-ideiar.md](como-ideiar.md). Se a equipe não responde, a nota B ou D cai.

1. Quem paga, de qual orçamento, e por quê agora?
2. Por que uma pessoa, uma planilha, um RPA ou o ChatGPT não resolve isso hoje?
3. Por que **este** time e por que esta abordagem?
4. O que acontece quando o agente erra? Quem percebe e como?
5. Quanto custa uma execução e quanto custa o processo manual? De onde vem cada número?
6. O que impede um concorrente grande de copiar em um mês?
7. Qual o próximo passo concreto depois do hackathon?

## 5. Padrões de evidência

- Número de mercado: sempre **faixa com fonte e data**, ou rótulo de estimativa com a conta mostrada.
- Percentual de preço, taxa de sucesso ou conversão sem fonte: **hipótese**.
- Tempo manual por tarefa: **premissa do time**, rotulada na tela.
- Custo do agente: o **medido no trace**.
