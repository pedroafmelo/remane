# Plano macro de implementação do Escalista

Última atualização: 2026-11-07 16:11 (Recife) · Situação: **aprovado pelo usuário em 2026-11-07 16:13** ([DEC-029](decisoes.md)) · Decisões desta etapa:
[DEC-027](decisoes.md) e [DEC-028](decisoes.md).

Este arquivo diz **o que cada camada entrega, do que depende e como saber que acabou**. Ele não repete o produto
([produto.md](produto.md)), a arquitetura ([arquitetura.md](arquitetura.md)), os requisitos ([requisitos.md](requisitos.md)) nem o
cronograma ([plano-de-horas.md](plano-de-horas.md)): aponta para eles. Cada camada ganha um plano detalhado próprio, numa sessão própria,
antes de ser executada (seção 6).

**Rótulos:** sem rótulo é decisão do usuário (com a DEC). **[PROPOSTA]** é sugestão do agente, ainda não confirmada. `[PREENCHER]` é o que
falta, com o motivo. Fatos de terceiros: **[FATO]** (fonte e data), **[INFERÊNCIA]**, **[NÃO ENCONTRADO]**. Todas as horas são
**[PROPOSTA]**, em faixa, e não foram medidas.

## 1. Visão geral

10 camadas: 9 de construção (C0 a C8) e a entrega (C9). Os **desejáveis** formam uma fila à parte (seção 5.11), puxada só se sobrar
tempo, na ordem de corte. **Evals** e **deploy** são trilhas que crescem em cada camada, e não camadas no fim ([DEC-027](decisoes.md)).

```
                 C0 Fundação (1 pessoa, sequencial)
                 ├─ C0a esqueleto local + contratos v0  ──► libera as frentes
                 └─ C0b hospedagem decidida + deploy de teste
                          │
     ┌────────────────────┼──────────────────────────┬──────────────────────────────┐
 Frente A (núcleo)   Frente B (LLM e leitura)     Frente C (API, SPA, deploy)    Frente D (dados, evals, negócio)
 C1 Domínio, regras  C3 Cliente LLM, pool de      C4 API, login, papéis e SPA    política fictícia (até 19h)
    e rede sintética    chaves, rastro               base                        dados sintéticos de arquivo,
 C2 Solver,               │                          │                           evals, pitch
    verificador, custo    │                          │
     └────────────────────┴───────────┬──────────────┘
                          C5 Primeira fatia vertical (FT-02 mínimo + FT-04 aprovação)  ◄── gate 21h30
                                      │
          ┌───────────────────────────┼──────────────────────────────┐
 C6 Leitura completa e FT-01   C7 Acompanhamento (FT-03)       C8 Exceções, painel, auditoria e FT-07
          └───────────────────────────┴──────────────┬───────────────┘
                                   fila de desejáveis (só se sobrar) e spike do WhatsApp (depois da C7)
                                                      │
                                         C9 Entrega (congelamento, vídeo, submissão)

 Trilhas: Evals E1 (C2) → E2 (C5) → E3 (C7) → E4 (C8)   ·   Deploy D0 (C0) → D1 (C4) → D2 (C5) → a cada camada
```

**Frentes ([DEC-027](decisoes.md)):** 3 frentes de código depois da C0 (A núcleo, B LLM e leitura, C API, SPA e deploy), como o usuário
escolheu. A **frente D** é `[PROPOSTA]`: com 4 pessoas até a madrugada, a quarta pessoa escreve a política fictícia (Pedro Veloso, até
19h, [DEC-028](decisoes.md)) e depois os dados sintéticos de arquivo, os evals e o material de negócio. **Quem fica em cada frente:**
`[PREENCHER]`, porque a tabela do time está vazia ([estado](estado-do-projeto.md), seção "Time").

**Regra de integração `[PROPOSTA]`:** os contratos pydantic da [arquitetura, seção 8](arquitetura.md) nascem como **v0 na C0a**. Mudança
de contrato acontece por PR pequeno, avisado às outras frentes. Cada frente trabalha num branch curto e integra no `main` ao fim de cada
tarefa, com `pytest` verde.

## 2. Caminho crítico e primeira fatia vertical

**Caminho crítico [PROPOSTA]:** C0a → C1 (subconjunto mínimo) → C2 (subconjunto mínimo) → C5 → C7 → C8 → C9. C3 e C4 correm em
paralelo e só precisam estar prontas na C5. A C6 não está no caminho crítico, porque a fatia lê CSV.

**Primeira fatia vertical ([DEC-028](decisoes.md); gate às 21h30, o que substitui o gate `[PROPOSTA]` das 19h):** no **deploy de teste**, o
jurado entra pelo botão de demo do gerente e escolhe a escala atual em **CSV sintético**. A fatia segue estes passos:

1. Validação determinística (RF-04).
2. Resumo da leitura para o gerente confirmar (RF-23).
3. Solver (RF-05).
4. Verificador independente com 0 violações (RF-02).
5. Antes e depois com custo, horas extras e cobertura (RF-14 parcial).
6. Justificativa escrita pelo **modelo pequeno** (RF-06; é o mínimo que cumpre o RE-02).
7. Aprovação do gerente e publicação da grade semanal (RF-08, RH-01).
8. `trace_event` gravado em cada passo, com `custo_usd` medido (RN-01, RN-03).

**Fora da fatia:** XLSX, PDF, leitura por modelo, convenção, FT-03, a fila de exceções completa, o painel e a auditoria em tela.

**Por isso C1 e C2 começam pelo subconjunto da fatia `[PROPOSTA]`:** rede e demanda sintéticas, CSV, as primitivas
`jornada_semanal_max`, `interjornada_min`, `repouso_semanal` e a cobertura. As demais primitivas entram depois do gate.

**Se o gate das 21h30 falhar:** aplicar a ordem de corte ([produto.md](produto.md), seção 2) e a da [arquitetura, seção 18](arquitetura.md)
antes de abrir C6 a C8. A fatia tem prioridade sobre qualquer camada nova.

## 3. Entradas externas que bloqueiam camadas

| Pendência | Bloqueia | Dono | Prazo sugerido `[PROPOSTA]` |
|---|---|---|---|
| Hospedagem do link público: **`[PREENCHER]`**; o Fly.io da [DEC-030](decisoes.md) está em suspenso e tudo do deploy foi adiado, só local por enquanto ([DEC-033](decisoes.md), [DEC-034](decisoes.md)) | C0b (G1), RE-07, RN-10 | Usuário | `[PREENCHER]` |
| Chave 1 da Featherless vazia ou ausente no `.env` | C3 (teste de fumaça, failover) | Dono da chave 1 `[PREENCHER]` | Antes da C3, ~17h30 |
| 4ª pessoa resgatar os US$ 25 (o código vence em 08/11) | C3 (pool completo), orçamento dos evals e da demo | 4ª pessoa `[PREENCHER: nome]` | Hoje, antes das 23h |
| Testar cada chave (validade, saldo, "Unlock Model") | C3, C5 | Frente B | 1ª hora da C3 |
| Política fictícia da demo: opções de exceção, prazos, os 3 tipos de exceção, valor do limite diário da convenção ([DEC-024](decisoes.md)) | C1 (camada `politica/` e `convencao/`), C7 (prazos), C8 (3 exceções) | **Pedro Veloso** ([DEC-028](decisoes.md)) | **19h** |
| "Gestor de RH": gerente, DP ou papel novo (pergunta 15) | C4 (papéis) | Usuário | Antes do plano da C4 |
| Dados do RN-13, incluindo o campo de sexo da [DEC-023](decisoes.md) | C1 (quadro sintético), C7 e C8 (filtro de saída) | Usuário | Antes do plano da C1 |
| Critério da reotimização semanal (RF-25) | C7 (varredor) | Usuário | Antes do plano da C7 |
| O que dispara o aviso de necessidade de hora extra e quem o recebe (RF-28) | C7 | Usuário | Antes do plano da C7 |
| Prioridade do FT-08; ordem entre os desejáveis; o que é a "consulta" do RF-40 | Fila de desejáveis | Usuário | Antes de abrir a fila |
| Chip e aparelho para o spike do WhatsApp (pergunta 7) | Spike (depois da C7) | Time `[PREENCHER]` | Antes do fim da C7 |
| Langfuse local no ar num notebook | Exportador opcional da C3 (corte técnico) | `[PREENCHER]` | Antes da C5 |
| Tabela do time (nomes, perfis, frente de cada um) | Divisão das frentes | Usuário | Agora |

## 4. Marcos e gates

As janelas fixas do evento e o cronograma estão no [plano de horas](plano-de-horas.md). Aqui fica só o que cada gate exige.

| Gate | Quando | Passa se | Se falhar |
|---|---|---|---|
| G0 · C0a pronta | ~17h15 `[PROPOSTA]`; **atingido às 16h41** (plano da C0) | `pytest` e `ruff` verdes; teste de fronteiras ativo; contratos v0 no `main` | As frentes não abrem; a C0 continua com prioridade |
| G1 · Hospedagem e deploy de teste | Fim da C0 ([DEC-027](decisoes.md)) | `/health` responde 200 na URL pública | Plano B: túnel do notebook ([arquitetura, seção 12](arquitetura.md)) até a decisão; registrar o risco |
| G2 · Política fictícia | 19h ([DEC-028](decisoes.md)) | YAMLs em `data/regras/politica/` e `convencao/` | C1 segue só com `lei/`; C7 e C8 esperam |
| **G3 · Primeira fatia vertical** | **21h30** ([DEC-028](decisoes.md)) | Seção 2, no deploy | Ordem de corte; nada de camada nova antes da fatia |
| G4 · Núcleo das features v1 | Dom 08h30 (janela do plano de horas) | C6, C7 e C8 concluídas ou cortadas conscientemente | Cortar na ordem do produto, seção 2 |
| G5 · Evals completos | Dom 10h30 | 30 cenários num comando, com relatório (RN-04) | Reportar só os que rodam, sem arredondar |
| G6 · Link público | Dom 11h30 (plano de horas) | Teste como jurado ([entrega.md](entrega.md), seção 2) | Parar de adicionar funções |
| G7 · Congelamento e submissão | Dom 12h00 e 13h00 | [entrega.md](entrega.md), item a item | Só correção de bug crítico |

## 5. Camadas

Política de teste ([DEC-018](decisoes.md)): **TDD estrito no núcleo** (regras, solver, verificador, leitura dos 3 formatos, RN-06,
controle de acesso por papel) e **teste de fumaça no resto**. **Toda camada termina com `uv run pytest` e `uv run ruff check .`
verdes.** Os comandos abaixo são `[PROPOSTA]`: o plano de cada camada os fixa.

### 5.0 C0 · Fundação e deploy de teste

- **Valor demonstrável:** uma URL pública responde `/health` e mostra uma página React "Escalista · dados sintéticos".
- **Escopo:** RE-01, RE-09, RN-08; [arquitetura](arquitetura.md), seções 2.1, 16 e 19. Fora: qualquer lógica de produto.
- **Entregáveis:**
  - **C0a:** `uv add` com versões e licenças conferidas (tabela abaixo); `src/escalista/` com os pacotes da seção 16 vazios;
    `domain/ports.py` (`Clock`, `LLMClient`, `TraceSink`; **`Channel` entra na C7 e `Repository` na C2**, [DEC-032](decisoes.md)); contratos v0 da seção 8 em `domain/`; configuração por
    pydantic-settings, que lê `FEATHERLESS_API_KEY_1` a `_4` sem nunca imprimir o valor; motor SQLAlchemy sobre SQLite, com `create_all`;
    pytest e ruff; **teste de importação das fronteiras** (`ast`, seção 2.1); `web/` com React e Vite; FastAPI servindo o build.
  - **C0b:** Dockerfile multi-stage (Node para o build, Python para rodar); a hospedagem decidida; o deploy de teste.
- **Depende de:** nada no código; **G1 depende da decisão de hospedagem**.
- **Pronto quando:** `uv run pytest` (inclui o teste de fronteiras, que falha se `verifier/` importar `ortools`); `uv run ruff check .`;
  `npm --prefix web run build`; `docker build .`; `curl -f https://<url>/health`.
- **Riscos e cortes:** a conta da hospedagem pode pedir cartão ou verificação ([arquitetura, seção 12](arquitetura.md)). Se travar, a C0a
  segue e o deploy roda pelo túnel do notebook até a decisão. Não cortar o teste de fronteiras.
- **Horas:** C0a 1 a 1,5 h (1 pessoa, sequencial); C0b 0,5 a 1,5 h. A C0b roda em paralelo à C1, na frente C.

**Versões conferidas para o `uv add`** ([FATO], PyPI JSON e registro do npm, consultados por subagente em 07/11/2026; o registro canônico está
em [declaracao-ferramentas.md](declaracao-ferramentas.md)): langgraph 1.2.20 (MIT), langfuse 5.2.0 (MIT), openai 3.46.0 (Apache-2.0),
sqlalchemy 2.1.8 (MIT), itsdangerous 2.2.0 (BSD-3-Clause), pypdfium2 5.15.1 (BSD-3-Clause e Apache-2.0, com licenças permissivas no
binário), react e react-dom 19.3.1 (MIT), vite 8.3.6 (MIT), @vitejs/plugin-react 6.2.1 (MIT). Nenhuma é copyleft. **Sete delas saíram
há menos de 14 dias.** **Decidido na [DEC-030](decisoes.md):** data de corte 2026-10-23 em tudo (uv e npm), o que resolveu langgraph 1.2.17, langfuse 5.0.4, openai 3.37.0 e sqlalchemy 2.1.6 (vite e plugin-react ainda não instalados); ver o [plano da C0](planos/camada-00-fundacao.md). [NÃO ENCONTRADO] compatibilidade do `langfuse.openai` com o openai 3.x
(testar na C3). O Vite 8 exige Node 20.19 ou mais, ou 22.12 ou mais.

### 5.1 C1 · Domínio, regras e rede sintética (frente A)

- **Valor demonstrável:** um comando gera a rede fictícia, e o cartão de regras carregado de `data/regras/` lista cada regra com fonte,
  status e vigência.
- **Escopo:** RF-01, RF-02 (parâmetros), RF-03, RF-04, RF-22, RN-09; contratos `Rule`, `RuleCard`, `SolveRequest`; primitivas da
  [arquitetura, seção 5](arquitetura.md). **Primeiro o subconjunto da fatia** (seção 2). Fora: leitura de arquivo (C4/C6) e convenção em PDF.
- **Entregáveis:** `domain/` (pessoa, escala, regra, evento); `rules/` (carregador das 3 camadas, validação do schema, fusão "a política só
  restringe", conflito → regra mais restritiva provisória + exceção ao DP); `synth/` (rede de ≈3 lojas e ≈60 pessoas, demanda por faixa de
  30 min, escala atual em CSV, um CSV com defeito e uma escala com violações plantadas, marca "SINTÉTICO", seed fixa).
- **Depende de:** C0a. A política fictícia (G2, 19h) entra assim que chegar. Sem ela, a C1 testa com `lei/`. O campo de sexo depende do RN-13.
- **Pronto quando:** `uv run pytest tests/domain tests/rules tests/synth`; YAML inválido é recusado com o motivo; conflito entre camadas gera
  regra provisória e um evento de exceção; `uv run python -m escalista.synth --seed 42` gera os arquivos.
- **Riscos e cortes:** o formato dos YAMLs pode não servir ao solver (próxima ação aberta no [estado](estado-do-projeto.md)). Confirmar no
  plano da C1. Corte: regras fora do subconjunto viram dado com fonte e `acao: escalar` (arquitetura, seção 5).
- **Horas:** 1,5 a 2,5 h. Em paralelo a C3 e C4.

### 5.2 C2 · Solver, verificador e custo (frente A)

- **Valor demonstrável:** a escala de 60 pessoas × 7 dias sai do solver, o verificador independente a confere com 0 violações e o custo
  antes e depois vem da mesma função.
- **Escopo:** RF-02, RF-05 (aceite da [DEC-020](decisoes.md)), RF-06 (dados da justificativa, não o texto), RF-14 (custo), RX-02, RX-12 do
  solver; [arquitetura, seção 5](arquitetura.md). Fora: replanejar trecho (entra no fim da C2 ou no começo da C7) e FT-07 (C8).
- **Entregáveis, em ordem:** (1) **benchmark 60 × 7 antes de tudo o que depende do solver**: 1 thread contra várias, registrado em Métricas
  medidas; (2) `solver/` (catálogo de turnos, CP-SAT, `num_workers` decidido pelo benchmark, seed, nomes estáveis); (3) `verifier/` em
  Python puro, implementação separada de cada primitiva; (4) função de custo; (5) persistência da escala com entradas, parâmetros, seed e hash;
  (6) replanejamento de janela (`[PROPOSTA]`, cortável para a C7).
- **Depende de:** C1, no subconjunto da fatia.
- **Pronto quando:** `uv run python -m escalista.solver.bench` grava o tempo; testes TDD de cada primitiva; **o verificador acha 100% das
  violações plantadas** (meta 0 não detectadas, RN-04); escala gravada e reverificada com 0 violações; demanda acima da capacidade vira RX-02,
  sem travar. **Trilha de evals E1:** os 10 primeiros cenários sem modelo.
- **Riscos e cortes:** solver lento (arquitetura, seção 17): limite de tempo, catálogo menor, escala pré-resolvida e persistida. Corte: o
  replanejamento de janela vai para a C7.
- **Horas:** 2 a 3,5 h (o benchmark leva 0,5 h).

### 5.3 C3 · Cliente LLM, pool de chaves e rastro (frente B)

- **Valor demonstrável:** um comando chama os 2 modelos em português, com tool calling, JSON e visão, e mostra custo e latência medidos,
  gravados em `trace_event`.
- **Escopo:** RN-01, RN-03, RN-05, RN-07, RX-12; DEC-020, DEC-021, DEC-025; [arquitetura, seções 7 e 9](arquitetura.md). Fora: os agentes
  (C5, C7), as telas de auditoria (C8) e a imagem do atestado (C7).
- **Entregáveis:**
  - `llm/`: cliente openai com `base_url` da Featherless; pool com failover em ordem; semáforo; até 3 tentativas no 503; guarda de
    orçamento por chave; saída estruturada como ferramenta com validação pydantic e até 2 reenvios.
  - Script de fumaça.
  - `audit/`: tabela `trace_event`, `TraceSink`, máscara.
  - Exportador Langfuse opcional.
- **Depende de:** C0a; das chaves válidas (seção 3).
- **Pronto quando:** o script de fumaça roda para cada chave e cada modelo, e o resultado vai a Métricas medidas. Testes com LLM falso
  cobrem três casos: 401 e 429 trocam de chave; 400 e 503 não trocam; **o valor da chave nunca aparece em log nem em trace**. Falha do
  modelo vira RX-12, sem exceção não tratada.
- **Riscos e cortes:** modelo reprovado na fumaça → reserva por papel ([PREENCHER] em [declaração](declaracao-ferramentas.md)). Corte
  técnico: o exportador Langfuse (fica só a tabela do app).
- **Horas:** 1,5 a 2,5 h. Em paralelo a C1 e C4.

### 5.4 C4 · API, login, papéis e SPA base (frente C)

- **Valor demonstrável:** na URL pública, a landing tem login e botões de demo; cada papel cai na sua tela vazia, rotulada "dados
  sintéticos" e "tempo simulado".
- **Escopo:** RF-29, RF-30, RF-12, RE-05, RE-07, RF-15 (o reset sem dados); [arquitetura, seção 11](arquitetura.md). Fora: telas de
  feature.
- **Entregáveis:**
  - `api/`: rotas, `require_role`, sessão por cookie assinado, senhas com `hashlib.scrypt`, `POST /auth/demo/{papel}` só com
    `DEMO_MODE=1` e limitado por taxa.
  - `web/`: landing, layout por papel e rótulos.
  - Deploy D1.
- **Depende de:** C0 (C0b para o deploy). **Precisa da resposta sobre o "gestor de RH"** (pergunta 15). Sem ela, entram só os 3 papéis atuais.
- **Pronto quando:** **matriz de testes rota × papel** (TDD; acesso indevido devolve 403); botão de demo recusado sem `DEMO_MODE`; a landing
  abre no deploy em janela anônima.
- **Riscos e cortes:** corte de polimento visual. Não cortar o teste de acesso.
- **Horas:** 1,5 a 2,5 h. Em paralelo a C1 a C3.

### 5.5 C5 · Primeira fatia vertical: FT-02 mínimo e aprovação do FT-04 (todas as frentes)

- **Valor demonstrável:** a seção 2, no deploy, até 21h30.
- **Escopo:** FT-02 (RF-04, RF-05, RF-06, RF-14 parcial, RF-23 em CSV, RF-33 "reotimizar quando quiser" como botão), FT-04 (RF-08, RH-01),
  RN-01, RN-03, RE-02; agente de otimização (LangGraph) com `ler_escala`, `otimizar`, `verificar` e `publicar`, este **só com aprovação
  humana gravada** (regra 5 da arquitetura, seção 2.1). Fora: o resto da seção 2.
- **Entregáveis:** `agents/optimizer/` (grafo mínimo; nós determinísticos e o modelo só na justificativa); rotas e telas: escolher o arquivo,
  resumo, antes e depois, grade, aprovar; lista simples de eventos do rastro; deploy D2; **trilha de evals E2:** `uv run python -m
  escalista.evals` roda os cenários sem modelo.
- **Depende de:** C1 e C2 (subconjunto), C3, C4.
- **Pronto quando:** teste de fumaça ponta a ponta com `TestClient` e LLM falso; **o mesmo fluxo à mão na URL pública**; `publicar` sem
  aprovação é recusado (teste); cada passo tem `trace_event` com o custo medido na justificativa.
- **Riscos e cortes:** integração de 3 frentes ao mesmo tempo. Se a justificativa pelo modelo falhar, a fatia passa com RX-12 visível,
  nunca com texto inventado.
- **Horas:** 1,5 a 2,5 h de integração.

### 5.6 C6 · Leitura completa e política (FT-01 e o resto do FT-02) (frentes B e D)

- **Valor demonstrável:** o gerente envia a escala em XLSX ou PDF e o agente devolve o mesmo resumo do CSV. O DP vê o cartão de regras com a
  cláusula de origem citada da convenção em PDF e aprova.
- **Escopo:** RF-23 (XLSX e PDF), RF-20, RF-26, RF-36, RX-01, RX-11, RX-13, RH-02, RN-12 (limites de arquivo, texto como dado); FT-01; [arquitetura, seções 6 e 14](arquitetura.md).
  Fora: o atestado (C7).
- **Entregáveis:** `ingest/` (openpyxl + defusedxml, pdfplumber, limites de segurança, extração pelo modelo grande em schema fechado,
  **checagem literal da cláusula citada**); tela do cartão com aprovação do DP; edição em texto e na grade, revalidada (P5 da
  [DEC-015](decisoes.md)); cadastro de quadro e horários; dados sintéticos de arquivo (frente D: layouts XLSX e PDF, convenção fictícia em PDF).
- **Depende de:** C5; C3; política fictícia (G2).
- **Pronto quando:** TDD da leitura dos 3 formatos com os layouts sintéticos; arquivo com defeito → RX-13 com o motivo; cláusula inventada
  pelo modelo é descartada (teste); edição que viola regra dura é bloqueada com a regra à mostra. **Trilha E2:** 2 cenários de leitura de
  escala com modelo.
- **Riscos e cortes:** **corte 5 do produto**: a convenção em PDF vira YAML. Células mescladas sem fonte (`[INFERÊNCIA]`, arquitetura,
  seção 6).
- **Horas:** 2 a 3 h. Em paralelo a C7 e C8.

### 5.7 C7 · Acompanhamento: FT-03 com canal simulado, relógio, ponto e atestado (frentes B e C)

- **Valor demonstrável:** o jurado avança o relógio e o agente detecta a falta. A colaboradora manda o atestado pelo celular simulado e um
  colega confirma o turno. O gerente valida e a escala muda (demo, item 2 de [requisitos, seção 6](requisitos.md)).
- **Escopo:** FT-03 (RF-09, RF-11, RF-16, RF-19, RF-25, RF-27, RF-28, RF-37, RF-38, RF-42), RH-05 substituído, RH-06, RN-06, RX-05,
  RX-06, RX-08, RX-09, RX-10; abono provisório (P2); `ReplanRequest`; [arquitetura, seções 4, 10 e 13](arquitetura.md).
- **Entregáveis:** `clock/` (relógio no banco, ponto simulado com desvios plantados, varredor); `channel/` (adaptador, `SimulatedPhone`,
  recusa de número fora do quadro); `agents/tracker/`; atestado em PDF (redação do CID por regex antes do modelo) e em foto (visão em memória,
  fora da instrumentação automática); celular simulado na SPA; atestados sintéticos (frente D).
- **Depende de:** C5; replanejamento de janela (C2). Precisa do RF-25 e do RF-28 (seção 3) e da política (prazos).
- **Pronto quando:** fumaça do fluxo de falta no deploy; **teste RN-06 que falha se CID ou imagem aparecer em banco, log ou trace**; número
  fora do quadro recusado e registrado (teste no adaptador); a oferta começa por quem não gera hora extra. **Trilha E3:** 6 cenários de
  atestado com modelo.
- **Riscos e cortes:** **cortes 3, 4 e 6 do produto**: os gatilhos de hora extra (fica falta ou atraso), a foto (fica o PDF) e a
  reotimização semanal. Depois desta camada, e só então, o **spike do WhatsApp** ([DEC-028](decisoes.md)): 1 h, só com chip, só no notebook.
- **Horas:** 3 a 4,5 h (a maior camada; candidata a ser dividida no plano dela).

### 5.8 C8 · Exceções, painel, auditoria e simulação de vigência (FT-04, FT-05, FT-07) (frentes A e C)

- **Valor demonstrável:** na URL, o jurado: (a) troca 44h por 42h e vê a nova escala, o custo e as contratações com o rótulo de vigência
  simulada; (b) decide uma exceção com opções e custos; (c) vai de um número do painel à regra, à mensagem e ao custo em 2 cliques.
- **Escopo:** FT-04 completo (fila, cartão, prazo, escalada ao próximo decisor), ≥ 3 tipos de exceção da política ([requisitos, seção
  3](requisitos.md)), FT-05 (RF-14, RN-02, RN-03), FT-07 (RF-07, RN-11), RF-15, RN-05 (RX-12 em cada dependência), RN-13 no filtro de saída.
- **Entregáveis:** fila e cartão de exceção; painel com números **medidos** e rotulados; tela de auditoria; comparação de vigência (o
  item 1 da demo, **primeiro desta camada**); reset da demo; testes que derrubam cada dependência.
- **Depende de:** C5; C7 para as exceções do FT-03; política (G2) para os 3 tipos.
- **Pronto quando:** 3 exceções ponta a ponta no deploy; troca de vigência sem refazer à mão; nenhum número sem rótulo na tela; um clique
  reinicia a demo. **Trilha E4:** 4 cenários de injeção e os 20 sem modelo completos (meta dos 30 em G5).
- **Riscos e cortes:** **nunca cortar exceções, rastro e evals.** Corte: polimento do painel; a 3ª exceção cai para a mais simples da
  política.
- **Horas:** 2,5 a 3,5 h.

### 5.9 C9 · Entrega

- **Valor demonstrável:** a submissão enviada, com o link testável, o vídeo e a declaração completos.
- **Escopo:** RE-03 a RE-08, RN-10; [entrega.md](entrega.md) inteiro; `/sync-docs`.
- **Entregáveis:** congelamento; relatório dos 30 evals; métricas medidas no [estado](estado-do-projeto.md); vídeo (plano B); descrição
  com o Desafio Tako e a declaração de dados sintéticos; [declaração de ferramentas](declaracao-ferramentas.md) sem `[PREENCHER]`; revisão
  de clean room.
- **Depende de:** G6 (link às 11h30).
- **Pronto quando:** checklist de [entrega.md](entrega.md) fechado e o envio confirmado até 13h00.
- **Horas:** 1,5 a 2 h (janelas no [plano de horas](plano-de-horas.md)). A frente D adianta o pitch e o vídeo desde sábado.

### 5.10 Trilhas transversais

- **Evals ([DEC-019](decisoes.md)):** E1 (C2, 10 sem modelo) → E2 (C5 e C6, comando único e leitura) → E3 (C7, atestado) → E4 (C8,
  injeção e os 20 sem modelo). O relatório diz quantos usam modelo. O custo dos evals sai da guarda de orçamento.
- **Deploy:** D0 (C0) → D1 (C4) → D2 (C5) → um deploy ao fim de cada camada. Um deploy quebrado bloqueia a camada seguinte.
- **Docs:** cada camada atualiza o [estado](estado-do-projeto.md) (registro e métricas) e a [declaração](declaracao-ferramentas.md) no
  mesmo turno.

### 5.11 Fila de desejáveis (só se sobrar, na ordem de corte invertida)

Itens: FT-06 e RF-34 (1º a cortar); FT-08, assistente do gestor somente leitura (prioridade `[PREENCHER]`); RF-39 a RF-41; RN-14; troca de
turno (RF-10); RF-17; RF-13. A ordem entre eles é `[PREENCHER]` (produto, seção 2). Cada item é planejado em poucas linhas no momento em que for
puxado. Não há sessão própria.

## 6. Convenção dos planos de camada

- **Arquivo:** `docs/planos/camada-NN-nome.md` (por exemplo `camada-00-fundacao.md`). A pasta é criada com o primeiro plano.
- **Cada plano tem:** objetivo e valor demonstrável; IDs cobertos e o que fica de fora; lista ordenada de tarefas (no núcleo, a lista de
  testes do TDD na ordem); contratos tocados e quem mais os usa; arquivos e pastas; critério de pronto com os comandos exatos;
  riscos e cortes; estimativa em faixa; modelo de desenvolvimento usado; pendências que bloqueiam; ao fim, um **registro de execução**
  (início, fim, desvios, métricas medidas).
- **Fluxo:** planejar (sessão própria) → o usuário aprova → executar → atualizar a tabela abaixo e o [estado](estado-do-projeto.md).

### Status das camadas

| Camada | Frente | Status | Plano |
|---|---|---|---|
| C0 Fundação e deploy de teste | 1 pessoa, depois C | C0a concluída (G0 às 16h41); C0b parada: Docker pronto, deploy adiado ([DEC-033](decisoes.md), [DEC-034](decisoes.md)) | [camada-00-fundacao.md](planos/camada-00-fundacao.md) |
| C1 Domínio, regras e rede sintética | A | a planejar | — |
| C2 Solver, verificador e custo | A | a planejar | — |
| C3 Cliente LLM, pool de chaves e rastro | B | a planejar | — |
| C4 API, login, papéis e SPA base | C | a planejar | — |
| C5 Primeira fatia vertical | todas | a planejar | — |
| C6 Leitura completa e FT-01 | B, D | a planejar | — |
| C7 Acompanhamento (FT-03) | B, C | a planejar | — |
| C8 Exceções, painel, auditoria e FT-07 | A, C | a planejar | — |
| C9 Entrega | todas | a planejar | — |

Status possíveis: `a planejar`, `planejada`, `em execução`, `concluída`, `cortada (motivo)`.

## 7. Modelos de desenvolvimento por camada

Isto vale para o **Claude Code que planeja e escreve o código**, e não para o produto (os modelos do produto são da Featherless,
[DEC-020](decisoes.md)). O uso não sai dos US$ 25 da Featherless. **Política escolhida ([DEC-028](decisoes.md)):** o Opus 5.5
(`claude-opus-5-5`) planeja todas as camadas. O Sonnet 5.5 (`claude-sonnet-5-5`) executa a maior parte. O Opus 5.5 executa as partes de
alto custo de erro, e o Haiku 5.5 (`claude-haiku-5-5`) só as mecânicas. **Sem benchmark nosso:** as razões abaixo são critérios
(custo do erro, ambiguidade, contexto, custo e latência, reversibilidade), e toda comparação entre modelos é **[INFERÊNCIA]**. Preços não
foram consultados `[NÃO ENCONTRADO]`. A distribuição por camada é **[PROPOSTA]**.

| Camada | Planejar | Executar (opcional) | Motivo | Alternativa mais barata | O que se perde `[INFERÊNCIA]` |
|---|---|---|---|---|---|
| C0 | Opus 5.5 | Sonnet 5.5; Haiku 5.5 no scaffold do `web/` | Baixa ambiguidade e reversível; o teste de fronteiras define a disciplina das outras camadas | Sonnet planeja | Menos cuidado no teste de fronteiras e na política de versões |
| C1 | Opus 5.5 | Opus 5.5 nas regras (fusão, conflito); Haiku 5.5 nos geradores sintéticos | Erro na fusão de camadas vira regra errada em todo o produto | Sonnet executa as regras | Mais risco em casos de conflito e vigência |
| C2 | Opus 5.5 | **Opus 5.5** | Maior custo de erro: um solver e um verificador que errem juntos derrubam o RN-04 e a demo | Sonnet executa | Mais risco na modelagem do CP-SAT e na independência do verificador |
| C3 | Opus 5.5 | Sonnet 5.5; Opus 5.5 na máscara do trace e no tratamento das chaves | Segredos e RN-06 no trace | Sonnet em tudo | Risco de vazar a chave ou o dado sensível no log |
| C4 | Opus 5.5 | **Opus 5.5** no acesso e na sessão; Sonnet 5.5 na SPA | Controle de acesso é núcleo (DEC-018) | Sonnet em tudo | Furo de autorização que o jurado pode achar |
| C5 | Opus 5.5 | Sonnet 5.5; Opus 5.5 na ferramenta `publicar` | Integração de 3 frentes; contexto grande | Sonnet planeja | Plano de integração mais raso |
| C6 | Opus 5.5 | Sonnet 5.5; Opus 5.5 nos limites de arquivo e na checagem da cláusula (RN-12) | Entrada não confiável | Sonnet em tudo | Menos defesa contra injeção e XML bomb |
| C7 | Opus 5.5 | Sonnet 5.5; **Opus 5.5** no atestado (RN-06), no RX-10 e nas aprovações | Privacidade e mensagem a terceiro | Sonnet em tudo | Risco de CID ou imagem persistidos |
| C8 | Opus 5.5 | Sonnet 5.5 | Telas e agregações, reversíveis | Sonnet planeja | Painel com número mal rotulado |
| C9 | Opus 5.5 | Sonnet 5.5; Haiku 5.5 no `/sync-docs` e no checklist | Texto para jurado e declaração honesta | Sonnet planeja | Descrição menos precisa |
| Fila de desejáveis | Opus 5.5 | Sonnet 5.5; Opus 5.5 na conexão somente leitura do FT-08 | Privilégio mínimo estrutural (RN-12) | Sonnet em tudo | Assistente com acesso de escrita por engano |

## 8. Riscos do plano

| Risco | Efeito | Mitigação |
|---|---|---|
| Contratos v0 mudam no TDD da C1 e da C2 | Retrabalho e conflito nas frentes B e C | PR pequeno avisado; contratos mínimos; integração frequente no `main` |
| Hospedagem trava no cadastro | Sem G1; RE-07 em risco | Túnel do notebook como ponte; decidir no fim da C0 ([DEC-027](decisoes.md)) |
| Chaves não testadas ou sem saldo | C3 e a fatia sem modelo | Testar na 1ª hora da C3; a 4ª pessoa resgata hoje |
| Política fictícia atrasa | C7 e C8 sem exceções da demo | G2 às 19h; C1 segue com `lei/` |
| C7 grande demais | FT-03 incompleto no Demo Day | Dividir no plano da C7; cortes 3, 4 e 6 do produto |
| Cansaço da madrugada | Bugs no núcleo | TDD no núcleo; deploy a cada camada; G4 às 08h30 |

## 9. Pendências deste plano

`[PREENCHER]`: quem fica em cada frente (tabela do time); (a política de versões foi decidida na [DEC-030](decisoes.md)); todos os itens da
seção 3. **A frente D, o caminho crítico, as horas, os comandos e a distribuição de modelos por camada são `[PROPOSTA]`** e entram no
"aprovado" deste plano ou mudam por nova DEC.
