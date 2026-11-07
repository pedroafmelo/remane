# Arquitetura do Escalista (IDEA-002)

Última atualização: 2026-11-07 16:11 (seção 19: versões conferidas; seção 10: quando fazer o spike, [DEC-028](decisoes.md)) · Etapa: definição técnica, Gate 3 ([DEC-005](decisoes.md)) · **Aprovado pelo usuário ([DEC-022](decisoes.md)), sem comentário item a item: os itens `[PROPOSTA]` seguem rotulados.**
Decisões desta etapa: [DEC-018](decisoes.md) a [DEC-021](decisoes.md). Produto e requisitos não foram reabertos: ver
[produto.md](produto.md) e [requisitos.md](requisitos.md).

**Como ler os rótulos:** o que não tem rótulo é **decisão do usuário** (com a DEC). **[PROPOSTA]** é suposição do agente, ainda não
confirmada. `[PREENCHER]` é o que falta, com o motivo. Fatos de terceiros: **[FATO]** (fonte e data), **[INFERÊNCIA]**,
**[NÃO ENCONTRADO]**. Pesquisas feitas em 07/11/2026 por subagentes somente leitura; **nenhuma API foi chamada por nós ainda**.

## 1. Visão em uma página

Um contêiner (SPA React servida pelo FastAPI), três agentes separados e um núcleo determinístico. **O modelo nunca calcula escala,
hora nem custo**: lê arquivos, conversa e explica. O solver gera, o verificador independente confere, o humano aprova.

```
Navegador (gerente, DP, colaboradora, jurado)
    │ HTTP
┌───▼──────────────────────── contêiner único (hospedagem: [PREENCHER]) ─────────────────────────┐
│ SPA React (estática)  ──►  API FastAPI: login, sessão, controle de acesso por papel             │
│                                │                                                                │
│        ┌───────────────────────┼─────────────────────────────┬───────────────────────────────┐ │
│        ▼                       ▼                             ▼                               │ │
│  Agente de otimização   Agente de acompanhamento     Assistente do gestor (somente leitura)  │ │
│  (LangGraph, FT-02)     (LangGraph, FT-03)           (LangGraph, FT-08, ferramentas get_*)   │ │
│        ▲  └── ReplanRequest (evento) ◄─────┘                        │                        │ │
│        │                                                            │ (conexão SQLite ro)    │ │
│  ┌─────┴─────────────────────────────┐   ┌────────────────────┐    │                        │ │
│  │ Solver CP-SAT  +  Verificador     │   │ Ingestão: XLSX,    │    │                        │ │
│  │ independente (0 violações)        │   │ CSV, PDF, atestado │    │                        │ │
│  │ regras = Cartão de regras (dados) │   └────────────────────┘    │                        │ │
│  └───────────────────────────────────┘                             │                        │ │
│  Canal (adaptador) ── celular simulado   Relógio de demo + ponto simulado + varredor         │ │
│  Cliente LLM (OpenAI SDK) ───────────────► Featherless   (2 modelos, por variável de ambiente)│ │
│  Rastro: tabela `trace_event` ──► tela de auditoria      └─(opcional)─► Langfuse local        │ │
│  Armazenamento: SQLAlchemy sobre SQLite (volume)                                              │ │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Stack

| Camada | Escolha | Origem |
|---|---|---|
| Backend | Python 3.12, FastAPI, pydantic v2, SQLAlchemy 2 sobre SQLite (portável a Postgres) | `pyproject.toml`; SQLAlchemy `[PROPOSTA]`, para a hospedagem não travar o banco |
| Front-end | React + Vite (SPA), build servido pelo FastAPI no mesmo contêiner | [DEC-018](decisoes.md) |
| Agentes | LangGraph, um grafo por agente (três agentes) | [DEC-018](decisoes.md) |
| Solver | OR-Tools CP-SAT | [DEC-005](decisoes.md) e fonte da seção 5 |
| Inferência | Featherless, via SDK `openai` com `base_url` da Featherless | [DEC-005](decisoes.md), [DEC-020](decisoes.md) |
| Rastro | Tabela do app (prova do jurado) + Langfuse local | [DEC-021](decisoes.md) |
| Testes | pytest; TDD estrito no núcleo, fumaça no resto | [DEC-018](decisoes.md) |

## 2.1 Estilo e regra de dependência `[PROPOSTA]`

**Estilo:** monolito modular, com hexagonal leve (portas e adaptadores) e **núcleo funcional, casca imperativa**. Um contêiner, pastas por
responsabilidade, sem microsserviços e sem a cerimônia da Clean Architecture completa. O pedido do usuário foi só acrescentar esta seção
(15h17); o estilo é recomendação do agente e entra no "aprovado" do Gate 3. Não vira DEC enquanto não for confirmado.

**Núcleo (puro: entram dados, saem dados; sem rede, sem banco, sem relógio, sem modelo):** `domain/`, `rules/`, `solver/`, `verifier/`.
É aqui que o TDD estrito da [DEC-018](decisoes.md) se paga.

**Bordas (efeitos):** `api/`, `ingest/` (a leitura do arquivo é borda; a validação dos dados extraídos é pura e fica em `rules/`), `llm/`,
`channel/`, `clock/`, `audit/`, `synth/`, `evals/`. **`agents/`** orquestra: usa o núcleo e as portas, nunca uma borda concreta.

**Portas** (interfaces `Protocol` em `domain/ports.py`): `Channel` (`send_message`, `on_message`), `Clock`, `LLMClient`, `TraceSink` e
`Repository`. Cada borda implementa uma porta; os testes usam implementações falsas.

**Regras de dependência (a seta aponta para quem é importado):**

1. `api/` → `agents/` → núcleo e portas. As bordas implementam as portas e são ligadas na inicialização do app, não importadas pelo núcleo.
2. **O núcleo só importa `domain/`, a biblioteca padrão e pydantic.** O OR-Tools só pode ser importado dentro de `solver/`.
3. **`verifier/` não importa `solver/` nem OR-Tools** (independência exigida pelo RF-02: o verificador não pode errar junto com o solver).
4. **`solver/` e `verifier/` não importam `llm/`, `channel/`, `api/`, `agents/` nem `audit/`**: o modelo nunca calcula escala.
5. Nenhuma ferramenta de agente com efeito executa sem o registro de aprovação humana (seção 4), checado no código da ferramenta.

**Como garantir sem dependência nova:** um teste de importação com o módulo `ast` da biblioteca padrão que lê os arquivos do núcleo e
**falha** se achar um import proibido (entra no núcleo do TDD). O `import-linter` faria o mesmo, mas é dependência a mais, com licença a
conferir: não adotado.

**Contra:** exige disciplina nas fronteiras num prazo apertado; sem o teste de importação, a regra se perde na primeira pressa.

## 3. Decisões e o que ficou em aberto

| # | Tema | Situação |
|---|---|---|
| D1 | Três agentes, LangGraph nos três | **Decidido** ([DEC-018](decisoes.md)) |
| D2 | Front-end React + Vite | **Decidido** ([DEC-018](decisoes.md)) |
| D3 | TDD no núcleo, fumaça no resto | **Decidido** ([DEC-018](decisoes.md)); exceção à regra global, registrada |
| D4 | Ponte do WhatsApp: spike de 1 h com critério de abandono | **Decidido** ([DEC-019](decisoes.md)) |
| D5 | Relógio simulado controlável e varredor | **Decidido** ([DEC-019](decisoes.md)) |
| D6 | Evals: 30 cenários, 20 sem modelo e 10 com modelo | **Decidido** ([DEC-019](decisoes.md)) |
| D7 | Dois modelos fixos: pequeno `Qwen/Qwen3.5-9B`, grande `google/gemma-4-31B-it`, com teste de fumaça | **Decidido** ([DEC-020](decisoes.md)) |
| D8 | Determinismo: persistir a escala e reverificar | **Decidido** ([DEC-020](decisoes.md)); **muda o aceite do RF-05** |
| D9 | Foto do atestado pelo modelo de visão da Featherless | **Decidido** ([DEC-020](decisoes.md)) |
| D10 | Rastro: tabela no app + Langfuse local | **Decidido** ([DEC-021](decisoes.md)) |
| D11 | **Hospedagem do link público** | **`[PREENCHER]`: o usuário disse "vamos ver isso depois"** ([DEC-021](decisoes.md)); ver seção 12 |
| D12 | Login, sessão e papéis (seção 11) | `[PROPOSTA]` |
| D13 | Segurança mínima contra injeção de prompt (seção 14) | `[PROPOSTA]` |
| D14 | Estado dos fluxos nas tabelas do domínio, sem checkpointer do LangGraph (seção 4) | `[PROPOSTA]` |
| D15 | Catálogo de turnos discretos no solver (seção 5) | `[PROPOSTA]` |
| D16 | Regras como primitivas parametrizadas pelo cartão (seção 5, tensão com o RF-22) | `[PROPOSTA]`, **avisar** |
| D17 | Estilo e regra de dependência: núcleo puro, portas e bordas (seção 2.1) | `[PROPOSTA]` |

## 4. Os três agentes (DEC-017, DEC-018)

Cada agente é um módulo com seu grafo LangGraph, suas ferramentas e sua **lista de ferramentas permitidas**. Fluxos que são regra
(falta → cobertura → validação) são nós determinísticos do grafo; o modelo só entra nos nós de linguagem.

| Agente | Feature | O que o modelo faz | O que é código | Ferramentas (efeito) |
|---|---|---|---|---|
| **Otimização** | FT-02, FT-07 (e FT-01 na leitura da convenção) | Extrai a escala e a convenção em schema fechado; escreve justificativas; interpreta pedido de edição em texto | Valida dados, monta e roda o solver, verifica, calcula antes e depois, versiona | `ler_escala` (leitura), `propor_regras` (rascunho), `otimizar` (rascunho), `verificar` (leitura), `comparar_vigencia` (leitura), `editar_rascunho` (rascunho, revalida), `publicar` (**só com aprovação humana gravada**) |
| **Acompanhamento** | FT-03 | Conduz a conversa curta com o colaborador; extrai campos da comprovação | Detecta gatilhos, acha elegíveis, oferece turno, registra, monta o cartão de exceção | `registrar_evento` (grava), `ler_comprovacao` (leitura), `listar_elegiveis` (leitura), `ofertar_turno` (mensagem a terceiro, registrada), `abrir_excecao` (grava), `pedir_replanejamento` (evento) |
| **Assistente do gestor** | FT-08 | Responde sobre a escala, as exceções, a hora extra e as leis | Nada além de ler | **Só `get_*`**: `get_escala`, `get_excecoes`, `get_hora_extra`, `get_regra`, `get_trace`. **Nenhuma ferramenta de escrita; conexão ao banco somente leitura** (a defesa é estrutural, não do prompt) |

**Como se falam.** O acompanhamento não chama o agente de otimização por função: grava um evento tipado `ReplanRequest`
(`caso_id`, `janela`, `pessoa_afastada`, `motivo`, `origem_trace_id`) na tabela `event`; um despachador in-process o entrega ao grafo
de otimização, que devolve um rascunho de replanejamento ao caso. Assim o rastro mostra quem pediu o quê.

**Estado dos fluxos `[PROPOSTA]`.** O estado vive nas tabelas do domínio (`caso`, `cartao_excecao`, `escala_versao`, `event`), e o
grafo é reexecutado a partir delas quando o humano responde. Sem checkpointer do LangGraph no v1: evita dependência extra e deixa o
rastro e o estado no mesmo lugar. Contra: se o time quiser `interrupt` nativo, muda.

**Autonomia.** Toda ferramenta com efeito sobre terceiros ou publicação exige um registro de aprovação humana (`aprovacao`) lido
**pelo código** da ferramenta, não pelo modelo. Sem o registro, a ferramenta recusa (RH-01 a RH-03, REG 6).

## 5. Solver e verificador

**Regras vêm do cartão de regras (RF-01, RF-22), nunca de constantes.** `[PROPOSTA]` Cada regra do cartão é uma **primitiva
parametrizada** (tipo + parâmetros + origem + vigência + status). O solver tem um registro de tipos de primitiva em código, e o
verificador tem uma implementação **separada** do mesmo tipo (código distinto, Python puro, sem OR-Tools).

| Tipo de primitiva | Parâmetros (do cartão) | Origem do requisito |
|---|---|---|
| `jornada_semanal_max` | horas, vigência (44h, 42h, 40h) | RF-01, RF-02 |
| `repouso_semanal` | mínimo por semana **ou** média no mês | RF-02, RF-22 |
| `interjornada_min` | horas (11) | RF-02 |
| `folga_dominical` | frequência | RF-02 |
| `restricao_perfil` | perfil (aprendiz) × tipo de turno (noturno) | RF-02, RX-04 |
| `hora_extra` | adicional, limite, ordem de preferência | RF-05, RF-22 |
| `indisponibilidade` | férias, afastamentos, disponibilidade | RF-03 |

**Dados de regra no repositório ([PR #1](https://github.com/pedroafmelo/converge-challenge-61/pull/1), `data/regras/`) `[PROPOSTA]`.**
Três camadas em YAML: `lei/` (`ec141.yaml`, `clt.yaml`, texto público lido por Claude e **ainda sem leitura de alguém do time**; todas as
regras `interpretacao` ou `pendente`), `convencao/` e `politica/` (fictícias da demo, **vazias**). O carregador fica em `rules/`: lê as
camadas, valida o schema (`id`, `fonte`, `status`, vigência `de`/`ate`, `acao`) e funde pela regra "a política só restringe". Os YAMLs
trazem mais regras do que as 7 primitivas da tabela acima. Para o v1, `[PROPOSTA]`, o solver e o verificador implementam um subconjunto
(jornada semanal e diária, repouso semanal, interjornada, domingo, restrição de menor e aprendiz à noite, adicional de hora extra); as
demais regras aparecem como dado com fonte e status, ou viram exceção a um humano (`acao: escalar` ou `verificar_convencao`). Quem
escrever o solver confirma o formato dos YAMLs antes de a regra nova entrar. **`jornada_diaria_max` e a ampliação por convenção são
parâmetros** ([DEC-024](decisoes.md)): o produto não fixa a resposta da Q13. A regra do domingo quinzenal para empregadas
([DEC-023](decisoes.md), art. 386) exige o campo de sexo no quadro e o inclui na pendência do RN-13.

**Tensão com o RF-22 (avisar).** O aceite do RF-22 é "trocar a política por outra muda a escala **sem alterar o código**". Isso se
cumpre para valores, ativação e combinação das primitivas. **Um tipo de regra novo exige código** (nova primitiva no solver e no
verificador). `[PROPOSTA]` interpretar o RF-22 assim e declarar o limite. Se você quer regras novas sem código, é outro produto
(DSL de regras), fora do v1.

**Modelagem `[PROPOSTA]`.** [FATO, exemplo oficial `shift_scheduling_sat.py`, 07/11/2026] O CP-SAT modela escala com um turno discreto
por pessoa e dia (booleanas `work[pessoa, dia, turno]`, com "folga" como turno). Adotamos um **catálogo de 10 a 20 tipos de turno por
dia** (início, duração, intervalo), derivado dos horários de funcionamento (RF-36), em vez de variáveis por faixa de 30 min.
Cobertura por faixa de 30 min: soma linear dos turnos que a cobrem ≥ demanda. Interjornada: cláusulas que proíbem pares de turnos
com intervalo menor que o mínimo. Hora extra: variável `max(0, horas − limite)` penalizada no objetivo. **Limite:** escalas
enviadas com horários fora do catálogo são mapeadas ao turno mais próximo e o mapeamento aparece no resumo de leitura (RF-23); o que
não mapear vira exceção RX-13.

**Reprodutibilidade ([DEC-020](decisoes.md), muda o aceite do RF-05).** [FATO, lista or-tools-discuss, out/2023] A busca paralela
do CP-SAT não é determinística; só `num_workers=1` é, e entre macOS arm64 e Linux x86_64 nem isso é garantido. Procedimento:
(1) seed fixa e nomes e ordem de variáveis estáveis; (2) no primeiro benchmark, medir 1 thread contra várias; (3) **a escala resolvida é
persistida** com entradas, parâmetros, seed e hash; (4) o verificador a reconfere; (5) **a tela mostra sempre a escala persistida**.
Novo critério do RF-05: **escala gravada e reverificada com 0 violações**, e não "mesma entrada, mesma escala".

**Replanejar um trecho `[PROPOSTA]`.** [INFERÊNCIA a partir da doc do CP-SAT] Fixar com restrições tudo fora da janela, marcar a pessoa
faltante como afastada nos dias da falta e penalizar mudanças em relação à escala base (com `add_hint` da escala anterior). Não usar
`assumptions` (exigem `num_workers=1`, [FATO] guia de troubleshooting do OR-Tools).

**Antes e depois (RF-14, FT-02).** O custo da escala enviada e o da otimizada vêm da **mesma função de custo em código**, sobre as
mesmas regras: a economia é medida, não estimada.

**Tempo de geração e de replanejamento: `[PREENCHER, a medir]`.** [NÃO ENCONTRADO] benchmark para 60 pessoas × 7 dias. Medir hoje, no
primeiro dia de construção, e registrar em [estado](estado-do-projeto.md) (Métricas medidas) antes de decidir 1 thread ou várias.

**Verificador.** Entrada: escala + cartão. Saída: lista de violações com regra, pessoa, dia e cláusula de origem. A publicação
exige `violacoes == 0` **calculado pelo verificador**, nunca pelo solver. Edição do gerente (grade ou texto) passa pelo mesmo
verificador; violação de regra dura **bloqueia** com a regra à mostra (P5, [DEC-015](decisoes.md)).

## 6. Leitura de arquivos (RF-23, RF-20, RF-19)

Pipeline comum: **arquivo → texto/grade em código → modelo extrai para schema fechado → validação determinística (RF-04) → resumo ao
humano para confirmar.** O texto do arquivo é dado, nunca instrução (seção 14).

| Entrada | Biblioteca | Observação |
|---|---|---|
| XLSX | `openpyxl` 3.1.5 (MIT) + `defusedxml` | [FATO, doc do openpyxl] não protege contra XML bomb: usar `defusedxml`. `data_only=True`, nunca avaliar fórmula, rejeitar `.xlsm` e `.xls`. Células mescladas: propagar o valor da célula superior esquerda `[INFERÊNCIA, não verificado em fonte; testar com os layouts sintéticos]` |
| CSV | `csv` da stdlib | |
| PDF digital (escala, convenção, atestado) | `pdfplumber` 0.11.10 (MIT) | [FATO, README] funciona melhor em PDF gerado por máquina, com `extract_tables`. Evitar PyMuPDF (AGPL-3.0). PDF escaneado não é lido (`[PROPOSTA]` já no produto) |
| Foto do atestado | Modelo de visão da Featherless (`Qwen/Qwen3.5-9B`) | [DEC-020](decisoes.md). Sem Tesseract e sem dependência nova |

**Limites de segurança (mínimos `[PROPOSTA]`):** tamanho máximo do arquivo (5 a 10 MB), limite de páginas, linhas e colunas, tipo
validado por conteúdo (magic bytes), timeout de extração, limite de tamanho descompactado, `Image.MAX_IMAGE_PIXELS` no Pillow.

**Convenção em PDF (RF-20).** O modelo grande propõe cada regra com a **cláusula de origem citada literalmente**; o código confere que
o trecho citado **existe** no texto extraído (substring) antes de aceitar a regra. Se não existir, a regra é descartada e vira
exceção ao DP. Se o corte da leitura da convenção ocorrer (ordem de corte 4), o cartão vem de YAML.

**Atestado (RN-06, DEC-020).** Texto de PDF: o código redige padrões de CID por expressão regular **antes** de qualquer modelo; o
modelo pequeno devolve só os campos. Foto: a imagem vai **uma vez** ao modelo de visão, **em memória**, e a resposta é um schema sem
texto livre: `legivel: bool`, `valido: bool`, `dias: int`, `data_inicio: date`, `crm_presente: bool`. **A imagem não é gravada, não é
logada e não é enviada ao trace** (a chamada de visão não usa a instrumentação automática do Langfuse; seção 9). **Risco declarado:
a imagem, com o CID dentro, trafega pela Featherless (terceiro).** Com dado sintético não há problema; o argumento de LGPD "o CID não
sai do servidor" **não vale** neste desenho e não deve ir ao pitch. [NÃO ENCONTRADO] teste de OCR em português ou de legibilidade com
foto ruidosa: **a medir** nos evals de atestado.

## 7. Inferência (RN-07, DEC-020)

| Papel | Modelo | Unidades de concorrência | Preço por 1M tokens (entrada/saída) | Uso |
|---|---|---|---|---|
| Pequeno | `Qwen/Qwen3.5-9B` | 1 | US$ 0,17 / US$ 0,25 | Agente do colaborador, assistente do gestor, justificativas, visão do atestado |
| Grande | `google/gemma-4-31B-it` | 2 | US$ 0,12 / US$ 0,36 | Ler escala e convenção em regras |

[FATO] unidades e preços das fichas de modelo em featherless.ai/models, 07/11/2026; o modelo `Qwen/Qwen3.5-9B` tem tag de visão e de
ferramentas. **Nenhum foi testado por nós, nem em português nem em chamada de ferramentas.**

- **Nomes em variáveis de ambiente** (`FEATHERLESS_MODEL_SMALL`, `FEATHERLESS_MODEL_LARGE`, mais um reserva por papel).
- **Teste de fumaça antes de adotar** (`scripts` de 1 comando): chamada real em português a cada modelo, tool calling, JSON e visão;
  registra `usage.cost`, latência e se o modelo está "warm". Sem passar, troca-se pelo reserva.
- **Saída estruturada `[PROPOSTA]`:** [NÃO ENCONTRADO] suporte documentado a `json_schema`; a doc só cita tool calling nativo (Kimi-K2 e
  Qwen3; as fichas marcam outros) e `response_format={"type":"json_object"}` como alternativa. Tratamos a saída estruturada como uma
  **ferramenta cujo schema é o JSON desejado**, validamos com pydantic e reenviamos **até 2 vezes** em caso de erro; teste real
  de `json_object` e `json_schema` fica no teste de fumaça.
- **Raciocínio desligado** onde der (`chat_template_kwargs`: `enable_thinking`), por custo e latência [FATO, featherless.ai/docs/chat-template-kwargs].
- **Concorrência:** [FATO] cada requisição reserva as unidades do modelo; passar do teto devolve 429. Um semáforo global no cliente
  LLM, com o teto em variável de ambiente. O teto do plano "Feather Per-Request" do evento: **[NÃO ENCONTRADO]**; conferir no painel.
- **Erros:** [FATO] modelo "cold" devolve 400; 503 ("no valid executor") pede nova tentativa, até 3 vezes. Falha vira RX-12 (exceção
  com contexto), nunca derruba o fluxo (RN-05).
- **Custo:** a resposta traz `usage.cost` em USD [FATO, doc de preços, editada em 06/11/2026]; esse é o custo **medido** gravado no
  rastro. **Guarda de orçamento `[PROPOSTA]`:** teto diário em variável de ambiente, para os US$ 25 por pessoa não acabarem nos evals.
- **Crédito:** segundo o usuário, 3 das 4 pessoas resgataram os US$ 25 e criaram chaves (**sem teste de fumaça ainda**: validade e
  saldo não verificados). O código vence em 08/11; falta a 4ª pessoa (pergunta 8 do estado). **Ação humana, fora do código.**
- **Pool de chaves com failover ([DEC-025](decisoes.md)).** O usuário decidiu usar as chaves das 4 pessoas como fallback; o desenho a
  seguir é `[PROPOSTA]`. [FATO, guia, seção 11] cada pessoa resgata na própria conta e "um time de 4 tem US$ 100 no total".
  - **Configuração:** `FEATHERLESS_API_KEY_1` a `FEATHERLESS_API_KEY_4` no `.env` (ou nos segredos da hospedagem, nunca na imagem); o
    cliente lê todas as `FEATHERLESS_API_KEY_*`; a ordem é a prioridade.
  - **Failover em ordem, não rodízio:** usa a chave 1 até falhar e passa para a seguinte. Rodízio gastaria as quatro ao mesmo tempo.
  - **Trocam de chave:** 401 (chave inválida), 429 (limite de concorrência, que é por conta [FATO, doc da Featherless]) e erro de
    saldo. [NÃO ENCONTRADO] qual status a Featherless devolve com saldo zero: tratar erro de autenticação ou cobrança como "chave
    esgotada" e desativá-la por um tempo `[PREENCHER: valor]`. **Não trocam:** modelo frio (400) e 503, que são do modelo; repete a chamada ou usa o modelo reserva.
  - **"Unlock Model" é por conta** [FATO, guia, seção 11]: cada pessoa libera o modelo restrito (provável no `gemma-4-31B-it`) na própria
    conta; sem isso o failover esconde o problema.
  - **Rastro:** só o índice da chave ("chave 2") e o `usage.cost` medido vão ao `trace_event` e ao Langfuse; **o valor da chave nunca é
    gravado nem logado**. O teto de gasto (`FEATHERLESS_DAILY_BUDGET_USD`) vale **por chave**.
  - **Menor privilégio:** as 4 chaves juntas só na hospedagem e em quem roda os evals; cada pessoa usa a própria chave nas outras
    máquinas. Reservar saldo para o app público no Demo Day.
  - **Formato:** o guia exemplifica a chave como `fw-...`; as recebidas começam com `rc_`. Não afirmo que seja erro: o teste de fumaça confirma.

## 8. Contratos (resumo; a forma exata nasce no TDD do núcleo)

| Contrato | Campos principais | Produzido por | Consumido por |
|---|---|---|---|
| `ScheduleExtraction` | pessoas, turnos, dias, origem (arquivo, aba/página, célula), confiança | Ingestão + modelo | Validador, resumo ao gerente |
| `Rule` e `RuleCard` | tipo, parâmetros, vigência, status (conferida, interpretação, pendente), cláusula de origem | Leitura da convenção, DP | Solver, verificador |
| `SolveRequest` / `SolveResult` | cartão, quadro, demanda, seed, janela fixa; escala, custo, horas extras, cobertura, hash | Agente de otimização | Verificador, painel |
| `ViolationReport` | lista de (regra, pessoa, dia, origem); `total` | Verificador | Publicação, tela, evals |
| `ReplanRequest` | caso, janela, pessoa afastada, motivo, trace de origem | Acompanhamento | Otimização |
| `ExceptionCard` | tipo, decisor, prazo, motivo, evidência, opções com custo, recomendação, o que ocorre sem resposta | Qualquer agente | Fila (FT-04) |
| `ChannelMessage` | direção, número, pessoa, texto, anexos em memória, caso, decisão que a gerou | Adaptador | Acompanhamento, registro (RH-06) |
| `TraceEvent` | id, run, pai, tipo, regra de origem, mensagem de origem, modelo, tokens, `custo_usd` medido, latência, carga redigida | Todos | Tela de auditoria, Langfuse |

## 9. Rastro (RN-01 a RN-03, DEC-021)

- **Tabela `trace_event` do app** é a prova do jurado (RN-02): cada passo grava um evento; a tela de auditoria leva de qualquer evento à
  regra de origem, à mensagem, à decisão e ao custo em até 2 cliques (FT-05).
- **Langfuse local** (self-hosted, DEC-005): os mesmos eventos vão ao notebook quando ele estiver no ar; **o app público não depende
  dele** (envio em lote em segundo plano, com falha ignorada; `[INFERÊNCIA]` a testar). [FATO, scaling e docker-compose do Langfuse,
  07/11/2026] a doc recomenda **4 CPU e 16 GiB** para a VM e não cabe em nenhum plano grátis pesquisado, por isso não vai ao servidor. O link
  de trace público ("Make Public") aponta para a instância, então o jurado não o abriria [INFERÊNCIA].
- **Para a submissão:** vídeo e prints do Langfuse local e um export JSON de um trace, **declarando que roda localmente**.
- **Custo no Langfuse:** [FATO] sem definição de modelo o custo fica "no cost"; enviar `cost_details` em USD (têm prioridade) com o
  `usage.cost` da Featherless. Custos derivados de assinatura são premissa e vão rotulados.
- **Privacidade no trace (RN-06):** [FATO] `Langfuse(mask_otel_spans=fn)` mascara no export, e uma exceção na função **descarta o lote
  inteiro**; manter a função simples e testada. **Regra mais forte:** a chamada de visão e a de atestado **não passam pela integração
  automática** `langfuse.openai`; o dado sensível nunca entra como entrada ou saída de span. Teste automático: injetar CID e imagem
  sintéticos e falhar se aparecerem em banco, log ou trace (RN-06).

## 10. Canal (RF-11, RF-12, RF-21, RF-42, DEC-019)

Adaptador com dois métodos, `send_message(destino, texto, anexos)` e `on_message(origem, texto, anexos)`. Duas implementações:

- **`SimulatedPhone`** (caminho garantido): o celular simulado na SPA. O jurado escolhe uma pessoa do quadro, então o número já é
  válido. **Rotulado como simulado.**
- **`WhatsAppBridge`** (spike de 1 h): microserviço Node (`whatsapp-web.js`, não oficial, contra os termos do WhatsApp) com chip
  dedicado, **só no notebook, nunca no servidor público** (`[PROPOSTA]`: o plano de hospedagem não promete Chromium).

**Critério de abandono do spike `[PROPOSTA]`, a confirmar:** em 1 hora, a ponte recebe uma mensagem e responde a um número de teste de
forma estável; senão, abandona e fica só o simulador. **Quando começa o spike:** depois que o FT-03 rodar no celular simulado (C7), em 1 hora e só com chip ([DEC-028](decisoes.md)).

**Número fora do quadro (RF-42, RX-10).** O adaptador real consulta o quadro antes de entregar a mensagem ao agente; número fora é
**recusado e registrado**, sem resposta ao remetente `[PROPOSTA]` (não confirma a existência do bot). Testado no adaptador, também sem
a ponte real.

**Q9 (bloqueio do número). `[PROPOSTA]`, `[INFERÊNCIA]`, sem fonte pesquisada:** a ponte só responde a números do quadro; sem
broadcast, volume baixo, chip dedicado e sessão no notebook; se for banido, cai para o simulador no mesmo adaptador; produção usaria a
API oficial do WhatsApp Business. **Não pesquisei a política de bloqueio do WhatsApp**: `[PREENCHER]` se o time quiser a fonte.

## 11. Acesso: login, papéis e botões de demo (RF-29, RF-30, DEC-017)

`[PROPOSTA]` Tudo abaixo é do agente, ainda sem confirmação.

- **Contas semeadas** nos dados sintéticos (gerente, DP e colaboradores). Senhas com `hashlib.scrypt` da stdlib (sem dependência);
  sessão por cookie assinado (`SessionMiddleware` do Starlette, que usa `itsdangerous`: confirmar licença na declaração).
- **Papéis:** `gerente`, `dp`, `colaborador`, e `[PREENCHER]` o "gestor de RH" do usuário (é o gerente, o DP ou um papel novo: pergunta 15).
  Controle de acesso por **dependência da rota** (`require_role`), com **teste automático** por rota e papel; a SPA só esconde, não protege.
- **Botões de demo** da landing: `POST /auth/demo/{papel}` cria sessão de uma conta semeada, sem digitar nada (RE-07), ativo só com
  `DEMO_MODE=1`, limitado por taxa. Rotulam "dados sintéticos" e "tempo simulado". O colaborador usa o celular simulado.
- **Sem isolamento por loja no v1** (roadmap), como no [produto.md](produto.md), seção 7.

## 12. Hospedagem do link público (Q3, requisito RE-07 e RN-10)

**`[PREENCHER]`: o usuário disse "vamos ver isso depois" ([DEC-021](decisoes.md)). Não adotei padrão.** Restrições que a
escolha precisa cumprir: no ar de dom 08/11 13h00 a 17h30; sem dormir; pelo menos 1 GB de RAM `[INFERÊNCIA]`; um contêiner com
Dockerfile multi-stage (build do React e FastAPI); estado pequeno que sobreviva a reinício e a reset da demo.

Resumo dos fatos pesquisados (07/11/2026, subagente; preços e limites não encontrados estão marcados): **Fly.io** não tem plano grátis
para conta nova, e a máquina shared-cpu-1x de 1 GB custa US$ 6,70 por mês [FATO]; **Render Free** dorme após 15 min, tem 0,1 CPU e 512 MB
e não guarda disco [FATO]; **Hugging Face Spaces** com Docker exige plano pago [FATO]; **Koyeb Free** exige cartão e dorme após 1 h [FATO];
**Cloud Run** não guarda disco e exige faturamento [FATO]; **Oracle Always Free** tem risco de falta de capacidade [FATO] e leva horas para configurar;
**notebook com túnel Cloudflare** não tem SLA [FATO] e serve só de reserva. Recomendação do agente, **não adotada**: Fly.io com 1 máquina
sempre ligada e 1 volume (a primeira opção oferecida), com o melhor argumento contra: exige cartão e a conta nova pode esbarrar em verificação.

**Risco (explícito):** sem hospedagem decidida, o "link público estável" (RE-07, RN-10) é a peça com mais risco do v1 (filtro G2). Sugestão
`[PROPOSTA]`: decidir até o fim do primeiro núcleo ponta a ponta e **fazer um deploy de teste antes de dom 08h30**; o plano de horas
já prevê o gate de domingo 11h30.

**Plano B comum a qualquer hospedagem:** vídeo gravado da demo (PDF§10) e túnel do notebook como reserva.

## 13. Relógio de demo, ponto simulado e varredor (RF-13, RF-16, RF-25, RF-27, RF-28, DEC-019)

- **`Clock`** injetável; o "agora" da demo é gravado no banco e mostrado na tela, **rotulado como tempo simulado**. Botões: avançar
  15 min, 1 dia, 1 semana, e reiniciar (RF-15).
- **Ponto simulado:** API própria que grava batidas conforme o relógio, com **desvios plantados** (falta, atraso, hora extra). O agente
  chama essa API de verdade (RE-11).
- **Varredor determinístico:** a cada avanço, roda os gatilhos do FT-03: falta ou atraso (sem batida 15 min após o início, RF-16, o
  prazo é da política), hora extra estourando o limite (RF-27) e, com o critério a definir, o aviso de necessidade de hora extra (RF-28).
  A **verificação semanal** (RF-25) é o mesmo varredor com o botão "rodar a verificação semanal agora".
- **Não há agendador real em segundo plano** (decidido). Critério da verificação semanal: `[PREENCHER]` (o usuário disse "ainda a definir");
  o varredor deixa o ponto de extensão pronto.
- **`[PREENCHER]`:** o que dispara o aviso de necessidade de hora extra e quem o recebe (RF-28); o que o agente faz além de avisar na
  hora extra estourada (RF-27).

## 14. Segurança e privacidade (RN-06, RN-12, RN-13)

**RN-12, mínimos contra injeção de prompt `[PROPOSTA]`** (apoio: OWASP LLM01, [FATO] genai.owasp.org, 07/11/2026, que recomenda separar
conteúdo não confiável, restringir privilégios, exigir aprovação humana e validar saídas estruturadas por código determinístico):
1. Texto de arquivo e mensagem entra no prompt **como dado**, em bloco delimitado e rotulado, nunca como instrução.
2. Toda saída do modelo passa por schema fechado e por validação em código (tipos, faixas, datas); o modelo não escolhe ferramenta fora da
   lista permitida do agente.
3. **Privilégio mínimo estrutural:** o assistente do gestor só tem ferramentas de leitura e conexão somente leitura; ferramentas com efeito
   exigem registro de aprovação humana verificado no código.
4. A mensagem do colaborador não altera regra, escala nem papel: as ferramentas validam o papel de **quem** pediu, vindo da sessão ou do
   quadro, nunca do texto.
5. Evals de injeção (4 cenários com modelo, seção 15), com a taxa de sucesso do ataque medida e reportada.

**RN-06 (CID e imagem):** redação por código no texto, schema sem texto livre na visão, imagem só em memória, chamada fora da
instrumentação automática do trace e **teste que falha se CID ou imagem aparecer em banco, log ou trace**.

**RN-13 (LGPD, quais dados o sistema não guarda nem informa ao gestor): `[PREENCHER]`** — o usuário ainda não listou os dados além de
CID e imagem. A arquitetura reserva o ponto: uma lista única de campos protegidos aplicada por um filtro de saída (gestor, trace, log).
Sobre leis, o assistente cita só o cartão de regras e a emenda, com fonte e o aviso "não é parecer jurídico" (`[PROPOSTA]` da DEC-017).

**Dados e segredos:** dados 100% sintéticos, rotulados no app; chaves só em `.env` (RE-09); o código de resgate da Featherless nunca vai
ao repositório.

## 15. Dados sintéticos e evals (RN-04, DEC-019)

**Geradores** (pacote `synth`, seed fixa, 100% fictícios, marca "SINTÉTICO" nos arquivos): rede (≈3 lojas, ≈60 pessoas, telefones fictícios);
demanda por faixa com sazonalidade; **escala atual em XLSX, CSV e PDF de layouts diferentes**, um arquivo com defeito plantado e uma escala
com violações plantadas; **convenção em PDF escrita por nós** com 1 cláusula em conflito com a emenda e 1 ambígua; **atestados em PDF e em
foto** (Pillow, rotação, ruído, desfoque) com médico, CRM e CID fictícios; ponto com desvios plantados; **política fictícia da demo:
`[PREENCHER]`** (do negócio; destrava opções de exceção, prazos e os 3 tipos da demo).

**Evals ([DEC-019](decisoes.md)): 30 cenários = 20 sem modelo + 10 com modelo, um comando** (`uv run python -m escalista.evals`):
- **20 sem modelo** (parametrizados): escala com violação plantada, 44h e 42h, falta sem substituto, demanda acima da capacidade etc.
- **6 de atestado** (legível, ruidoso, inconsistente, com CID que não pode vazar) e **4 de injeção e de leitura de escala**, com modelo.
- **Métricas do RN-04:** violações não detectadas (meta 0, o verificador contra violações plantadas); cobertura; custo contra a
  planilha (função de custo de código); acerto na leitura do atestado. Mais: custo medido (`usage.cost`) e latência.
- O relatório diz **quantos cenários usam modelo** e o resultado de cada um; nada é arredondado a favor.

## 16. Estrutura de pastas proposta `[PROPOSTA]`

```
src/escalista/
  api/            rotas por papel, autenticação, SPA estática
  domain/         pessoa, escala, regra, caso, excecao, evento (pydantic)
  rules/          cartão de regras e primitivas (parâmetros)
  solver/         catálogo de turnos, modelo CP-SAT, custo
  verifier/       verificador independente (sem OR-Tools)
  ingest/         xlsx, csv, pdf, atestado; schemas de extração
  agents/         optimizer/, tracker/, manager_assistant/ (um grafo cada)
  llm/            cliente Featherless, semáforo, schemas por ferramenta, retry
  channel/        adaptador, simulated_phone, whatsapp_bridge (spike)
  clock/          relógio de demo, ponto simulado, varredor
  audit/          trace_event, exportador Langfuse, máscara
  synth/          geradores de dados sintéticos
  evals/          cenários e relatório
web/              SPA React + Vite
data/regras/      regras em YAML: lei/ (EC 141, CLT), convencao/ e politica/ (fictícias da demo); lidas por rules/
tests/            núcleo com TDD; fumaça no resto
```

## 17. Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| Hospedagem não decidida | Sem link estável: reprova RE-07 e RN-10 | Decidir cedo, deploy de teste, plano B de vídeo (seção 12) |
| Crédito da Featherless: 3 de 4 resgatados, sem teste | Chave inválida ou sem saldo só aparece no teste de fumaça; falta a 4ª pessoa e o código vence em 08/11 | Testar cada chave hoje; pool com failover ([DEC-025](decisoes.md)); a 4ª pessoa resgata hoje (ação humana) |
| Modelos de 2026 sem teste em português e em tool calling | Agente erra argumentos | Teste de fumaça, reserva por papel, validação pydantic |
| Solver lento para 60 × 7 | Demo ao vivo trava | Medir cedo; limite de tempo; catálogo de turnos pequeno; escala pré-resolvida persistida |
| Escopo do v1 grande (G2) | Fluxo ponta a ponta atrasa | Ordem de corte do produto, seção 2 |
| Imagem do atestado passa pela Featherless | Argumento de LGPD enfraquecido | Declarar; usar só dado sintético; não usar o argumento no pitch |
| Regras como primitivas exigem código para tipo novo | RF-22 lido ao pé da letra falha | Interpretar pelo aceite; declarar o limite |
| Ponte do WhatsApp não oficial | Banimento, queda de sessão | Spike limitado, só no notebook, simulador garantido |
| Dois lugares de rastro (tabela e Langfuse) | Mais código | Um único `TraceEvent` e dois exportadores |

## 18. Cortes se o tempo apertar

Vale a ordem do [produto.md](produto.md), seção 2: FT-06; desejáveis novos (FT-08, questionar a escala, consulta futura, aprovar remanejo,
demanda maior ou menor, tom configurável; **ordem entre eles: `[PREENCHER]`**); gatilhos de hora extra; foto do atestado; convenção em PDF (vira
YAML); reotimização semanal. **Cortes técnicos adicionais `[PROPOSTA]`:** Langfuse (fica só a tabela do app), spike do WhatsApp, compartilhar
trace público. **Não se corta:** exceções, rastro e evals.

## 19. Dependências a adicionar com `uv add` (depois do "aprovado" do Gate 3; **ainda não adicionadas**)

| Pacote | Versão conferida | Licença | Uso |
|---|---|---|---|
| ortools | 9.15.6755 | Apache-2.0 | Solver |
| openpyxl, defusedxml | 3.1.5, 0.7.1 | MIT, PSF | XLSX |
| pdfplumber | 0.11.10 | MIT | PDF digital |
| langgraph | 1.2.20 | MIT | Agentes |
| langfuse | 5.2.0 | MIT | Rastro local |
| openai | 3.46.0 | Apache-2.0 | Cliente da Featherless |
| sqlalchemy, itsdangerous | 2.1.8, 2.2.0 | MIT, BSD-3-Clause | Banco, sessão |
| pillow, reportlab (grupo dev) | 13.0.0, 5.1.0 | MIT-CMU, BSD | Dados sintéticos |

Fontes: PyPI JSON de cada pacote, 07/11/2026 (subagente). **Evitados:** PyMuPDF (AGPL-3.0), fpdf2 (LGPL-3.0). O `pandas` vem como
dependência transitiva do ortools; não importamos. `pypdfium2` (via pdfplumber): BSD-3-Clause e Apache-2.0, conferida em 07/11. Versões das linhas acima conferidas em 07/11; várias saíram há menos de 14 dias: detalhe e versões anteriores em [declaracao-ferramentas.md](declaracao-ferramentas.md) e a escolha no plano da C0 ([plano-implementacao.md](plano-implementacao.md)).

## 20. Pendências (resumo)

`[PREENCHER]`: hospedagem (D11); prioridade do FT-08 e ordem dos desejáveis; "gestor de RH"; o que é a "consulta" do RF-40; dados do RN-13;
critério da reotimização semanal; o que dispara o RF-28; política fictícia da demo; tempo do solver (a medir); tabela do time (a disponibilidade à noite foi respondida na [DEC-027](decisoes.md)). Versões e licenças: conferidas em 07/11.
