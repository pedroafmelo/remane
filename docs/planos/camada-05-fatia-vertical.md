# Plano da C5 · Primeira fatia vertical (com os subconjuntos de C1 a C4)

Última atualização: 2026-11-08 00:45 (Recife; registro de execução na seção 12) · Situação: **aprovado pelo usuário em 2026-11-07 23:49** ([DEC-040](../decisoes.md)); **executado: itens 1 a 5 do G3 passaram, item 6 pendente** · Decisões desta etapa:
[DEC-038](../decisoes.md) e [DEC-039](../decisoes.md). Planejado pelo Opus 5.5 ([DEC-028](../decisoes.md)).

**Rótulos:** sem rótulo é decisão do usuário (com a DEC). **[PROPOSTA]** é sugestão do agente, ainda não confirmada. `[PREENCHER]` é o que
falta, com o motivo. **[INFERÊNCIA]** é dedução sem medição. Todas as horas são **[PROPOSTA]**, em faixa, e não foram medidas.

Este plano cobre **só o subconjunto de C1, C2, C3 e C4 que a fatia exige, mais a integração da C5**. Os planos completos de C1 a C4 vêm
depois ([plano macro](../plano-implementacao.md), seção 6). Ele não repete o produto, a arquitetura nem os requisitos: aponta para eles.

## 0. Como o trabalho roda ([DEC-039](../decisoes.md))

- **Uma pessoa, 4 sessões do Claude Code em paralelo**, uma por frente (A, B, C e D), cada uma no seu `git worktree` e branch. O usuário
  (Pedro Vieira) revisa e integra no `main`. Os outros 3 integrantes não programam nesta madrugada.
- **Janela:** hoje até ~03h e de volta às 07h ([DEC-038](../decisoes.md)): **~3h15 + 1h30 = ~4h45 de relógio por sessão** até o G4
  (dom 08h30), contando a partir das 23h45.
- **G3 vale local** ([DEC-038](../decisoes.md)): `http://localhost:8000`, não deploy. O deploy volta a ser decidido antes do G6.
- **Gargalo [INFERÊNCIA]:** a atenção do usuário (revisar ~20 merges e trocar entre 4 sessões), e não a escrita do código. A C0a levou
  ~4 min de relógio contra 75 a 110 min estimados ([estado](../estado-do-projeto.md), Métricas medidas); as faixas abaixo já são menores
  que as do plano macro, mas o solver e a integração têm risco real de modelagem e de depuração.

## 1. Objetivo e valor demonstrável

Em `http://localhost:8000`, o jurado (aqui, o usuário) entra pelo botão de demo do **gerente**, envia a escala atual em **CSV sintético**
(ou clica em "usar escala de exemplo") e vê os 8 passos da [seção 2 do plano macro](../plano-implementacao.md):

1. validação determinística do CSV, com o motivo e a linha de cada erro (RF-04; arquivo com defeito → RX-13);
2. resumo da leitura para o gerente confirmar (RF-23);
3. solver CP-SAT (RF-05);
4. verificador independente com **0 violações** na escala otimizada (RF-02);
5. antes e depois com custo, horas extras, cobertura e violações, pela **mesma função de custo** (RF-14 parcial);
6. justificativa escrita pelo **modelo pequeno**, só com fatos do solver e regras do cartão (RF-06; RE-02). Se o modelo falhar, aparece o
   cartão RX-12, nunca um texto inventado;
7. aprovação do gerente gravada e só então a publicação da grade semanal (RF-08, RH-01; regra 5 da [arquitetura, 2.1](../arquitetura.md));
8. um `trace_event` por passo, com `custo_usd` e latência medidos (RN-01, RN-03).

**A história da demo [PROPOSTA]:** a escala atual foi feita no regime de 44h com 1 folga. A semana planejada é **11 a 17/01/2027**, já
sob as 42h e os 2 repousos da EC 141, sem feriado nacional. O "antes" mostra as violações que a emenda cria e as horas extras. O "depois" mostra 0
violações e o custo medido.

### "G3 passou" quando (comandos exatos)

```
uv run pytest -q                                          # tudo verde, inclui fronteiras e tests/e2e/test_fatia.py
uv run ruff check .                                       # limpo
npm --prefix web run build                                # gera web/dist sem erro de TypeScript
uv run python -m escalista.solver.bench --seed 42         # grava o tempo 60 × 7 (1 thread e várias)
uv run python -m escalista.evals --suite e1               # 10 cenários sem modelo, relatório em var/evals/
DEMO_MODE=1 SESSION_SECRET=<local> uv run uvicorn escalista.api.app:create_app --factory --port 8000
```

E o fluxo à mão da seção 6, item 6, com a lista de eventos do rastro mostrando os 8 passos e o custo de cada um.

## 2. IDs cobertos e o que fica de fora

- **Cobertos:** RF-02 (4 primitivas e mais uma, ver A3), RF-04, RF-05 (aceite da [DEC-020](../decisoes.md)), RF-06 (texto pelo modelo pequeno), RF-08,
  RF-14 parcial (custo, horas extras, cobertura, violações; sem painel), RF-23 só em CSV, RF-29 e RF-30 só no papel gerente (botão de demo),
  RF-33 como botão "reotimizar", RN-01, RN-03, RN-09 (status por regra, com o novo `ficticia`), RN-13 no quadro, RE-02, RH-01, RX-02,
  RX-12 e RX-13; [DEC-023](../decisoes.md) só como campo no quadro.
- **Fora (vai para C6, C7 e C8):** XLSX, PDF, leitura por modelo, convenção em PDF, FT-01 em tela, FT-03, fila completa de exceções, painel,
  auditoria em tela (fica só a lista simples de eventos), edição na grade e em texto (RF-26), FT-07, as primitivas `folga_dominical`,
  `domingo_mulher`, `restricao_perfil`, `hora_extra` (limite diário de 2h) e `indisponibilidade`, os papéis DP e colaborador em tela,
  Langfuse e deploy.

## 3. Contratos a congelar primeiro (tarefa T0, frente A)

**Quem:** a sessão A (dono dos contratos, [DEC-038](../decisoes.md)). **Quanto:** **30 a 45 min** [PROPOSTA]. **Como:** um único PR
`feat(domain): add slice contracts and repository port`, com `tests/domain/test_contracts_v1.py` fixando os nomes dos campos (mesma
regra da [C0, seção 4](camada-00-fundacao.md)). Só forma, sem lógica: a lógica nasce no TDD de cada frente.

**Enquanto a T0 roda, ninguém fica parado:** B usa `TraceEvent`, `LLMClient` e `TraceSink`, que já existem; C usa `Role`; D escreve os YAMLs.
Só os geradores de D (D2) e as rotas de C que devolvem resumo e comparação (C2) esperam a T0.

### 3.1 Modelos pydantic novos (`src/escalista/domain/`) [PROPOSTA nos nomes e campos]

Arquivos: `domain/rules.py`, `domain/schedule.py`, `domain/results.py`, mais as portas em `domain/ports.py`. Nomes em inglês; datas e
horas como `date`, `time` e `datetime` sem fuso (horário de Brasília implícito, dado sintético).

| Modelo | Campos mínimos | Produz | Consome |
|---|---|---|---|
| `RuleStatus` (StrEnum) | `conferida`, `interpretacao`, `pendente`, **`ficticia`** ([DEC-039](../decisoes.md)) | A (carregador) | C (tela), evals |
| `RuleLayer` (StrEnum) | `lei`, `convencao`, `politica` | A | A, C |
| `Rule` (frozen) | `id`, `kind` (tipo de primitiva ou `"info"`), `layer`, `params: dict`, `valid_from: date \| None`, `valid_to: date \| None`, `status`, `source` (fonte), `action: Literal["escalar","verificar_convencao"] \| None`, `note` | A (`rules/`) | solver, verificador, custo, justificativa |
| `RuleCard` | `reference_date: date`, `rules: list[Rule]` (já fundidas e vigentes), `provisional: list[str]` (ids aplicados como "mais restritiva provisória"), `exceptions: list[ExceptionCard]` (conflitos ao DP) | A | todos do núcleo; agente |
| `Store` | `id`, `name`, `opens: time`, `closes: time` | D (`synth/`) | A, C |
| `Employee` | `id`, `name`, `store_id`, `job` (cargo), `hourly_wage: Decimal`, `contract_hours: int`, `sex: Literal["F","M"]` (**RN-13: nunca vai à tela, à resposta da API do gerente nem ao trace**, [DEC-039](../decisoes.md)), `profile: Literal["padrao","aprendiz","menor"] = "padrao"` | D | A; C só via `EmployeePublic` (sem `sex`) |
| `DemandSlot` | `store_id`, `day: date`, `start: time` (faixa de 30 min), `required: int` | D | solver, verificador (cobertura) |
| `Shift` | `employee_id`, `store_id`, `start: datetime`, `end: datetime` (`end` > `start`; turno que vira a noite termina no dia seguinte) | ingestão, solver | verificador, custo, grade |
| `Schedule` | `week_start: date` (segunda), `shifts: list[Shift]` | ingestão, solver | todos |
| `CsvIssue` | `line: int`, `field: str \| None`, `reason: str` | A (validação) | C (resumo), RX-13 |
| `ReadSummary` (RF-23) | `file_name`, `rows`, `employees`, `stores`, `week_start`, `total_hours: Decimal`, `issues: list[CsvIssue]`, `ok: bool` | A (validação) | C (tela do resumo), agente |
| `SolveRequest` | `card`, `stores`, `employees`, `demand`, `week_start`, `seed: int`, `time_limit_s: float`, `num_workers: int`, `hint: Schedule \| None` | agente | solver |
| `SolveResult` | `status: Literal["optimal","feasible","infeasible","timeout"]`, `schedule: Schedule \| None`, `uncovered: list[DemandSlot]` (o que faltou), `wall_ms`, `seed`, `input_hash`, `exception: ExceptionCard \| None` (RX-02 ou RX-12) | A (`solver/`) | agente, verificador |
| `Violation` | `rule_id`, `kind`, `employee_id`, `day: date \| None`, `source`, `detail` | A (`verifier/`) | C, evals |
| `ViolationReport` | `violations: list[Violation]`, `total: int` (calculado) | verificador | publicação, tela, evals |
| `ScheduleMetrics` | `total_cost`, `regular_hours`, `overtime_hours`, `overtime_cost` (`Decimal`), `coverage_pct: float`, `uncovered_slots: int`, `violations: int` | A (`solver/cost.py`, função pura) | `Comparison` |
| `Comparison` (antes e depois) | `before`, `after: ScheduleMetrics`, `savings: Decimal`, `overtime_hours_avoided`, `violations_avoided` | A | C, justificativa |
| `Justification` (saída do modelo) | `summary: str`, `items: list[{text: str, rule_refs: list[str]}]`; **todo `rule_ref` precisa existir no cartão**, senão reenvia (até 2 vezes) e depois RX-12 | B (schema e validação) | C |
| `ScheduleVersion` | `id`, `run_id`, `schedule`, `status: Literal["draft","approved","published"]`, `input_hash`, `seed`, `violations_total`, `created_at` | agente | Repository, C |
| `Approval` | `id`, `version_id`, `approved_by` (id do usuário), `role: Role`, `at: datetime` | API (ato humano) | ferramenta `publicar` |
| `RunState` | `run_id`, `phase: Literal["read","awaiting_confirm","optimized","awaiting_approval","published","failed"]`, `summary`, `comparison`, `report`, `justification`, `version_id`, `exception` | agente | API, SPA |

**Fora da T0, de propósito:** `ScheduleExtraction` (C6), `ReplanRequest` e `ChannelMessage` (C7).

### 3.2 Porta `Repository` (em `domain/ports.py`) [PROPOSTA]

```
save_run(state: RunState) -> None            get_run(run_id: str) -> RunState | None
save_version(v: ScheduleVersion) -> None     get_version(version_id: str) -> ScheduleVersion | None
record_approval(a: Approval) -> None         get_approval(version_id: str) -> Approval | None
mark_published(version_id: str, at: datetime) -> None
latest_published() -> ScheduleVersion | None
```

Falso: `InMemoryRepository` em `tests/fakes.py`, junto na T0. A implementação SQL fica num pacote novo de borda, **`store/`**
(`store/tables.py` e `store/sql_repository.py`), e a T0 inclui `store` em `CONCRETE_BORDERS` de `tests/architecture/boundaries.py`. Sem isso, o
`agents/` poderia importá-lo sem que o teste de fronteiras acusasse.

### 3.3 Tabela `trace_event` (frente B, `audit/tables.py`)

Colunas iguais ao `TraceEvent` v0, que **não muda**: `id` (pk), `run_id` (índice), `parent_id`, `kind` (índice), `at`, `rule_ref`, `message_ref`,
`model`, `key_index`, `tokens_in`, `tokens_out`, `cost_usd Numeric(12, 6)`, `latency_ms`, `payload JSON` (já redigido).

**Tipos de evento da fatia [PROPOSTA]:** `csv.validate`, `read.summary`, `read.confirmed` (humano), `solver.run`, `verifier.check`,
`cost.compare`, `llm.justify`, `approval.recorded` (humano), `schedule.publish` e `schedule.publish_refused`, além de `exception.raised` (RX-02,
RX-12 e RX-13). **Custo:** passos sem modelo gravam `cost_usd = 0` e `payload.cost_basis = "sem chamada de modelo"`, com a latência medida. O
`llm.justify` grava o `usage.cost` da Featherless e o índice da chave, nunca o valor.

### 3.4 Como se avisa uma mudança de contrato

Igual à [C0, seção 4](camada-00-fundacao.md): um PR só de contrato (`feat(domain): ...`, com `!` se quebrar), o teste de contratos editado
junto e o merge feito pelo usuário, que avisa as outras 3 sessões ("rebase no `main`; mudou `X`"). **Só a sessão A edita `domain/`.** As
outras pedem a mudança a ela pelo usuário.

## 4. Tarefas por frente, em ordem

Comando de verificação de toda tarefa, antes do merge: `uv run pytest -q && uv run ruff check .`, mais o específico indicado.

### Frente A · núcleo (sessão A; Opus 5.5)

| # | Tarefa | Arquivos | Depende de | Verificação | Horas |
|---|---|---|---|---|---|
| T0 | Contratos e porta `Repository`, falso, `store` nas fronteiras, marcador `slow` do pytest | `domain/*.py`, `tests/fakes.py`, `tests/domain/test_contracts_v1.py`, `tests/architecture/boundaries.py`, `pyproject.toml` (só a seção do pytest) | nada | `uv run pytest tests/domain tests/architecture` | 0,5 a 0,75 |
| A1 | Carregador das 3 camadas: schema, status (`ficticia` só em `convencao/` e `politica/`), vigência, fusão "a política só restringe", conflito → mais restritiva provisória + `ExceptionCard` ao DP; regras fora da fatia viram `kind="info"` | `rules/loader.py`, `rules/merge.py`, `tests/rules/` | T0 (D1 opcional) | `uv run pytest tests/rules` | 0,5 a 0,75 |
| A2 | Benchmark e solver CP-SAT: catálogo de turnos, cobertura com penalidade, 4 primitivas como restrição dura, seed e nomes estáveis, `input_hash`, demanda acima da capacidade → RX-02 com o cálculo de contratação | `solver/catalog.py`, `solver/model.py`, `solver/bench.py`, `tests/solver/` | A1, D2 (dados 60 × 7; antes, um gerador mínimo no teste) | `uv run python -m escalista.solver.bench --seed 42`; `uv run pytest tests/solver` | 1 a 1,5 |
| A3 | Função de custo e `Comparison` (a mesma para o antes e o depois) | `solver/cost.py`, `tests/solver/test_cost.py` | T0, A1 | `uv run pytest tests/solver/test_cost.py` | 0,25 a 0,5 |

**Por que o verificador não está na frente A [PROPOSTA]:** o RF-02 pede um verificador que não erre junto com o solver. Escrito por
**outra sessão** (D), a partir do mesmo cartão e do mesmo contrato, o verificador fica independente também na implementação, e não só no import. A
sessão A não lê o código do verificador antes de terminar o solver.

**Primitivas e semântica da fatia [PROPOSTA]:** `jornada_semanal_max` (42h na semana de referência), `interjornada_min` (11h),
`repouso_semanal` (2 dias por semana na semana de referência), cobertura (métrica e penalidade, **não** violação) e **`jornada_diaria_max`** (8h).
A quinta primitiva entra por custar ~10 min e porque a função de custo precisa dela para separar a hora normal da hora extra. Sem ela, a
escala enviada com turno de 10h passaria sem aviso. Se você não a quiser, ela sai sem afetar o resto. **Hora extra na fatia:** o solver não
escala hora extra (a política fictícia de D1 diz "hora extra só com autorização do DP"). Na escala enviada, a hora além do limite conta como
custo (adicional da convenção fictícia, ou 50% da lei) **e** como violação de `jornada_semanal_max` ou `jornada_diaria_max`. A demanda que
não couber vira RX-02.

**Lista de testes do TDD da frente A, na ordem:**

1. `test_loads_lei_layer` (ec141 e clt viram `Rule` com id, fonte e status)
2. `test_rejects_rule_without_id_source_or_status` (erro cita o arquivo e o campo)
3. `test_ficticia_status_only_outside_lei`
4. `test_weekly_limit_by_reference_date` (01/12/2026 → 44; 11/01/2027 → 42)
5. `test_policy_more_restrictive_wins`
6. `test_policy_looser_than_law_applies_law_provisionally_and_opens_exception`
7. `test_rules_outside_slice_are_info_with_status`
8. `test_cost_splits_regular_and_overtime` (diária e semanal sem contar em dobro: HE = máx. entre a soma dos excessos diários e o excesso semanal)
9. `test_cost_uses_convention_overtime_premium_else_law_minimum`
10. `test_comparison_same_function_before_and_after`
11. `test_solver_tiny_instance_respects_four_primitives` (3 pessoas × 2 dias; conferido com um verificador falso mínimo do próprio teste,
    e não com o de D)
12. `test_solver_stable_hash_for_same_input_and_seed`
13. `test_demand_above_capacity_returns_rx02_with_hiring_math`
14. `test_solver_60x7_within_time_limit` (`@pytest.mark.slow`)

### Frente B · LLM e rastro (sessão B; Sonnet 5.5, Opus 5.5 na máscara e nas chaves)

| # | Tarefa | Arquivos | Depende de | Verificação | Horas |
|---|---|---|---|---|---|
| B1 | Tabela `trace_event`, `SqlTraceSink`, `SystemClock` e máscara (nunca o valor da chave; nada fora do `payload` redigido) | `audit/tables.py`, `audit/sink.py`, `audit/mask.py`, `clock/system.py`, `tests/audit/` | nada (C0a) | `uv run pytest tests/audit` | 0,5 a 0,75 |
| B2 | Cliente Featherless: `openai` com `base_url`, pool com failover em ordem (401 e 429 trocam; 400 e 503 não trocam; 503 até 3 tentativas), semáforo, `usage.cost` → `cost_usd`, falha → `LLMUnavailableError` (RX-12), um `trace_event` por chamada | `llm/client.py`, `llm/pool.py`, `tests/llm/` (cliente HTTP falso) | B1 | `uv run pytest tests/llm` | 0,75 a 1,25 |
| B3 | Saída estruturada como ferramenta: schema pydantic → `tool_schema`, validação, até 2 reenvios; `Justification` com checagem de `rule_refs` contra o cartão | `llm/structured.py`, `llm/prompts/justify.py`, `tests/llm/test_structured.py` | B2, T0 | `uv run pytest tests/llm` | 0,25 a 0,5 |
| B4 | Script de fumaça: cada chave × modelo pequeno, em português, com ferramenta; imprime só o índice da chave, o custo e a latência | `src/escalista/llm/smoke.py` | B2 | `uv run python -m escalista.llm.smoke` (o usuário roda; o `.env` fica fora do worktree e é ele quem o liga) | 0,25 a 0,5 |
| I1 | **Integração:** agente LangGraph mínimo, com nós `ler_escala` (CSV → validação → resumo), `otimizar`, `verificar`, `comparar`, `justificar` e `publicar` e o estado em `RunState` pelo `Repository` (sem checkpointer, [arquitetura, seção 4](../arquitetura.md)); `publicar` lê `get_approval` **no código** e recusa sem ela | `agents/optimizer/graph.py`, `agents/optimizer/tools.py`, `tests/agents/` | T0, A1, A2, A3, D3, B3 (com falsos antes) | `uv run pytest tests/agents` | 0,75 a 1,25 |

Testes obrigatórios de B e I1: `test_key_value_never_in_trace_or_log`, `test_401_429_switch_key_400_503_do_not`,
`test_invalid_rule_ref_resends_then_rx12`, `test_publish_without_approval_is_refused` (evento `schedule.publish_refused`),
`test_every_step_emits_trace_event_with_cost`, `test_llm_failure_yields_rx12_not_text`.

### Frente C · API e SPA (sessão C; Opus 5.5 no acesso, Sonnet 5.5 na SPA)

| # | Tarefa | Arquivos | Depende de | Verificação | Horas |
|---|---|---|---|---|---|
| C1 | Sessão por cookie assinado, `require_role`, `POST /auth/demo/{papel}` só com `DEMO_MODE=1`, `GET /api/me`, `POST /auth/logout`; contas semeadas dos 3 papéis (só o gerente usado na fatia); matriz rota × papel (TDD) | `api/auth.py`, `api/deps.py`, `tests/api/test_access.py` | nada (C0a) | `uv run pytest tests/api` | 0,75 a 1 |
| C2 | Rotas da fatia contra um agente falso: `POST /api/runs` (CSV, ≤ 1 MB, UTF-8) → resumo; `POST /api/runs/{id}/confirm`; `GET /api/runs/{id}`; `POST /api/runs/{id}/approve` (grava `Approval` e chama `publicar`); `GET /api/schedules/published`; `GET /api/runs/{id}/trace`; `GET /api/demo/files/{nome}`. Nenhuma resposta leva `sex` (teste) | `api/routes_runs.py`, `api/wiring.py`, `tests/api/test_runs.py` | C1, T0 | `uv run pytest tests/api` | 0,75 a 1 |
| C3 | SPA: landing com botão "Entrar como gerente (demo)" e rótulos "dados sintéticos"; escolher arquivo ou "usar escala de exemplo"; resumo com "Confirmar"; antes e depois; justificativa ou cartão RX-12; grade semanal; "Aprovar e publicar"; lista de eventos do rastro (tipo, hora, regra, modelo, custo, latência) | `web/src/**` | C2 (contra o agente falso) | `npm --prefix web run build` | 1 a 1,5 |
| C4 | Ligação real: `wiring.py` troca o agente falso pelo de I1, com `SqlTraceSink`, `SqlRepository` e o cliente Featherless | `api/wiring.py`, `api/app.py`, `tests/e2e/test_fatia.py` | I1, B1, D4 | fumaça ponta a ponta (seção 6) | 0,25 a 0,5 |

### Frente D · dados, política fictícia, verificador e evals (sessão D; Haiku 5.5 nos dados, Opus 5.5 no verificador e no CSV)

| # | Tarefa | Arquivos | Depende de | Verificação | Horas |
|---|---|---|---|---|---|
| D1 | Convenção e política fictícias **mínimas**, com `status: ficticia`: adicional de hora extra da convenção, hora extra só com autorização do DP, repouso por semana. Valor da ampliação diária (pergunta 17): `[PREENCHER]` (a fatia não precisa dele, porque 5 × 8h = 40h < 42h). **Se Pedro Veloso entregar a dele, a dele substitui esta** | `data/regras/convencao/demo.yaml`, `data/regras/politica/demo.yaml` | nada | YAML válido (`uv run python -c "import yaml,sys; [yaml.safe_load(open(p)) for p in sys.argv[1:]]" data/regras/*/demo.yaml`) | 0,25 a 0,5 |
| D2 | Geradores com seed: 3 lojas (08h às 22h), ~60 pessoas (com `sex`), demanda por faixa de 30 min; `escala_atual.csv` (regime 44h e 1 folga, com hora extra), `escala_defeito.csv` (5 defeitos plantados) e `escala_violacoes.csv` com `violacoes_plantadas.json`; 1ª linha `# SINTETICO - dados ficticios` | `synth/*.py`, `data/demo/*`, `tests/synth/` | T0 | `uv run python -m escalista.synth --seed 42 --out data/demo`; `uv run pytest tests/synth` | 0,5 a 0,75 |
| D3 | Leitura e validação do CSV (RF-04): o parse é borda (`ingest/csv_schedule.py`) e a validação é pura (`rules/validation.py`); produz `Schedule` + `ReadSummary`; erro → `CsvIssue` com linha; arquivo ilegível → RX-13 | `ingest/csv_schedule.py`, `rules/validation.py`, `tests/ingest/`, `tests/rules/test_validation.py` | T0 | `uv run pytest tests/ingest tests/rules/test_validation.py` | 0,5 a 0,75 |
| D4 | **Verificador independente**, Python puro, uma função por primitiva + cobertura; **acha 100% das violações plantadas** | `verifier/*.py`, `tests/verifier/` | T0, A1 (o cartão), D2 | `uv run pytest tests/verifier` | 0,5 a 1 |
| D5 | Evals E1: 10 cenários sem modelo num comando, relatório JSON e tabela | `evals/__main__.py`, `evals/e1.py`, `tests/evals/` | D4, A2, A3 | `uv run python -m escalista.evals --suite e1` | 0,5 a 0,75 |

**Lista de testes do TDD da frente D (núcleo), na ordem:**

1. `test_csv_ok_yields_schedule_and_summary`
2. `test_missing_column_issue_at_line_1`
3. `test_bad_time_format_issue_with_line`
4. `test_unknown_employee_issue`
5. `test_overlapping_shifts_issue`
6. `test_date_outside_week_issue`
7. `test_overnight_shift_ends_next_day`
8. `test_non_utf8_or_too_large_is_rx13` (borda)
9. `test_weekly_hours_violation_cites_source` (43h com limite de 42 → 1 violação; 42 → 0)
10. `test_daily_hours_violation`
11. `test_rest_between_shifts_10h_violates_11h_ok`
12. `test_two_weekly_rest_days`
13. `test_coverage_metric_not_violation`
14. `test_finds_all_planted_violations` (meta 0 não detectadas, RN-04)

**Os 10 cenários da E1 [PROPOSTA]:** um por primitiva (5); a escala enviada em 44h julgada sob 42h; a demanda acima da capacidade → RX-02; o CSV com
defeito → RX-13; a escala otimizada com 0 violações; o turno que vira a noite e a interjornada.

### Integração (C5): quem e quando

A sessão B assume **I1** quando termina B1 a B4 (é a frente mais curta). A sessão C assume **C4** e a fumaça ponta a ponta. O usuário faz o
teste à mão. Ordem de merge: **T0 → (B1, C1, D1 em qualquer ordem) → A1 → D2 → D3 → A3 → B2 → B3 → C2 → A2 → D4 → I1 → C3 → D5 → C4.**

## 5. Grafo de dependências e caminho crítico

```
T0 contratos (A, 30-45 min) ──┬─► A1 carregador ─► A3 custo ─┐
                              │         └──────► A2 solver ──┤
                              ├─► D2 geradores ─► D4 verificador ─► D5 evals E1
                              ├─► D3 CSV ────────────────────┤
                              └─► C2 rotas (agente falso) ─► C3 SPA
B1 trace ─► B2 cliente ─► B3 estruturada ─► B4 fumaça        │
                              └──────────────► I1 agente ◄───┘ ─► C4 ligação ─► fumaça e2e ─► G3 à mão
C1 acesso (sem dependência)   D1 YAMLs (sem dependência)
```

- **Bloqueia todo mundo:** **T0**. Depois dela, **A1** (o cartão que solver, verificador, custo e justificativa usam) e **D2** (os dados do
  60 × 7, do verificador e da E1).
- **Caminho crítico [PROPOSTA]:** T0 (0,5–0,75) → A1 (0,5–0,75) → A2 (1–1,5) → I1 (0,75–1,25) → C4 + fumaça (0,25–0,5) → G3 à mão (0,25)
  = **3,25 a 5 h**.
- **Sozinho com os falsos de `tests/fakes.py`:** B1 a B4 (`FakeLLMClient`, `ListTraceSink`, `FixedClock`), C1 e C2 (agente falso que devolve
  `RunState` fixo), D1 a D4 (D4 só precisa do cartão de A1; até lá, um `RuleCard` montado no teste), I1 (com `InMemoryRepository` e
  `FakeLLMClient` até A2 e D4 entrarem).
- **Onde as frentes se encontram:** em I1 (núcleo + LLM + rastro + repositório) e em C4 (API + agente). São os dois merges de maior risco:
  o usuário os faz com todas as sessões paradas.

## 6. Teste de aceite do G3

1. `uv run pytest -q`: verde, incluindo fronteiras (o verificador não importa o solver nem o OR-Tools) e os testes de contrato.
2. `uv run ruff check .`: limpo.
3. `npm --prefix web run build`: sem erro.
4. `uv run pytest tests/e2e/test_fatia.py -q`: `TestClient` + `FakeLLMClient` + SQLite em memória. Fluxo: login demo do gerente →
   envia `data/demo/escala_atual.csv` → resumo `ok` → confirma → `report.total == 0` na otimizada, `before.violations > 0` →
   justificativa → aprova → `GET /api/schedules/published` devolve a versão. Mais 5 casos: **`publicar` sem aprovação é recusado** (403 na
   rota e `schedule.publish_refused` no rastro); **cada um dos 8 passos tem um `trace_event` com `cost_usd` não nulo** (0 nos passos sem modelo,
   o custo falso no `llm.justify`); CSV com defeito → RX-13 com a linha; LLM falhando → RX-12 visível e nenhum texto de justificativa; nenhuma
   resposta contém `sex`.
5. `uv run python -m escalista.evals --suite e1`: 10/10, ou o número real, sem arredondar.
6. **À mão em `http://localhost:8000`** (com o `.env` do usuário, modelo real): entrar como gerente → "usar escala de exemplo" → confirmar
   o resumo → conferir 0 violações, o antes e o depois e a justificativa em português → aprovar → ver a grade publicada → abrir os eventos
   e conferir o custo medido do `llm.justify`. Repetir com `escala_defeito.csv` (RX-13). Registrar o custo e a latência medidos no
   [estado](../estado-do-projeto.md) (Métricas medidas).

## 7. Fluxo de git (uma pessoa, 4 sessões) [PROPOSTA]

- **Worktrees:** `git worktree add ../cc61-a -b c5/a-contracts main` (e `cc61-b`, `cc61-c`, `cc61-d`). Em cada um: `uv sync`. Em `cc61-c`:
  `npm --prefix web ci`. O `.env` não vai para os worktrees, salvo o da sessão B **na hora da fumaça (B4)**, e quem o copia é o usuário.
- **Branch curto por tarefa** (`c5/<frente>-<tarefa>`, por exemplo `c5/d-verifier`). Antes do merge: `git rebase main`, `uv run pytest -q`,
  `uv run ruff check .`. O usuário integra com `git merge --ff-only` no `main` e faz `git push`. Sem PR no GitHub (com uma pessoa, o PR só
  custa tempo); o histórico de commits pequenos fica como evidência.
- **Donos exclusivos:** `domain/`, `tests/fakes.py` e `tests/architecture/` → sessão A. `pyproject.toml` e `uv.lock` → **ninguém**: nada de
  `uv add`. A única edição prevista é o marcador `slow` na T0. Se faltar pacote, o usuário decide e o adiciona sozinho no `main`, um por vez, sob a
  data de corte. `api/` e `web/` → C. `llm/`, `audit/`, `clock/` e `agents/` → B. `rules/` → A (exceto `rules/validation.py`, de D).
  `synth/`, `ingest/`, `verifier/`, `evals/`, `data/demo/` e `data/regras/{convencao,politica}/` → D. `store/` → B (implementa o `Repository`
  de A).
- **Docs sem conflito:** cada sessão escreve só na sua subseção do **Registro de execução** (seção 12 deste plano). O registro do
  [estado](../estado-do-projeto.md) e as Métricas medidas, só o usuário (ou a sessão A, a pedido dele) no merge. O hook `docs_sync.py`
  vai cobrar doc em cada sessão: a resposta é a linha no registro deste plano.
- **Commits:** em inglês, Conventional Commits, terminando com `Co-Authored-By` do modelo que executou. **Só quando o usuário pedir**
  (CLAUDE.md): se o "aprovado" deste plano vale como pedido de commit por tarefa nas 4 sessões **foi autorizado na [DEC-040](../decisoes.md)**, só na branch do worktree.
  Sequência sugerida: `feat(domain): add slice contracts and repository port` → `feat(rules): load and merge rule layers` →
  `feat(audit): persist trace events with masking` → `feat(api): add demo session and role guard` → `feat(rules): add fictitious demo
  convention and policy` (D1, mesmo sendo dado) → `feat(synth): generate seeded network, demand and schedules` → `feat(ingest): validate
  schedule csv` → `feat(solver): add cost function and before-after comparison` → `feat(llm): add featherless client with key failover` →
  `feat(llm): add structured output with pydantic retries` → `feat(api): add slice routes` → `feat(solver): add cp-sat model and benchmark`
  → `feat(verifier): add independent checks for slice primitives` → `feat(agents): add minimal optimizer graph with approval-gated publish` →
  `feat(web): add slice screens` → `feat(evals): add e1 scenarios without model` → `test(e2e): add slice smoke` → `docs: record c5 execution and g3`.

## 8. Divisão por sessão e modelo de desenvolvimento

O usuário opera as 4 sessões ([DEC-039](../decisoes.md)). Os modelos seguem a política da [DEC-028](../decisoes.md); a distribuição por tarefa
é **[INFERÊNCIA]** e se troca com `/model` antes de cada tarefa.

| Sessão | Tarefas | Modelo | Por quê |
|---|---|---|---|
| A | T0, A1, A3, A2 | **Opus 5.5** em tudo | Contratos que destravam tudo; fusão de camadas e solver têm o maior custo de erro (DEC-028, C1 e C2) |
| B | B1, B2, B3, B4, I1 | Sonnet 5.5; **Opus 5.5** em B1 (máscara), no pool de chaves de B2 e na ferramenta `publicar` de I1 | Segredos e aprovação humana |
| C | C1, C2, C3, C4 | **Opus 5.5** em C1 e C2 (acesso); Sonnet 5.5 em C3 e C4 | Controle de acesso é núcleo (DEC-018) |
| D | D1, D2, D3, D4, D5 | Haiku 5.5 em D1 e D2; **Opus 5.5** em D3 e D4; Sonnet 5.5 em D5 | Dados mecânicos; validação e verificador são núcleo |

Os outros 3 integrantes não programam nesta madrugada. O que podem fazer está na mensagem da seção 10.

## 9. Estimativa honesta e riscos

**Soma por sessão [PROPOSTA]:** A 2,25 a 3,5 h · B 2,5 a 4,25 h · C 2,75 a 4 h · D 2,25 a 3,75 h. **Caminho crítico:** 3,25 a 5 h.
**Janela:** ~4,75 h por sessão (23h45 às 03h e 07h às 08h30).

- **Na faixa baixa ou no meio, o G3 passa antes do G4**, provavelmente na manhã (07h às 08h). **Na faixa alta, o caminho crítico passa
  ~15 min do G4**, e a sessão B passa ~30 min por causa de I1.
- **O G4 em si não cabe [INFERÊNCIA, com números]:** o G4 pede C6, C7 e C8 "concluídas ou cortadas conscientemente". O plano macro estima
  C6 2 a 3 h, C7 3 a 4,5 h e C8 2,5 a 3,5 h (7,5 a 11 h, em paralelo nas frentes), e a fatia consome quase toda a janela até 08h30.
  Entre 08h30 e o G6 (11h30) sobram 3 h. **Você decide** o que fazer com C6 a C8. Este plano não corta nada.
- **Se escorregar (só com a sua aprovação):** a ordem de corte é a do [produto, seção 2](../produto.md) e só toca o que está fora da
  fatia (FT-06, desejáveis, gatilhos de hora extra, foto do atestado, convenção em PDF, reotimização semanal). **Não se cortam** exceções
  (RX-02, RX-12 e RX-13 da fatia), rastro, evals E1 e o teste de fronteiras. Cortes técnicos de polimento dentro da fatia, se você
  aprovar: grade simples em tabela em vez de visual rico; lista de eventos sem filtro.

| Risco | Efeito | Mitigação |
|---|---|---|
| Solver 60 × 7 lento ou inviável | A2 estoura; caminho crítico passa do G4 | Bench primeiro; limite de tempo; catálogo de turnos menor; escala persistida e mostrada da tabela |
| Chaves da Featherless não testadas (chave 1 vazia; 4ª pessoa sem resgatar) | `llm.justify` falha no teste à mão | B4 roda cedo; a fatia passa com RX-12 visível, nunca com texto inventado ([plano macro, 5.5](../plano-implementacao.md)) |
| Contrato muda no TDD de A ou D | Retrabalho em B, C e I1 | T0 mínima; PR só de contrato; rebase avisado pelo usuário |
| Usuário vira o gargalo de 4 sessões | Sessões paradas esperando merge | Tarefas de 15 a 60 min; merges agrupados; I1 e C4 com tudo parado |
| Cansaço depois da 01h | Bug no núcleo | TDD no núcleo; parar às 03h como decidido |
| Política do Pedro Veloso chega no meio | Conflito com D1 | A dele substitui D1 por um PR de dados; os testes de A1 usam fixtures próprias, e não os arquivos de `data/` |

## 10. Mensagem para o grupo do WhatsApp

> Plano da madrugada (G3 local, sem deploy): eu rodo 4 sessões do Claude em paralelo, uma por frente. A: contratos, regras e solver. B: LLM,
> rastro e agente. C: login demo, API e telas. D: dados sintéticos, política fictícia, verificador e evals. Primeiro congelo os contratos
> (~40 min) e depois abro as 4. Paro às 03h e volto às 07h. Meta: a fatia ponta a ponta rodando em localhost antes das 08h30.
> Preciso de 3 coisas de vocês: (1) @Pedro Veloso, se tiver a política e a convenção fictícias, manda até 00h30. Senão eu escrevo uma
> versão mínima e você revisa amanhã. (2) Quem ainda não resgatou os US$ 25 da Featherless: resgata hoje (vence amanhã) e me passa a
> chave no privado, nunca no grupo. (3) Quem estiver acordado pode adiantar o roteiro do pitch de 3 min (docs/entrega.md). Nada de código
> no repo hoje, para não dar conflito.

## 11. Pendências que bloqueiam

- `Commits por tarefa nas 4 sessões: **autorizados** na branch do worktree, sem push e sem commit no `main` ([DEC-040](../decisoes.md)).
- `[PREENCHER]` O que fazer com C6, C7 e C8 diante do G4 (seção 9).
- `[PREENCHER]` Política e convenção do Pedro Veloso (G2 venceu às 19h sem entrega; D1 cobre a fatia).
- `[PREENCHER]` Valor da ampliação diária da convenção fictícia (pergunta 17); a fatia não depende dele.
- `[PREENCHER]` "Gestor de RH" (pergunta 15): a fatia usa só o gerente; resolver antes da C8.
- Chave 1 da Featherless e o resgate da 4ª pessoa (ação humana; B4 depende).
- Os itens `[PROPOSTA]` deste plano (nomes de contratos, quinta primitiva, semana de 11/01/2027, hora extra só com autorização, `store/`,
  verificador na sessão D, fluxo sem PR) entraram no "aprovado" ([DEC-040](../decisoes.md)) ou mudam por nova DEC.

## 12. Registro de execução

Cada sessão escreve só na sua subseção: início, fim (`date`), desvios e métricas medidas.

**Como rodou (08/11, 23h52 a 00h43):** uma sessão orquestradora (Claude, Opus 5.5) delegou cada tarefa a um subagente no worktree da
frente, verificou o diff, a suíte e o ruff, fez o rebase e integrou no `main` local com `merge --ff-only`, **sem push**. Escolhas do
usuário às 23h55: merge pelo orquestrador; commit das docs de registro pelo orquestrador; duração "indefinido" (lida como "até o G3").
Horários abaixo por `date` nos relatórios dos subagentes; os hashes são os do `main` depois do rebase.

### Sessão A
- **T0** (opus) 23:54:38–23:56:58, `7ce7517`: contratos da tabela 3.1 em `domain/rules.py`, `schedule.py` e `results.py`; porta
  `Repository`; `InMemoryRepository`; `store` em `CONCRETE_BORDERS`; marcador `slow`. Escolhas de forma: `Schedule.week_start` exige
  segunda-feira; `EmployeePublic` não herda de `Employee`; `ViolationReport.total` é campo calculado.
- **A1** (opus) 23:59:19–00:03:03, `81eeb99`: `rules/loader.py` e `merge.py`; 7 testes do TDD na ordem. `kind` = id do YAML; `params`
  `{"hours"}`, `{"days"}` ou `{"percent"}`. **Desvio:** todo conflito entre camadas abre `ExceptionCard` com código RX-01 (o requisito
  define RX-01 só para convenção contra a EC 141); constante `merge.CONFLICT_CODE`.
- **A3** (opus) 00:03:55–00:05:35, `39ad2a7`: `solver/cost.py` (`compute_metrics`, `compare`, `compare_schedules`). Turno noturno conta
  no dia de início; arredondamento `ROUND_HALF_UP` só na saída.
- **A2** (opus) 00:06:35–00:18:52, `3b5795c`: catálogo (85 turnos por loja), CP-SAT decomposto por loja (exato: a pessoa só trabalha na
  própria loja), presolve desligado (medido: com ele, 13,5 s e 20,5 s), RX-02 com o DP como decisor e a conta de contratação. Bench
  medido na demanda original: 7,39 s (1 thread) e 6,46 s (8), ótimo, 9,5 pessoa-horas descobertas → motivou a D2b.

### Sessão B
- **B1** (opus) 23:54:38–23:59:28, `847c231`: tabela `trace_event`, `SqlTraceSink` (máscara também nas colunas de texto), `Masker`,
  `SystemClock`. **Desvio:** coluna `seq` a mais na tabela, só para ordenar (o `TraceEvent` não mudou).
- **B2** (opus) 00:00:29–00:07:35, `4f89986`: `FeatherlessClient` e `KeyPool`. **Desvios:** 402 e 403 também trocam de chave; 5xx e
  erro de conexão repetem como o 503; semáforo padrão 2 `[PROPOSTA]`; sem guarda de orçamento diário. Da documentação da Featherless
  (consultada em 08/11): `usage.cost` em USD confirmado; o status de saldo zerado (402) e o `tool_choice` forçado **não** confirmados.
- **B3** (sonnet) 00:08:31–00:10:04, `b214414`: `tool_schema_for`, `call_structured` (até 2 reenvios, depois RX-12), `justify` com
  checagem de `rule_refs`; prompt sem nome nem sexo.
- **S1** (sonnet) 00:10:42–00:11:46, `041f236`: `store/` com `SqlRepository`; mesma bateria de testes contra o falso e o SQL. Lacuna do
  plano preenchida (a seção 3.2 previa o pacote, mas nenhuma tarefa o criava).
- **B4** (sonnet) 00:12:22–00:13:42, `b424677`: `uv run python -m escalista.llm.smoke` (`--dry-run`, `--large`). **Não rodado com chave
  real** (é do usuário).
- **I1** (opus) 00:21:11–00:31:08, `7455fe1`: `OptimizerAgent` com um grafo LangGraph por trecho entre as paradas humanas, sem
  checkpointer; `publicar` lê `get_approval` no código e recusa em 7 casos (inclui papel sem permissão e versão com violação).
  **Desvios:** o CSV enviado fica em memória entre `start_run` e `confirm` (reinício do processo → 409); o `RunState` guarda um só cartão;
  na falha do modelo, o `exception.raised` do cliente real tem `cost_usd` nulo (custo não medido).

### Sessão C
- **C1** (opus) 23:54:38–23:56:35, `8b2d3f5`: sessão por cookie assinado, `require_role`, login de demo, matriz rota × papel.
  **Pendentes:** limite de taxa no login de demo; `Secure` no cookie quando houver https.
- **C2** (opus) 23:59:19–00:04:19, `3e54c30`: rotas da fatia contra o agente falso; Protocol `SliceAgent`. **Desvio de ambiente:** sem
  `python-multipart` instalado (e sem `uv add`), o CSV vai no corpo bruto `text/csv`.
- **C3** (sonnet) 00:05:18–00:07:32, `5f0dbfc`: telas da SPA. Build e typecheck verdes; **ainda não aberta num navegador**.
- **C4** (sonnet) ~00:31–00:39:20, `81c8680` e `90ed22c`: `build_agent` e o adaptador `OptimizerSliceAgent`; `tests/e2e/test_fatia.py`
  (7 testes). **Ponto frágil:** o teste de recusa sem aprovação depende da ordem dos testes do arquivo.

### Sessão D
- **D1** (haiku) 23:54–23:55, `b9ddb98`: convenção e política fictícias (`status: ficticia`); hora extra só com autorização do DP em
  `excecoes:`.
- **D2** (haiku) 23:59–00:04, `cff6037`: geradores com seed 42; 3 lojas, 60 pessoas, CSV longo da DEC-039 com a marca SINTETICO;
  9 violações e 5 defeitos plantados.
- **D3** (opus) 00:04:45–00:08:11, `8b61450`: leitura (borda) e validação (pura). RX-13 também para dado inconsistente, com a escala
  parcial; `fim == inicio` é problema, não turno de 24h.
- **D4** (opus) 00:09:00–00:11:11, `b8fd023`: verificador independente; 9 de 9 violações plantadas, 0 falso positivo.
- **D2b** (sonnet) 00:21:11–00:23:31, `5691b58`: teto de 8 pessoas por faixa (40% da equipe) na demanda sintética, porque o ótimo deixava
  9,5 pessoa-horas descobertas e a demo padrão cairia sempre no RX-02. **Decisão do orquestrador** (a D2 já tinha que caber na
  capacidade); só `demanda.json` mudou em `data/demo/`. Texto "46h40" de P003 corrigido para 46h.
- **D5** (sonnet) 00:24:28–00:27:23, `bf9ab44`: E1 com 10 cenários sem modelo.

### Integração e G3
- **Ordem real de merge:** T0, C1, D1, B1, A1, D2, C2, A3, C3, B2, D3, B3, D4, S1, B4, A2, D2b, D5, I1, C4. Sempre que mais de uma tarefa
  estava pronta, valeu a ordem do plano; a C2 e a C3 entraram antes da sua vez porque eram as únicas prontas. A I1 e a C4 foram
  integradas com as outras frentes paradas. Nenhum conflito de rebase.
- **G3, itens 1 a 5, conferidos pelo orquestrador no `main` às 00h42** (`90ed22c`): (1) `uv run pytest -q` **463 passed** em 66 s
  (o padrão roda os `slow`), fronteiras incluídas; (2) `ruff check` limpo; (3) `npm --prefix web run typecheck` e `build` sem erro;
  (4) `tests/e2e/test_fatia.py` **7 passed** em 25 s; (5) E1 **10/10**. Bench `--seed 42`: 1 thread 11,99 s e 8 threads 12,27 s, ótimo
  nas 3 lojas, R$ 20.014,00, cobertura 100%. Nenhum teste lê o `.env` real (conferido: todo `Settings(...)` dos testes usa
  `_env_file=None`).
- **Fumaça da C4 (sem chave, porta 8010):** `confirm` em 12,02 s; antes 158 violações e R$ 33.989,15 com 216,5 h de hora extra; depois
  0 violações, R$ 20.014,00 e 0 h de hora extra; RX-12 visível sem texto inventado; publicação e rastro persistidos depois de reiniciar;
  `escala_defeito.csv` → RX-13 com as 5 linhas.
- **Item 6 (à mão, com o `.env` e o modelo real): pendente, é do usuário.** Roteiro na resposta da sessão orquestradora e em
  [estado](../estado-do-projeto.md) (próximas ações).
