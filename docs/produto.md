# Produto: Escalista (IDEA-002)

Última atualização: 2026-11-07 13:24 · Etapa: definição de negócio ([DEC-012](decisoes.md)) · **Rascunho para o time definir; sem aprovação**

Este documento define **o que o produto é e como ele se comporta**: features, capacidade de cada uma, entradas e saídas, fluxos,
o que fica com o agente e o que fica com o humano, como os dois se falam e como o produto se generaliza. Não define stack nem
arquitetura (etapa técnica). Os IDs `RF-`, `RX-`, `RH-` e `RN-` vêm de [requisitos.md](requisitos.md). A ficha da ideia, com
mercado, concorrência e hipóteses, está em [IDEA-002](ideacao/ideias/IDEA-002-escalista.md).

**Como ler os rótulos:** **[DERIVADO]** vem dos requisitos aprovados ou do PDF (base, não verdade: [DEC-010](decisoes.md)).
**[PROPOSTA]** é sugestão do agente e precisa da sua decisão. `[PREENCHER]` é medida ou escolha que não existe ainda.

## 1. O produto em uma frase e os papéis

O Escalista é um digital worker que **monta, mantém e audita a escala de trabalho de uma operação com turnos, conforme a lei, a
convenção coletiva e a política de cada empresa**, e cobre faltas conversando com a equipe. O gerente aprova e decide as exceções.

| Papel | Quem é | O que faz no produto | Onde interage |
|---|---|---|---|
| **Agente** | O Escalista | Planeja, replaneja, valida, conversa, explica, abre exceção e registra tudo | Todos os pontos |
| **Gerente** | Responsável pela unidade | Aprova e publica a escala; decide exceções de escala e de cobertura | Grade e fila no app |
| **DP** | Departamento Pessoal | Aprova o cartão de regras e mudanças de regra; decide regras pendentes e atestados inconsistentes | Cartão de regras e fila no app |
| **Colaborador** | Pessoa escalada | Avisa falta, envia atestado, aceita ou recusa turno, pede troca, consulta horário | Celular simulado (WhatsApp, se a ponte existir) |
| **Jurado** | Quem testa o link | Faz um dos papéis acima por uma persona | App público |

## 2. Features

Cada feature tem: capacidade (o que faz, o que **não** faz, limites), entradas, saídas, fluxo, divisão agente e humano, como
interagem e o que ela deixa parametrizável (generalização). A prioridade vem de [requisitos.md](requisitos.md).

### F1 · Política e cartão de regras

- **Objetivo:** transformar lei, convenção e política da empresa em regras executáveis, cada uma com a origem. [DERIVADO] RF-01, RF-22.
- **Capacidade.** *Faz:* cadastrar regras por tipo (jornada semanal, repouso semanal, interjornada, domingo, noturno e aprendiz,
  hora extra, banco de horas, prazos de resposta); dar a cada regra origem, vigência e status (conferida, interpretação ou
  pendente); versionar e mostrar a diferença entre versões; levar a regra ao DP para aprovar uma vez. *Não faz:* dar parecer
  jurídico; resolver sozinho regra pendente ou ambígua; mudar regra sem o DP. *Limite:* ler a convenção em PDF é cortável (RF-20,
  C3); o caminho garantido é entrar a política em YAML.
- **Entradas:** texto da lei (EC 141, CLT), convenção coletiva (fictícia), política da empresa (parâmetros), vigência.
- **Saídas:** cartão de regras versionado, lista de regras pendentes, diferença entre versões.
- **Fluxo:**
  1. O DP carrega as fontes e a política.
  2. O agente propõe cada regra com a cláusula de origem (ou lê o YAML).
  3. O agente confere conflito entre camadas e ambiguidade (ver seção 5).
  4. O que for conflito ou ambíguo vira regra **pendente** e vai ao DP como exceção (RX-01, RX-11).
  5. O DP aprova; o cartão fica ativo com a vigência.
- **Agente:** propõe a regra e a origem, detecta conflito. **Humano (DP):** aprova, decide pendência, muda regra (RH-02).
- **Interação:** tela do cartão com pendências; cada pendência é um cartão de exceção (seção 4.2).

### F2 · Planejamento da escala

- **Objetivo:** gerar a escala semanal que cobre a demanda ao menor custo, sem violar regra. [DERIVADO] RF-02 a RF-06.
- **Capacidade.** *Faz:* cobrir a demanda por faixa de 30 min; respeitar disponibilidade, férias, afastamentos e banco de horas;
  minimizar hora extra; replanejar só o trecho afetado por um evento; explicar cada escolha em linguagem natural; apontar
  lacunas e contratações que faltam quando a demanda não cabe na regra. *Não faz:* calcular com o modelo (o solver calcula);
  inventar regra; publicar. *Limites:* tamanho-base de ≈3 lojas e ≈60 colaboradores (PDF§6); tempo para gerar e para replanejar:
  [PREENCHER, a medir].
- **Entradas:** quadro de pessoal (com telefone), demanda por faixa, disponibilidade, banco de horas, férias e afastamentos,
  cartão de regras ativo.
- **Saídas:** escala em **rascunho** (grade), custo, cobertura, lacunas, justificativas, trace.
- **Fluxo:** validar os dados (sem custo de modelo) → solver com as regras do cartão → verificador independente confere 0
  violações → diagnóstico (F3) → rascunho para aprovação (F4).
- **Agente:** tudo até o rascunho. **Humano:** nada até a aprovação.
- **Generaliza por:** as regras vêm do cartão (F1); o solver não tem regra fixa.

### F3 · Simulação e diagnóstico

- **Objetivo:** mostrar o que muda com outra vigência ou política, em custo, cobertura e contratações. [DERIVADO] RF-06, RF-07, RN-11.
- **Capacidade.** *Faz:* comparar vigências (44h, 42h, 40h) e políticas alternativas; calcular o impacto em custo, hora extra,
  cobertura e contratações necessárias; recomendar contratação **com o cálculo**. *Não faz:* decidir contratar ou adotar.
  A tela mostra "vigência simulada a partir de ≈16/12/2026 (conta nossa)".
- **Entradas:** dados atuais, vigência ou política alternativa. **Saídas:** comparativo lado a lado, recomendação, justificativa.
- **Fluxo:** o usuário escolhe a alternativa → o agente monta o cartão alternativo → o solver replaneja → o agente calcula a
  diferença → apresenta; se a demanda não couber, abre RX-02 com o cálculo.
- **Agente:** calcula e recomenda. **Humano (gerente e DP):** decide adotar ou contratar.

### F4 · Aprovação e publicação

- **Objetivo:** nada vai à equipe sem um humano aprovar. [DERIVADO] RF-08, RH-01.
- **Capacidade.** *Faz:* mostrar o rascunho com resumo (custo, cobertura, 0 violações, exceções abertas); aprovar, rejeitar ou
  editar; **revalidar** regras e custo a cada edição do gerente [PROPOSTA]; publicar a cada colaborador; guardar a versão.
  *Não faz:* publicar sem aprovação.
- **Entradas:** rascunho. **Saídas:** escala publicada e versionada, mensagens aos colaboradores, registro.
- **Fluxo:** gerente revisa → aprova (ou edita e o agente revalida) → agente publica no canal → registra a versão.
- **Agente:** prepara, valida e envia depois do ok. **Humano (gerente):** aprova.

### F5 · Cobertura de falta e atestado

- **Objetivo:** da mensagem de falta ao turno coberto, sem o gerente digitar. [DERIVADO] RF-09, RN-06.
- **Capacidade.** *Faz:* receber o aviso e o atestado (texto; imagem é cortável, C2); extrair data, dias e CRM; registrar o
  recebimento; identificar o turno afetado; listar quem pode cobrir pelas regras; oferecer o turno começando por quem não gera
  hora extra; registrar o aceite; atualizar a escala; resumir ao gerente; se não houver solução dentro da regra, abrir exceção
  com opções e custo. *Não faz:* recusar atestado, guardar ou mostrar diagnóstico (CID), decidir hora extra ou remanejamento,
  advertir ou descontar.
- **Entradas:** mensagem do colaborador, atestado, escala vigente, cartão de regras, banco de horas.
- **Saídas:** turno coberto ou exceção, resumo ao gerente, abono **provisório** para o DP, mensagens, trace.
- **Fluxo:**
  1. O colaborador avisa a falta; o agente confirma o recebimento.
  2. O agente lê o atestado; dado inconsistente ou ilegível vai ao DP (RX-08), sem recusar.
  3. O agente replaneja o trecho e lista os elegíveis.
  4. Oferece o turno em ordem; um colega aceita.
  5. Atualiza a escala e notifica os dois.
  6. O gerente recebe só o resumo: "atestado de 1 dia, válido; turno das 14h coberto por Carlos, sem hora extra".
  7. Ninguém aceita no prazo, ou só resta hora extra: exceção RX-06 ou RX-05 para o gerente.
- **Agente:** do passo 1 ao 6, quando não gera hora extra e cumpre todas as regras (RH-05, provisória). **Humano:** o gerente
  decide qualquer caso com hora extra; o DP decide atestado inconsistente e confirma o abono.
- **Decisão pendente:** o abono nasce **provisório** até o DP confirmar, porque afeta pagamento (REG 6). [PROPOSTA]

### F6 · Troca de turno

- **Objetivo:** validar a troca pedida pelo colaborador antes de qualquer aceite. [DERIVADO] RF-10, RX-07. Prioridade S.
- **Capacidade.** *Faz:* validar a troca nas regras e no custo; pedir o aceite do colega; levar ao gerente; aplicar e notificar.
  *Não faz:* aplicar troca que viola regra.
- **Entradas:** pedido do colaborador, escala, regras. **Saídas:** troca aplicada ou recusada com o motivo.
- **Fluxo:** pedido → agente valida → se viola, responde o motivo (e abre RX-07 só se o colaborador insistir) → pede aceite ao
  colega → gerente aprova → agente aplica e notifica.
- **Agente:** valida e conduz. **Humano:** colega aceita; gerente aprova.

### F7 · Fila de exceções

- **Objetivo:** todo caso fora da regra chega a um humano com o contexto pronto. [DERIVADO] RX-01 a RX-12, RH-01.
- **Capacidade.** *Faz:* reunir as exceções de todas as features; montar o cartão de exceção (seção 4.2); mostrar a quem cabe
  decidir; registrar a decisão e **executá-la** (replanejar, notificar); escalar quando o prazo vence. *Não faz:* decidir.
  Os tipos e o destino de cada exceção saem da política da empresa (RF-22).
- **Entradas:** eventos das outras features. **Saídas:** decisão registrada, execução, trace.
- **Fluxo:** o agente detecta → abre o cartão → notifica o decisor → o humano escolhe uma opção ou ajusta → o agente executa e
  registra → sem resposta até o prazo da política, escala (seção 4.4).
- **Agente:** detecta, monta as opções com custo, recomenda, executa. **Humano:** decide.

### F8 · Canal do colaborador

- **Objetivo:** o trabalhador fala com o agente pelo canal que já usa. [DERIVADO] RF-11, RF-12, RF-16 a RF-18, RF-21.
- **Capacidade.** *Faz:* receber falta, atestado, aceite, recusa e pedido de troca; enviar escala publicada, oferta de turno e
  confirmações; reconhecer o colaborador pelo telefone; no modo demo, dar uma persona a quem não está no quadro. *Cortável:*
  atraso proativo, lembretes e consulta de horário (C1); ponte real do WhatsApp (C4). *Não faz:* tratar assunto fora da escala
  (holerite, férias e benefícios ficam no roadmap).
- **Entradas:** mensagens (texto; foto em C2). **Saídas:** mensagens curtas em português, eventos para as outras features.
- **Fluxo:** mensagem → o agente identifica o colaborador e o assunto → aciona a feature certa (F5, F6 ou consulta) → responde.
  Número fora do quadro vira RX-10 ou persona de demo.
- **Agente:** conversa e aciona. **Humano:** o colaborador age; o gerente só recebe resumo.
- **Garantia:** o canal fica atrás de um adaptador, e o **simulador de celular** é o caminho garantido do link público.

### F9 · Fechamento com o ponto

- **Objetivo:** conferir o realizado contra a escala antes da folha. [DERIVADO] RF-13. Prioridade S.
- **Capacidade.** *Faz:* comparar o ponto realizado (simulado) com a escala e as regras; pedir justificativa de atraso aberto;
  sinalizar risco antes da folha. *Não faz:* advertir, descontar ou punir (decisão humana, RH-04).
- **Entradas:** ponto realizado, escala, regras. **Saídas:** relatório de desvios e riscos, justificativas registradas.
- **Fluxo:** o agente compara → lista desvios → pede justificativa ao colaborador → entrega o relatório ao gerente e ao DP.
- **Agente:** compara e registra. **Humano:** decide o que fazer com cada desvio.

### F10 · Painel de impacto e auditoria

- **Objetivo:** provar o ganho e mostrar por que o agente fez o que fez. [DERIVADO] RF-14, RN-01 a RN-03.
- **Capacidade.** *Faz:* mostrar hora extra evitada, violações evitadas, tempo da falta até a cobertura, % de faltas cobertas
  sem o gerente e custo por execução, **todos medidos no trace**; premissas rotuladas; para qualquer evento, abrir regra de
  origem, mensagem, decisão e custo em até 2 cliques (RN-02). *Não faz:* mostrar número estimado sem o rótulo de premissa.
- **Entradas:** trace e eventos. **Saídas:** painel e tela de auditoria.

## 3. Quem decide o quê

| Ato | Agente sozinho | Agente propõe, humano decide | Só humano |
|---|---|---|---|
| Validar dados e gerar rascunho de escala | ✔ | | |
| **Publicar** a escala | | ✔ gerente | |
| Propor regra do cartão e a origem | ✔ | | |
| **Aprovar ou mudar** regra, resolver regra pendente | | ✔ DP | |
| Oferecer turno a colegas elegíveis, sem hora extra e dentro das regras | ✔ (RH-05, provisória) | | |
| Cobertura que gera hora extra, remanejamento entre lojas, turno descoberto | | ✔ gerente | |
| Registrar recebimento do atestado e abono provisório | ✔ | confirmar o abono: DP | |
| Atestado ilegível ou inconsistente | sinaliza | ✔ DP | |
| Aprovar troca de turno | valida | ✔ gerente (e aceite do colega) | |
| Recomendar contratação, com o cálculo | ✔ | decidir contratar: gerente e DP | |
| Aplicar a regra mais restritiva num conflito de cláusula | provisório | ✔ DP | |
| Advertência, desconto, recusa de atestado, salário, demissão, promoção | | | ✔ |

## 4. Como o agente interage com o humano

### 4.1 Canais por papel [PROPOSTA]

- **Gerente e DP:** no app. Uma **grade** de escala e uma **fila** (exceções e aprovações). Eles não conversam em texto livre com o
  agente; o produto "não é um chat" (PDF§6): o agente trabalha e a pessoa decide na fila.
- **Colaborador:** pelo celular simulado (WhatsApp, se a ponte existir). Mensagens curtas, em português, **uma pergunta por vez**.
- **Resumo ao gerente:** uma linha por evento resolvido, no formato do exemplo da F5. Só o que exige decisão vira cartão.

### 4.2 O cartão de exceção [PROPOSTA]

Todo caso que chega a um humano traz: **tipo; quem decide; prazo; motivo; evidência** (trecho da regra ou a mensagem original);
**opções com custo** (ex.: hora extra, remanejamento, turno descoberto); **a recomendação do agente e por quê**; **o que acontece
se ninguém responder**; histórico. O humano escolhe uma opção, ajusta ou recusa, e o agente executa e registra.

### 4.3 Regras de comunicação [PROPOSTA]

- O agente se identifica como assistente automático e confirma o recebimento do que o colaborador manda.
- Nunca mostra nem repete diagnóstico; ao gerente diz só "válido, N dias".
- Nunca promete o que depende de um humano ("o gerente vai confirmar").
- Quando falha uma ferramenta, o modelo ou o solver, o agente diz o que aconteceu e abre exceção (RX-12), sem inventar resposta.

### 4.4 Tempo e escalada [PROPOSTA]

O **prazo de resposta** de cada tipo de exceção e de cada oferta de turno é parâmetro da política da empresa (valor:
[PREENCHER]). Vencido o prazo, o agente escala para o próximo decisor; se ninguém decidir, o turno fica marcado como
**descoberto**, sem ação irreversível.

## 5. Como o produto se generaliza

O produto **não codifica uma política**: a política da empresa e a lei entram como dados ([DEC-010](decisoes.md), RF-22).

**5.1 Camadas de regra [PROPOSTA; o conflito 2 de [requisitos.md](requisitos.md) segue em aberto]:**

1. **Lei** (EC 141, CLT): o piso.
2. **Convenção coletiva** da categoria: pode ampliar a proteção ou compensar o que a lei permite.
3. **Política da empresa**: escolhe o que as duas camadas anteriores deixam em aberto (por exemplo repouso mínimo por semana ou
   média no mês, regime de domingo, ordem de oferta de turno, prazos).
4. **Parâmetros da unidade**: demanda, quadro, horários de funcionamento.

Regra de precedência proposta: o produto **nunca gera escala que viole uma camada superior**; a política só restringe. Quando
duas camadas conflitam, o agente aplica a mais restritiva **provisoriamente** e abre a exceção para o DP (RX-01).

**5.2 O que é parâmetro e o que é produto:**

| É parâmetro (muda por empresa) | É produto (igual para todas) |
|---|---|
| Jornada semanal e vigência (44h, 42h, 40h) | O solver e o verificador independente |
| Repouso mínimo por semana ou média no mês; regime de domingo | O cartão de regras, sua versão e seu status |
| Interjornada, trabalho noturno, regras de aprendiz | O cartão de exceção e a fila |
| Hora extra: adicional, limite e ordem de preferência | A regra "nada publicado sem aprovação" |
| Banco de horas, prazos de resposta, destino de cada exceção | Rastro, custo por execução e painel |
| Demanda por faixa, quadro, lojas e horários | O canal (adaptador) e as regras de comunicação |

**5.3 Como uma empresa nova entra [PROPOSTA]:** (1) o DP escolhe a vigência e carrega a convenção; (2) o agente propõe o cartão com
as origens; (3) o DP aprova e resolve as pendências; (4) entram quadro e demanda; (5) gera-se a primeira escala e o gerente
aprova. Nenhum passo exige mudança de código.

**5.4 Verticais e regimes:** varejo, alimentação e farmácia são o alvo (ficha). Regimes diferenciados e 12x36 ficam como regra
**pendente** até haver lei ou convenção (EC 141, art. 7º §3º). *Limite:* o produto não decide interpretação jurídica nem cuida
de folha de pagamento.

**5.5 Na demo:** a rede fictícia (≈3 lojas, ≈60 colaboradores) é **um exemplo de política**. A demo troca a política ou a vigência ao
vivo para provar que o motor não é fixo.

## 6. Entradas e saídas consolidadas

| Entrada | De onde vem | Usada em |
|---|---|---|
| Lei, convenção e política (cartão de regras) | DP | F1, F2, F5, F6 |
| Quadro de pessoal, com telefone | Cliente (sintético na demo) | F2, F5, F8 |
| Demanda por faixa de 30 min | Cliente (sintético) | F2, F3 |
| Disponibilidade, banco de horas, férias, afastamentos | Cliente (sintético) | F2, F5 |
| Mensagens e atestados | Colaborador | F5, F6, F8 |
| Ponto realizado (simulado) | Sistema de ponto simulado | F9 |
| Decisões e aprovações | Gerente e DP | F4, F7 |

| Saída | Para quem | Gerada em |
|---|---|---|
| Escala rascunho e publicada (versionada) | Gerente, colaboradores | F2, F4 |
| Diagnóstico e comparativo de vigência | Gerente, DP | F3 |
| Cartão de exceção | Gerente ou DP | F7 |
| Resumo de evento resolvido | Gerente | F5, F6 |
| Mensagens curtas | Colaborador | F8 |
| Relatório de fechamento | Gerente, DP | F9 |
| Painel de impacto, auditoria e trace | Gerente, DP, jurado | F10 |

## 7. Capacidade e limites do produto

- **Tamanho-base da demo:** ≈3 lojas e ≈60 colaboradores, demanda por faixa de 30 min (PDF§6). Tamanho máximo do produto: [PREENCHER, a medir].
- **Tempo do solver** (gerar e replanejar): [PREENCHER, a medir]. **Custo por execução:** o medido no trace. **Evals:** [PREENCHER] (Q5, etapa técnica).
- **O que o produto não faz (v1):** folha, férias, benefícios, holerite, qualquer decisão sobre pessoas, parecer jurídico.

## 8. Decisões para o time

| # | Decisão | Proposta do agente |
|---|---|---|
| P1 | Camadas e precedência (5.1): a política da empresa só pode restringir a lei e a convenção, nunca afrouxá-las? | Sim; conflito entre camadas: aplica a mais restritiva e abre exceção ao DP |
| P2 | O abono de atestado é **provisório até o DP confirmar** (F5)? | Sim, por ser efeito em pagamento |
| P3 | O gerente e o DP **não conversam em texto livre** com o agente; só grade e fila (4.1)? | Sim |
| P4 | O prazo de resposta de exceção e de oferta é parâmetro da política (4.4); vencido, o turno fica **descoberto**, sem ação irreversível? | Sim |
| P5 | O gerente pode editar a escala em rascunho e o agente **revalida** a cada edição (F4)? | Sim |
| P6 | Quais features entram no v1 da demo? | F1 a F5, F7, F8 (simulador) e F10 obrigatórias; F6 e F9 desejáveis; C1 a C4 cortáveis, como em [requisitos.md](requisitos.md) |
| P7 | A regra de autonomia (RH-05) confirma: sem hora extra e dentro das regras, o agente cobre sozinho? | Sim (hoje é premissa provisória) |
