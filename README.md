# Converge Challenge: projeto do time

Hackathon de AI Agents (**tema aberto**), 07 e 08/11/2026, Porto Digital, Recife. Fase e ideia escolhida: ver
[docs/estado-do-projeto.md](docs/estado-do-projeto.md). Quem trabalha aqui, humano ou agente, começa pelo [CLAUDE.md](CLAUDE.md).

**Prazo duro: submissão domingo 08/11 às 13h00. Demo Day às 16h00.**

## Onde está cada coisa

| Quero... | Vá para |
|---|---|
| Saber em que pé estamos agora | [docs/estado-do-projeto.md](docs/estado-do-projeto.md) |
| Gerar e escolher a ideia | [docs/ideacao/como-ideiar.md](docs/ideacao/como-ideiar.md) |
| Entender como a ideia é julgada | [docs/ideacao/criterios.md](docs/ideacao/criterios.md) |
| Ver ou registrar ideias | [docs/ideacao/backlog-ideias.md](docs/ideacao/backlog-ideias.md) · [template](docs/ideacao/_template-ideia.md) |
| Ver o que o produto precisa fazer e provar | [docs/requisitos.md](docs/requisitos.md) |
| Ver o produto definido (features, agente e humano) | [docs/produto.md](docs/produto.md) |
| Ver a arquitetura técnica (Gate 3, aprovada em [DEC-022](docs/decisoes.md)) | [docs/arquitetura.md](docs/arquitetura.md) |
| Ver o plano de implementação em camadas (e o status de cada uma) | [docs/plano-implementacao.md](docs/plano-implementacao.md) |
| Ver as regras legais em YAML (lei, convenção e política fictícias) | [data/regras/README.md](data/regras/README.md) |
| Ver o que já foi decidido | [docs/decisoes.md](docs/decisoes.md) |
| Conferir as regras do evento | [docs/regras-e-integridade.md](docs/regras-e-integridade.md) · [docs/contexto-hackathon.md](docs/contexto-hackathon.md) · [guia oficial](docs/guia-converge-challenge.md) |
| Planejar as horas | [docs/plano-de-horas.md](docs/plano-de-horas.md) |
| Preparar submissão, pitch e demo | [docs/entrega.md](docs/entrega.md) |
| Marca, copy e movimento da landing Remane | [docs/landing.md](docs/landing.md) |
| Design system (tokens, componentes, logos) | [docs/design-system/README.md](docs/design-system/README.md) |
| Listar ferramentas e modelos usados | [docs/declaracao-ferramentas.md](docs/declaracao-ferramentas.md) |
| Consultar a ideia anterior (arquivada) | [docs/ideacao/ideias/IDEA-001-recuperacao-depositos.md](docs/ideacao/ideias/IDEA-001-recuperacao-depositos.md) |

## O que é

**Escalista** (marca **Remane**) é um digital worker de escala e jornada para operações com turnos (Desafio Tako, frente DP): lê a
escala atual, valida contra a lei (CLT, EC 141), a convenção coletiva e a política da empresa, otimiza a escala ao menor custo,
publica, e cobre faltas conversando com a equipe. O gestor aprova e decide as exceções; o agente prepara. Detalhes em
[docs/produto.md](docs/produto.md). **Todos os dados de demo são sintéticos** (convenção, política, pessoas e atestados fictícios).

## Guia: clonar e rodar localmente

### 1. Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Git | qualquer recente | clonar |
| [uv](https://docs.astral.sh/uv/) | 0.9.x | gerencia Python e dependências do backend |
| Python | 3.12 (`.python-version`) | o `uv` baixa sozinho se faltar |
| Node.js e npm | 22.12 ou mais | build do front-end (Next.js) |
| Docker | opcional | só para rodar a imagem de produção |

### 2. Clonar e instalar

```bash
git clone https://github.com/pedroafmelo/converge-challenge-61.git
cd converge-challenge-61
uv sync                  # dependências Python (travadas em uv.lock, data de corte 2026-10-23, DEC-030)
npm --prefix web ci      # dependências do front-end (versões exatas, web/.npmrc)
```

### 3. Configurar o ambiente

```bash
cp .env.example .env     # o .env é ignorado pelo git; nunca commite chaves
```

Variáveis que importam (o `.env.example` tem todas, comentadas):

| Variável | Obrigatória? | Descrição |
|---|---|---|
| `FEATHERLESS_API_KEY_1` (até `_4`) | Só para as etapas com modelo | Chave(s) da [Featherless](https://featherless.ai). O cliente lê todas as `FEATHERLESS_API_KEY_*` como pool, na ordem. Sem chave, as chamadas ao modelo não funcionam; o solver, as regras e os testes não dependem dela |
| `FEATHERLESS_MODEL_SMALL` / `_LARGE` | Não | Padrões: `Qwen/Qwen3.5-9B` e `google/gemma-4-31B-it` |
| `DEMO_MODE` | Para a demo | `1` habilita os botões de entrada por persona (gestor e colaborador) e o "Reiniciar demo". Padrão `0` |
| `SESSION_SECRET` | Recomendada | Texto aleatório longo para assinar o cookie de sessão. Ex.: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Não | Padrão `sqlite:///./var/escalista.db` (a pasta `var/` é criada e ignorada pelo git) |
| `WEB_DIST_DIR` | Não | Padrão `web/dist` (SPA estática servida pelo FastAPI) |
| `LANGFUSE_*` | Não | Tracing opcional, só se você subir um Langfuse próprio. O rastro do app fica no banco de qualquer forma |

Para uma demonstração completa, deixe no mínimo `DEMO_MODE=1`, `SESSION_SECRET` e uma chave da Featherless.

### 4. Rodar (API + front em um só processo)

```bash
npm --prefix web run build                                          # gera web/dist (export estático, DEC-035)
uv run uvicorn escalista.api.app:create_app --factory --port 8000   # http://localhost:8000
```

Confira `GET http://localhost:8000/health` (app e banco no ar). Abra `http://localhost:8000`, entre como **gestor** ou
**colaborador** (com `DEMO_MODE=1`) e use "Reiniciar demo" para voltar à semana sintética.

**Desenvolvimento do front com recarga:** em outro terminal, `npm --prefix web run dev` abre `http://localhost:3000`, com proxy de
`/api` para a porta 8000 (deixe a API rodando).

### 5. Testes e qualidade

```bash
uv run pytest -q                      # backend (padrão inclui os testes lentos, ~1 min)
uv run pytest -m "not slow" -q        # sem o benchmark do solver
uv run ruff check .                   # lint Python
npm --prefix web run typecheck        # TypeScript
npm --prefix web run lint             # ESLint
npm --prefix web test                 # testes do front (node --test)
```

Os testes usam um cliente de modelo falso: **não gastam chave nem precisam de rede**.

### 6. Docker (opcional)

```bash
docker build -t escalista .
docker run --rm -p 8080:8080 --env-file .env -v escalista_data:/data escalista   # http://localhost:8080
```

A imagem é multi-stage (build do Next.js em Node, execução em Python), roda sem root e guarda o SQLite em `/data`.

### 7. Problemas comuns

- **Tela em branco ou 404 em `/`:** falta `npm --prefix web run build` (a API serve `web/dist`).
- **Sem botões de entrada por persona:** `DEMO_MODE` não está `1` no `.env`; reinicie o uvicorn.
- **Erro de versão do Node:** use 22.12 ou mais (`node -v`).
- **Resolução de dependências diferente:** use `uv sync` e `npm ci` (não `install`), para respeitar as travas.

**Deploy:** Railway ([DEC-037](docs/decisoes.md)), a partir do `Dockerfile` e do `railway.json`; cada merge na `main` publica.
O `fly.toml` ficou sem uso (substituído pelo Railway).

## Stack completa

Fonte de verdade das versões: `pyproject.toml`, `uv.lock` e `web/package.json`. A lista oficial, com licenças e status, está em
[docs/declaracao-ferramentas.md](docs/declaracao-ferramentas.md).

### Modelos de IA (inferência via Featherless)

| Modelo | Tamanho | Uso | Status |
|---|---|---|---|
| `Qwen/Qwen3.5-9B` | Pequeno | **Todas as etapas com modelo:** leitura da escala (mapeamento de colunas), formulação, justificativa, chat do colaborador, assistente do gestor, leitura do atestado em PDF e em foto (visão) | **Em uso**, medido em chamadas reais (08/11) |
| `google/gemma-4-31B-it` | Grande | Configurado em `FEATHERLESS_MODEL_LARGE` | Configurado, **não usado** |

O modelo classifica, extrai e redige; **o solver e o verificador de regras decidem a escala**. Decisões de consequência ficam com o humano.

### APIs de terceiros

| Serviço | Uso | Status |
|---|---|---|
| [Featherless](https://featherless.ai) (API compatível com OpenAI, `https://api.featherless.ai/v1`) | Única API externa de inferência do produto, via SDK `openai` com `base_url` própria | Em uso |
| Langfuse (self-hosted) | Tracing opcional, só no notebook do time | Opcional |
| WhatsApp Cloud API (Meta) | Cogitada para o canal | **Não usada**: o chat é dentro do app ([DEC-069](docs/decisoes.md)); o celular é simulado |
| Cadastro de RH, ponto e HRIS | Integrações **simuladas** por nós, com dados sintéticos | Simulado |

### Backend (Python 3.12)

| Biblioteca | Papel |
|---|---|
| FastAPI, Uvicorn, Pydantic, pydantic-settings | API HTTP, validação e configuração por ambiente |
| Google OR-Tools (CP-SAT) | Solver de escala (otimização com restrições legais) |
| LangGraph | Grafo dos agentes (otimização, acompanhamento, assistente) |
| openai (SDK) | Cliente da API da Featherless |
| Langfuse (SDK) | Tracing (opcional) |
| SQLAlchemy + SQLite | Banco, estado e rastro auditável (portável a Postgres) |
| itsdangerous | Sessão por cookie assinado |
| openpyxl, defusedxml, pdfplumber | Leitura de escalas em XLSX, CSV e PDF digital; geração de XLSX sintéticos |
| PyYAML | Regras em YAML (`data/regras/`: lei, convenção, política) |
| Dev: pytest, pytest-cov, ruff, httpx, Pillow, reportlab | Testes, lint e geração de atestados sintéticos |

### Front-end (`web/`)

Next.js 16 (export estático), React 19, TypeScript 6, Tailwind CSS 4, fonte Geist, ESLint 9. Design system **Remane** em
[docs/design-system/](docs/design-system/README.md).

### Infraestrutura e ferramentas

Docker multi-stage (`node:22-bookworm-slim` e `python:3.12-slim-bookworm`, com `uv`), Railway (hospedagem), Git/GitHub.
Desenvolvimento assistido por **Claude Code** (Anthropic; Opus, Sonnet e Haiku 5.5), que **não faz parte do produto**, com servidores
MCP de documentação do Langfuse e do LangChain (`.mcp.json`).

## Comandos do Claude Code (`.claude/commands/`)

| Comando | Para quê |
|---|---|
| `/nova-ideia <frase>` | Cria a ficha e a linha no backlog |
| `/avaliar-ideias [IDs]` | Aplica filtros e rubrica e recomenda uma ideia (a decisão é do time) |
| `/decisao <frase>` | Registra a decisão e propaga para as docs afetadas |
| `/sync-docs` | Audita as docs contra o repositório e corrige a defasagem |

## Como as docs se mantêm atualizadas

1. **Protocolo** (vale sempre): quem muda algo atualiza a doc correspondente no mesmo turno. A tabela de gatilhos está em
   "Documentação viva" no [CLAUDE.md](CLAUDE.md).
2. **Comandos** acima automatizam os fluxos mais comuns.
3. **Hook de aviso** (opcional, ver abaixo): ao abrir a sessão mostra a contagem regressiva dos marcos e as docs defasadas; ao
   encerrar um turno em que o código mudou e a doc não, bloqueia uma vez e pede a atualização.

### Ativando o hook

> Neste repositório o hook **já está registrado** em `.claude/settings.json` ([DEC-004](docs/decisoes.md)). O texto abaixo vale
> para quem copiar o modelo para outro projeto.

O script já está em [.claude/hooks/docs_sync.py](.claude/hooks/docs_sync.py), mas **só vale depois de registrado**. Crie
`.claude/settings.json` com:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/docs_sync.py\" session-start" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/docs_sync.py\" stop" } ] }
    ]
  }
}
```

Regras que ele verifica (por data de modificação): código em `src/`, `tests/` ou `pyproject.toml` mais novo que
`docs/estado-do-projeto.md`; `pyproject.toml` mais novo que `docs/declaracao-ferramentas.md`. Para testar sem registrar:
`python3 .claude/hooks/docs_sync.py session-start`.

## Regras que não mudam

Clean room, dados sintéticos e declarados, segredos fora do git, humano decide nos atos de consequência e declaração de
tudo que é de terceiros. Detalhes no [CLAUDE.md](CLAUDE.md) e em [docs/regras-e-integridade.md](docs/regras-e-integridade.md).
