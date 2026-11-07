# Registro de decisões

Última atualização: 2026-11-07 13:24. Uma entrada por decisão, mais recente embaixo. **Nunca apague nem reescreva uma
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
    gerente.
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
- **Consequências:** gate de ambiente já fechado ([DEC-009](#dec-009--gate-1-fechado-idea-001-descartada-e-início-dos-requisitos)) e gate de requisitos fechado agora; RN-11 criado (rótulo de vigência simulada); RN-07 mantém "toda a inferência via Featherless", sem JEV; a Q4 e o conflito 5 estão resolvidos. A Q7 fica como escrito no documento (RF-13 desejável). **Pendências encaminhadas:** hospedagem (Q3) e mínimo de evals (Q5) vão para a etapa técnica; o conflito 2 (convenção em conflito com a emenda) segue "a definir". Próxima etapa: negócio.

## DEC-012 · A etapa de negócio passa a ser a definição do produto

- 2026-11-07 13:24 · Decidido por: usuário da sessão · Status: aceita
- **Decisão (o que o usuário disse):** em negócio, o usuário quer definir: as features do produto; a capacidade de cada feature; como o produto se generaliza; o que fica com o agente; o que fica com o humano; como o agente interage com o humano; quais as entradas e as saídas; os fluxos de cada feature, "etc.".
- **Motivo:** o que foi entregue antes (pesquisa de mercado, rubrica e pitch) não cobria a definição do produto.
- **Consequências:** [produto.md](produto.md) foi criado agora, em rascunho, com F1 a F10, quem decide o quê, interação agente e humano, generalização, entradas e saídas, capacidade e 7 decisões (P1 a P7). Isso **supera a espera** registrada na [DEC-003](#dec-003--escalista-idea-002-como-direção-do-projeto-e-participação-no-desafio-tako) para criar `produto.md`; `arquitetura.md` continua para a etapa técnica. A pesquisa de mercado, a rubrica (14/20) e o pitch ficam como apoio na [ficha](ideacao/ideias/IDEA-002-escalista.md) e em [entrega.md](entrega.md). O Gate 2 passa a incluir a aprovação do `produto.md`.
