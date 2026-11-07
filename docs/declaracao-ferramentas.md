# Declaração de ferramentas, modelos e APIs de terceiros

Última atualização: 2026-11-07 14:45. **A submissão exige esta lista** (guia, seção 7) e a regra de uso de IA pede que APIs,
modelos e plataformas sejam declarados (seção 5). Atualize **no mesmo turno** em que algo entrar ou sair do projeto.
Status: `planejado`, `em uso`, `removido`. Não remova linhas: marque `removido`.

## Ferramentas de desenvolvimento e IA

| Item | Tipo | Uso no projeto | Status |
|---|---|---|---|
| Claude Code (Anthropic) | Ferramenta de código com IA | Desenvolvimento e documentação; liberada pelo guia. Não faz parte do produto ([DEC-003](decisoes.md), provisória) | em uso |
| Langfuse docs MCP (`https://langfuse.com/api/mcp`, oficial, sem autenticação) | Servidor MCP de documentação | Consulta de documentação durante o desenvolvimento; configurado em `.mcp.json` | planejado (aprovar ao reabrir a sessão) |
| LangChain docs MCP (`https://docs.langchain.com/mcp`, oficial, sem autenticação) | Servidor MCP de documentação | Consulta de documentação do LangGraph durante o desenvolvimento; configurado em `.mcp.json` | planejado (aprovar ao reabrir a sessão) |

## Modelos e APIs de inferência

| Item | Tipo | Uso no projeto | Status |
|---|---|---|---|
| Featherless (API compatível com OpenAI, `https://api.featherless.ai/v1`) | Inferência de modelos open source | Inferência de todo o agente do produto (US$ 25 por pessoa, benefício do evento), via SDK da OpenAI com `base_url` da Featherless | planejado ([DEC-003](decisoes.md), provisória) |

Quando decidir, liste **cada modelo** (nome exato, provedor, para qual etapa, tamanho pequeno ou grande).

**Modelos ainda não escolhidos.** A documentação da Featherless diz que, hoje, a chamada de ferramentas nativa existe em
`moonshotai/Kimi-K2-Instruct` e na família Qwen3; outros modelos podem devolver a chamada como texto
([featherless.ai/docs/tool-calling](https://featherless.ai/docs/tool-calling), lida por subagente em 07/11/2026; conferir em
[featherless.ai/models](https://featherless.ai/models) no dia). Para o agente de ferramentas, escolher entre esses.

## Observabilidade e infraestrutura

| Item | Tipo | Uso no projeto | Status |
|---|---|---|---|
| Langfuse (self-hosted, Docker Compose; núcleo MIT) | Tracing de agentes | Rastro auditável e custo por execução, desde a primeira hora | planejado ([DEC-005](decisoes.md)) |
| Postgres, ClickHouse, Redis e MinIO (contêineres do Langfuse self-hosted) | Armazenamento do Langfuse | Dependências do Langfuse v4 (docker compose do projeto deles) | planejado |
| whatsapp-web.js (Node.js, Apache-2.0, **não oficial**, contrário aos termos do WhatsApp) | Ponte de canal | Receber e enviar mensagens do WhatsApp no evento, com chip dedicado. Produção usaria a API oficial do WhatsApp Business. Declarar na submissão | planejado, spike de 1 h ([DEC-003](decisoes.md), provisória) |
| [PREENCHER: hospedagem do link público] | Deploy | Link estável exigido na submissão | a decidir |

## Bibliotecas e frameworks

O `pyproject.toml` foi reescrito em 07/11 ([DEC-007](decisoes.md)) e traz só a base já decidida; OR-Tools, LangGraph,
langfuse e openai entram na implementação. Antes da submissão, deixe aqui só o que o projeto realmente usa.

| Item | Origem | Status |
|---|---|---|
| fastapi, uvicorn, pydantic, pydantic-settings | `pyproject.toml` (reescrito, [DEC-007](decisoes.md)) | planejado (backend) |
| numpy, pandas, requests | `pyproject.toml` (scaffold) | removido ([DEC-007](decisoes.md)); voltam com `uv add` se a técnica pedir |
| bs4 | `pyproject.toml` (scaffold) | removido do `pyproject.toml` ([DEC-005](decisoes.md)) |
| python-bcb | `pyproject.toml` (scaffold) | removido do `pyproject.toml` ([DEC-005](decisoes.md)) |
| pytest, pytest-cov, ruff | `pyproject.toml` (grupo dev) | planejado |
| taskipy, typos, isort | `pyproject.toml` (scaffold) | removido ([DEC-007](decisoes.md)) |
| Google OR-Tools (CP-SAT) | Solver de escala (núcleo) | planejado, ainda não está no `pyproject.toml` |
| LangGraph | Grafo do agente | planejado, ainda não está no `pyproject.toml` |
| langfuse (SDK Python) | Tracing | planejado, ainda não está no `pyproject.toml` |
| openai (SDK Python) | Cliente da API compatível da Featherless | planejado, ainda não está no `pyproject.toml` |
| Node.js, whatsapp-web.js e Puppeteer (Chromium) | Microserviço da ponte do WhatsApp | planejado, serviço ainda não existe |

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
parcial:** faltam commit e push (ver DEC-007).

## Dados e simulações

Todo dado de demo é **sintético** e toda integração externa simulada deve ser listada aqui com a descrição de como foi
gerada, para a declaração honesta exigida na submissão.

| Item | Como foi gerado | Status |
|---|---|---|
| Rede fictícia (≈3 lojas, ≈60 colaboradores, telefones fictícios) | Gerada por script no evento; 100% fictícia | planejado |
| Demanda por faixa de 30 minutos com sazonalidade semanal | Gerada por script; parâmetros inventados | planejado |
| Convenção coletiva fictícia (PDF) | Escrita por nós; não reproduz convenção real | planejado |
| Atestados sintéticos com ruído de digitalização | Gerados por script; médicos, CRM e CID fictícios | planejado |
| Ponto realizado e HRIS (mocks) | Simulados por nós, com desvios plantados; o agente chama de verdade a API simulada | planejado |
| Celular simulado no app | Mesmo adapter da ponte do WhatsApp; mensagens simuladas | planejado |
| EC 141 e CLT como fonte das regras | Texto público real; **as regras codificadas são interpretação do time**, a validar com o DP | planejado |
| [data/regras/lei/ec141.yaml](../data/regras/lei/ec141.yaml) | Escrito pelo time a partir do texto do Planalto, lido pela cópia do repositório público `github.com/ctresb/leis` (`fonte/emc141.htm`; texto de norma, sem código copiado). Conferido por Claude contra o Planalto em 07/11 (status `interpretacao` ou `pendente` em cada regra); falta a leitura de alguém do time e declarar se alguma IA ajudou a escrever | em uso (entrada do cartão de regras) |
