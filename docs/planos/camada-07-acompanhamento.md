# Plano da C7 · Acompanhamento de escala (FT-03): passivo, oferta ao colega e gatilhos ativos

Última atualização: 2026-11-08 10:32 (Recife) · Situação: **aprovado pelo usuário às 09:22; M1 (10:10), M2 (10:16) e M3 = T2 parcial (10:31, foto e RF-27) prontos; recomendado um PR só pela branch `c7/m3`** (DECs gravadas como [DEC-058](../decisoes.md) a [DEC-067](../decisoes.md)). Antes: 09:24, contrato v1.1 incorporado · Planejado por Claude (Opus 5.5)
numa sessão só de planejamento (worktree `cc61-plan-acomp`, branch `plan/acompanhamento`, a partir de `origin/main` `b6f4a01`): sem
código, sem `uv add`, sem commit. As DECs propostas (seção 16) **não foram gravadas** em [decisoes.md](../decisoes.md) nem no
[estado](../estado-do-projeto.md): outras sessões editam esses arquivos ao mesmo tempo.

**Rótulos:** sem rótulo, é decisão do usuário (citada). **[FATO]** tem fonte (arquivo, comando ou medição). **[PROPOSTA]** é sugestão do
agente. **[INFERÊNCIA]** é dedução sem medição. **[HIPÓTESE]** é premissa de produto não confirmada. `[PREENCHER]` é o que falta.
`[NÃO ENCONTRADO]` é o que se procurou e não se achou. **Todas as horas são [PROPOSTA], em faixa, e nenhuma foi medida.**

**Contrato com os evals:** `/Users/pedrohmv/Projetos/cc61-plan-shared/contrato-acompanhamento-evals.md` (fora do repositório). As saídas
`SAIDA-AC-01` a `SAIDA-AC-18` deste plano estão na seção 2 de lá; os pedidos `PEDIDO-EV-01` a `16` do plano dos evals (sessão B,
`docs/planos/evals-e3-e4.md`) estão respondidos na seção 4. **Congelamento do lado A: ver a seção 6 do contrato** (hora registrada lá e
na seção 17 deste plano: **09:18**). Se este plano e o contrato divergirem, vale o contrato e abre-se linha na seção 4 de lá.

## 0. Como o trabalho roda

- **Hora de referência:** 09:01 de dom 08/11 (`date`). **Link público testado às 11h30 (G6), congelamento às 12h00, submissão às
  13h00.** Cada merge no `main` publica no Railway e **só o usuário faz merge no `main`**.
- **Tempo de referência medido:** C5 ~45 min de relógio; C6 ~3h25 (02h54 a 06h19), ambas com orquestrador e 4 frentes
  ([estado](../estado-do-projeto.md), Métricas medidas, e [plano da C6](camada-06-leitura-e-formulacao.md), seção 21).
- **Mesmo arranjo da C6:** um orquestrador, 4 frentes (A a D), um worktree por frente (`cc61-c7-{a,b,c,d}`), integração em
  **`c7/integra`** (worktree `cc61-c7-integra`), rebase e `merge --ff-only`. O `main` só recebe os marcos **M1** e **M2** (seção 12).
- **Janela real [PROPOSTA]:** execução de ~09h45 a ~11h15 para o T1. **O T1 está dividido em T1a (M1) e T1b (M2)** para que, se o
  relógio vencer, o M1 sozinho já seja uma demo honesta do FT-03.
- **Corte por relógio (regra do orquestrador) [PROPOSTA]:** às **10h50**, o que não estiver verde em `c7/integra` sai do M1. Às **11h15**,
  o M2 vai ao usuário como está (só o que estiver verde). **Nada do T2 começa antes de o M2 estar pronto para o merge.** Depois das
  11h30, só correção de defeito.

## 1. Objetivo e valor demonstrável

**Em uma frase:** a falta ou o atraso vira um turno coberto, com o colega que aceitou, a validação do gestor, a escala republicada sem
violação nova, as mensagens registradas e o rastro de cada passo; e o agente percebe sozinho quem não bateu o ponto.

**Roteiro de ~2 minutos no link público (o que o jurado vê) [PROPOSTA]:**

1. **(gestor)** Entra como gestor e clica **"Reiniciar demo"**: publica a semana sintética com folga (rótulo "cenário pré-carregado,
   SINTÉTICO") e o relógio de demo vai para **qua 13/01/2027 13:55 (tempo simulado)**, mostrado no topo.
2. **(colaborador)** Abre o celular simulado como **Ana (sintético)**, toca "Vou faltar" em qui 14/01 e anexa o atestado em PDF
   (`at-01-legivel.pdf`). O Pat confirma o recebimento, diz "atestado lido: válido, 2 dias; abono **provisório** até o gestor
   confirmar", **sem CID**.
3. **(colaborador)** Troca de pessoa no celular para **o candidato 1** (o seletor "Você é:" só lista o quadro). Vê a oferta "cobrir qui
   14/01, 14–22h, sem hora extra" e toca **Aceitar**.
4. **(gestor)** Em Exceções, o cartão **"Cobertura: <candidato> aceitou"** traz motivo, evidência (avaliados, aprovados pelo
   verificador, custo adicional) e opções. **Valida**: a escala é republicada (0 violações novas) e os dois recebem a mensagem.
5. **(gestor)** Clica **"+15 min"** duas vezes: às 14:10 o varredor vê que a **Carla (sintético)** não bateu o ponto (turno das 14h,
   tolerância de 10 min da política) e pergunta a ela; às 14:25, sem resposta, abre o **RX-09** com opções.
6. **(gestor)** Abre a auditoria de um caso: `track.report.received` → `track.llm.read_atestado` (modelo, tokens, **custo medido**,
   latência) → `track.offer.sent` → `track.offer.accepted` → `exception.decided` → `schedule.republished` → `track.case.closed`.

**O que fica fora de cada nível** está na seção 2.

## 2. IDs cobertos, por nível, e o que fica de fora

| Nível | Cobre | Fica fora |
|---|---|---|
| **T1a (M1)** obrigatório | relógio de demo e botões (arquitetura, seção 13); "Reiniciar demo" com a semana com folga; RF-09 sem atestado (aviso → `ReplanRequest` → `find_cover` → **oferta ao colega, que confirma antes** → **gestor valida sempre** → republica → avisa os dois); RX-05, RX-06 (prazo por oferta, próximo da lista); RH-06 (toda mensagem registrada); RX-10 na entrada; RN-01 (eventos `track.*`); portão de aprovação no código | atestado, gatilhos ativos |
| **T1b (M2)** obrigatório | RF-19 **só PDF digital** (texto + modelo `small`, campos fechados); RX-08 (não recusa, escala ao gestor); RX-12 (modelo, busca ou ponto fora não derrubam o fluxo); abono provisório; **RN-06** (filtro de saída e teste de vazamento); RF-16 (sem batida no ponto simulado → pergunta → RX-09); RF-28 (aviso ao gestor quando a cobertura só fecha com hora extra) | foto, RF-27, RF-25, conversa livre |
| **T2** se sobrar tempo antes das 12h | foto do atestado pelo modelo de visão (o usuário escolheu T2, 09:10); RF-27 (80% e 100% do limite semanal de hora extra); `confirmar_abono` pelo gestor; conversa livre curta (`Tracker.message`, alvo dos evals de injeção E4-03/04/07) | — |
| **T3** depois da submissão ou nunca | RF-25 (verificação semanal pelos critérios de `pol_reotimizacao_semanal`); solver de janela no replanejamento; `CloudApiChannel` (o canal real, [DEC-043](../decisoes.md); a porta `Channel` já o comporta) | — |

**Fora da C7 em qualquer nível:** advertência e desconto (só humanos, RH-04); recusa de atestado (nunca); folha e férias; ponte não
oficial do WhatsApp (abandonada, [DEC-043](../decisoes.md)); agendador em segundo plano (decidido: o varredor só roda quando o relógio
avança, arquitetura seção 13).

## 3. Estado atual × alvo

Lido em `origin/main` `b6f4a01` [FATO, `git grep` e leitura dos arquivos citados].

| Peça | Existe hoje (arquivo) | O que muda | Novo |
|---|---|---|---|
| Aviso de falta | `POST /api/colaborador/falta` em [api/excecoes.py](../../src/escalista/api/excecoes.py): texto aceito e **não gravado**; vai direto ao cartão do gestor com 3 candidatos | a rota passa a chamar `Tracker.report` (mesmo corpo, compatível com a tela atual) | `POST /api/colaborador/aviso` (multipart, com anexo) |
| Busca de cobertura | `find_cover` em [agents/cover.py](../../src/escalista/agents/cover.py): mesma loja, sem turno no dia, verificador independente, ordem (hora extra, função, custo, id) | **reaproveitada sem mudança**, chamada pelo despachador do `ReplanRequest` | `agents/tracker/replan.py` |
| Oferta ao colega e aceite | **[NÃO ENCONTRADO]** (o gestor escolhe direto) | — | ofertas com prazo, aceite, recusa, próximo (RX-06) |
| Validação do gestor e publicação | `ExceptionDesk.decide` → `_covered_version` → `_publish` → `publicar` (relê a aprovação) | itens `source.kind == "track"` delegam ao `Tracker.on_decision`, que usa a ferramenta `aplicar_cobertura` (aceite + aprovação) e o mesmo `publicar` | `agents/tracker/tools.py` |
| Fila de exceções | `ExceptionStore` ([store/exceptions.py](../../src/escalista/store/exceptions.py)), tela `web/app/plataforma/excecoes` | cartões novos: `COBERTURA`, RX-06, RX-08, RX-09, RX-12 | porta `ExceptionQueue` em `domain/ports.py` (o agente não importa `store/`) |
| Relógio | só `SystemClock` ([clock/system.py](../../src/escalista/clock/system.py)); `FixedClock` em [tests/fakes.py](../../tests/fakes.py) | `build_desk` passa a usar o `DemoClock` | `clock/demo.py` (`demo_clock` no banco), `FakeClock` que avança |
| Ponto simulado, varredor | **[NÃO ENCONTRADO]** | — | `synth/ponto.py` (`SimulatedPunchSource`), `agents/tracker/sweep.py` (puro) |
| Canal | `channel/__init__.py` só com docstring; porta `Channel` e `ChannelMessage` **não existem** [FATO, `git grep`] | — | porta `Channel`, `SimulatedPhone`, tabela `channel_message` |
| `ReplanRequest` | **não existe** em `domain/` [FATO] | — | contrato e tabela (dentro de `track_case`) |
| Leitura de atestado | **[NÃO ENCONTRADO]**; `pdfplumber` já é dependência [FATO, `pyproject.toml`] | — | `ingest/atestado.py` (texto, corte do CID, chamada ao modelo), `rules/atestado.py` (`judge`, puro), `llm/prompts/atestado.py`, porta `AtestadoReader` |
| Visão | `LLMMessage.content: str` [FATO, `domain/contracts.py`]: **não aceita imagem** | T2: `content` aceita partes (texto e imagem) | — |
| Máscara do rastro | `audit/mask.py` cobre só segredos e chaves de API, **não CID** [FATO] | `SqlTraceSink` aplica também `protected.scrub` | `audit/protected.py` |
| Política | `pol_atraso`, `pol_oferta_turno`, `pol_hora_extra`, `pol_aviso_*`, `excecoes_demo` com RX-01, RX-05, RX-08 [FATO, `politica_ficticia.yaml`] | acrescentar **RX-06 e RX-09** em `excecoes_demo` (fictícios, `status: interpretacao`, "proposta do agente") | `rules/tracking_policy.py` (`TrackPolicy`) |
| Escala com folga | na otimizada do exemplo, 5 de 5 faltas abrem RX-05 [FATO, briefing]; com o piso da carga do contrato ([DEC-055](../decisoes.md)) as 60 pessoas têm 44 h de contrato [FATO, DEC-055] | — | `data/demo/acompanhamento/cenario_folga.json` com gente de **meio período** (contrato de 24 h) na loja da falta [INFERÊNCIA: é o que abre folga sem hora extra; a D1 prova com teste] |
| Celular simulado | [web/app/colaborador/page.tsx](../../web/app/colaborador/page.tsx): semana, "vou faltar", sondagem a cada 3 s | seletor "Você é:", caixa de mensagens, ofertas com Aceitar/Recusar, anexo PDF | barra do relógio de demo (gestor e colaborador) |

## 4. Desenho (decisões de arquitetura) [PROPOSTA]

**4.1 Estado nas tabelas, sem checkpointer e sem LangGraph no acompanhamento.** O caso (`track_case`) guarda o estado inteiro em JSON,
como `exception_item`; mensagens em `channel_message`; o relógio em `demo_clock`. O fluxo é uma **máquina de estados em código**
(`agents/tracker/flow.py`) reexecutada a partir das tabelas a cada evento (aviso, aceite, decisão, avanço do relógio). O modelo só entra
em nós de linguagem (leitura da comprovação no T1; conversa no T2). **Por quê:** todo passo é disparado por um humano ou pelo relógio; um
grafo não acrescenta nada e custaria tempo. **Melhor argumento contra:** a arquitetura (seção 4) diz "cada agente é um grafo LangGraph"; o
pitch fala em agentes e um jurado técnico pode procurar o grafo. Resposta: os nós determinísticos são o desenho declarado ("fluxos que
são regra são nós determinísticos"), e o rastro mostra cada nó. Vira DEC (seção 16).

**4.2 `ReplanRequest` e despachador in-process.** O acompanhamento nunca chama a busca de cobertura direto: grava um `ReplanRequest`
(dentro do caso, com evento `track.replan.requested`) e o despachador in-process (`agents/tracker/replan.py`) o entrega à
`find_cover`, que devolve a lista ordenada. **Só `find_cover` no v1** (o usuário escolheu às 09:10); o solver de janela fica no T3. Sem
candidato: RX-05. Se o melhor candidato gera hora extra: RF-28 (aviso ao gestor). **Contra:** a cobertura só reatribui o turno; não
remaneja outras pessoas para abrir espaço. O pitch diz "cobertura verificada pelas regras", nunca "reotimização".

**4.3 Porta `Channel` e `SimulatedPhone`.** `Channel.send(message: ChannelMessage) -> None` e `Channel.inbound(...)`. O
`SimulatedPhone` grava em `channel_message` e é lido pela caixa do celular (sondagem de 3 s, a que a tela já faz). **Como o colega
confirma:** o celular simulado ganha o seletor **"Você é: <pessoa>"**, que lista só o quadro da escala publicada; as rotas do
colaborador aceitam `as=<employee_id>` **só com `DEMO_MODE=1`**, validado contra o quadro (RX-10, [DEC-017](../decisoes.md)). Sem `as`,
vale a regra atual de quem é a colaboradora da demo. **Contra:** o login de colaborador vira "qualquer pessoa do quadro"; aceitável numa
demo rotulada, inaceitável em produção (lá, o canal real identifica pelo número).

**4.4 Relógio de demo no banco e botões.** `DemoClock` lê e grava `demo_clock` (uma linha). Botões: **+15 min, +1 dia, +1 semana,
Reiniciar** (gestor e colaborador veem; só o gestor reinicia). **Cada avanço chama `Tracker.run_sweep()`** e devolve o resumo. "Reiniciar"
publica a semana com folga (escolha do usuário, 09:10), apaga casos e mensagens do acompanhamento e põe o relógio em qua 13/01/2027 13:55.
A fila de exceções passa a usar o `DemoClock` (prazos coerentes com o tempo simulado). O resto do app segue no `SystemClock`.
**Contra:** dois relógios no mesmo app; a tela mostra sempre "tempo simulado" junto da hora.

**4.5 Varredor determinístico.** `sweep.detect(schedule, punches, policy, cases, now)` é **puro** (sem banco, sem relógio do sistema) e
devolve `Trigger`s; `Tracker.run_sweep` aplica os efeitos e é **idempotente** (um gatilho com o mesmo `kind` e `ref` não volta). Gatilhos
T1: `no_punch`, `no_answer`, `offer_expired`. `overtime_needed` (RF-28) nasce na busca de cobertura, não no varredor. T2:
`overtime_near_limit`, `overtime_limit`. T3: `weekly_check`.

**4.6 Ponto simulado.** `SimulatedPunchSource.punches(until)` deriva as batidas da escala publicada e dos desvios plantados
(`ponto_desvios.json`), sem tabela: entrada no início e saída no fim, salvo o desvio (falta: sem batida; atraso: entrada `+minutos`; hora
extra: saída `+minutos`). Determinístico. Mora em `synth/` (borda), atrás da porta `PunchSource` [PROPOSTA].

**4.7 Leitura do atestado (T1b, só PDF).** O agente não pode importar `llm/` nem `ingest/` (seção 5.5), então a leitura é uma borda
injetada pela porta `AtestadoReader`. `ingest/atestado.py::read_atestado(*, data, media_type, llm, run_id, expected_day, employee_name)`
(SAIDA-AC-05 v1.1): `pdf_text` (pdfplumber, em memória) → `audit.protected.strip_cid` (corta o CID **antes** do modelo) →
`call_structured` com o schema fechado da seção 5, `size="small"`, `kind="track.llm.read_atestado"`, ferramenta
`llm/prompts/atestado.TOOL_NAME = "read_atestado"` (PEDIDO-EV-19) → `rules/atestado.py::judge(fields, expected_day, employee_name)`, **puro**,
que calcula `verdict` e `reasons`. PDF sem texto (escaneado) → `ilegivel`, sem chamar o modelo. O `Tracker` só vê a porta.

**4.8 Ofertas sequenciais.** Uma oferta por vez, na ordem do `find_cover`; a 2ª sai quando a 1ª vence (20 min) ou é recusada; até 3
(`candidatos_max_antes_de_escalar`); depois, RX-06 (confirmado aos evals, nota do PEDIDO-EV-15). **Contra:** ofertas simultâneas cobririam
mais rápido; mas criam o problema de dois aceites para um turno.

## 5. Contratos (tarefa A0; só a frente A edita `domain/`)

### 5.1 Modelos novos: `domain/tracking.py` [PROPOSTA]

```python
class Attachment(BaseModel):  # só em memória; nunca persistido
    data: bytes
    media_type: Literal["application/pdf", "image/png", "image/jpeg"]
    filename: str


class Punch(BaseModel):  # batida do ponto simulado
    employee_id: str
    shift_start: datetime
    kind: Literal["in", "out"]
    at: datetime


class Deviation(BaseModel):  # desvio plantado
    id: str
    employee_id: str
    shift_start: datetime
    kind: Literal["falta", "atraso", "hora_extra"]
    minutes: int = 0


TriggerKind = Literal[
    "no_punch", "no_answer", "offer_expired", "overtime_near_limit", "overtime_limit", "overtime_needed", "weekly_check"
]


class Trigger(BaseModel):
    kind: TriggerKind
    employee_id: str | None
    ref: str
    observed: str
    threshold: str
    rule_ref: str


class AtestadoFields(BaseModel):  # o que o modelo devolve (schema fechado; sem CID, sem médico, sem texto livre)
    legible: bool
    issued_on: date | None
    start_on: date | None
    days: int | None = Field(default=None, ge=1, le=30)
    patient_matches: bool | None
    has_crm: bool | None


Reason = Literal["data_nao_bate", "sem_data", "sem_crm", "nome_nao_bate", "ilegivel", "dias_fora_da_faixa"]


class AtestadoReading(AtestadoFields):
    verdict: Literal["valido", "inconsistente", "ilegivel"]
    reasons: list[Reason]


class ReplanRequest(BaseModel):  # arquitetura, seção 4 e 8
    id: str
    case_id: str
    window_start: datetime
    window_end: datetime
    absent_id: str
    reason: Literal["falta", "atraso", "no_punch", "overtime_limit"]
    origin_trace_id: str | None


class Offer(BaseModel):
    id: str
    candidate_id: str
    rank: int
    status: Literal["enviada", "aceita", "recusada", "vencida"]
    sent_at: datetime
    deadline: datetime
    overtime_hours: Decimal
    added_cost: Decimal


CaseStatus = Literal[
    "aguardando_colaborador",
    "oferta_enviada",
    "aguardando_gestor",
    "coberto",
    "descoberto",
    "atraso_registrado",
    "decidido",
]


class Case(BaseModel):
    id: str
    kind: Literal["falta", "atraso"]
    origin: Literal["aviso", "ponto"]
    employee_id: str
    shift: Shift
    status: CaseStatus
    created_at: datetime
    abono: Literal["provisorio", "nenhum"] = "nenhum"
    reading: AtestadoReading | None = None
    replan: ReplanRequest | None = None
    offers: list[Offer] = []
    exception_ids: list[str] = []
    handled: list[str] = []  # "<kind>:<ref>" dos gatilhos já tratados (idempotência)
    closed_at: datetime | None = None


class ChannelMessage(BaseModel):  # arquitetura, seção 8 (RH-06)
    id: str
    case_id: str | None
    direction: Literal["in", "out"]
    party: str  # employee_id ou "gestor"
    template: str
    body: str | None  # saída: texto nosso; entrada: sempre None (o texto do colaborador não é gravado)
    has_text: bool = False
    attachment_media_type: str | None = None
    decision_ref: str | None
    at: datetime


class TrackPolicy(BaseModel):  # lido de politica_ficticia.yaml por rules/tracking_policy.py
    late_tolerance_min: int
    answer_deadline_min: int
    offer_deadline_min: int
    max_candidates: int
    overtime_weekly_limit_h: Decimal
    overtime_warn_pct: int
```

`CaseView`, `OfferView`, `SweepResult` e `TrackMetrics` são modelos de saída do `agents/tracker/` (contrato, SAIDA-AC-03, 06, 12).

### 5.2 Portas novas em `domain/ports.py`

```python
class Channel(Protocol):
    def send(self, message: ChannelMessage) -> None: ...
    def inbox(self, party: str) -> list[ChannelMessage]: ...


class PunchSource(Protocol):
    def punches(self, *, until: datetime) -> list[Punch]: ...  # levanta PunchUnavailableError -> RX-12


class ExceptionQueue(Protocol):  # o agente abre cartões sem importar store/
    def open(self, card: ExceptionCard, source: dict[str, Any]) -> str: ...


class AtestadoReader(Protocol):  # a borda ingest/atestado.py implementa
    def __call__(
        self, *, data: bytes, media_type: str, run_id: str, expected_day: date, employee_name: str
    ) -> AtestadoReading: ...  # levanta LLMUnavailableError -> RX-12


class TrackRepository(Protocol):
    def save_case(self, case: Case) -> None: ...
    def get_case(self, case_id: str) -> Case | None: ...
    def open_cases(self) -> list[Case]: ...
    def reset(self) -> None: ...
```

### 5.3 Contratos alterados

- `Clock`: sem mudança. `tests/fakes.py` ganha `FakeClock(start)` com `advance(delta)` (A0).
- `LLMMessage.content` (T2, A5): `str | list[ContentPart]`, `ContentPart = {type: "text", text} | {type: "image", media_type, data:
  bytes}`; o `FeatherlessClient` converte para `image_url` com `data:` URI em memória. Só o T2 mexe nisso.
- `excecoes_demo` ganha RX-06 e RX-09 (A2, seção 8).

### 5.4 Eventos de rastro

Lista exata e payloads: **SAIDA-AC-07** no contrato. Regra: `run_id = "track-<case_id>"` (gatilho sem caso: `track-sweep`). Assim o
custo do acompanhamento não se mistura ao da execução da otimização no painel de impacto (que soma por `run_id` [FATO,
`api/insights.py`]).

### 5.5 Regras de importação que o acompanhamento respeita ([arquitetura](../arquitetura.md), seção 2.1; `tests/architecture/boundaries.py`)

1. `agents/tracker/` importa só `domain/`, `rules/`, `verifier/`, `solver.cost` (como a `cover.py` já faz [FATO]), `agents/cover.py`,
   `agents/optimizer/tools.publicar` e as portas. **Nunca** `store/`, `audit/`, `ingest/`, `llm/`, `channel/`, `clock/`, `synth/`, `api/`.
2. `ingest/atestado.py` e `synth/ponto.py` são bordas; quem as liga é `api/tracker_wiring.py`.
3. `rules/tracking_policy.py` e `rules/atestado.py` (`judge`) são núcleo: só `domain/`, stdlib, pydantic e `yaml` (já permitido em
   `rules/` [FATO, teste de fronteira]).
4. **Novo teste (A0):** `datetime.now(` e `date.today(` proibidos em `agents/tracker/` (PEDIDO-EV-01).

## 6. Modelo e privacidade (RN-06, RN-03, RN-07)

| Nó | Nível | Modelo | O que entra | O que sai | Medido onde |
|---|---|---|---|---|---|
| Leitura do atestado em PDF | T1b | `small` (`Qwen/Qwen3.5-9B`, [DEC-020](../decisoes.md)) por `call_structured` | texto do PDF **com o CID já cortado por código**, em bloco delimitado como dado | `AtestadoFields` (fechado) | `trace_event` `track.llm.read_atestado`: `model, key_index, tokens_in, tokens_out, cost_usd, latency_ms` |
| Leitura do atestado em foto | T2 | modelo de visão da Featherless ([DEC-020](../decisoes.md); **nunca testado**) | a imagem, em memória (DEC-020 permite que passe pela Featherless) | `AtestadoFields` | idem |
| Conversa curta | T2 | `small` | o texto do colaborador, como dado | `{intent, day, minutes_late}` | `track.llm.classify_message` |

Custo e latência por leitura **não medidos**; o G da C7 (seção 13) manda medir com a chave e anotar em Métricas medidas.

**RN-06, regras que viram teste:**

1. **Lista única** `audit/protected.py`: `PROTECTED_KEYS`, `CID_PATTERN`, `strip_cid(text)`, `scrub(payload, *, kind)`,
   `find_leaks(blobs, planted, *, pattern_surfaces) -> list[Leak{surface, kind}]` (SAIDA-AC-13 v1.1). O `SqlTraceSink` aplica `scrub`
   antes de gravar, além da máscara de segredos que já existe: **por nome de campo em todo evento; pelo padrão de CID só em `track.*` e
   `channel_message`**, porque o padrão casa referência de célula (`B12`) da evidência da leitura do E2 (achado da sessão B).
2. **CID nunca entra no modelo no caminho PDF** (`ingest.atestado.strip_protected`), nunca no schema de saída, nunca no rastro.
3. **Texto livre do colaborador** é lido e descartado: só `has_text: bool` vai a evento e tabela.
4. **Imagem e PDF só em memória**: `UploadFile.read()`, sem arquivo temporário nomeado; nenhuma chamada de leitura passa pela integração
   automática `langfuse.openai` (já é assim no `FeatherlessClient` [INFERÊNCIA: confirmar na B3]).
5. **Onde o teste olha** (SAIDA-AC-14, tarefa D3): todas as tabelas do SQLite (todas as colunas de todas as linhas), `trace_event`, log
   capturado (`caplog` + `capsys`), todas as respostas HTTP do roteiro e, no caminho PDF, as mensagens enviadas ao `FakeLLMClient`.

## 7. Atos de consequência × humano

| Ato | Quem | Como o código garante |
|---|---|---|
| Confirmar o recebimento, ler a comprovação, registrar, abrir abono **provisório**, avisar o gestor | agente sozinho | — (registrado; RH-06) |
| Achar elegíveis (`find_cover`), oferecer o turno ao próximo da lista, lembrar, passar ao próximo no prazo | agente sozinho | a mensagem só sai para um `candidate_id` da lista do caso; outro destinatário → `track.tool.refused` |
| Perguntar a quem não bateu o ponto | agente sozinho | — |
| **Aceitar o turno** | **o colega** | `Offer.status = "aceita"` só por `respond_offer` com `employee_id == candidate_id` |
| **Validar a cobertura** (a escala muda) | **o gestor, sempre** | `aplicar_cobertura` exige oferta aceita **e** `Approval` gravada; `publicar` relê a aprovação [FATO, já é assim] |
| **Confirmar o abono** | o gestor | T2: `confirmar_abono` exige decisão gravada; no T1 o abono só existe como provisório |
| Decidir RX-05, RX-06, RX-08, RX-09, RX-12 | o gestor | fila existente; opções da política |
| Recusar atestado, advertir, descontar | **ninguém no sistema** | não há ferramenta; RX-08 lista "recusar" como opção vedada [FATO, política] |

Toda recusa do portão grava `track.tool.refused {tool, reason, case_id}` (SAIDA-AC-16, PEDIDO-EV-09).

## 8. Exceções

Todas viram `ExceptionCard` na fila existente, com `exception.raised` no rastro e `source = {kind: "track", case_id}`.

| Código | Quando | Decisor e prazo | Opções (custo) | Sem resposta | Fonte |
|---|---|---|---|---|---|
| `COBERTURA` | o colega aceitou | gestor; 30 min | "Validar: <pessoa> cobre (+R$ x, h extra)", "Recusar e oferecer ao próximo", "Deixar descoberto" | nada é publicado; o turno segue descoberto | `pol_oferta_turno.nota` [FATO] |
| RX-05 | `find_cover` sem candidato | gestor; 30 min | as 3 de `excecoes_demo` (hora extra, remanejar, descoberto) | lembra +30 min; depois descoberto | [FATO, política] |
| RX-06 | 3 ofertas sem aceite (20 min cada) ou lista acabou | gestor; 30 min | **[PROPOSTA, fictícia]** "Hora extra de um colega", "Remanejar de outra loja", "Deixar descoberto" (mesmos custos do RX-05) | descoberto | a acrescentar em `excecoes_demo` |
| RX-08 | `verdict != "valido"` | gestor; 24 h | as 2 de `excecoes_demo` (manter provisório; pedir nova foto ou PDF) | abono segue provisório; **nunca recusa** | [FATO, política] |
| RX-09 | sem resposta 15 min depois da pergunta | gestor; 30 min | **[PROPOSTA, fictícia]** "Tratar como falta e buscar cobertura" (abre `ReplanRequest`), "Aguardar mais 15 min", "Registrar atraso sem cobertura" | turno descoberto, registrado | a acrescentar em `excecoes_demo` |
| RX-10 | `as` ou remetente fora do quadro | ninguém (registro) | — | `track.channel.rejected`; nenhum caso | [DEC-017](../decisoes.md) |
| RX-12 | modelo, `find_cover` ou ponto levantam | gestor | "Tentar de novo", "Seguir sem a leitura (abono provisório)" | o fluxo segue; nada é publicado | `LLMUnavailableError` [FATO] |

## 9. Dados sintéticos e fixtures (frente D; tudo com seed 42 e a marca SINTÉTICO)

Caminhos, formatos e gabaritos: **seção 2.2 do contrato** (SAIDA-AC-15). Resumo:

- `data/demo/acompanhamento/cenario_folga.json`, **três lojas**: (1) a da falta principal **com folga** (pessoas de meio período, contrato
  de 24 h); (2) uma em que **a única cobertura gera hora extra** (RF-28, PEDIDO-EV-18); (3) uma **sem candidato** (RX-05). **Teste
  obrigatório (D1):** na loja 1, `find_cover` devolve ≥ 2 candidatos e o 1º sem hora extra; na 2, todos com hora extra; na 3, nenhum.
- `ponto_desvios.json`: falta da Carla qua 13/01 14h (para o roteiro, passo 5), atraso de 25 min, hora extra que cruza 80% e 100% de 6 h.
- `cenario.esperado.json`: gatilho, instante (`fires_at`, `not_before`), ordem dos candidatos, `overtime_needed`, `new_violations: 0`. Os
  instantes são **literais**, calculados pelo gerador por aritmética sobre a política, **sem chamar `detect`** (PEDIDO-EV-20; senão o eval é
  circular).
- `atestados/at-01` a `at-04` e **`at-08-injecao`** em PDF (T1b) e `at-05` a `at-07` em PNG (T2), com gabarito `*.esperado.json` (formato
  na seção 2.2 do contrato). PDF escrito à mão, como `synth/e2.py::_pdf_sem_tabela` [FATO]; o escaneado (`at-04`) e as fotos com Pillow
  (dependência de dev [FATO]); gerados uma vez e versionados, como os do E2. O `at-08` traz texto que manda o leitor declarar válido e
  com mais dias, num atestado cujas datas não cobrem o dia (E4-01 e E4-05).

## 10. Contrato com os evals (resumo; o detalhe está no arquivo do contrato)

- **Aceitos sem mudança:** PEDIDO-EV-01, 02, 04, 07, 08, 10, 11, 12, 14, 15 (ofertas sequenciais, confirmado), 16, 17 (at-08 com
  injeção), 18 (loja em que só cobre com hora extra), 20 (instantes literais no gabarito), 21 (at-09 com o CID em vários lugares e
  formas, para o E3-24 ter entrada própria).
- **Ajustados:** EV-03 (o limite é 10 min, da política, não 15); EV-05 (gabarito sem médico; PDF escaneado vira `ilegivel` sem modelo no
  T1); EV-06 (achado da B: o padrão de CID casa célula `B12`, então `scrub` por nome de campo em tudo e por padrão só em `track.*`;
  `find_leaks` devolve a superfície); EV-09 (mensagem ao colega não é gated, pelo produto; o gated é mudar escala e confirmar abono); EV-13
  (só no T2; se o T2 cair, os E4-03, 04 e 07 saem como **não executado**); EV-19 (`TOOL_NAME` mora em `llm/prompts/`, não em `agents/`).
- **Cortados:** nenhum.
- **Achados da B aceitos:** todo tempo até a cobertura é **simulado** e é rotulado assim na tela e no pitch; `cost_usd` ausente vira "não
  medido"; no T1 o acerto do atestado sai de poucos PDFs (at-01 a 04, 08 e 09), e o relatório diz n.
- **Contagem dos 30 (da B, seção 3.2 do contrato):** sem modelo já passa de 20 hoje (26); com modelo, o T1 dá 6 e o T2, 12; **a meta de 10
  com modelo só fecha com o T2 e com a rodada à mão com chave**. Esse é o argumento mais forte para tentar o T2 se o M2 sair cedo.
- **Ganchos (2.1 do contrato):** os 7 marcados, com tarefa.
- O código da suíte E3/E4 é do plano dos evals; aqui ficam os ganchos, as fixtures e o teste de vazamento.

## 11. Tarefas por frente

Donos exclusivos de pastas [PROPOSTA]: **A** `domain/`, `clock/`, `rules/tracking_policy.py`, `rules/atestado.py`,
`agents/tracker/sweep.py`, `data/regras/politica/` (só o acréscimo de RX-06 e RX-09), `tests/architecture/`. **B** `agents/tracker/` (menos
`sweep.py`), `store/`, `channel/`, `llm/`, `ingest/atestado.py`. **C** `api/`, `web/`. **D** `synth/`, `data/demo/acompanhamento/`, `audit/protected.py` (+ a linha no
`SqlTraceSink`), `tests/privacy/`, `tests/e2e/test_c7.py`. `tests/fakes.py`: só a A0.

### Frente A · contratos, relógio, política e varredor (Opus 5.5 na A0 e na A3)

| Id | Nível | Tarefa | Depende | Horas | Verificação |
|---|---|---|---|---|---|
| A0 | T1a | `domain/tracking.py` e portas da seção 5; `FakeClock`; `FakeChannel`, `FakePunchSource`, `InMemoryTrackRepository`, `ListExceptionQueue` em `tests/fakes.py`; teste de fronteira de `datetime.now` | — | 0,25–0,5 | `uv run pytest -q tests/domain tests/architecture` |
| A1 | T1a | `clock/demo.py` (`DemoClock` + tabela `demo_clock`; `advance`, `reset`) | A0 | 0,25 | teste: avança, persiste, reinicia em 13/01/2027 13:55 |
| A2 | T1a | `rules/tracking_policy.py` (`TrackPolicy` da política) + RX-06 e RX-09 em `excecoes_demo` | A0 | 0,25 | teste lê 10, 15, 20, 3, 6, 80 da política [FATO, valores atuais] |
| A2b | T1b | `rules/atestado.py::judge(fields, expected_day, employee_name) -> AtestadoReading` (puro: `data_nao_bate`, `sem_data`, `sem_crm`, `nome_nao_bate`, `dias_fora_da_faixa`) | A0 | 0,25 | gabaritos at-01 a at-04 e at-08 com campos fixos |
| A3 | T1b | `agents/tracker/sweep.py::detect` (`no_punch`, `no_answer`, `offer_expired`), puro, idempotente pelo `handled` | A0, A2 | 0,5–0,75 | "dispara com 10, não com 9"; duas chamadas no mesmo instante = um gatilho |
| A4 | T2 | `overtime_near_limit` e `overtime_limit` no `detect` | A3 | 0,25–0,5 | 80% e 100% de 6 h nos desvios plantados |
| A5 | T2 | `LLMMessage.content` com partes de imagem (seção 5.3) | A0 | 0,25–0,5 | contrato v0 editado junto; E2 sem mudança |

### Frente B · fluxo do agente, store e leitura (Opus 5.5 na B2; Sonnet 5.5 no resto)

| Id | Nível | Tarefa | Depende | Horas | Verificação |
|---|---|---|---|---|---|
| B1 | T1a | `store/tracking.py`: `track_case`, `channel_message`, `SqlTrackRepository`, `SimulatedPhone` (em `channel/simulated.py`), adaptador `ExceptionQueue` sobre `ExceptionStore` | A0 | 0,5 | ida e volta de `Case` e `ChannelMessage`; `reset` |
| B2 | T1a | `agents/tracker/flow.py` (`Tracker`: `report`, `respond_offer`, `on_decision`, `case`, `inbox`, `inbound`), `replan.py` (despachador → `find_cover`, RF-28), `tools.py` (`aplicar_cobertura` com portão, `publicar`), mensagens por template, eventos `track.*` | A0, A2 | 0,75–1,25 | testes com falsos: aceite → `COBERTURA`; recusa → próximo; sem candidato → RX-05; sem aprovação → `track.tool.refused` e escala inalterada; 4 mensagens registradas |
| B3 | T1b | `ingest/atestado.py::read_atestado` (`pdf_text` → `strip_cid` → `call_structured` → `judge`), `llm/prompts/atestado.py` (`TOOL_NAME = "read_atestado"`), `Tracker.attach` pela porta `AtestadoReader`, RX-08, RX-12 | A0, A2b, D3 (só `strip_cid`) | 0,5–0,75 | gabaritos at-01 a at-04 e at-08 com `FakeLLMClient`; at-04 não chama o modelo; o texto enviado ao falso não tem o CID; modelo fora → RX-12 e a oferta sai mesmo assim |
| B4 | T1b | `Tracker.run_sweep` (aplica `no_punch` → pergunta; `no_answer` → RX-09; `offer_expired` → próximo/RX-06; ponto fora → RX-12) e decisão do RX-09 "tratar como falta" | A3, B2 | 0,5 | roteiro do contrato (SAIDA-AC-06) com `FakeClock` |
| B5 | T2 | foto pela visão; `Tracker.message` (conversa curta, schema fechado); `confirmar_abono` | A5, B3 | 0,75–1,25 | at-05 a at-07 com falso; injeção no texto não gera efeito |

### Frente C · API e SPA (Sonnet 5.5)

| Id | Nível | Tarefa | Depende | Horas | Verificação |
|---|---|---|---|---|---|
| C1 | T1a | `api/tracker_wiring.py` (`build_tracker`, `read_atestado_bytes`), rotas da SAIDA-AC-10, `as` só com `DEMO_MODE`, `/falta` delega ao `Tracker`, `build_desk` com `DemoClock`, `decide` delega itens `track`, "Reiniciar" | B1, B2 (assinaturas da A0 bastam para começar) | 0,5–0,75 | linhas novas na matriz de `tests/api/test_access.py`; `TestClient` do roteiro passos 1 a 4 |
| C2 | T1a | SPA: barra do relógio (+15 min, +1 dia, +1 semana, Reiniciar, "tempo simulado"); celular: seletor "Você é:", caixa, ofertas Aceitar/Recusar; cartão `COBERTURA` na fila | A0 (tipos) | 0,75–1 | `npm --prefix web run typecheck && npm --prefix web run build`; testes de `web/lib` |
| C3 | T1b | anexo de PDF no celular (multipart), estado "atestado lido / abono provisório", pergunta do agente e resposta "vou chegar / não vou" | C2, B3 | 0,25–0,5 | idem + roteiro passo 2 e 5 à mão |
| C4 | T2 | foto no celular; texto livre ao Pat; botão "confirmar abono" | B5 | 0,5 | idem |

### Frente D · dados, privacidade e E2E (Sonnet 5.5; Opus 5.5 na D3)

| Id | Nível | Tarefa | Depende | Horas | Verificação |
|---|---|---|---|---|---|
| D1 | T1a | `synth/acompanhamento.py` + `synth/ponto.py` (`SimulatedPunchSource`): `cenario_folga.json` (três lojas), `ponto_desvios.json`, `cenario.esperado.json` (instantes literais), README SINTÉTICO | A0 | 0,5–0,75 | teste das três lojas (seção 9); o gerador não importa `sweep`; arquivos = seed 42 |
| D2 | T1b | atestados at-01 a at-04, at-08 (injeção) e at-09 (CID espalhado: cabeçalho, corpo, rodapé; `J11` e `J11.1`) em PDF + gabaritos (`planted_cid: list[str]`) | — | 0,5 | releitura independente do texto e do gabarito |
| D3 | T1b | `audit/protected.py` (`strip_cid` primeiro, para destravar a B3; depois `scrub` por `kind` no `SqlTraceSink` e `find_leaks` por superfície); `tests/privacy/test_rn06_tracker.py` (superfícies da seção 6); teste de que o padrão não apaga `B12` de evento `llm.map_columns` | B3, C1 (só o teste) | 0,5 | `uv run pytest -q tests/privacy`: 0 ocorrências; E2 sem mudança |
| D4 | T1a/b | `tests/e2e/test_c7.py`: roteiro da seção 1 por `TestClient` com `FakeLLMClient` (passos 1 a 4 no M1; 2 e 5 no M2) | C1 | 0,25–0,5 | verde |
| D5 | T2 | fotos at-05 a at-07 + gabaritos | — | 0,25 | idem D2 |

## 12. Dependências, caminho crítico, integração e marcos

```
A0 ─┬─► A1 ─────────────────────────────┐
    ├─► A2 ─┬─► B2 ─┬─► C1 ─► D4(M1) ───┼─► M1 (T1a)
    ├─► B1 ─┘       │                   │
    ├─► C2 ─────────┘                   │
    ├─► D1 ─────────────────────────────┘
    ├─► A3 ─► B4 ──────┐
    ├─► A2b ─┐         │
    D2 ──────┼─► B3 ───┼─► C3 ─► D3 ─► D4(M2) ─► M2 (T1b)
    D3a(strip_cid) ─┘
```

- **Caminho crítico [PROPOSTA]:** A0 (0,25–0,5) → B2 (0,75–1,25) → C1 (0,5–0,75) → D4 + à mão (0,25–0,5) = **1,75 a 3 h** até o M1. O M2
  corre em paralelo (A3, B3, D2 começam logo depois da A0). [INFERÊNCIA] Pela medida da C5 (45 min) e da C6 (3h25), o M1 cabe em ~1h15 se a
  A0 sair em 20 min; o M2 é o que corre risco antes das 11h15.
- **Ordem de integração em `c7/integra`:** A0 (sozinha) → A1, A2, B1, D1, D2, C2 (qualquer ordem) → B2 → C1 → D4 → **M1** → A3, B3 → B4,
  C3 → D3 → D4 → **M2** → T2 só depois do M2.
- **Marcos (só o usuário faz o merge no `main`; um PR por marco, merge commit, sem squash):**
  - **M1 = T1a** (meta 10h45 [PROPOSTA]): falta pelo celular → oferta → aceite → validação → republica; relógio e Reiniciar; RX-05 e RX-06.
  - **M2 = T1b** (meta 11h15 [PROPOSTA]): atestado PDF, RX-08, RX-12, RN-06 testado, ponto simulado com RF-16 e RX-09, RF-28.
  - **M3 = T2** só se o M2 estiver no ar e conferido antes das 11h30; senão, não entra.
- Depois de cada merge: conferir `/health`, login de gestor e de colaborador e o roteiro da seção 1 **no link**.

## 13. Critério de pronto (comandos)

```
uv run pytest -q                                   # verde: fronteiras (inclui datetime.now proibido no tracker), contratos, fluxo, varredor
uv run ruff check .
uv run pytest -q tests/privacy                     # RN-06: 0 ocorrências por superfície
uv run pytest -q tests/e2e/test_c7.py              # roteiro da seção 1 com FakeLLMClient
uv run pytest -q tests/e2e/test_fatia.py           # a C5 continua passando
uv run python -m escalista.evals --suite e1        # sem mudança
uv run python -m escalista.evals --suite e3        # suíte do plano dos evals (sem modelo); nome final: o do plano B
uv run python -m escalista.synth acompanhamento --seed 42 --out data/demo && git diff --exit-code data/demo/acompanhamento
npm --prefix web run typecheck && npm --prefix web run build
```

**À mão, com a chave (usuário), local e depois no link:** `DEMO_MODE=1 SESSION_SECRET=<local> uv run uvicorn escalista.api.app:create_app
--factory --port 8000` → roteiro da seção 1, passos 1 a 6. Depois `uv run python -m escalista.evals --suite e3 --with-model` e anotar em
Métricas medidas o custo e a latência de `track.llm.read_atestado` (lidos do `trace_event`, nunca de log).

## 14. Riscos e cortes, em ordem

| # | Risco | Mitigação | Corte |
|---|---|---|---|
| 1 | Relógio: o M2 não fecha até 11h15 | T1a/T1b separados; regra de corte do orquestrador (seção 0) | entra só o M1; atestado vira "anexo recebido, abono provisório, leitura indisponível" (RX-12 honesto) |
| 2 | A escala com folga não dá candidato sem hora extra (piso do contrato, [DEC-055](../decisoes.md)) | teste da D1 antes de tudo; meio período de 24 h | aceitar o 1º candidato com hora extra e mostrar o aviso do RF-28 |
| 3 | Modelo `small` erra campos do atestado em português | `verdict` em código; divergência vira RX-08, nunca recusa | — |
| 4 | Vazamento de CID por caminho esquecido (log de exceção do pdfplumber, `repr` de modelo) | teste da D3 sobre as 5 superfícies | bloqueia o M2 |
| 5 | Conflito com a sessão que mexe na fila e no celular (`api/excecoes.py`, `web/app/colaborador`) | C é a única dona; rebase curto | — |
| 6 | "Reiniciar" apaga a escala que o jurado aprovou | só o gestor reinicia; texto de confirmação | — |
| 7 | Visão nunca testada na Featherless | fica no T2 (decisão do usuário) | **corte 1:** foto |

**Ordem de corte recomendada:** (1) foto (T2) e conversa livre; (2) RF-27 (T2); (3) RF-25 e solver de janela (T3); (4) RF-28 (já é
barato; só sai se a B2 atrasar); (5) RF-16 e RX-09 (o M2 sem o ponto). **Não cortar:** exceções (RX-05/06/08/12), rastro `track.*`, teste
de vazamento RN-06 e os ganchos dos evals.

## 15. Perguntas ao usuário

Respondidas em 2026-11-08 09:10 (uma rodada, AskUserQuestion; registradas na seção 5 do contrato):

1. Foto no T1 ou T2? **T2.**
2. Como entra a escala com folga? **Botão "Reiniciar demo".**
3. Padrões de RF-28, RF-27 e RF-25 da política fictícia? **Aceitos** (RF-28 no T1, RF-27 no T2, RF-25 no T3).
4. Replanejamento só com `find_cover` no v1? **Sim.**

**Ainda em aberto (padrão [PROPOSTA] adotado, sem travar):**

- Opções de RX-06 e RX-09 (fictícias, seção 8): confirmar ou trocar; o Pedro Veloso é o autor da política.
- O "Reiniciar demo" pode ser usado pelo colaborador? Padrão: não, só o gestor.
- Hora do reinício (qua 13/01/2027 13:55): conferir com o roteiro do pitch em [entrega.md](../entrega.md).

## 16. DECs propostas (não gravadas; o número final é o próximo livre em [decisoes.md](../decisoes.md), hoje **DEC-056**)

1. **C7 em níveis T1a (M1), T1b (M2), T2 e T3**, com corte por relógio às 10h50 e 11h15 e nada do T2 antes do M2.
2. **Foto do atestado no T2** (usuário, 09:10); o T1 lê só PDF digital; PDF sem texto vira `ilegivel` sem modelo.
3. **Escala com folga pelo botão "Reiniciar demo"** (usuário, 09:10): semana sintética rotulada, relógio em qua 13/01/2027 13:55.
4. **Pendências de negócio** (usuário, 09:10): RF-28 = aviso ao gestor quando a cobertura só fecha com hora extra; RF-27 = 80% avisa o
   gestor, 100% avisa os dois e abre cartão (banco de horas, pedir replanejamento, só registrar); RF-25 = critérios de
   `pol_reotimizacao_semanal`, no T3.
5. **Replanejamento só com `find_cover` no v1** (usuário, 09:10); `ReplanRequest` despachado in-process; solver de janela no T3.
6. **Acompanhamento sem LangGraph e sem checkpointer**: máquina de estados em código sobre `track_case`; o modelo só nos nós de linguagem.
   Contra: a arquitetura fala em grafo por agente.
7. **Seletor "Você é:" no celular simulado** (`as`, só com `DEMO_MODE=1`, validado contra o quadro) para o colega confirmar.
8. **Tolerância de atraso de 10 min** (política, `pol_atraso`) prevalece sobre os 15 min do texto do RF-16.
9. **RX-06 e RX-09 entram em `excecoes_demo`** como fictícios, rotulados "proposta do agente".
10. **`run_id = "track-<case_id>"`** para o acompanhamento; o custo dele não entra no custo da execução da otimização.

## 17. Registro de execução

Cada sessão escreve só na sua subseção: início, fim (`date`), hash, desvios e métricas medidas.

**Planejamento:** 09:01 a 09:18 (`date`). Contrato: seção 2 publicada às 09:06 (v1) e revista às ~09:16 (v1.1); seção 4 com as
respostas aos pedidos PEDIDO-EV-01 a 21; perguntas ao usuário registradas às 09:10; **congelamento do lado A às 09:18** (seção 6 do
contrato). A sessão B ainda não tinha congelado nessa hora.

**Como rodou (08/11, a partir de 09h22):** um orquestrador (Claude, Opus 5.5) fez a A0 sozinho e delegou cada tarefa a um subagente no
worktree da frente (`cc61-c7-{a,b,b2,c,d,d2}`; `b2` e `d2` foram worktrees extras para correr B1 × B2 e D1 × D3a em paralelo), conferiu
diff, donos, testes e ruff de cada entrega, fez o rebase e integrou em `c7/integra` com `merge --ff-only`, **sem push e sem tocar no
`main`**. Linha de base: 1319 testes em 2min05 (09:25). Hashes abaixo são os de `c7/integra`.

### Sessão A

- **A0** (orquestrador, 09:23 a 09:26): `6052e64` contratos (`domain/tracking.py`), portas, falsos, teste de fronteira do relógio.
- **A1, A2, A2b, A3** (09:31 a 09:37): relógio de demo, `load_track_policy` + RX-06 e RX-09 na política, `judge`, `detect`; integrados até `fc3dd2a`. **Desvios:** `judge(fields, *, expected_day)` sem `employee_name` (o nome chega em `patient_matches`); a tabela `demo_clock` é criada pelo próprio `DemoClock` se faltar; o `no_punch` vale também para turnos já encerrados.

### Sessão B

- **B1** (09:31 a 09:35): `06341c7` tabelas `track_case` e `channel_message`, `SqlTrackRepository`, `SimulatedPhone` (recusa gravar texto de entrada), `ExceptionStoreQueue`.
- **B2** (09:31 a 09:42): `a5b962d` `Tracker` (ofertas sequenciais, portão `aplicar_cobertura`, cartões, mensagens, `summarize`).
- **B3** (09:40 a 09:43): `17f017a` leitura do PDF (`pdf_text` → `strip_cid` → modelo `small` → `judge`). **Achado:** o pdfminer loga o conteúdo do PDF em DEBUG; os loggers `pdfminer`/`pdfplumber` ficam em WARNING.
- **B4** (09:45 a 09:51): `d7be9fc` `run_sweep`, `answer`, RF-28 também sem candidato ([DEC-068](../decisoes.md)).

### Sessão C

- **C2** (09:31 a 09:35): `f128caa` barra do relógio, celular simulado com seletor, ofertas e perguntas.
- **C1** (09:45 a 10:00): `3451489` `tracker_wiring`, rotas, `decide` delegando cartões do acompanhamento, semente do cenário na subida (sem `Approval`: é dado sintético pré-carregado), aviso em JSON e PDF em corpo bruto ([DEC-068](../decisoes.md)).

### Sessão D

- **D1, D2** (09:31 a 09:43): `a6ec80a`, `0816b44` cenário com folga (3 lojas, 17 pessoas, 0 violações), ponto simulado, atestados at-01 a 04, 08, 09 com gabarito. **Achado:** a `find_cover` nunca devolve hora extra numa escala válida; D1b (`224a549`) ajustou o gabarito do RF-28.
- **D3a** (09:31 a 09:36): `2068a69` `audit/protected.py` e `scrub` por `kind` no `SqlTraceSink`.
- **D4** (10:01 a 10:06): `8cdcf25` E2E do roteiro (passos 1 a 7) por HTTP. **Lacuna:** não havia rota para o rastro do caso (passo 6) → tarefa C3b.

### Integração (`c7/integra`) e marcos

- **10:01 a 10:04:** merge de `origin/main` (`e17996b`, logo novo da DEC-056) → `527d001`; 1 conflito em `decisoes.md` (número da DEC-056), DECs da C7 renumeradas para 057 a 066, DEC-068 nova.
- **M1 (10:10), gates em `c7/integra`:** `uv run pytest -q` 1664 passed (1min58; 1665 com a D4); ruff check e format 0; E2E fatia + C6 20 passed; E1 10/10; E2 16/16 sem modelo; `synth acompanhamento` sem diff; web typecheck, lint, test (60) e build 0; `docker build` 0 e `/health` ok na imagem (`demo_mode: true`). **Não verificado:** navegador, link público, modelo real.
- **10:09 · D3** (`f77b8d9`, com `9877f1c`): teste de vazamento RN-06, 40 superfícies por rodada (9 tabelas, bytes do arquivo SQLite, eventos `track.*`, log em DEBUG, stdout/stderr, 25 respostas HTTP, mensagens ao modelo), 0 achados; o teste falha se o `strip_cid` sair. **Correção na origem:** o motivo de reenvio do `call_structured` repetia ao modelo um nome de campo extra com cara de CID; agora mostra "(campo fora do schema)".
- **10:12 · C3b** (`6516264`): `GET /api/runs/track-<case_id>/trace` (só gestor) e "Ver rastro do caso" na fila, com "tempo simulado", tokens e "não medido" quando não há custo.
- **10:12 a 10:15 · merge de `origin/main` `a2f6536`** (só docs: link novo e pitch) → `4815b31`. **M2, gates:** `uv run pytest -q` 1674 passed (1min37, antes do merge só de docs); ruff 0/0; `tests/privacy` + `tests/e2e` 25 passed; E1 10/10; E2 16/16; `synth` sem diff; web typecheck, lint, test (61), build 0; `docker build` 0, `/health` ok, login de gestor 200 e `/api/demo/clock` = 13:55 simulado na imagem. **Não verificado:** navegador, link público, modelo real (custo e latência de `track.llm.read_atestado` não medidos).
- **10:17 a 10:31 · T2 (M3):** D5 + C4 (`1c210f6`, fotos at-05 a at-07 com gabarito, anexo aceita PNG/JPEG pelos bytes, "PDF ou foto" no celular); RF-27 (`8b6798a`, gatilhos a 80% e acima de 6 h por semana, cartão `HORA_EXTRA` que nunca muda a escala, + `5bc8f5d` na fila); foto pelo modelo de visão (`ca0be0b`: `LLMMessage.content` com partes de texto e imagem, size `vision` com `featherless_model_vision = Qwen/Qwen3.5-9B` **nunca testado com imagem**, o rastro do cliente guarda só tipo e tamanho da imagem, teste de vazamento da foto). Merge de `origin/main` `4e1e3e8` (DEC-057, logo de volta à grade): DECs da C7 renumeradas de novo, para **DEC-058 a DEC-068**. **Gates M3 (10:27 a 10:29):** pytest 1732 passed (1min33); ruff 0/0; `tests/privacy` + `tests/e2e` 28 passed; E1 10/10; E2 16/16; `synth` sem diff; web typecheck, lint, test (63), build 0; `docker build` 0, `/health` ok, login de colaborador 200 e `/api/colaborador/pessoas` com o quadro sintético na imagem. **Não verificado:** navegador, link, modelo real (visão nunca chamada).
- **Cortado / não feito:** do T2, a conversa livre (`Tracker.message`, SAIDA-AC-17) e o `confirmar_abono`; T3 inteiro; `/sync-docs` não rodou (audita o checkout principal, defasado e intocável nesta execução).

**Nota (2026-11-08 11:33):** a conversa livre (SAIDA-AC-17) cortada acima foi feita depois, na [C7b](camada-07b-chat.md) (`c7/chat`, DEC-069 a DEC-074), junto com o assistente do gestor; o canal virou chat dentro do app, sem WhatsApp.
