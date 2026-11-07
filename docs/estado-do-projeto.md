# Estado do projeto

> **Fonte da verdade do momento.** Atualize ao fim de cada bloco de trabalho (ver "Documentação viva" no
> [CLAUDE.md](../CLAUDE.md)). Última atualização: **2026-11-07 15:50** (Recife), por Claude, ao integrar o `main` no branch
> `chore/legal-rules-data` (regras legais em `data/regras/`, DEC-013).

## Fase atual

**2 · Definição (em andamento).** Fases: 1 Ideação → 2 Definição → 3 Construção → 4 Medição e polimento → 5 Submissão →
6 Demo Day. A ideia foi escolhida às 12h16 de sábado, de forma provisória ([DEC-003](decisoes.md)). Nesta fase, o usuário
aprova em gates: ambiente, requisitos, negócio e técnica ([DEC-005](decisoes.md)). `produto.md` foi criado na etapa de negócio ([DEC-012](decisoes.md)); `arquitetura.md` só depois do gate de negócio. Gates fechados: ambiente ([DEC-009](decisoes.md)) e requisitos ([DEC-011](decisoes.md)).

## Ideia escolhida

**IDEA-002 · Escalista** (digital worker de escala e jornada, Desafio Tako, frente DP), **provisória**, por
[DEC-003](decisoes.md). Ficha: [IDEA-002](ideacao/ideias/IDEA-002-escalista.md). Foi escolhida sem comparação com outras candidatas. Filtros e rubrica aplicados em 2026-11-07 13:18: 14/20, risco alto (proposta do agente; o time confirma). Backlog em [ideacao/backlog-ideias.md](ideacao/backlog-ideias.md).

## Time

| Pessoa | Perfil / foco | Disponibilidade |
|---|---|---|
| [PREENCHER] | | |

Mínimo 2, máximo 4 pessoas (guia, seção 5). Recomenda-se ao menos um perfil técnico forte.

## Próximas ações

- [ ] Time alinhar restrições (perfis, interesses, o que fica de fora) e semear o backlog: ver
      [como-ideiar.md](ideacao/como-ideiar.md), passos 1 e 2.
- [ ] Filtrar e pontuar as finalistas com [criterios.md](ideacao/criterios.md) (`/avaliar-ideias`). Ainda não feito para
      a IDEA-002; o Gate 2 aplica filtros e rubrica.
- [x] Decidir a ideia e registrar (`/decisao`): Escalista, [DEC-003](decisoes.md), provisória.
- [ ] Fluxo com o usuário, com gate em cada etapa: ambiente (Gate 1, falta fechar) → requisitos → negócio → técnica →
      implementação ([DEC-005](decisoes.md)).
- [ ] Time confirmar as premissas (a) e (e) da DEC-003 (as demais foram resolvidas ou viraram pergunta) e preencher a tabela do time.
- [x] Remediação do histórico concluída ([DEC-007](decisoes.md)): remoto e repositório local limpos.
- [x] Requisitos aprovados ([DEC-011](decisoes.md)). Pendências para a etapa técnica: hospedagem (Q3) e mínimo de evals (Q5). O conflito 2 tem regra pelo resumo do time das 15h20: vale a mais restritiva, provisória, e abre exceção ao DP (P1 de [produto.md](produto.md)); o registro formal chega com o push dessa sessão.
- [ ] **Gate 2 (negócio) com o usuário:** definir o produto em [produto.md](produto.md) (decisões P1 a P7) e rever a [ficha](ideacao/ideias/IDEA-002-escalista.md) (avaliação, hipóteses) e o pitch em [entrega.md](entrega.md) (seção 3.1).
- [x] Regras legais em YAML: [ec141.yaml](../data/regras/lei/ec141.yaml) e [clt.yaml](../data/regras/lei/clt.yaml),
      conferidas por Claude contra o Planalto (status `interpretacao` ou `pendente`; formato no [README](../data/regras/README.md)).
- [ ] **Quem escreve o solver e o verificador:** confirmar que o formato dos YAMLs de `data/regras/` serve (campos `de`,
      `ate`, `horas`, `status` e `acao`), antes de escrever mais regras.
- [ ] **Quadro sintético com campo de sexo**, para aplicar o domingo quinzenal das empregadas ([DEC-013](decisoes.md)).
- [ ] Escrever a convenção e a política fictícias da demo em `data/regras/convencao/` e `data/regras/politica/`. Depende da
      pergunta 13 e define as 3 exceções da demo (Q6 de `requisitos.md`).
- [ ] Opcional: alguém do time lê os artigos no Planalto e troca `interpretacao` por `conferida` (RN-09).
- [ ] Confirmar no WhatsApp os pontos em aberto abaixo.
- [ ] Decidir se o time concorre aos créditos AWS (exige domínio próprio e e-mail corporativo; ver
      [contexto-hackathon.md](contexto-hackathon.md)).

## Perguntas em aberto

| # | Pergunta | Quem resolve | Status |
|---|---|---|---|
| 1 | Início do código é 10h ou 10h30? O guia diz as duas coisas (programação: 10h30; FAQ: 10h) | WhatsApp dos organizadores | Em aberto; tratar 10h30 como oficial |
| 2 | Dados sintéticos e integrações simuladas são permitidos no tema aberto? O guia só os permite expressamente no Desafio Tako | WhatsApp dos organizadores | Em aberto para o tema aberto. Com o Desafio Tako ([DEC-003](decisoes.md)), o guia permite expressamente dados sintéticos e integrações simuladas; declarar o caráter sintético de qualquer forma |
| 3 | Pode-se continuar trabalhando fora do local depois das 17h de sábado? O guia não diz | WhatsApp dos organizadores | Em aberto |
| 4 | O repositório nasceu de um scaffold (commit inicial às 10h55 de 07/11). Qual a origem e há algo que não seja nosso? | Time | Respondida ([DEC-006](decisoes.md)): template de um amigo do usuário que trabalha em uma empresa; o usuário confirma que entra na regra de clean room. 10 arquivos do commit inicial citam "[termo de terceiro omitido por clean room]". Remediação na pergunta 11. Ver [declaracao-ferramentas.md](declaracao-ferramentas.md) |
| 5 | Concorrer ou não ao Desafio Tako (RH)? | Time | Resolvida em 07/11 12h16: concorre ([DEC-003](decisoes.md), provisória); sinalizar na submissão |
| 6 | Hospedagem do link público e da ponte: o time não tem servidor nem conta hoje | Time | Em aberto; entra nos requisitos e na definição técnica. O guia exige link navegável e testável na submissão |
| 7 | Chip dedicado e aparelho para a ponte real do WhatsApp | Time | "Vamos ver"; sem chip, só o simulador de celular |
| 8 | Resgate dos US$ 25 da Featherless por integrante | Time | Ninguém resgatou ainda. Link e código estão só no guia original (redigidos na cópia local). O código vence em 08/11 e tem limite de resgates |
| 9 | Domínio próprio (créditos AWS) | Time | O time não tem; só importa se ficar no pódio |
| 10 | Onde roda o Langfuse self-hosted, sem servidor | Time | Em aberto; sem servidor, só na máquina local ([DEC-005](decisoes.md)) |
| 11 | Como remediar o histórico do scaffold (commit inicial `16e1a5c`, remoto privado) | Time | Resolvida ([DEC-007](decisoes.md), [DEC-008](decisoes.md)): histórico recriado e publicado no `main` do remoto; branch antigo e commit `16e1a5c` removidos do repositório local. Os outros 3 colaboradores precisam atualizar o clone |
| 12 | Onde usar o JEV (TypeSafe), se for usar | Time | Resolvida: JEV descartado ([DEC-011](decisoes.md)) |
| 13 | As 42h não cabem em 5 dias de 8h (com 2 repousos, 5 × 8h = 40h). A convenção fictícia da demo permite passar de 8h por dia? (a) Sim: cláusula com base no art. 7º da EC, e a demo usa as 42h inteiras. (b) Não: o teto prático é 40h, e o agente leva isso ao DP como exceção | Time | Em aberto (Pedro Veloso: "decido depois"). Ver `jornada_diaria_max` em [ec141.yaml](../data/regras/lei/ec141.yaml) |

## Riscos atuais

- **Tempo:** ideação consome horas do hacking. Mitigação: funil com tempo marcado em
  [como-ideiar.md](ideacao/como-ideiar.md) e gate de decisão no [plano](plano-de-horas.md).
- **Escopo:** tentar fazer seis coisas. Mitigação: prioridades do [CLAUDE.md](../CLAUDE.md).
- **Ponte do WhatsApp:** biblioteca não oficial, com risco de banimento e de queda de sessão; precisa de servidor sempre
  ligado. Mitigação: simulador de celular como caminho padrão. Detalhes na [ficha da IDEA-002](ideacao/ideias/IDEA-002-escalista.md).
- **Clean room:** ideias inspiradas em trabalho de empregadores ou clientes. Mitigação: filtro G5 em
  [criterios.md](ideacao/criterios.md).

## Métricas medidas

Vazio. Preencher só com número **medido** (trace, evals, cronômetro), com data e como foi medido. Estimativas vão
rotuladas como premissa.

| Métrica | Valor | Como foi medido | Data |
|---|---|---|---|
| | | | |

## Registro de atualizações

Mais recente primeiro. Uma linha por mudança relevante (docs, decisão, código).

| Data e hora | O quê | Por |
|---|---|---|
| 2026-11-07 15:50 | Merge do `main` no branch `chore/legal-rules-data`: a DEC do art. 386 virou [DEC-013](decisoes.md), porque o `main` já tinha a DEC-012; o conflito 2 de `requisitos.md` passa a ter regra (a mais restritiva, provisória, com exceção ao DP; resumo do time das 15h20 e P1 de `produto.md`) e os YAMLs apontam para ela; novas ações para os dados de regras | Claude |
| 2026-11-07 15:35 | [DEC-013](decisoes.md) (registrada como DEC-012 no branch): o art. 386 da CLT (domingo quinzenal para empregadas) entra como regra dura e prevalece sobre a Lei 10.101 no comércio; `domingo_mulher` passa a `interpretacao`, e o `clt.yaml` fica com 17 itens `interpretacao` e nenhum `pendente`; o quadro sintético precisa de um campo de sexo | Claude |
| 2026-11-07 15:20 | `data/regras/lei/clt.yaml` criado a partir do texto compilado do Planalto (CLT, Lei 10.101/2000 e art. 7º da CF): 12 regras e 5 exceções; 16 itens `interpretacao` e 1 `pendente` (`domingo_mulher`, art. 386); nenhum `conferida` | Claude |
| 2026-11-07 14:45 | `ec141.yaml` conferido contra o Planalto, artigo por artigo: 10 itens `interpretacao` e 2 `pendente` (marcos, pela data exata, e hipersuficiente, sem teto do RGPS); nenhum `conferida` (falta leitura do time); `acao` padronizado (`escalar` ou `verificar_convencao`); pergunta 13 aberta (42h contra 8h por dia) | Claude |
| 2026-11-07 14:15 | Branch `chore/legal-rules-data`: `data/regras/` com as camadas `lei/`, `convencao/` e `politica/` ([README](../data/regras/README.md)); `lei/ec141.yaml` (enviado por Pedro Veloso, YAML válido, 6 regras e 5 exceções; ainda sem status por regra, RN-09); origem declarada em `declaracao-ferramentas.md` | Claude |
| 2026-11-07 13:24 | [DEC-012](decisoes.md): a etapa de negócio passa a ser a definição do produto; [produto.md](produto.md) criado (F1 a F10, quem decide o quê, interação, generalização, entradas e saídas, capacidade; decisões P1 a P7); CLAUDE.md lista o arquivo | Claude |
| 2026-11-07 13:18 | Etapa de negócio: pesquisa de concorrência, preço e mercado e dor/custo (subagentes, com fonte); IDEA-002 avaliada (G1 a G7 passam, G2, G4 e G7 com condição; A4 B3 C3 D4 = 14/20; risco alto); ficha, backlog e `entrega.md` (pitch, seção 3.1) atualizados; 11 hipóteses listadas | Claude |
| 2026-11-07 13:13 | [DEC-011](decisoes.md): requisitos aprovados; rótulo de vigência simulada (RN-11); JEV descartado; Q3 e Q5 e conflito 2 encaminhados à etapa técnica; etapa de negócio aberta | Claude |
| 2026-11-07 13:10 | [DEC-010](decisoes.md): o PDF é base, não a verdade; política da empresa define as regras (RF-22 novo); tela de auditoria incluída (RN-02); exceções derivadas da política; conflitos 2 e 3 e Q3, Q4, Q5, Q7, Q8 em aberto; `requisitos.md` com seção 9 | Claude |
| 2026-11-07 13:01 | [DEC-009](decisoes.md): Gate 1 fechado (MCPs conectados); IDEA-001 descartada; [requisitos.md](requisitos.md) criado (11 de elegibilidade, 21 funcionais, 12 de exceção, 6 de atos humanos, 10 não funcionais; 9 conflitos entre fontes; 8 perguntas); histórico antigo removido do repositório local | Claude |
| 2026-11-07 12:54 | [DEC-008](decisoes.md): identidade do git (conta `pedrohmvv`), dois commits no `clean-main`, `git` e `gh` liberados no `settings.json`, PDF da ideia antiga fora do git, termo de terceiro retirado das docs; push para o remoto bloqueado pelo modo automático | Claude |
| 2026-11-07 12:44 | [DEC-007](decisoes.md): opção A, recriar o histórico. `LICENSE` vazio, `.vscode/settings.json` e `uv.lock` removidos; `pyproject.toml` reescrito (só fastapi, uvicorn, pydantic, pydantic-settings e dev pytest, pytest-cov, ruff); `uv.lock` regenerado (26 pacotes); branch órfão `clean-main` com índice limpo; sem commit (falta identidade do git) | Claude |
| 2026-11-07 12:35 | [DEC-006](decisoes.md): respostas 12 a 15 (JEV em aberto, aviso de dado fictício confirmado, sem validação externa, conectores só se necessários) e origem do scaffold: template de um amigo, entra no clean room; auditoria do commit inicial (31 arquivos, 10 citam "[termo de terceiro omitido por clean room]", remoto privado); perguntas 11 e 12 abertas; `declaracao-ferramentas.md` atualizada | Claude |
| 2026-11-07 12:30 | [DEC-005](decisoes.md): respostas da Etapa 0 e novo fluxo (ambiente → requisitos → negócio → técnica → implementação); Langfuse self-hosted; sem trabalho em paralelo ainda. `pyproject.toml` sem python-bcb e bs4; `.gitignore` com exceções para PDF e HTML de dados, docs e `src/`; `.env.example` com `LANGFUSE_BASE_URL`. Perguntas em aberto 6 a 10 adicionadas; a 4 tem resposta parcial | Claude |
| 2026-11-07 12:24 | [DEC-004](decisoes.md): `.claude/settings.json` criado (hook `docs_sync.py` registrado, testado com saída 0, e permissões mínimas); só os dois MCPs de documentação; skills próprias `nova-regra` e `novo-cenario-eval` ficam para depois do Gate 3. Gate 1 aguarda respostas às perguntas 5 a 11 da Etapa 0 | Claude |
| 2026-11-07 12:20 | Auditoria `/sync-docs`: 23 arquivos verificados, 0 links quebrados; `src/` e `tests/` vazios, `pyproject.toml` ainda do scaffold; `.env.example` bate com a declaração; corrigido o README (dizia "ideia não escolhida") e acrescentado o risco da ponte do WhatsApp; ainda sem commit, `.claude/settings.json` ausente (hook não registrado) | Claude |
| 2026-11-07 12:18 | `.mcp.json` criado com os MCPs de documentação do Langfuse e do LangChain (planejados); `CLAUDE.md` passou a apontar para o estado em vez de repetir "ideia não escolhida"; `contexto-hackathon.md` atualizado com a escolha do Desafio Tako | Claude |
| 2026-11-07 12:16 | DEC-003 gravada: Escalista como direção (provisória) e Desafio Tako; fase passa a "2 · Definição"; premissas (a) a (f) adotadas por padrão; declaração de ferramentas e plano de horas atualizados | Claude |
| 2026-11-07 12:14 | IDEA-002 (Escalista, Desafio Tako) registrada no backlog como `candidata` e direção provisória; ficha criada em `docs/ideacao/ideias/IDEA-002-escalista.md` | Claude |
| 2026-11-07 11:55 | Documentação genérica de ideação criada em `converge-challenge-61`; ideia anterior (depósitos judiciais) arquivada como IDEA-001 | Claude |
