# Estado do projeto

> **Fonte da verdade do momento.** Atualize ao fim de cada bloco de trabalho (ver "Documentação viva" no
> [CLAUDE.md](../CLAUDE.md)). Última atualização: **2026-11-07 15:49** (Recife), por Claude, ao sincronizar depois do merge do PR #1 por Pedro Veloso
> (regras legais em `data/regras/`, DEC-023 e DEC-024) e do pool de chaves da Featherless (DEC-025, ainda sem commit).

## Fase atual

**2 · Definição (concluída às ~15h19; a 3 · Construção ainda não começou).** Fases: 1 Ideação → 2 Definição → 3 Construção → 4 Medição e polimento → 5 Submissão →
6 Demo Day. A ideia foi escolhida às 12h16 de sábado, de forma provisória ([DEC-003](decisoes.md)). Nesta fase, o usuário
aprova em gates: ambiente, requisitos, negócio e técnica ([DEC-005](decisoes.md)). `produto.md` foi criado na etapa de negócio ([DEC-012](decisoes.md)); `arquitetura.md` foi criado na etapa técnica. Gates fechados: ambiente ([DEC-009](decisoes.md)), requisitos ([DEC-011](decisoes.md)) e negócio ([DEC-016](decisoes.md), [DEC-017](decisoes.md)); a técnica foi aprovada ([DEC-018](decisoes.md) a [DEC-022](decisoes.md)).

## Ideia escolhida

**IDEA-002 · Escalista** (digital worker de escala e jornada, Desafio Tako, frente DP), **provisória**, por
[DEC-003](decisoes.md). Ficha: [IDEA-002](ideacao/ideias/IDEA-002-escalista.md). Foi escolhida sem comparação com outras candidatas. Filtros e rubrica aplicados em 2026-11-07 13:18 e refeitos às 14:47 com o produto definido: 14/20, risco alto (proposta do agente; o time confirma). Backlog em [ideacao/backlog-ideias.md](ideacao/backlog-ideias.md).

## Time

| Pessoa | Perfil / foco | Disponibilidade |
|---|---|---|
| [PREENCHER] | | |

Mínimo 2, máximo 4 pessoas (guia, seção 5). Recomenda-se ao menos um perfil técnico forte.

## Próximas ações

- [x] ~~Time alinhar restrições e semear o backlog ([como-ideiar.md](ideacao/como-ideiar.md), passos 1 e 2)~~: superada, a ideia
      foi escolhida pela [DEC-003](decisoes.md) sem esse passo (auditoria de 14:42).
- [x] Filtrar e pontuar a IDEA-002 com [criterios.md](ideacao/criterios.md): feito às 13:18 e refeito às 14:47 com o produto
      definido (14/20, risco alto); o time ainda confirma a pontuação.
- [x] Decidir a ideia e registrar (`/decisao`): Escalista, [DEC-003](decisoes.md), provisória.
- [ ] Fluxo com o usuário, com gate em cada etapa ([DEC-005](decisoes.md)): ambiente fechado ([DEC-009](decisoes.md)) →
      requisitos fechados ([DEC-011](decisoes.md)) → negócio fechado ([DEC-016](decisoes.md), [DEC-017](decisoes.md)) → técnica
      fechada ([DEC-022](decisoes.md)) → implementação (ainda não começou).
- [ ] Time confirmar a premissa (e) da DEC-003 (a escolha do usuário na [DEC-019](decisoes.md), spike de 1 h do WhatsApp, coincide com ela, mas o time não confirmou) (a (a) foi substituída pela [DEC-014](decisoes.md); as demais foram resolvidas ou viraram pergunta) e preencher a tabela do time.
- [x] Remediação do histórico concluída ([DEC-007](decisoes.md)): remoto e repositório local limpos.
- [x] Requisitos aprovados ([DEC-011](decisoes.md)). Das pendências para a etapa técnica: Q5 (evals) foi resolvida ([DEC-019](decisoes.md)), o conflito 2 foi resolvido ([DEC-014](decisoes.md)) e a hospedagem (Q3) segue em aberto ([DEC-021](decisoes.md)).
- [x] **Gate 2 (negócio) aprovado pelo usuário em 07/11 às 14h47** ([DEC-016](decisoes.md)) e fechado de novo às 14h57 com os requisitos adicionais ([DEC-017](decisoes.md)): entrevista de 13h28 a 14h39 ([DEC-013](decisoes.md) a [DEC-015](decisoes.md)) e `produto.md` aprovado, com as pendências da seção 12 (inclusive o P3 do DP). Rever depois, sem bloquear: a [ficha](ideacao/ideias/IDEA-002-escalista.md) (avaliação, hipóteses) e o pitch em [entrega.md](entrega.md) (seção 3.1).
- [x] **Gate 3 (técnica) aprovado pelo usuário às ~15h19** ([DEC-022](decisoes.md); o usuário pediu "não implemente ainda").
      `arquitetura.md` criado até 15h14 ([DEC-018](decisoes.md) a [DEC-021](decisoes.md)). As três pesquisas com fonte foram refeitas e concluídas (modelos e limites da Featherless, com visão;
      hospedagem e Langfuse; solver e leitura de arquivos). Q5 (evals) resolvida. **Hospedagem (Q3) segue `[PREENCHER]`**: o usuário disse
      "vamos ver isso depois". Pendências do negócio em [produto.md](produto.md), seções 12 e 13.
- [ ] **Featherless:** 3 das 4 pessoas resgataram e criaram chaves (palavra do usuário, 15h46; **nenhuma chave foi testada**). Falta a 4ª pessoa resgatar hoje (o código vence em 08/11), mover as chaves do `APIs.yaml` para o `.env` e apagar o arquivo, e testar cada chave ([DEC-025](decisoes.md)).
- [ ] **Aguardando o comando do usuário para começar a implementar** (ele disse "não implemente ainda"). Depois dele: `uv add` das dependências ([arquitetura.md](arquitetura.md), seção 19), teste de fumaça dos
      modelos, primeiro benchmark do solver (60 × 7), e decidir a hospedagem com um deploy de teste.
- [x] Regras legais em YAML: [ec141.yaml](../data/regras/lei/ec141.yaml) e [clt.yaml](../data/regras/lei/clt.yaml),
      conferidas por Claude contra o Planalto (status `interpretacao` ou `pendente`; formato no [README](../data/regras/README.md)).
- [ ] **Quem escreve o solver e o verificador:** confirmar que o formato dos YAMLs de `data/regras/` serve (campos `de`,
      `ate`, `horas`, `status` e `acao`), antes de escrever mais regras.
- [ ] **Quadro sintético com campo de sexo**, para aplicar o domingo quinzenal das empregadas ([DEC-023](decisoes.md)).
- [ ] Escrever a convenção e a política fictícias da demo em `data/regras/convencao/` e `data/regras/politica/`. Depende da
      pergunta 17 e define as 3 exceções da demo (Q6 de `requisitos.md`).
- [ ] Opcional: alguém do time lê os artigos no Planalto e troca `interpretacao` por `conferida` (RN-09).
- [ ] Confirmar no WhatsApp os pontos em aberto abaixo.
- [ ] Decidir se o time concorre aos créditos AWS (exige domínio próprio e e-mail corporativo; ver
      [contexto-hackathon.md](contexto-hackathon.md)).

## Perguntas em aberto

| # | Pergunta | Quem resolve | Status |
|---|---|---|---|
| 1 | Início do código é 10h ou 10h30? O guia diz as duas coisas (programação: 10h30; FAQ: 10h) | WhatsApp dos organizadores | Em aberto; tratar 10h30 como oficial |
| 2 | Dados sintéticos e integrações simuladas são permitidos no tema aberto? O guia só os permite expressamente no Desafio Tako | WhatsApp dos organizadores | Em aberto para o tema aberto. Com o Desafio Tako ([DEC-003](decisoes.md)), o guia permite expressamente dados sintéticos e integrações simuladas; declarar o caráter sintético de qualquer forma |
| 3 | Pode-se continuar trabalhando fora do local depois das 17h de sábado? O guia não diz | WhatsApp dos organizadores | Em aberto. O usuário afirma que o time pode continuar depois das 17h ([DEC-016](decisoes.md)); o guia não diz e os organizadores não confirmaram |
| 4 | O repositório nasceu de um scaffold (commit inicial às 10h55 de 07/11). Qual a origem e há algo que não seja nosso? | Time | Respondida ([DEC-006](decisoes.md)): template de um amigo do usuário que trabalha em uma empresa; o usuário confirma que entra na regra de clean room. 10 arquivos do commit inicial citam "[termo de terceiro omitido por clean room]". Remediação na pergunta 11. Ver [declaracao-ferramentas.md](declaracao-ferramentas.md) |
| 5 | Concorrer ou não ao Desafio Tako (RH)? | Time | Resolvida em 07/11 12h16: concorre ([DEC-003](decisoes.md), provisória); sinalizar na submissão |
| 6 | Hospedagem do link público e da ponte: o time não tem servidor nem conta hoje | Time | **Em aberto, `[PREENCHER]`:** pesquisada em 07/11 ([arquitetura.md](arquitetura.md), seção 12); o usuário disse "vamos ver isso depois" ([DEC-021](decisoes.md)). Sem ela o link estável (RE-07, RN-10) não existe. A ponte do WhatsApp roda só no notebook |
| 7 | Chip dedicado e aparelho para a ponte real do WhatsApp | Time | "Vamos ver"; sem chip, só o simulador de celular |
| 8 | Resgate dos US$ 25 da Featherless por integrante | Time | **3 de 4 resgataram** (palavra do usuário, 15h46; sem teste ainda); falta 1 pessoa. Link e código estão só no guia original (redigidos na cópia local). O código vence em 08/11 e tem limite de resgates. As chaves formam um pool com failover ([DEC-025](decisoes.md)) |
| 9 | Domínio próprio (créditos AWS) | Time | O time não tem; só importa se ficar no pódio |
| 10 | Onde roda o Langfuse self-hosted, sem servidor | Time | **Resolvida ([DEC-021](decisoes.md)):** só no notebook (a doc recomenda 4 CPU e 16 GiB); o jurado vê a tabela de rastro do app |
| 11 | Como remediar o histórico do scaffold (commit inicial `16e1a5c`, remoto privado) | Time | Resolvida ([DEC-007](decisoes.md), [DEC-008](decisoes.md)): histórico recriado e publicado no `main` do remoto; branch antigo e commit `16e1a5c` removidos do repositório local. Os outros 3 colaboradores precisam atualizar o clone |
| 12 | Onde usar o JEV (TypeSafe), se for usar | Time | Resolvida: JEV descartado ([DEC-011](decisoes.md)) |
| 13 | O `features.md` temporário (raiz, não versionado) deve ser apagado, movido para `docs/arquivo/` ou versionado? O conteúdo já está resumido em [produto.md](produto.md), seção 11 | Usuário | Resolvida: o usuário apagou o arquivo ([DEC-016](decisoes.md)) |
| 15 | "Gestor de RH" nos requisitos do usuário: é o gerente, o DP ou um papel novo? | Usuário | Em aberto ([requisitos.md](requisitos.md), seção 10) |
| 16 | Como lidar com bloqueio do número do WhatsApp (Q9)? | Etapa técnica | Em aberto: o spike de 1 h foi mantido ([DEC-019](decisoes.md)); mitigações `[PROPOSTA]` e `[INFERÊNCIA]`, sem fonte pesquisada, em [arquitetura.md](arquitetura.md), seção 10 |
| 14 | O cronograma do [plano de horas](plano-de-horas.md) está atrasado frente à Definição e o v1 cresceu: reescrever as janelas? | Time | Resolvida em 14:47: janelas reescritas como `[PROPOSTA]` ([DEC-016](decisoes.md)); o time confirma e informa a disponibilidade à noite |
| 17 | As 42h não cabem em 5 dias de 8h (com 2 repousos, 5 × 8h = 40h). A convenção fictícia da demo permite passar de 8h por dia? (a) Sim: cláusula com base no art. 7º da EC, e a demo usa as 42h inteiras. (b) Não: o teto prático é 40h, e o agente leva isso ao DP como exceção | Time | **Parcialmente respondida ([DEC-024](decisoes.md)):** é parâmetro da política e da legislação, não regra fixa; o valor da convenção fictícia da demo segue `[PREENCHER]`. Antes: Pedro Veloso disse "decido depois". Ver `jornada_diaria_max` em [ec141.yaml](../data/regras/lei/ec141.yaml) |

## Riscos atuais

- **Tempo:** ideação consome horas do hacking. Mitigação: funil com tempo marcado em
  [como-ideiar.md](ideacao/como-ideiar.md) e gate de decisão no [plano](plano-de-horas.md).
- **Escopo:** tentar fazer seis coisas. Mitigação: prioridades do [CLAUDE.md](../CLAUDE.md). **Aumentou na entrevista
  ([DEC-014](decisoes.md)):** os cortes C1 a C3 do PDF entraram no v1 e há leitura de 3 formatos, reotimização semanal e 3 gatilhos
  ativos; só a ponte real do WhatsApp e o polimento seguem cortáveis. Ordem de corte: a definir na Fase 3 **[INFERÊNCIA]**.
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
| 2026-11-07 15:49 | PR #1 aceito por Pedro Veloso às ~15h49 (18h49 UTC) como merge commit `19ef74f`, que contém o meu merge `f904ef2`; `main` local atualizada por `git pull --ff-only` e as alterações da DEC-025 reaplicadas por cima, sem conflito. Sincronia: a DEC-023 (art. 386) e a DEC-024 (Q13) agora estão no `main`; **a DEC-023 segue sem confirmação do time**; README aponta para `data/regras/`. Alterações da DEC-025 **ainda sem commit**; branch local `merge/legal-rules-data` já está contida no `main` | Claude |
| 2026-11-07 15:46 | [DEC-025](decisoes.md): as chaves da Featherless das 4 pessoas formam um pool com failover (3 de 4 resgataram, **sem teste**); `.env.example` com `FEATHERLESS_API_KEY_1` a `_4` (só nomes); [arquitetura.md](arquitetura.md) seção 7 e riscos com o desenho do failover (`[PROPOSTA]`); `APIs.yaml` no `.gitignore` por proteção; pergunta 8 e próximas ações com o resgate. Alterações **sem commit** (depois movidas para a `main` local, ver a linha seguinte); nenhum código | Claude |
| 2026-11-07 15:41 | Integração do PR #1 (`chore/legal-rules-data`, Pedro Veloso) numa branch de merge, sem push: conflitos em `decisoes.md`, `estado-do-projeto.md` e `declaracao-ferramentas.md` resolvidos com o conteúdo do `main` por cima; a decisão do art. 386 virou [DEC-023](decisoes.md) (o `main` já tinha DEC-013 a DEC-022) e a pergunta 13 do PR virou a 17; [DEC-024](decisoes.md) registra a resposta do usuário à Q13; referências nos YAMLs e no README de `data/regras/` atualizadas. **Atenção:** os carimbos dos registros do branch (15:20, 15:35, 15:50) não batem com os commits dele (14:57 e 15:30); mantidos como estavam | Claude |
| 2026-11-07 15:50 | Merge do `main` no branch `chore/legal-rules-data`: a DEC do art. 386 virou [DEC-023](decisoes.md), porque o `main` já tinha a DEC-012; o conflito 2 de `requisitos.md` passa a ter regra (a mais restritiva, provisória, com exceção ao DP; resumo do time das 15h20 e P1 de `produto.md`) e os YAMLs apontam para ela; novas ações para os dados de regras | Claude |
| 2026-11-07 15:35 | [DEC-023](decisoes.md) (registrada como DEC-012 no branch): o art. 386 da CLT (domingo quinzenal para empregadas) entra como regra dura e prevalece sobre a Lei 10.101 no comércio; `domingo_mulher` passa a `interpretacao`, e o `clt.yaml` fica com 17 itens `interpretacao` e nenhum `pendente`; o quadro sintético precisa de um campo de sexo | Claude |
| 2026-11-07 15:20 | `data/regras/lei/clt.yaml` criado a partir do texto compilado do Planalto (CLT, Lei 10.101/2000 e art. 7º da CF): 12 regras e 5 exceções; 16 itens `interpretacao` e 1 `pendente` (`domingo_mulher`, art. 386); nenhum `conferida` | Claude |
| 2026-11-07 15:19 | [DEC-022](decisoes.md): o usuário aprovou o Gate 3 e pediu para não implementar ainda; `arquitetura.md`, plano de horas e estado atualizados; os itens `[PROPOSTA]` seguem rotulados (a aprovação não os comentou); nenhum código nem dependência | Claude |
| 2026-11-07 15:17 | A pedido do usuário, [arquitetura.md](arquitetura.md) ganha a seção 2.1 (estilo: monolito modular, hexagonal leve e núcleo funcional; regras de dependência e teste de importação) e a linha D17, ambas `[PROPOSTA]` até o "aprovado" do Gate 3; sem DEC nova, porque o usuário só autorizou escrever a seção | Claude |
| 2026-11-07 15:15 | Auditoria `/sync-docs` (relógio do `date`: 15h15; sem código: `src/` e `tests/` vazios; `pyproject.toml` sem mudança, o que bate com a declaração; `.env.example` com 13 nomes, todos citados em [arquitetura.md](arquitetura.md); 0 links quebrados em 22 arquivos `.md`). **Corrigido:** carimbos de hora que eu tinha gravado à frente do relógio (15h18 a 15h25) nas docs, e as horas das DEC-018 a DEC-021, agora marcadas como aproximadas (não foram registradas); `arquitetura.md` incluído no índice do README e na estrutura do CLAUDE.md; seção 12 do [produto.md](produto.md) aponta para o que a técnica já tratou; premissa (e) da DEC-003 anotada com a DEC-019. **Pendente de decisão humana:** ver a resposta desta auditoria | Claude |
| 2026-11-07 15:14 | Gate 3 (técnica) conduzido em 4 rodadas: [arquitetura.md](arquitetura.md) criado; [DEC-018](decisoes.md) a [DEC-021](decisoes.md) (LangGraph, React + Vite, TDD no núcleo, spike do WhatsApp, relógio simulado, 30 evals, modelos, determinismo, foto por visão, rastro; hospedagem adiada); [requisitos.md](requisitos.md) (RF-05, RF-19, RN-04, Q3, Q5), [declaracao-ferramentas.md](declaracao-ferramentas.md), [plano-de-horas.md](plano-de-horas.md) e `.env.example` atualizados; nenhuma dependência adicionada ao `pyproject.toml`, nenhum código de produto; aguardando o "aprovado" | Claude |
| 2026-11-07 14:59 | A pedido do usuário, o Gate 3 não segue nesta sessão: 3 pesquisas técnicas em subagentes interrompidas sem resultado; nenhum arquivo de código ou de docs técnico foi criado; `arquitetura.md` não existe | Claude |
| 2026-11-07 14:57 | [DEC-017](decisoes.md): requisitos adicionais do usuário registrados ([requisitos.md](requisitos.md), seção 10: RF-29 a RF-42, RN-12 a RN-14) e [produto.md](produto.md) (seção 13, FT-08, papéis, ordem de corte); login com botões de demo, FT-08 como agente separado, número fora do quadro recusado no canal real; Gate de negócio fechado; começa o Gate 3 (técnica); pendente: prioridade do FT-08, RN-12, RN-13, "gestor de RH", "consulta" do RF-40 | Claude |
| 2026-11-07 14:47 | [DEC-016](decisoes.md): `produto.md` aprovado (Gate 2 fechado); `plano-de-horas.md` reescrito como `[PROPOSTA]` (Definição técnica até 15h30, núcleo até 19h, noite condicionada à disponibilidade, 17h deixa de ser gate duro por informação do usuário); avaliação da IDEA-002 refeita com `/avaliar-ideias` (14/20 iguais, risco alto, G2 mais frágil, G7 com a dúvida do modelo de visão); backlog, ficha e perguntas 3, 13 e 14 atualizados | Claude |
| 2026-11-07 14:45 | `ec141.yaml` conferido contra o Planalto, artigo por artigo: 10 itens `interpretacao` e 2 `pendente` (marcos, pela data exata, e hipersuficiente, sem teto do RGPS); nenhum `conferida` (falta leitura do time); `acao` padronizado (`escalar` ou `verificar_convencao`); pergunta 17 aberta (42h contra 8h por dia) | Claude |
| 2026-11-07 14:42 | Auditoria `/sync-docs` (sem código: `src/` e `tests/` vazios; `pyproject.toml` e `.env.example` batem com a declaração; 0 links quebrados em 21 arquivos `.md`, incluindo CLAUDE.md e README). **Corrigido:** próximas ações do estado (itens de ideação e Gate 1 já fechados), 2 perguntas novas (13 e 14); `declaracao-ferramentas.md` (MCPs conectados, execução da remediação concluída, dados da escala em XLSX, CSV e PDF, atestado em PDF e foto, leitura de documentos a decidir); `plano-de-horas.md` (situação, atraso e marcos); `backlog-ideias.md` e ficha da IDEA-002 (autonomia e descrição); `entrega.md` (pitch); `decisoes.md` (notas de substituição em DEC-003 e DEC-011); README (hook já registrado, links de requisitos e produto). **Pendente de decisão humana:** perguntas 13 e 14, tabela do time, status e pontuação da IDEA-002 | Claude |
| 2026-11-07 14:39 | [DEC-015](decisoes.md): Fase 3 (ordem de corte, abono provisório, edição bloqueada se viola regra, persona sem login); [produto.md](produto.md) reescrito (Fase 4, seções 1 a 12); [requisitos.md](requisitos.md): ordem de corte substituída, RF-26, demo e painel ajustados; aguardando o "aprovado" do Gate 2 | Claude |
| 2026-11-07 14:36 | [DEC-014](decisoes.md): Fase 2 da entrevista; FT-01 a FT-05 detalhados em [produto.md](produto.md) (seção 1.2), FT-06 e FT-07 em esboço; [requisitos.md](requisitos.md): RH-05 substituído, RF-09, RF-14, RF-16, RF-19 e RF-20 mudam, RF-25 a RF-28 e RX-13 novos, conflitos 2 e 6 resolvidos; P1, P4, P6 e P7 respondidas | Claude |
| 2026-11-07 14:15 | Branch `chore/legal-rules-data`: `data/regras/` com as camadas `lei/`, `convencao/` e `politica/` ([README](../data/regras/README.md)); `lei/ec141.yaml` (enviado por Pedro Veloso, YAML válido, 6 regras e 5 exceções; ainda sem status por regra, RN-09); origem declarada em `declaracao-ferramentas.md` | Claude |
| 2026-11-07 14:13 | [DEC-013](decisoes.md): Fase 1 da entrevista de produto; lista FT-01 a FT-06 e prioridade em [produto.md](produto.md) (seção 1.1, P6 respondida); [requisitos.md](requisitos.md): RF-03 ampliado, RF-16 sai de C1 e vira obrigatório só no gatilho, RF-23 e RF-24 novos; nota de risco na ficha da IDEA-002 | Claude |
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
