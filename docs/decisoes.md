# Registro de decisões

Última atualização: 2026-11-07 15:19. Uma entrada por decisão, mais recente embaixo. **Nunca apague nem reescreva uma
entrada:** se a decisão mudar, crie outra e marque a antiga como `substituída por DEC-NNN`. Use `/decisao` para registrar e
propagar o efeito para as outras docs.

Formato:

```
## DEC-NNN · título
- Data e hora · Decidido por · Status: aceita | provisória | substituída por DEC-NNN
- Contexto:
- Decisão:
- Alternativas consideradas:
- Consequências (o que muda nas docs e no plano):
```

## DEC-001 · Abandonar a ideia de recuperação de depósitos e reabrir a ideação

- 2026-11-07 · Decidido por: time · Status: aceita
- **Contexto:** a ideia inicial (IDEA-001) estava detalhada em proposta, arquitetura e pesquisa.
- **Decisão:** o time resolveu mudar de ideia. **Motivo: [não informado; completar].**
- **Alternativas consideradas:** [não informado].
- **Consequências:** IDEA-001 arquivada em [arquivo/](arquivo/ideia-001-recuperacao-depositos/), documentação generalizada
  para apoiar a ideação, fase atual passa a "1 · Ideação".

## DEC-002 · Documentação genérica e viva, com protocolo de atualização

- 2026-11-07 · Decidido por: time (pedido ao agente) · Status: aceita
- **Contexto:** a ideia mudou e o time precisa de documentos que acompanhem o desenvolvimento sem retrabalho.
- **Decisão:** estruturar `docs/` em torno de estado, ideação, decisões, declaração de ferramentas e entrega; adotar o
  protocolo "Documentação viva" do [CLAUDE.md](../CLAUDE.md), comandos `/nova-ideia`, `/avaliar-ideias`, `/decisao` e
  `/sync-docs`, e um hook opcional de aviso de defasagem (`.claude/hooks/docs_sync.py`).
- **Alternativas consideradas:** documentação específica da nova ideia (prematura, pois a ideia não foi escolhida).
- **Consequências:** o hook só passa a valer depois de registrado em `.claude/settings.json`; até lá a regra é manual.

## DEC-003 · Escalista (IDEA-002) como direção do projeto e participação no Desafio Tako

- 2026-11-07 12:16 · Decidido por: usuário da sessão, em nome do time (ok à Etapa 0: "Vamos prosseguir"); confirmação
  dos demais integrantes: **[pendente]** · Status: **aceita como direção**; detalhamento sujeito aos Gates 2 (negócio) e 3
  (técnica) do usuário; pode ser substituída por outra DEC.
- **Contexto:** a proposta [proposta_escalista_converge_1.pdf](proposta_escalista_converge_1.pdf) (versão 2, 07/11/2026)
  foi revisada na Etapa 0: divergências com as docs listadas e números da EC 141 conferidos (ver
  [IDEA-002](ideacao/ideias/IDEA-002-escalista.md)). O time confirmou seguir.
- **Decisão:** adotar o Escalista (digital worker de escala e jornada) como direção e concorrer ao Desafio Tako, frente DP
  (sinalizar na submissão). **Motivo da escolha: [motivo não informado]**; o usuário só confirmou o prosseguimento.
- **Alternativas consideradas:** nenhuma outra candidata foi comparada com a rubrica; filtros eliminatórios e pontuação de
  [criterios.md](ideacao/criterios.md) **ainda não foram aplicados** à IDEA-002 (o Gate 2 faz isso). IDEA-001 segue
  arquivada ([DEC-001](#dec-001--abandonar-a-ideia-de-recuperação-de-depósitos-e-reabrir-a-ideação)).
- **Consequências:** IDEA-002 passa a `escolhida` (provisória) no backlog; no estado, a fase vai para "2 · Definição" e as
  perguntas em aberto 2 e 5 mudam de situação. `produto.md` e `arquitetura.md` **não** são criados agora: só depois do
  Gate 2, por pedido do usuário (a regra geral do CLAUDE.md prevê criá-los na escolha). Declaração de ferramentas
  atualizada com a stack planejada.
- **Premissas adotadas por padrão pelo agente (o time não respondeu; todas provisórias, a confirmar):**
  - (a) Cobertura de turno sem o gerente só quando não gera hora extra e cumpre todas as regras; qualquer hora extra vai ao
    gerente. **[substituída pela DEC-014: o gerente valida sempre a cobertura]**
  - (b) Toda a inferência do produto passa pela Featherless; o Claude Code é usado só no desenvolvimento.
    **[confirmada pelo usuário em DEC-005]**
  - (c) Langfuse em nuvem (cloud), não self-host. **[substituída por DEC-005: self-hosted]**
  - (d) JEV/TypeSafe descartado (não é necessário para um solver determinístico). **[não confirmada em DEC-006; confirmada em DEC-011: JEV descartado]**
  - (e) A ponte do WhatsApp é um spike de 1 hora com critério de abandono; o simulador de celular é o caminho padrão.
  - (f) O número do bot mostra o aviso "use só dado fictício" e a imagem do atestado não é persistida. **[confirmada pelo usuário em DEC-006]**

## DEC-004 · Ambiente mínimo: dois MCPs de documentação, hook registrado e skills próprias só depois do Gate 3

- 2026-11-07 12:24 · Decidido por: usuário da sessão (Gate 1) · Status: aceita
- **Contexto:** Etapa 1 avaliou skills, MCPs e hooks para a stack do Escalista (tabela no relatório do Gate 1).
- **Decisão:** (1) instalar só os MCPs de documentação oficiais do Langfuse e do LangChain (`.mcp.json`); (2) criar
  `.claude/settings.json` com o hook `docs_sync.py` e permissões mínimas (allow de `uv`, `git status/diff/log` e
  `WebFetch` de domínios de documentação; deny de `.env` e `git push`; `git add` e `git commit` continuam pedindo
  confirmação); (3) escrever as skills próprias `nova-regra` e `novo-cenario-eval` só depois do Gate 3.
  **Motivo: [motivo não informado]**; o usuário aprovou a proposta. **[As permissões de `git` e `gh` e o deny de `git push` foram alterados pela DEC-008.]**
- **Alternativas consideradas:** skills de terceiros de design, deploy e docs (Vercel, Cult UI, ui-ux-pro-max, Context7);
  adiadas ou descartadas pelo relatório do Gate 1. Skills próprias de gerador de dados e de checklist LGPD descartadas
  (viram módulo e teste automático).
- **Consequências:** hook ativo; `declaracao-ferramentas.md` mantém os MCPs como `planejado` até a primeira conexão
  confirmada; nenhuma skill de terceiros instalada.

## DEC-005 · Respostas da Etapa 0: novo fluxo de definição, Langfuse self-hosted e limites de infraestrutura

- 2026-11-07 12:30 · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** o usuário respondeu às perguntas 5 a 11 da Etapa 0 e descreveu o fluxo de trabalho.
- **Decisão (o que o usuário disse):**
  - **Fluxo:** preparação de ambiente → definição de requisitos → definição de negócio (lapidar a ideia e definir regras,
    fluxos etc.) → definição técnica → implementação. A etapa de requisitos é nova em relação ao plano inicial da sessão.
  - **Sem trabalho em paralelo ainda** (pergunta 5): nada de solver nem de dados antes das definições.
  - **Langfuse self-hosted** (pergunta 9). Substitui a premissa (c) da [DEC-003](#dec-003--escalista-idea-002-como-direção-do-projeto-e-participação-no-desafio-tako).
  - **Toda a inferência via Featherless** (pergunta 10). Confirma a premissa (b) da DEC-003.
  - **Chip dedicado:** "vamos ver" (pergunta 6). **Servidor:** o time não tem (pergunta 7). **Domínio próprio:** o time
    não tem (pergunta 8). **Featherless:** ninguém resgatou ainda; o time quer saber como (pergunta 9).
  - **Scaffold (pergunta 11):** autorizou alterar o `pyproject.toml` e o `.gitignore`, e disse que "o scaffold é de outra
    coisa totalmente diferente". Esta última frase **não** esclarece se há material de empregador ou cliente: a pergunta
    segue em aberto no [estado](estado-do-projeto.md).
- **Motivo: [motivo não informado]** para o Langfuse self-hosted.
- **Alternativas consideradas:** Langfuse cloud (premissa (c) da DEC-003), substituída.
- **Consequências:** `declaracao-ferramentas.md` e `.env.example` atualizados (`LANGFUSE_BASE_URL`); `pyproject.toml` sem
  python-bcb e bs4 (requests, isort, pandas e numpy ficam até a definição técnica); `.gitignore` com exceções para PDF e
  HTML em `docs/`, `data/` e `src/`; perguntas em aberto 6 a 10 no estado. As premissas (a), (d), (e) e (f) da DEC-003
  continuam sem confirmação.

## DEC-006 · Respostas 12 a 15 e origem do scaffold

- 2026-11-07 12:35 · Decidido por: usuário da sessão · Status: aceita nos itens abaixo; **remediação do histórico do scaffold pendente**
- **Respostas (o que o usuário disse):**
  - **JEV/TypeSafe (12):** "ainda não sabemos, vamos ver no que podemos usá-lo". A premissa (d) da [DEC-003](#dec-003--escalista-idea-002-como-direção-do-projeto-e-participação-no-desafio-tako) (descartado) deixa de valer: volta a ser pergunta em aberto. Se for usado, é um segundo provedor de inferência e precisa de declaração e de custo medido.
  - **Dados reais enviados pelos jurados (13):** o usuário aceita o aviso "use só dado fictício" e não guardar a imagem do atestado. Confirma a premissa (f).
  - **Pessoa externa para ouvir (14):** não há. Sem validação externa hoje.
  - **Conectores do claude.ai (15):** autorizar só se forem realmente necessários. O usuário consertou o CLI do `claude`.
  - **Origem do scaffold (4):** é um template de um amigo do usuário que trabalha em uma empresa, "não tem nada a ver com esse projeto". O usuário confirma que **entra na regra de clean room**.
- **Evidência levantada pelo agente (só nomes de arquivo, sem copiar conteúdo):** o commit inicial (31 arquivos, 10h55, na conta dona do remoto) traz `.claude/`, `.github/`, `SECURITY.md`, `src/app`, `tests` e `uv.lock`. Dez desses arquivos citam "[termo de terceiro omitido por clean room]" (inclusive um hook com esse termo no nome); nenhum cita "dharma" ou "sileto". O remoto `origin` é privado e tem só esse commit. O working tree não tem mais nenhuma menção a "[termo de terceiro omitido por clean room]". Sobraram do scaffold: `.gitignore`, `.python-version`, `.vscode/settings.json`, `LICENSE` (vazio), `pyproject.toml` e `uv.lock` (desatualizado: ainda lista bs4, python-bcb e o pacote "projeto").
- **Motivo: [motivo não informado]** para manter o JEV em aberto.
- **Consequências:** nenhum commit até a remediação ser decidida (pergunta 11 do [estado](estado-do-projeto.md)); a premissa (d) volta a ser pergunta em aberto; `declaracao-ferramentas.md` registra a origem do scaffold.

## DEC-007 · Remediação do histórico do scaffold: recriar o repositório limpo (opção A)

- 2026-11-07 12:44 · Decidido por: usuário da sessão ("A: Recriar") · Status: aceita; **execução parcial**
- **Contexto:** [DEC-006](#dec-006--respostas-12-a-15-e-origem-do-scaffold). O commit inicial `16e1a5c` veio de um template de terceiro e 10 dos seus 31 arquivos citam "[termo de terceiro omitido por clean room]".
- **Decisão:** recriar o histórico: um commit inicial novo, só com arquivos nossos, sem o commit `16e1a5c`. **Motivo: [motivo não informado]**; a recomendação do agente foi que nada nosso estava versionado e que os organizadores podem pedir o histórico.
- **Alternativas consideradas:** B, manter e declarar; C, limpar só o working tree (não resolve o histórico).
- **Feito até agora:** `LICENSE` vazio, `.vscode/settings.json` e `uv.lock` removidos; `pyproject.toml` reescrito (base: fastapi, uvicorn, pydantic, pydantic-settings; dev: pytest, pytest-cov, ruff; sem pins herdados e sem taskipy, typos, isort, pandas, numpy, requests); `uv.lock` regenerado do zero (26 pacotes); branch órfão `clean-main` criado com índice limpo (33 arquivos a adicionar, nenhum cita "[termo de terceiro omitido por clean room]", nenhum parece segredo). O branch `main` antigo está preservado localmente, sem alteração.
- **Pendente:** (1) identidade do git (não há `user.name` nem `user.email` configurados); (2) os commits; (3) o push, que só o usuário faz (`git push` está negado nas permissões): apagar e recriar o repositório remoto, ou `git push --force`; (4) depois de publicado, apagar o branch `main` antigo e limpar o reflog local; (5) confirmar se `docs/arquivo/ideia-001-recuperacao-depositos/proposta_converge_challenge.pdf` pode ser versionado, já que a exceção do `.gitignore` passou a incluí-lo.
- **Consequências:** substitui a parte da [DEC-005](#dec-005--respostas-da-etapa-0-novo-fluxo-de-definição-langfuse-self-hosted-e-limites-de-infraestrutura) que mantinha requests, isort, pandas e numpy até a definição técnica: agora estão removidos e voltam com `uv add` se a técnica pedir. Nenhum commit foi feito.

## DEC-008 · GitHub: conta do usuário, uso livre e PDF da ideia antiga fora do git

- 2026-11-07 12:54 · Decidido por: usuário da sessão · Status: aceita; **push pendente**
- **Decisão (o que o usuário disse):**
  - Usar a conta do GitHub do usuário nos commits. O `gh` tem duas contas logadas; foi usada a ativa, `pedrohmvv`, que é colaboradora do repositório. A outra (`pedrohmv-DharmaAI`) não foi usada.
  - "Permitir o uso livre do GitHub": `.claude/settings.json` passa a permitir `git` e `gh` e deixa de negar `git push` (altera a [DEC-004](#dec-004--ambiente-mínimo-dois-mcps-de-documentação-hook-registrado-e-skills-próprias-só-depois-do-gate-3)). O modo automático do Claude Code ainda bloqueou o `git push --force-with-lease`, por ser destrutivo.
  - O PDF da ideia antiga fica fora do git ("essa ideia foi descartada"): o `.gitignore` volta a ignorar `docs/arquivo/**/*.pdf`. No backlog a IDEA-001 está `arquivada`, não `descartada`: **[pergunta ao usuário]**.
  - O usuário aprovou o recorte da etapa de requisitos e disse que aprova os dois MCPs; a aprovação em si ainda precisa ser feita no `claude` (status atual: "Pending approval").
- **Motivo: [motivo não informado]** para a conta escolhida e para o uso livre.
- **Feito:** identidade local do git (conta `pedrohmvv`, e-mail noreply); dois commits no branch local `clean-main`; o termo do projeto de origem do template foi retirado das docs (clean room). A tentativa de pré-aprovar os MCPs com `enabledMcpjsonServers` no `settings.json` do projeto não surtiu efeito e foi retirada: a aprovação é feita pelo usuário, no `claude`.
- **Pendente:** o push que sobrescreve o `main` do remoto (o repositório é de `pedroafmelo`, e o usuário tem push, sem admin, então não dá para apagar e recriar). Depois dele: limpeza local do histórico antigo. **Impacto:** os outros 3 colaboradores do repositório precisam atualizar o clone (reclonar, ou `git fetch` e `git reset --hard origin/main`).

## DEC-009 · Gate 1 fechado, IDEA-001 descartada e início dos requisitos

- 2026-11-07 13:01 · Decidido por: usuário da sessão · Status: aceita
- **Decisão (o que o usuário disse):** (1) Gate 1 (ambiente) fechado: aprovou os dois MCPs, que passaram a "Connected", e pediu o push; (2) a IDEA-001 muda de `arquivada` para `descartada` ("essa ideia foi descartada"); (3) o tempo de 20 min para a etapa de requisitos está ok e o recorte foi aprovado; (4) ao final desta etapa, atualizar tudo e enviar um novo push.
- **Motivo: [motivo não informado]** para descartar a IDEA-001.
- **Consequências:** backlog, ficha da IDEA-001 e CLAUDE.md atualizados; [requisitos.md](requisitos.md) criado e **aguardando aprovação** (perguntas Q1 a Q8); o remoto já estava com o histórico limpo quando o agente tentou o push, e o histórico antigo (commit `16e1a5c`) foi removido do repositório local.

## DEC-010 · O PDF é base, a política da empresa define as regras, e respostas aos requisitos

- 2026-11-07 13:10 · Decidido por: usuário da sessão · Status: aceita
- **Decisão (o que o usuário disse):**
  - **O PDF do Escalista não é a fonte 100% da verdade, é uma base.** O que sair ao final do fluxo completo de definição (requisitos, negócio e técnica) será a verdade do projeto, que ainda pode mudar durante o desenvolvimento.
  - **Generalização:** questões como a folga (regra dura ou média no mês) "dependerão da política da empresa". A maioria dos pontos deve ser generalizável, para o produto funcionar conforme a política de cada empresa e a lei. Resolve a Q1: a folga não é fixada, é parâmetro da política.
  - **Conflito 2** (convenção em conflito com a emenda): "vamos definir ainda".
  - **Conflito 3** (demo antes da vigência): o usuário lembrou que "temos até 13h de amanhã para finalizar tudo". Não houve decisão sobre o rótulo de vigência simulada: segue como pergunta.
  - **Conflito 4** (Langfuse local e link público): "Ok". Junto com a Q2 ("Sim"), a tela de auditoria no app entra no escopo.
  - **Conflito 5** (JEV): um colega do time tem acesso ao JEV. Segue em aberto se e onde usar.
  - **Q6** (tipos de exceção obrigatórios na demo): "depende da política da empresa". Os tipos de exceção saem da política; os 3 da demo serão escolhidos quando existir a política fictícia da demo.
- **Motivo:** o produto deve servir à política de cada empresa e à lei, e não a uma regra fixa do PDF.
- **Consequências:** [requisitos.md](requisitos.md) atualizado (RF-22 de política parametrizável, RN-02 incluída, exceções derivadas da política, seção 9 com as respostas). Q3, Q4, Q5, Q7 e Q8 e os conflitos 2 e 3 seguem em aberto, e o documento continua sem aprovação.

## DEC-011 · Requisitos aprovados, vigência simulada rotulada e JEV descartado

- 2026-11-07 13:13 · Decidido por: usuário da sessão · Status: aceita
- **Decisão (o que o usuário disse):** (1) aprova o [requisitos.md](requisitos.md), com as pendências marcadas; (2) a tela mostra o rótulo "vigência simulada a partir de ≈16/12/2026" (conflito 3: "Sim"); (3) "esqueça o JEV": o JEV está descartado.
- **Motivo: [motivo não informado]** para descartar o JEV. Pelo texto do usuário, a prioridade é fechar o gate logo.
- **Consequências:** gate de ambiente já fechado ([DEC-009](#dec-009--gate-1-fechado-idea-001-descartada-e-início-dos-requisitos)) e gate de requisitos fechado agora; RN-11 criado (rótulo de vigência simulada); RN-07 mantém "toda a inferência via Featherless", sem JEV; a Q4 e o conflito 5 estão resolvidos. A Q7 fica como escrito no documento (RF-13 desejável). **Pendências encaminhadas:** hospedagem (Q3) e mínimo de evals (Q5) vão para a etapa técnica; o conflito 2 (convenção em conflito com a emenda) segue "a definir". Próxima etapa: negócio. **[Parcialmente substituída pelas DEC-013, DEC-014 e DEC-015: prioridades de RF-09, RF-16, RF-19 e RF-20, RH-05 e a ordem de corte.]**

## DEC-012 · A etapa de negócio passa a ser a definição do produto

- 2026-11-07 13:24 · Decidido por: usuário da sessão · Status: aceita
- **Decisão (o que o usuário disse):** em negócio, o usuário quer definir: as features do produto; a capacidade de cada feature; como o produto se generaliza; o que fica com o agente; o que fica com o humano; como o agente interage com o humano; quais as entradas e as saídas; os fluxos de cada feature, "etc.".
- **Motivo:** o que foi entregue antes (pesquisa de mercado, rubrica e pitch) não cobria a definição do produto.
- **Consequências:** [produto.md](produto.md) foi criado agora, em rascunho, com F1 a F10, quem decide o quê, interação agente e humano, generalização, entradas e saídas, capacidade e 7 decisões (P1 a P7). Isso **supera a espera** registrada na [DEC-003](#dec-003--escalista-idea-002-como-direção-do-projeto-e-participação-no-desafio-tako) para criar `produto.md`; `arquitetura.md` continua para a etapa técnica. A pesquisa de mercado, a rubrica (14/20) e o pitch ficam como apoio na [ficha](ideacao/ideias/IDEA-002-escalista.md) e em [entrega.md](entrega.md). O Gate 2 passa a incluir a aprovação do `produto.md`.

## DEC-013 · Fase 1 da entrevista de produto: lista de features e prioridade do v1

- 2026-11-07 14:13 · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Gate 2, entrevista de definição de produto, Fase 1. O usuário listou as features dele num arquivo temporário (`features.md`, não versionado) **antes** de ver o rascunho F1 a F10 do [produto.md](produto.md). A lista dele está resumida em [produto.md, seção 1.1](produto.md).
- **Decisão (o que o usuário disse):**
  - **Lista própria:** #1 Otimização de escala (recebe a escala atual da empresa em qualquer formato, padroniza, estrutura dados e variáveis, otimiza com pesquisa operacional pelo menor custo e maior cobertura); #2 Acompanhamento de escala (agente passivo e ativo: presença, horas, faltas, registros, avisos e remanejamento); #3 sazonalidade e demanda ("talvez, se viável", sem "como funciona").
  - **Primeiro momento de valor para o jurado:** "Escala pronta, legal e ao menor custo".
  - **Mantém como feature própria:** Política e cartão de regras; Aprovação e fila de exceções; Painel de impacto e auditoria. Não marcou a troca de turno.
  - **Modo ativo no v1:** passivo completo mais 1 gatilho ativo.
  - **Entrada:** 2 ou 3 formatos reais de escala no v1.
  - **Sazonalidade:** desejável, na forma de eventos que aumentam a demanda.
- **Motivo:** [motivo não informado].
- **Alternativas consideradas (as oferecidas):** só o modo passivo, ou ativo completo; formato fixo, ou qualquer formato sem limite; sazonalidade cortável, ou previsão a partir de histórico.
- **Consequências:** [produto.md](produto.md) ganha a lista FT-01 a FT-06 e o P6 fica respondido. Em [requisitos.md](requisitos.md): o RF-16 (atraso proativo) sai do primeiro corte (C1) e passa a obrigatório **só no gatilho**, o RF-03 é ampliado, e RF-23 (ingestão) e RF-24 (eventos de demanda) são novos. Isso **substitui, nessa parte, a prioridade aprovada na [DEC-011](#dec-011--requisitos-aprovados-vigência-simulada-rotulada-e-jev-descartado)**. O escopo do v1 cresce e o risco do filtro G2 aumenta (nota na [ficha](ideacao/ideias/IDEA-002-escalista.md)). **Assumido pelo agente como [PROPOSTA], sem confirmação do usuário:** a simulação 44h para 42h como "e se" dentro da otimização, o canal do colaborador e o fechamento com o ponto dentro do acompanhamento, e a troca de turno como cortável. Serão confirmados na Fase 2. **[Parcialmente superada pela [DEC-014](#dec-014--fase-2-da-entrevista-de-produto-detalhamento-das-features-e-mudanças-em-requisitos-aprovados): os 3 gatilhos ativos no v1, a simulação como feature própria.]**

## DEC-014 · Fase 2 da entrevista de produto: detalhamento das features e mudanças em requisitos aprovados

- 2026-11-07 14:36 · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Gate 2, Fase 2. FT-01 a FT-05 foram detalhados em [produto.md, seção 1.2](produto.md); FT-06 e FT-07 só em esboço.
- **Decisão (o que o usuário disse):**
  - **FT-02:** a escala existente entra em XLSX, CSV e PDF; o gerente confirma sempre um resumo curto da leitura; o resultado é
    antes e depois (custo, horas, extras, cobertura, economia), medido pelo solver; a escala vira nativa e o agente a verifica toda
    semana por um critério "ainda a definir"; o gerente edita direto e também pede edição em texto ao agente; a simulação 44h para
    42h é feature própria (FT-07).
  - **FT-03:** os **3 gatilhos ativos** (falta ou atraso, hora extra estourando o limite, aviso de necessidade de hora extra) entram
    no v1; a cobertura exige **confirmação prévia do colaborador e validação do gerente, sempre**; se o colega não responde, oferece
    ao próximo, e sem mais ninguém abre exceção ao gerente; a comprovação entra em **PDF ou foto**.
  - **FT-01:** o agente **lê a convenção em PDF** e propõe as regras; em conflito ou ambiguidade aplica a mais restritiva,
    provisória, e abre exceção ao DP.
  - **FT-04:** sem resposta no prazo, escala ao próximo decisor e, sem ninguém, o turno fica descoberto.
  - **FT-05:** "% de faltas cobertas sem hora extra" substitui "% sem o gerente".
  - Confirmou "como está" os itens derivados dos requisitos em FT-02, FT-03, FT-01, FT-04 e FT-05.
- **Motivo:** [motivo não informado].
- **Alternativas consideradas (as oferecidas):** só falta ou atraso como gatilho; manter o RH-05; texto digitado ou PDF como
  comprovação; YAML ou formulário para a política; bloquear ou seguir a lei no conflito de regra; insistir no mesmo decisor.
- **Consequências (substitui, nas partes abaixo, requisitos aprovados na [DEC-011](#dec-011--requisitos-aprovados-vigência-simulada-rotulada-e-jev-descartado)):**
  **RH-05 substituído** (o gerente valida sempre); **RF-16** cobre os 3 gatilhos (substitui a DEC-013, que dizia 1); **RF-19** (foto do
  atestado) e **RF-20** (convenção em PDF) sobem de cortáveis (C2, C3) para obrigatórios; **RF-09** passa de S para M; RF-14 troca a
  métrica; conflitos 2 e 6 resolvidos; P1, P4, P6 e P7 respondidas e P3 em parte. Novos: RF-25 a RF-28 e RX-13. **O escopo do v1
  cresce muito:** dos cortes do PDF só a ponte real do WhatsApp e o polimento continuam cortáveis; a ordem de corte fica para a
  Fase 3. **Abertos:** critério da reotimização semanal, o que dispara o aviso de necessidade de hora extra, a regra do FT-06, as
  opções de exceção e os 3 tipos da demo (saem da política fictícia), o FT-07 em esboço, o P2 (abono provisório) e o canal e prazo
  do aviso semanal.

## DEC-015 · Fase 3 da entrevista de produto: ordem de corte, abono, edição do gerente e papéis

- 2026-11-07 14:39 · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Gate 2, Fase 3 (transversais). Resolve o que restava de P2, P3, P5 e a ordem de corte.
- **Decisão (o que o usuário disse):**
  - **Ordem de corte**, se o tempo estourar: (1) FT-06 eventos de demanda; (2) os gatilhos de hora extra (fica falta ou atraso);
    (3) a foto do atestado (fica PDF); (4) a leitura da convenção em PDF (vira YAML); (5) a reotimização semanal.
  - **P2:** o abono do atestado válido **nasce provisório até o DP confirmar**.
  - **P5:** a edição do gerente (na grade ou em texto) é revalidada a cada vez; a que viola regra dura é **bloqueada**, com a regra
    violada à mostra, e o gerente pode abrir uma exceção ao DP.
  - **Papéis:** o jurado **escolhe uma persona** (gerente, DP ou colaboradora), sem login, e **vê a rede fictícia toda**; a persona só
    muda as telas e as ações.
- **Motivo:** [motivo não informado].
- **Alternativas consideradas (as oferecidas):** cortar primeiro as leituras de PDF, ou não definir a ordem; abono direto, ou sem
  abono; avisar sem bloquear, ou sem revalidação; persona com permissões reais.
- **Consequências:** [produto.md](produto.md) reescrito (Fase 4) com tudo isso; a ordem do PDF para os cortes (C1 a C5) está
  **substituída** por esta; RF-26 perde a marca de proposta (recusa com o motivo, P5); permissões por papel ficam como roadmap, o
  v1 não demonstra isolamento (o jurado vê a rede toda). **[Em parte substituída pela DEC-017: landing com login e botões de demo; cada papel vê só as telas e ações dele.]**

## DEC-016 · Gate 2 (negócio) aprovado, plano de horas a reescrever e avaliação refeita

- 2026-11-07 14:47 · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Fase 4 da entrevista concluída; auditoria `/sync-docs` com 5 perguntas ao usuário.
- **Decisão (o que o usuário disse):**
  - **Aprova o [produto.md](produto.md)**, com as pendências da seção 12 (incluindo o P3 do DP). **Gate 2 fechado.**
  - **Plano de horas:** reescrever as janelas. O usuário informa que o fim do dia às 17h **não impede** o time de continuar depois
    das 17h ("podemos"). O guia não diz isso e os organizadores não confirmaram (pergunta 3 do [estado](estado-do-projeto.md)).
  - **Avaliação:** refazer a rubrica da IDEA-002 com o produto definido.
  - O `features.md` temporário foi **apagado pelo usuário**.
  - Sobre a tabela do time e a premissa (e) da DEC-003 (ponte do WhatsApp): perguntou "como assim"; sem decisão ainda.
- **Motivo:** [motivo não informado].
- **Alternativas consideradas:** nenhuma registrada.
- **Consequências:** `produto.md` passa a **aprovado**; a próxima etapa é a técnica (Gate 3), com `arquitetura.md`. O plano de horas
  foi reescrito como **[PROPOSTA]** com as janelas após as 17h dependentes da disponibilidade do time (`[PREENCHER]`). Avaliação
  refeita às 14:47: 14/20 iguais, risco alto, G2 mais frágil e G7 com a dúvida do modelo de visão (ver a
  [ficha](ideacao/ideias/IDEA-002-escalista.md)). A IDEA-002 segue `escolhida` (provisória).

## DEC-017 · Requisitos adicionais do usuário, Gate de negócio fechado e início da etapa técnica

- 2026-11-07 14:57 · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** depois de aprovar o [produto.md](produto.md) ([DEC-016](#dec-016--gate-2-negócio-aprovado-plano-de-horas-a-reescrever-e-avaliação-refeita)), o usuário enviou requisitos do gestor, do trabalhador e não funcionais (em [requisitos.md, seção 10](requisitos.md), RF-29 a RF-42 e RN-12 a RN-14) e pediu para registrá-los, fechar o Gate de negócio e partir para o técnico.
- **Decisão (o que o usuário disse):**
  - **Login:** a landing page tem login real e botões de demo que entram com um clique (escolheu a primeira opção). Cada papel vê só as telas e as ações dele. Substitui, nesse ponto, a persona sem login da [DEC-015](#dec-015--fase-3-da-entrevista-de-produto-ordem-de-corte-abono-edição-do-gerente-e-papéis); o botão de demo mantém o jurado sem cadastro (RE-07).
  - **Conversa do gestor (somente leitura):** "pode ser uma feature a mais", **separada do agente de otimização e do de acompanhamento** (FT-08). A prioridade não foi dita: `[PREENCHER]`.
  - **Número do canal:** no WhatsApp real, número fora do quadro é recusado; no celular simulado, o jurado escolhe uma pessoa do quadro. O RF-12 e o RX-10 mudam.
  - **Prioridade:** v1 = agenda e motivo para o trabalhador, reotimizar quando quiser e definir quadro e horários; desejável (cortado logo depois do FT-06) = questionar a escala, consulta futura, aprovar remanejo, demanda maior ou menor e tom configurável.
  - **Gate de negócio fechado** com esses itens.
- **Motivo:** [motivo não informado].
- **Alternativas consideradas (as oferecidas):** login real com contas na submissão, ou sem login; chat obrigatório no v1, ou só "por quê?" por evento; recusa total do número desconhecido, ou modo demo ligável; tudo no v1, ou tudo desejável.
- **Consequências:** `requisitos.md` e `produto.md` atualizados. **Assumido pelo agente como `[PROPOSTA]`:** o FT-08 é desejável e cortado logo depois do FT-06 enquanto o usuário não disser a prioridade, e sobre leis o agente só cita o cartão de regras e a emenda, com fonte e o aviso "não é parecer jurídico". **Ficou `[PREENCHER]`:** prioridade do FT-08, RN-12 (injeção de prompt), RN-13 (quais dados além de CID e imagem), o que é o "gestor de RH", o que é a "consulta" do RF-40, e a pergunta sobre bloqueio do número (Q9, técnica). Começa a etapa técnica (Gate 3).

## DEC-018 · Gate 3, rodada 1: LangGraph nos três agentes, React + Vite e TDD no núcleo

- 2026-11-07 (hora aproximada, entre 15h03 e 15h14; não registrada) · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Gate 3 (técnica), rodada 1. Os três agentes são separados ([DEC-017](#dec-017--requisitos-adicionais-do-usuário-gate-de-negócio-fechado-e-início-da-etapa-técnica)).
- **Decisão (o que o usuário escolheu entre as opções oferecidas):**
  - **Orquestração:** LangGraph nos três agentes (otimização, acompanhamento e assistente do gestor).
  - **Front-end:** React + Vite (SPA).
  - **TDD:** TDD no núcleo, teste de fumaça no resto. Isto **relaxa, por decisão do usuário, o TDD das instruções globais** (o `CLAUDE.md` exige decisão registrada). O núcleo: regras do cartão, solver e verificador, leitura dos 3 formatos, privacidade do CID e da imagem (RN-06) e controle de acesso por papel.
- **Motivo: [motivo não informado]** nas três escolhas.
- **Alternativas consideradas (as oferecidas):** Python puro com eventos (recomendada pelo agente) ou híbrido; FastAPI com Jinja2 e HTMX (recomendada) ou Streamlit/Gradio; TDD pleno ou sem TDD.
- **Consequências:** [arquitetura.md](arquitetura.md) criado. O agente registrou como `[PROPOSTA]`, sem confirmação: estado dos fluxos nas tabelas do domínio, sem checkpointer do LangGraph. O React exige build de Node no mesmo contêiner (pesa na hospedagem). O LangGraph confirma o item "planejado" da declaração de ferramentas; o agente não achou fonte que meça a compatibilidade dele com o tool calling da Featherless **[NÃO ENCONTRADO]**.

## DEC-019 · Gate 3, rodada 2: spike do WhatsApp, relógio simulado e 30 evals

- 2026-11-07 (hora aproximada, entre 15h03 e 15h14; não registrada) · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Gate 3, rodada 2. Ponte real do WhatsApp (RF-21, cortável), gatilhos ativos do FT-03 e evals (Q5).
- **Decisão (o que o usuário escolheu entre as opções oferecidas):**
  - **WhatsApp real:** spike de 1 hora com critério de abandono (não cortou do v1; o simulador continua o caminho garantido, RF-11).
  - **Ponto e relógio:** relógio simulado controlável (interface `Clock`, botões de avanço, ponto simulado com desvios plantados, varredor determinístico que também faz a verificação semanal).
  - **Evals (Q5):** 30 cenários, 20 sem modelo e 10 com modelo, rodando com um comando.
- **Motivo: [motivo não informado]** nas três escolhas.
- **Alternativas consideradas (as oferecidas):** cortar a ponte do v1 (recomendada pelo agente) ou fazê-la fluxo principal; agendador real com APScheduler, ou os dois; 15 cenários, ou decidir depois das medições.
- **Consequências:** Q5 resolvida; Q9 (bloqueio do número) segue aberta, com mitigações `[PROPOSTA]` em [arquitetura.md](arquitetura.md), seção 10. **Ficou `[PREENCHER]`:** quando fazer o spike (depende de chip, aparelho e do núcleo pronto) e o critério de abandono exato (o agente propôs "recebe e responde a um número de teste de forma estável em 1 hora"). Não haverá agendador real em segundo plano; a tela rotula o tempo como simulado.

## DEC-020 · Gate 3, rodada 3: modelos da Featherless, determinismo do solver e foto do atestado por visão

- 2026-11-07 (hora aproximada, entre 15h03 e 15h14; não registrada) · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** Gate 3, rodada 3, com as pesquisas de 07/11/2026 (modelos e limites da Featherless; solver e leitura de arquivos).
- **Decisão (o que o usuário escolheu entre as opções oferecidas):**
  - **Modelos:** dois fixos, com teste de fumaça: pequeno `Qwen/Qwen3.5-9B` e grande `google/gemma-4-31B-it`, em variáveis de ambiente, com modelo reserva por papel. **Nenhum foi testado em português nem em tool calling.**
  - **Determinismo:** persistir a escala resolvida (entradas, parâmetros, seed, hash) e reverificar com o verificador independente. **Altera o critério de aceite do RF-05** ("mesma entrada gera a mesma escala"), que passa a ser "escala gravada e reverificada com 0 violações". Se 1 thread couber no tempo medido, usa-se 1 thread.
  - **Foto do atestado:** modelo de visão da Featherless (`Qwen/Qwen3.5-9B`), sem Tesseract.
- **Motivo: [motivo não informado]** nas três escolhas.
- **Alternativas consideradas (as oferecidas):** um modelo por etapa; um modelo grande para tudo; exigir 1 thread sempre; paralelo sem garantia; OCR local (Tesseract) com modelo de texto; os dois.
- **Consequências:** [requisitos.md](requisitos.md) (RF-05, RF-19, RN-04) e [declaracao-ferramentas.md](declaracao-ferramentas.md) atualizados. **Risco declarado:** a imagem do atestado, com o CID, trafega pela Featherless (terceiro); com dado sintético não é problema, mas o argumento de LGPD "o CID não sai do servidor" **não vale** e não deve ir ao pitch. A dúvida do filtro G7 sobre modelo com visão está **resolvida** [FATO, featherless.ai/docs/vision, 07/11/2026]; o crédito de US$ 25 segue não resgatado.

## DEC-021 · Gate 3, rodada 4: hospedagem fica para depois e rastro em tabela do app com Langfuse local

- 2026-11-07 (hora aproximada, entre 15h03 e 15h14; não registrada) · Decidido por: usuário da sessão · Status: aceita nos itens abaixo; **hospedagem pendente**
- **Contexto:** Gate 3, rodada 4, com a pesquisa de hospedagem e Langfuse de 07/11/2026.
- **Decisão (o que o usuário disse):**
  - **Hospedagem do link público (Q3 dos requisitos, pergunta 6 do estado):** "Vamos ver isso depois." **Nenhuma opção adotada**; fica `[PREENCHER]`: o usuário não disse quando.
  - **Rastro:** tabela de rastro no app (a tela de auditoria é a prova do jurado, RN-02) mais Langfuse local no notebook. Para a submissão: vídeo, prints e export JSON, declarando que o Langfuse roda localmente.
- **Motivo: [motivo não informado]** nas duas respostas.
- **Alternativas consideradas (as oferecidas):** Fly.io (a recomendação do agente), Render pago com Postgres, Render grátis com pinger, notebook com túnel; e, para o rastro, só a tabela do app ou Langfuse exposto por túnel.
- **Consequências:** a pergunta 10 do estado (onde roda o Langfuse) está resolvida: local. A pergunta 6 segue em aberto, e **sem hospedagem o link estável (RE-07, RN-10) continua sem solução**, o maior risco do filtro G2. O agente adotou por padrão **apenas** o que não bloqueia: `[PROPOSTA]` SQLAlchemy sobre SQLite, portável a Postgres, e Dockerfile multi-stage.

## DEC-022 · Gate 3 (técnica) aprovado; implementação ainda não começa

- 2026-11-07 (hora aproximada, 15h19; não registrada) · Decidido por: usuário da sessão · Status: aceita
- **Contexto:** o agente entregou [arquitetura.md](arquitetura.md) com a seção 2.1 (estilo e regra de dependência) e pediu o "aprovado".
- **Decisão (o que o usuário disse):** "Aprovado." e, sobre o passo seguinte, "Não implemente ainda."
- **Motivo: [motivo não informado].**
- **Alternativas consideradas:** nenhuma registrada.
- **Consequências:** Gate 3 fechado. **O usuário não comentou item a item:** os itens que o agente rotulou `[PROPOSTA]` na arquitetura (D12 a D17: login com `scrypt` e cookie assinado, segurança mínima contra injeção de prompt, estado dos fluxos sem checkpointer, catálogo de turnos, regras como primitivas, estilo e regra de dependência) **seguem rotulados `[PROPOSTA]`** e são a base de trabalho; qualquer um pode mudar por nova DEC. **Segue `[PREENCHER]`:** hospedagem (Q3), os quatro pontos de negócio (prioridade do FT-08, "gestor de RH", "consulta" do RF-40, dados do RN-13), o critério da reotimização semanal, o que dispara o RF-28, a política fictícia da demo, quando fazer o spike do WhatsApp e a tabela do time. **Nada foi implementado:** `src/`, `tests/` e `pyproject.toml` seguem como estavam (as dependências da seção 19 da arquitetura ainda não entraram com `uv add`).
