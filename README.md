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
| Listar ferramentas e modelos usados | [docs/declaracao-ferramentas.md](docs/declaracao-ferramentas.md) |
| Consultar a ideia anterior (arquivada) | [docs/ideacao/ideias/IDEA-001-recuperacao-depositos.md](docs/ideacao/ideias/IDEA-001-recuperacao-depositos.md) |

## Rodar e testar localmente

Requisitos: uv, Node 22.12 ou mais. Copie `.env.example` para `.env` (ignorado pelo git) e preencha só o que for usar. O deploy está adiado
([DEC-034](docs/decisoes.md)); por enquanto tudo roda na máquina.

```
uv sync                                    # dependências Python (travadas pela data de corte, DEC-030)
uv run pytest && uv run ruff check .       # testes e lint
npm --prefix web ci                        # dependências do front-end
npm --prefix web run build                 # gera web/dist (export estático do Next.js, DEC-035)
uv run uvicorn escalista.api.app:create_app --factory --port 8000   # API + SPA em http://localhost:8000
npm --prefix web run dev                   # opcional: front com recarga em http://localhost:3000 (proxy de /api para a 8000)
```

`GET /health` confirma que o app e o banco (SQLite em `var/`, ignorado pelo git) estão de pé. Docker é opcional: `docker build .`.

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
