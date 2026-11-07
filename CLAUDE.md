# Converge Challenge: projeto do time

Repositório do time no **Converge Challenge powered by Tako**: hackathon de AI Agents, **tema aberto**, 07 e 08/11/2026,
Porto Digital, Recife. Este arquivo é o ponto de entrada para quem (humano ou agente) trabalha aqui. Leia-o primeiro.

**Estado atual:** fase, ideia escolhida e próximas ações estão em
[docs/estado-do-projeto.md](docs/estado-do-projeto.md). Confira lá antes de agir, porque este arquivo não muda a cada hora.
O PDF do Escalista é base, não a verdade: a verdade do projeto é o que sair do fluxo de definição ([DEC-010](docs/decisoes.md)).

## Missão nesta fase

Ajudar o time a chegar, rápido, a **uma ideia que seja boa de negócio, executável em cerca de 11 horas de hacking e
demonstrável a jurados que vão testá-la**. Depois da decisão, ajudar a detalhar e construir. A ideia anterior
(recuperação de depósitos judiciais) foi descartada ([DEC-009](docs/decisoes.md)); o material segue em [docs/arquivo/](docs/arquivo/ideia-001-recuperacao-depositos/).

Leia, nesta ordem: [estado](docs/estado-do-projeto.md), [como ideiar](docs/ideacao/como-ideiar.md),
[critérios](docs/ideacao/criterios.md), [backlog de ideias](docs/ideacao/backlog-ideias.md),
[contexto do evento](docs/contexto-hackathon.md). O guia oficial completo está em
[docs/guia-converge-challenge.md](docs/guia-converge-challenge.md).

## Regras inegociáveis (elegibilidade e integridade)

Fonte: guia, seções 5 e 14. Detalhes e interpretações em [docs/regras-e-integridade.md](docs/regras-e-integridade.md).

1. **Código do projeto só a partir das 10h30 de sábado (07/11).** Esse horário já passou. Faça commits pequenos e
   frequentes (os organizadores podem pedir o histórico) e **não importe histórico de outro repositório**.
2. **Clean room.** Nenhum dado, código, prompt, schema, critério ou documento de clientes ou de empregadores de qualquer
   integrante entra aqui, nem como referência, **nem como inspiração de ideia**. Não cole trechos de outros repositórios.
   Bibliotecas e open source de terceiros são permitidos e devem ser declarados.
3. **Dados sintéticos e honestos.** Dados de demo são gerados por nós. Nunca apresentar dado sintético, simulador ou mock
   como se fosse real. Declarar isso na submissão.
4. **Declarar na submissão** todas as ferramentas, modelos e APIs de terceiros: mantenha
   [docs/declaracao-ferramentas.md](docs/declaracao-ferramentas.md) em dia.
5. **Segredos fora do repositório.** Chaves só em variável de ambiente ou `.env` (ignorado pelo git). O código de resgate
   da Featherless é exclusivo dos participantes: não commitar nem publicar.
6. **O agente prepara, o humano decide nos atos de consequência.** Cada ideia define quais atos exigem aprovação humana.
   Por padrão: nada irreversível, financeiro ou dirigido a terceiros sem aprovação. Se o time escolher o Desafio Tako (RH),
   decisões sobre pessoas (demissão, promoção, salário, avaliação) ficam sempre com humanos.
7. **Não afirmar o que não foi medido.** Números de mercado sempre como faixa com fonte. Separar **[FATO]** (com fonte),
   **[INFERÊNCIA]** e **[HIPÓTESE]**. Custo e ganho do agente são os medidos no trace; estimativas de tempo manual são
   premissas, rotuladas como tal.

## Como o projeto será avaliado (guia, seção 8; 4 critérios, pesos iguais)

1. Qualidade do protótipo e aderência ao desafio (faz trabalho real, funciona na demo, se sustenta fora dela).
2. Viabilidade como startup (mercado, quem paga, caminho de crescimento).
3. Criatividade e originalidade.
4. Pitch (3 minutos: problema, solução, potencial de mercado).

"Metade da régua é negócio, não só código." Os jurados **testam** a solução: precisa de link público estável, com dados
pré-carregados. A rubrica interna que traduz isso em nota está em [docs/ideacao/criterios.md](docs/ideacao/criterios.md).

## Prioridades de escopo

**Fazer uma coisa muito bem, em vez de seis pela metade.** Em ordem: (1) fluxo ponta a ponta funcionando e demonstrável;
(2) tratamento real de exceções, com escalada ao humano e contexto pronto; (3) rastro auditável (tracing desde a primeira
hora); (4) evals pequenos e honestos, e custo por execução medido; (5) polimento. **Não cortar:** exceções, rastro, evals.

## Modo ideação: como o agente ajuda

- Proponha poucas opções boas, com recomendação clara e o melhor argumento contra ela, em vez de listas exaustivas.
- Aplique primeiro os **filtros eliminatórios** e só depois a rubrica ([critérios](docs/ideacao/criterios.md)).
- Faça perguntas de negócio do guia: quem sofre, com que frequência, quanto custa, quem paga, o que mudou (why now), como
  o cliente resolve hoje sem nós.
- Pesquise mercado e concorrência com fonte; diga o que **não** encontrou. Não invente número.
- Conduza com os comandos: `/nova-ideia`, `/avaliar-ideias`, `/decisao`, `/sync-docs` (em `.claude/commands/`).
- **A decisão é do time.** O agente recomenda e registra; não escolhe a ideia sozinho.

## Documentação viva (auto-atualização)

A documentação é parte do trabalho, não uma etapa final. **Quem muda algo atualiza a doc correspondente no mesmo turno**,
e atualiza a data de "Última atualização" do arquivo tocado. Gatilhos:

| Quando acontecer | Atualizar |
|---|---|
| Surgir, mudar ou sair uma ideia | `docs/ideacao/backlog-ideias.md` e a ficha em `docs/ideacao/ideias/` |
| O time decidir algo (ideia, stack, corte, divisão) | `docs/decisoes.md` e `docs/estado-do-projeto.md` (comando `/decisao`) |
| Ideia escolhida | Criar `docs/produto.md` e `docs/arquitetura.md`; fase passa a "Definição" |
| Entrar dependência, modelo, API ou serviço de terceiros | `docs/declaracao-ferramentas.md` |
| Escopo mudar, algo for cortado ou um marco for atingido | `docs/estado-do-projeto.md` e `docs/plano-de-horas.md` |
| Chegar aviso do WhatsApp ou o guia mudar | `docs/contexto-hackathon.md` e `docs/regras-e-integridade.md` |
| Medir custo, latência ou resultado de eval | `docs/estado-do-projeto.md` (Métricas medidas) |
| Alterar código | Uma linha em "Registro de atualizações" de `docs/estado-do-projeto.md` |
| Antes de submeter | Percorrer `docs/entrega.md` item a item |

Regras de manutenção:

- Não duplique: cada fato mora em **um** arquivo; os outros apontam para ele.
- Nunca apague ideia nem decisão: mude o status (`descartada`, `arquivada`, `substituída`) e registre o motivo.
- Na dúvida entre escrever e perguntar, **pergunte**. Docs com dado inventado são pior do que docs incompletas.
- `/sync-docs` audita a doc contra o repositório. Rode ao fim de cada bloco de trabalho e antes da submissão.
- `.claude/hooks/docs_sync.py` automatiza o aviso de defasagem (contagem regressiva ao abrir a sessão e bloqueio único
  ao encerrar um turno em que o código mudou e a doc não). **O hook só está ativo depois de registrado em
  `.claude/settings.json`** (instruções no [README](README.md#ativando-o-hook)). Sem ele, vale a regra acima.

## Estrutura do repositório

```
CLAUDE.md                          este arquivo
README.md                          índice rápido e como usar as docs
.claude/commands/                  /nova-ideia, /avaliar-ideias, /decisao, /sync-docs
.claude/hooks/docs_sync.py         aviso de documentação defasada (opcional, ver README)
docs/
  estado-do-projeto.md             FONTE DA VERDADE do momento: fase, ideia, próximas ações, métricas
  guia-converge-challenge.md       cópia local do guia oficial (código de resgate redigido)
  contexto-hackathon.md            resumo operacional do evento
  regras-e-integridade.md          regras de elegibilidade e interpretações do time
  plano-de-horas.md                cronograma com gates de decisão
  requisitos.md                    requisitos funcionais, de exceção, não funcionais e de aceite
  produto.md                       definição do produto: features, fluxos, agente x humano, generalização
  decisoes.md                      registro de decisões (DEC-NNN)
  declaracao-ferramentas.md        lista de ferramentas, modelos e APIs de terceiros (vai para a submissão)
  entrega.md                       submissão, pitch de 3 min e roteiro de demo
  ideacao/                         como ideiar, critérios, backlog, template e fichas das ideias
  arquivo/                         material de ideias arquivadas (nada é apagado)
src/  tests/                       código (a partir da decisão)
```

## Convenções de trabalho

- Documentação e interface em **português**. Código e mensagens de commit em **inglês**, Conventional Commits.
- As instruções globais do usuário (`~/.claude/CLAUDE.md`) continuam valendo, inclusive commit e TDD. Relaxar TDD durante o
  hackathon só por decisão explícita do usuário (registre em `docs/decisoes.md`).
- Commits só quando o usuário pedir.
- Deploy em link público estável é requisito de submissão: trate como funcionalidade, não como acabamento.

## Datas e prazos (horário de Brasília)

- **Sáb 07/11:** hacking desde 10h30; encerramento do dia 17h00.
- **Dom 08/11:** **submissão até 13h00** (https://hackathons.canastra.ventures/); Demo Day 16h00; premiação 17h30.
- Canal oficial de avisos: grupo de WhatsApp do evento. Critérios e programação podem mudar com aviso por lá.
