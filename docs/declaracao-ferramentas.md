# Declaração de ferramentas, modelos e APIs de terceiros

Última atualização: 2026-11-08 11:33 (C7b: Cloud API do WhatsApp não usada, [DEC-069](decisoes.md); nenhuma dependência nova). Antes, 2026-11-08 04:37 (C6 em `c6/integra`: openpyxl e defusedxml em uso, cadastro simulado, arquivos E2). Antes, 2026-11-08 02:05 (WhatsApp: sai o whatsapp-web.js, entra a Cloud API de teste, [DEC-043](decisoes.md)). Antes, 2026-11-08 01:23 (integração do remoto com a C5: `web/` em Next.js ([DEC-035](decisoes.md)) e hospedagem no Railway ([DEC-037](decisoes.md)) valem; nada novo entrou por esta integração. Antes: 2026-11-08 00:45, execução da C5: `httpx2`, dependência indireta do `openai`, passou a ser importada nos testes; o `pyproject.toml` ganhou só o marcador `slow` do pytest, na tarefa T0, **sem dependência nova**; o Claude Code passou a rodar com subagentes, ver a linha abaixo. Antes: 2026-11-07 16:48, auditoria depois da C0a, com dependências Python e npm sob a data de corte 2026-10-23, [DEC-030](decisoes.md)). **A submissão exige esta lista** (guia, seção 7) e a regra de uso de IA pede que APIs,
modelos e plataformas sejam declarados (seção 5). Atualize **no mesmo turno** em que algo entrar ou sair do projeto.
Status: `planejado`, `em uso`, `removido`. Não remova linhas: marque `removido`.

## Ferramentas de desenvolvimento e IA

| Item | Tipo | Uso no projeto | Status |
|---|---|---|---|
| Claude Code (Anthropic) | Ferramenta de código com IA | Desenvolvimento e documentação; liberada pelo guia. Não faz parte do produto ([DEC-003](decisoes.md), provisória). Modelos: Opus 5.5, Sonnet 5.5 e Haiku 5.5 (política da [DEC-028](decisoes.md)); na C5, 4 sessões em paralelo ([DEC-039](decisoes.md)), executadas por uma sessão orquestradora que delega cada tarefa a um subagente (Opus, Sonnet ou Haiku 5.5, conforme a tarefa) | em uso |
| Langfuse docs MCP (`https://langfuse.com/api/mcp`, oficial, sem autenticação) | Servidor MCP de documentação | Consulta de documentação durante o desenvolvimento; configurado em `.mcp.json` | em uso (conectado desde a [DEC-009](decisoes.md)) |
| LangChain docs MCP (`https://docs.langchain.com/mcp`, oficial, sem autenticação) | Servidor MCP de documentação | Consulta de documentação do LangGraph durante o desenvolvimento; configurado em `.mcp.json` | em uso (conectado desde a [DEC-009](decisoes.md)) |

## Modelos e APIs de inferência

| Item | Tipo | Uso no projeto | Status |
|---|---|---|---|
| Featherless (API compatível com OpenAI, `https://api.featherless.ai/v1`) | Inferência de modelos open source | Inferência de todo o agente do produto (US$ 25 por pessoa, benefício do evento), via SDK da OpenAI com `base_url` da Featherless | **em uso no código** desde a C5 (`src/escalista/llm/client.py`, justificativa da fatia); **ainda sem chamada real medida** (teste de fumaça das chaves pendente, do usuário) ([DEC-003](decisoes.md), provisória) |

**Modelos escolhidos ([DEC-020](decisoes.md)).** Nomes e preços das fichas em featherless.ai/models, lidas por subagente em 07/11/2026.
**Nenhum foi testado por nós** (nem em português, nem em tool calling, nem em visão); o teste de fumaça decide antes de adotar.

| Modelo | Provedor | Tamanho | Etapa | Status |
|---|---|---|---|---|
| `Qwen/Qwen3.5-9B` | Featherless | Pequeno (1 unidade de concorrência; US$ 0,17 entrada e US$ 0,25 saída por 1M tokens) | Agente do colaborador, assistente do gestor, justificativas, **visão da foto do atestado** | planejado, aguardando teste de fumaça |
| `google/gemma-4-31B-it` | Featherless | Grande (2 unidades; US$ 0,12 e US$ 0,36 por 1M tokens) | Leitura da escala e da convenção em regras | planejado, aguardando teste de fumaça |
| Modelo reserva por papel | Featherless | `[PREENCHER]` | Troca se o teste de fumaça falhar | a decidir no teste |

A foto do atestado trafega, com o CID dentro, pela Featherless (terceiro). Dado 100% sintético; **declarar na submissão**.
Tool calling nativo documentado só em `moonshotai/Kimi-K2-Instruct` e na família Qwen3
([featherless.ai/docs/tool-calling](https://featherless.ai/docs/tool-calling), doc de 07/08/2025, defasada em relação às fichas do catálogo).

## Observabilidade e infraestrutura

| Item | Tipo | Uso no projeto | Status |
|---|---|---|---|
| Langfuse (self-hosted, Docker Compose; núcleo MIT) | Tracing de agentes | Rastro e custo por execução, **só no notebook do time** (a doc recomenda 4 CPU e 16 GiB; não cabe em hospedagem grátis). O link público lê a tabela de rastro do app, não o Langfuse ([DEC-021](decisoes.md)) | planejado ([DEC-005](decisoes.md), [DEC-021](decisoes.md)) |
| Postgres, ClickHouse, Redis e MinIO (contêineres do Langfuse self-hosted) | Armazenamento do Langfuse | Dependências do Langfuse v4 (docker compose do projeto deles); só no notebook | planejado |
| WhatsApp Cloud API (Meta, oficial), número de teste | Canal real só no pitch, com os celulares do time; webhook no Railway | Demonstração ao vivo do atendimento ([DEC-043](decisoes.md), [plano](planos/whatsapp-cloud-api.md)); jurados usam o celular simulado | **não usado**: superado pela [DEC-069](decisoes.md) (chat dentro do app, 2026-11-08 11:33) |
| whatsapp-web.js (Node.js, Apache-2.0, **não oficial**, contrário aos termos do WhatsApp) | Ponte de canal | Receber e enviar mensagens do WhatsApp no evento, com chip dedicado, **só no notebook**. Produção usaria a API oficial do WhatsApp Business. Declarar na submissão | **removido** em 2026-11-08: o WhatsApp recusa parear o cliente automatizado; spike fora do repositório ([DEC-043](decisoes.md)) |
| Railway (plano Hobby da conta do usuário, US$ 5/mês com US$ 5 de uso incluído; 1 serviço Docker e 1 volume) | Hospedagem do link público | Link estável exigido na submissão; deploy a cada merge na `main` ([DEC-037](decisoes.md)) | planejado |
| Fly.io (app com 1 máquina shared-cpu-1x de 1 GB e 1 volume) e `flyctl` | Hospedagem do link público | Link estável exigido na submissão ([DEC-030](decisoes.md)); preço em [arquitetura.md](arquitetura.md), seção 12 (volume: [NÃO ENCONTRADO]) | substituído pelo Railway ([DEC-037](decisoes.md)); `fly.toml` fica sem uso |
| Docker (multi-stage: `node:22-bookworm-slim` e `python:3.12-slim-bookworm`) e imagem `ghcr.io/astral-sh/uv` | Build e execução do contêiner | Imagem única que o Railway executa ([DEC-037](decisoes.md); antes, o Fly.io) ([plano da C0](planos/camada-00-fundacao.md)) | planejado (C0b) |
| SQLite (stdlib do Python) | Banco do app | Estado, rastro e dados sintéticos; portável a Postgres via SQLAlchemy `[PROPOSTA]` | planejado |
| Node.js e npm (build do Next.js, export estático; antes React + Vite) | Build do front-end | Local (v25.8.2 nesta máquina) e no estágio `node:22-bookworm-slim` do contêiner ([DEC-018](decisoes.md)) | **em uso** |

## Bibliotecas e frameworks

O `pyproject.toml` foi reescrito em 07/11 ([DEC-007](decisoes.md)) e traz só a base já decidida; OR-Tools, LangGraph,
langfuse e openai entram na implementação. Antes da submissão, deixe aqui só o que o projeto realmente usa.

| Item | Origem | Status |
|---|---|---|
| fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.1, pydantic-settings 2.16.1, starlette 1.9.0 | `pyproject.toml` | **em uso** (C0a, versões do `uv.lock` sob a data de corte de [DEC-030](decisoes.md): só o publicado até 2026-10-23) |
| numpy, pandas, requests | `pyproject.toml` (scaffold) | removido ([DEC-007](decisoes.md)); voltam com `uv add` se a técnica pedir |
| bs4 | `pyproject.toml` (scaffold) | removido do `pyproject.toml` ([DEC-005](decisoes.md)) |
| python-bcb | `pyproject.toml` (scaffold) | removido do `pyproject.toml` ([DEC-005](decisoes.md)) |
| httpx2 2.16.0 | dependência indireta do `openai` 3.37 (no `uv.lock`, **não** declarada no `pyproject.toml`) | **em uso só nos testes** (`tests/llm/`: transporte HTTP falso do cliente Featherless, C5/B2); se o time quiser, declarar com `uv add --dev` |
| pytest 9.1.1, pytest-cov 7.1.0, ruff 0.17.2, httpx 0.28.1 (BSD-3-Clause; `TestClient`), pillow 13.0.0, reportlab 5.1.0 | `pyproject.toml` (grupo dev) | **em uso** (httpx é `[PROPOSTA]` fora da seção 19 da arquitetura; pillow e reportlab ainda sem código que os use) |
| pyyaml 6.0.3 (MIT) | Leitura de `data/regras/*.yaml` na C1 | **em uso** (instalado na C0a, `[PROPOSTA]` fora da seção 19; PyPI, 07/11/2026) |
| uv_build (`>=0.9.17,<0.10`; MIT ou Apache-2.0) | Backend de build do pacote `escalista` | **em uso** (`[PROPOSTA]`) |
| taskipy, typos, isort | `pyproject.toml` (scaffold) | removido ([DEC-007](decisoes.md)) |
| Google OR-Tools (CP-SAT) 9.15.6755, Apache-2.0 | Solver de escala (núcleo) | **em uso** desde a C5 (`src/escalista/solver/model.py`) |
| LangGraph (MIT; **resolvido 1.2.17**, instalado na C0a; a mais nova era 1.2.20; Python >= 3.10; exige langchain-core >= 1.4.7, < 2, hoje 1.7.6, MIT) | Grafo dos três agentes ([DEC-018](decisoes.md)) | **em uso** desde a C5 (agente de otimização, `src/escalista/agents/optimizer/graph.py`; os outros dois ainda não existem) ([FATO] PyPI JSON e registro do npm, subagente só leitura, 07/11/2026; saiu há menos de 14 dias, anterior 1.2.16) |
| langfuse (SDK Python, MIT; **resolvido 5.0.4**, instalado na C0a; a mais nova era 5.2.0; Python >= 3.11) | Tracing; `langfuse.openai` existe nesta versão, compatibilidade com o openai 3.x **[NÃO ENCONTRADO]**, testar | planejado ([FATO] PyPI JSON e registro do npm, subagente só leitura, 07/11/2026; menos de 14 dias, anterior 5.0.4) |
| openai (SDK Python, Apache-2.0; **resolvido 3.37.0**, instalado na C0a; a mais nova era 3.46.0; Python >= 3.10) | Cliente da API compatível da Featherless | **em uso** desde a C5 (`src/escalista/llm/client.py`) ([FATO] PyPI JSON e registro do npm, subagente só leitura, 07/11/2026; menos de 14 dias, anterior 3.37.0) |
| Node.js, whatsapp-web.js e Puppeteer (Chromium) | Microserviço da ponte do WhatsApp | **removido** em 2026-11-08: o WhatsApp recusa parear o cliente automatizado; spike fora do repositório ([DEC-043](decisoes.md)) |
| openpyxl 3.1.5 (MIT) e defusedxml 0.7.1 (PSF) | Leitura de XLSX (`ingest/tables.py`, `read_only` e `data_only`; o openpyxl usa o defusedxml quando instalado, conferido na D2) e geração dos XLSX sintéticos (`synth/e2.py`) | em uso desde a C6 (branch `c6/integra`; versões e licenças pelo PyPI, 07/11/2026) |
| pdfplumber 0.11.10 (MIT), com pdfminer.six (MIT) e pypdfium2 5.15.1 (BSD-3-Clause e Apache-2.0, com licenças permissivas de terceiros no binário do PDFium; nenhuma copyleft fora dos builds musl, que trazem a GCC Runtime Library Exception; [FATO] PyPI JSON e registro do npm, subagente só leitura, 07/11/2026) | Leitura de PDF digital: escala, convenção e atestado | **em uso** para a escala em PDF digital (`ingest/tables.py`, `extract_tables`, até 5 páginas; C6, D6); convenção e atestado seguem planejados |
| React e react-dom 19.3.1 (MIT), Vite (MIT; Node ^20.19 ou >= 22.12; **instalado 8.3.5**, a mais nova era 8.3.6), @vitejs/plugin-react (MIT; **instalado 6.1.2**, a mais nova era 6.2.1), TypeScript 6.0.3 (Apache-2.0; fixado pelo template), @types/react 19.3.0, @types/react-dom 19.3.0, @types/node 24.19.2 | SPA do front-end ([DEC-018](decisoes.md)) | Vite e @vitejs/plugin-react **removidos** em 2026-11-07 ([DEC-035](decisoes.md)); React, react-dom, TypeScript e os @types seguem na linha abaixo. Scaffold original gerado por `create-vite` 9.3.1 (MIT) |
| next 16.4.2 (MIT), eslint-config-next 16.4.2 (MIT), eslint 9.39.5 (MIT), tailwindcss e @tailwindcss/postcss 4.3.3 (MIT), geist 1.8.2 (fonte Geist da Vercel, SIL Open Font License 1.1), qrcode.react 4.2.0 (ISC; **removido** em 2026-11-08, a landing não tem mais QR, [DEC-043](decisoes.md)), com React e react-dom 19.3.1, TypeScript 6.0.3, @types/react 19.3.0, @types/react-dom 19.3.0 e @types/node 24.19.2 | Landing e front-end da plataforma em `web/`; build em export estático servido pelo FastAPI ([DEC-035](decisoes.md)) | **em uso** desde 2026-11-07, sob `before=2026-10-23` e `save-exact` em `web/.npmrc` |
| SQLAlchemy (MIT; Python >= 3.11; **resolvido 2.1.6**, em uso desde a C0a; a mais nova era 2.1.8) e itsdangerous 2.2.0 (BSD-3-Clause) | Banco e sessão por cookie assinado `[PROPOSTA]` | **em uso** (SQLAlchemy desde a C0a; itsdangerous via `SessionMiddleware` do Starlette desde a C5) ([FATO] PyPI JSON e registro do npm, subagente só leitura, 07/11/2026; SQLAlchemy com menos de 14 dias, anterior 2.1.6) |
| Pillow 13.0.0 (MIT-CMU) e reportlab 5.1.0 (BSD) | Geração de dados sintéticos (grupo dev) | planejado |
| pandas, numpy | Dependências transitivas do OR-Tools; não importadas por nós | planejado como transitivas |
| PyMuPDF (AGPL-3.0) e fpdf2 (LGPL-3.0) | Descartados por licença | removido (nunca entrou) |
| Tesseract e pytesseract | OCR local da foto do atestado | removido: a foto usa o modelo de visão ([DEC-020](decisoes.md)) |

## Origem do repositório (clean room)

O repositório foi criado a partir de um scaffold, com commit inicial às 10h55 de 07/11/2026. **Confirmar a origem do
scaffold e que ele não contém código, dado ou configuração de empregador ou cliente** (regra 2 do
[CLAUDE.md](../CLAUDE.md)). Se contiver, remover e registrar em [decisoes.md](decisoes.md). Bibliotecas e frameworks de
terceiros são permitidos como ponto de partida, desde que declarados.

**Resposta do time ([DEC-006](decisoes.md)):** o scaffold é um template de um amigo de um integrante, que trabalha em uma empresa, e
entra na regra de clean room. O commit inicial (`16e1a5c`, 31 arquivos) tem 10 arquivos que citam "[termo de terceiro omitido por clean room]"; o remoto é
privado e só tem esse commit. Remediação ([DEC-007](decisoes.md), opção A): histórico recriado em um branch novo, sem o commit inicial; `uv.lock`
regenerado; `LICENSE` vazio e `.vscode/settings.json` removidos; `pyproject.toml` reescrito. Restam, por serem genéricos,
`.gitignore` (modelo de gitignore para Python, com exceções nossas) e `.python-version`; declarar na submissão. **Execução
concluída ([DEC-009](decisoes.md)):** o histórico recriado foi publicado no `main` do remoto e o histórico antigo saiu do repositório local.

## Dados e simulações

Todo dado de demo é **sintético** e toda integração externa simulada deve ser listada aqui com a descrição de como foi
gerada, para a declaração honesta exigida na submissão.

| Item | Como foi gerado | Status |
|---|---|---|
| Rede fictícia (≈3 lojas, ≈60 colaboradores, telefones fictícios) | Gerada por script no evento; 100% fictícia | planejado |
| Demanda por faixa de 30 minutos com sazonalidade semanal | Gerada por script; parâmetros inventados | planejado |
| Escala atual da rede fictícia em XLSX, CSV e PDF | Gerada por script, com layouts diferentes; um arquivo com defeito plantado e uma escala com violações plantadas; 100% fictícia | planejado ([DEC-014](decisoes.md)) |
| Convenção coletiva fictícia (PDF) | Escrita por nós; não reproduz convenção real | planejado |
| Convenção e política fictícias em YAML ([convencao/](../data/regras/convencao/cct_comercio_ficticia.yaml), [politica/](../data/regras/politica/politica_ficticia.yaml)) | Escritas por Claude a pedido de Pedro Veloso em 08/11; empresa, sindicatos e lojas inventados; sem base em documento real (clean room) | em uso (camadas 2 e 3 do cartão de regras) |
| Atestados sintéticos em PDF e em foto, com ruído de digitalização ([DEC-014](decisoes.md)) | Gerados por script (Pillow e reportlab), com marca "SINTÉTICO"; médicos, CRM e CID fictícios. A foto vai ao modelo de visão da Featherless ([DEC-020](decisoes.md)) | planejado |
| Relógio de demo e ponto simulado ([DEC-019](decisoes.md)) | Relógio gravado no banco, avançado por botões; batidas geradas por script com falta, atraso e hora extra plantados. **O tempo é simulado e a tela rotula** | planejado |
| Ponto realizado e HRIS (mocks) | Simulados por nós, com desvios plantados; o agente chama de verdade a API simulada | planejado |
| Cadastro simulado de pessoas e lojas (C6, D7, [DEC-047](decisoes.md)) | `ingest/cadastro.py` casa o nome lido no arquivo com `data/demo/pessoas.json` e `lojas.json` (sintéticos) para trazer salário-hora, cargo e horário das lojas: **integração simulada** com um sistema de RH; sem par, o salário-hora vem do gestor na confirmação ou de um valor de referência sintético (mediana do cadastro), rotulado na tela | em uso (`c6/integra`) |
| Arquivos de leitura E2 ([data/demo/e2/](../data/demo/e2/README.md)) e exemplo em grade (`escala_exemplo_grade.xlsx`) | Gerados por script com seed (`synth/e2.py`), com a marca SINTETICO e defeitos plantados (cabeçalho livre, cp1252, grade, códigos de turno, duplicatas, homônimo, célula adversária, ilegíveis); 100% fictícios | em uso (`c6/integra`) |
| Celular simulado no app | Mesmo adapter da ponte do WhatsApp; mensagens simuladas | planejado |
| EC 141 e CLT como fonte das regras | Texto público real; **as regras codificadas são interpretação do time**, a validar com o DP | planejado |
| [data/regras/lei/ec141.yaml](../data/regras/lei/ec141.yaml) | Escrito pelo time a partir do texto do Planalto, lido pela cópia do repositório público `github.com/ctresb/leis` (`fonte/emc141.htm`; texto de norma, sem código copiado). Conferido por Claude contra o Planalto em 07/11 (status `interpretacao` ou `pendente` em cada regra); falta a leitura de alguém do time e declarar se alguma IA ajudou a escrever | em uso (entrada do cartão de regras) |
| [data/regras/lei/clt.yaml](../data/regras/lei/clt.yaml) | Escrito por Claude a partir do texto compilado do Planalto (CLT, Lei 10.101/2000 e art. 7º da CF), lido em 07/11; status `interpretacao` ou `pendente` em cada regra; falta a leitura de alguém do time | em uso (entrada do cartão de regras) |
