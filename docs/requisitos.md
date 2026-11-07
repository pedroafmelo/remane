# Requisitos do Escalista (IDEA-002)

Última atualização: 2026-11-07 15:14 (Gate 3: RF-05, RF-19, RN-04, Q3 e Q5 ajustados pelas DEC-019 a DEC-021) · Etapa: definição de requisitos ([DEC-005](decisoes.md)) · **Aprovado pelo usuário em 2026-11-07 13:13** ([DEC-011](decisoes.md)), com pendências na seção 9 · **Alterado em 14:13 pela [DEC-013](decisoes.md):** RF-03 ampliado, RF-16 muda de prioridade, RF-23 e RF-24 novos · **Alterado em 14:26 (entrevista, Fase 2, FT-02):** RF-23 ajustado, RF-25 e RF-26 novos, RX-13 novo · **Alterado em 14:33 (entrevista, Fase 2, FT-03 e FT-01):** RH-05 substituído; RF-09, RF-14, RF-16, RF-19 e RF-20 mudam; RF-27 e RF-28 novos; conflito 6 resolvido · **Alterado em 14:36 (Fase 2, FT-01, FT-04 e FT-05):** conflito 2 resolvido; métrica substituta do RF-14 definida · **Alterado em 14:52 (entradas do usuário depois do Gate 2):** seção 10, RF-29 a RF-42 e RN-12 a RN-14 novos, com 3 pontos que contradizem decisões anteriores e aguardam decisão

Este documento diz **o que o produto precisa fazer e provar**. Não cobre mercado, preço, concorrência nem pitch (etapa de
negócio), nem stack, arquitetura ou contratos (etapa técnica). Ideia: [IDEA-002](ideacao/ideias/IDEA-002-escalista.md).

## Como ler

- **Fonte:** `G§n` = [guia](guia-converge-challenge.md), seção n · `PDF§n` = proposta do Escalista
  ([PDF](proposta_escalista_converge_1.pdf)) · `REG` = regras do [CLAUDE.md](../CLAUDE.md) e de
  [regras-e-integridade.md](regras-e-integridade.md) · `EC141` = texto da emenda · `DEC-nnn` = [decisões](decisoes.md) ·
  **`INF` = inferência do agente, a confirmar**.
- **Prioridade:** **M** obrigatório (exigência do guia ou "núcleo que não pode ser cortado", PDF§7) · **S** desejável (o
  canal, "em seguida", PDF§7) · **C1 a C5** cortável, na ordem de corte do PDF (C1 corta primeiro): C1 atraso proativo,
  lembretes e consulta; C2 atestado por imagem; C3 convenção em PDF; C4 WhatsApp real; C5 polimento visual. As prioridades
  vêm do PDF e do guia; não são decisão nova. **A ordem de corte do PDF (C1 a C5) foi substituída na entrevista
  ([DEC-015](decisoes.md)):** (1) FT-06 eventos de demanda (RF-24); (2) gatilhos de hora extra (RF-27 e RF-28), ficando a falta ou o
  atraso (RF-16); (3) foto do atestado (RF-19), ficando o PDF; (4) leitura da convenção em PDF (RF-20), que vira YAML; (5)
  reotimização semanal (RF-25). **A [DEC-017](decisoes.md) acrescenta, logo depois do FT-06:** os desejáveis novos (FT-08
  `[PROPOSTA]`, RF-39, RF-40, RF-41, RN-14); a ordem entre eles: `[PREENCHER]`. A ponte real do WhatsApp (RF-21, C4) e o polimento (C5) seguem cortáveis, e lembretes e consulta
  (RF-17, RF-18) não foram revistos.
- Número entre colchetes, como `[PREENCHER]`, é medida ou escolha que ainda não existe.
- **Hierarquia das fontes ([DEC-010](decisoes.md)):** o PDF é uma base, não a verdade. A verdade do projeto é o que sair do fluxo completo de definição (requisitos, negócio e técnica), e ela ainda pode mudar durante o desenvolvimento. Onde este documento e o PDF divergem, vale este documento depois de aprovado.

## 1. Elegibilidade e submissão (RE)

| ID | Requisito | Fonte | Prio. | Critério de aceite |
|---|---|---|---|---|
| RE-01 | Código só a partir de 10h30 de 07/11, commits pequenos e frequentes, nada importado de outro histórico | G§5, REG 1 | M | Histórico do repositório começa limpo ([DEC-007](decisoes.md)) e tem commits regulares |
| RE-02 | IA obrigatória e central: o agente conduz o processo | G§5, G§3 | M | O fluxo ponta a ponta não roda sem o modelo (regras, explicação, conversa, atestado) |
| RE-03 | Declarar toda ferramenta, modelo e API de terceiros, inclusive o whatsapp-web.js (não oficial) | G§5, G§7 | M | [declaracao-ferramentas.md](declaracao-ferramentas.md) completo antes de submeter |
| RE-04 | Sinalizar o Desafio Tako na descrição | G§7 | M | A descrição cita o desafio |
| RE-05 | Dados 100% sintéticos e declarados; nunca apresentar sintético como real | G§3, REG 3 | M | Rótulo "dados sintéticos" visível no app, no vídeo e na descrição |
| RE-06 | Submissão completa: descrição, vídeo, link testável, material do pitch, lista de ferramentas | G§7 | M | Checklist de [entrega.md](entrega.md) fechado até 08/11 13h00 |
| RE-07 | Link público estável, com dados pré-carregados, que o jurado usa sem setup | G§4, G§7 | M | Um jurado abre o link, sem cadastro, e chega a um fluxo completo |
| RE-08 | Clean room: nada de empregador ou cliente de integrante | REG 2 | M | Revisão final dos arquivos; histórico já recriado |
| RE-09 | Segredos fora do repositório; código de resgate da Featherless nunca publicado | G§11, REG 5 | M | `.env` ignorado e nenhum segredo no histórico do git |
| RE-10 | Decisões sobre pessoas (demissão, promoção, salário, avaliação) ficam com humanos | G§3 | M | Ver RH-03 |
| RE-11 | Integrações simuladas valem se o agente de fato opera sobre elas | G§3 | M | Ponto e HRIS simulados são chamados pelo agente na demo |

## 2. Requisitos funcionais (RF)

| ID | Requisito | Fonte | Prio. | Critério de aceite |
|---|---|---|---|---|
| RF-01 | Cartão de regras versionado, com vigência (44h; 42h a partir de ≈16/12/2026; 40h a partir de ≈dez/2027) e cláusula de origem em cada regra; o DP aprova uma vez | PDF§2.1, EC141 | M | Cada regra mostra origem e status (conferida, interpretação ou pendente); trocar a vigência muda a escala |
| RF-02 | Regras do solver, cada uma parametrizável pela política (RF-22): jornada semanal, repouso semanal (mínimo por semana ou média no mês, conforme a política), interjornada de 11h, folga dominical, aprendiz sem turno noturno | PDF§2.4. As três últimas ainda sem conferência na CLT e no ECA (`INF`) | M | Escala gerada com 0 violações pelo verificador independente |
| RF-03 | Entrada: quadro de pessoal (com telefone), demanda por faixa de 30 min, disponibilidade, banco de horas, férias, afastamentos | PDF§2.2, PDF§6 | M | Carga de uma rede pré-carregada, sem digitação. **Ampliado pela [DEC-013](decisoes.md):** a entrada também pode vir de uma escala existente em 2 ou 3 formatos (RF-23) |
| RF-04 | Validação determinística dos dados, sem custo de modelo | PDF§2.3 | M | Dado inconsistente é recusado com o motivo |
| RF-05 | Otimização: o solver cobre a demanda ao menor custo de hora extra sem violar regra dura; o modelo não calcula escala nem horas | PDF§2.4, PDF§9 | M | ~~Mesma entrada gera a mesma escala~~ **Substituído pela [DEC-020](decisoes.md):** a escala resolvida é gravada (entradas, parâmetros, seed, hash) e **reverificada com 0 violações**; a tela mostra a escala gravada. Custo e cobertura vêm do solver. Motivo técnico: o CP-SAT paralelo não é determinístico |
| RF-06 | Diagnóstico: custo, cobertura, lacunas, justificativa em linguagem natural e contratações que faltam quando a demanda não cabe na lei | PDF§2.5 | M | Cada escolha do solver tem justificativa legível |
| RF-07 | Trocar a versão da regra (44h para 42h) ao vivo: nova escala, impacto em custo e em contratações | PDF§7, PDF§8 | M | Em até [PREENCHER, a medir] s, com diferença de custo e de contratações na tela |
| RF-08 | Aprovação do gerente e publicação da escala em grade semanal | PDF§2.6 | M | Nada é publicado sem aprovação |
| RF-09 | Falta com atestado: receber o aviso e o atestado, registrar o abono (simulado), nunca guardar o CID, replanejar o trecho, listar elegíveis, oferecer o turno começando por quem não gera hora extra, registrar o aceite e resumir ao gerente. **Alterado na entrevista (Fase 2):** o colega confirma antes e o gerente valida **sempre** a cobertura, antes de a escala mudar (substitui o RH-05) | PDF§3, entrevista Fase 2 | ~~S~~ → **M** (passivo completo no v1, [DEC-013](decisoes.md)) | Ciclo completo registrado; o gerente vê "válido, N dias", sem diagnóstico |
| RF-10 | Troca de turno pedida pelo colaborador: validar regras e custo antes de pedir o aceite do colega e a aprovação do gerente | PDF§3 | S | Troca que viola regra nunca chega ao gerente como válida |
| RF-11 | Canal atrás de um adapter `send_message` e `on_message`, com celular simulado no app como caminho garantido | PDF§3, DEC-003 (e) | M | O mesmo fluxo roda no simulador e, se existir, na ponte real |
| RF-12 | Modo demo: ~~usuário ou número desconhecido assume uma persona~~ o jurado entra por um botão de demo e assume um papel e uma pessoa do quadro ([DEC-017](decisoes.md): número desconhecido não assume persona) ("você está testando como a Joana") | PDF§3 | S | Jurado novo entra sem cadastro e já tem papel |
| RF-13 | Fechamento: comparar o ponto realizado (simulado) com a escala e as regras, pedir justificativa de atraso aberto, sinalizar risco antes da folha | PDF§2.8 | S (`INF`: o PDF não o põe na ordem de corte) | Desvios plantados aparecem no relatório |
| RF-14 | Painel de impacto: hora extra evitada, violações evitadas, tempo da falta até a cobertura, ~~% de faltas cobertas sem o gerente~~ (perde o sentido, o gerente valida sempre; **substituída por "% de faltas cobertas sem hora extra"**, entrevista Fase 2, FT-05), custo por execução; tempo do gerente por escala como premissa rotulada | PDF§5 | M | Números vêm do trace; premissa aparece rotulada na tela |
| RF-15 | Reiniciar o estado da demo para o próximo jurado | `INF` a partir de G§4 (jurados testam) | S | Um clique restaura a rede pré-carregada |
| RF-16 | Atraso proativo (sem batida 15 min após o início) | PDF§3, DEC-013, entrevista Fase 2 | ~~C1~~ → ~~M só para 1 gatilho ativo~~ → **M, os 3 gatilhos ativos no v1** (o usuário escolheu "os três no v1", o que substitui a [DEC-013](decisoes.md) nesse ponto) | O agente detecta sozinho falta ou atraso pelo ponto simulado e abre o fluxo; RF-27 e RF-28 cobrem os outros dois |
| RF-17 | Lembretes de turno, escala nova e troca confirmada | PDF§3 | C1 | |
| RF-18 | Consulta do colaborador ("qual meu horário amanhã?") | PDF§3 | C1 | |
| RF-19 | Ler o atestado por imagem (OCR barato e visão só com baixa confiança) e por PDF | PDF§3, entrevista Fase 2 | ~~C2~~ → **M** (o usuário quer PDF ou foto no v1) | Atestado em PDF e em foto entram e são validados; imagem e CID nunca persistidos (RN-06). Antes: "sem isso, o atestado entra como texto". **Técnica ([DEC-020](decisoes.md)):** a foto é lida pelo modelo de visão da Featherless, que devolve só campos (sem texto livre); a imagem passa pela Featherless, o que o RN-06 não proíbe |
| RF-20 | Ler a convenção em PDF para gerar o cartão de regras | PDF§2.1, entrevista Fase 2 | ~~C3~~ → **M** (o usuário quer que o agente leia a convenção em PDF e proponha as regras) | Regras propostas com a cláusula de origem; o YAML como plano B técnico é [PROPOSTA] |
| RF-21 | Ponte real do WhatsApp (whatsapp-web.js, chip dedicado, nunca número pessoal) | PDF§3, DEC-003 (e) | C4 | Sem isso, só o simulador |
| RF-22 | Política da empresa parametrizável: cada empresa define, no cartão de regras, o que a convenção e a lei deixam em aberto (por exemplo repouso mínimo por semana ou média no mês, domingo, interjornada, tratamento e destino de cada exceção). Nenhuma regra de negócio fica fixa no código | DEC-010, EC141 art. 7º §2º | M | Trocar a política fictícia por outra muda a escala e as exceções sem alterar o código |
| RF-23 | Leitura da escala atual: o agente lê a escala existente da empresa em 3 formatos, **XLSX, CSV e PDF** (PDF digital, não escaneado: [PROPOSTA]), padroniza em dados e variáveis e mostra **sempre** ao gerente um resumo curto do que entendeu, que ele confirma antes de otimizar | DEC-013, entrevista Fase 2 | M | Cada formato entra e o gerente confirma o resumo; o que não for lido vira exceção ao gerente com o motivo (RX-13) |
| RF-24 | Eventos de demanda: o gerente informa um evento que aumenta a demanda (por exemplo promoção ou feriado) e o agente ajusta a demanda e replaneja | DEC-013 | S | Regra de ajuste: [PREENCHER, Fase 2] |
| RF-25 | Reotimização semanal: a escala aprovada vira nativa; toda semana o agente verifica, por um critério [PREENCHER: o usuário disse "ainda a definir"], se precisa reotimizar. Se sim, informa o gestor o que achou e pede confirmação antes de otimizar; se não, ignora. A escala nova continua exigindo aprovação (RH-01) | Entrevista Fase 2 (FT-02) | [PREENCHER: o usuário não disse a prioridade] | Canal e prazo do aviso: [PREENCHER, Fase 3] |
| RF-26 | Pedido de edição em texto: o gerente pode pedir ao agente, em texto, uma edição da escala em rascunho (por exemplo "tire a Ana do domingo"); o agente refaz respeitando as regras e revalida. O gerente também edita direto na grade, com revalidação | Entrevista Fase 2 (FT-02) | [PREENCHER: o usuário não disse a prioridade] | A edição que viola regra dura é bloqueada, com a regra violada à mostra; o gerente pode abrir exceção ao DP ([DEC-015](decisoes.md), P5) |
| RF-27 | Hora extra estourando o limite: o agente detecta, pelo ponto simulado, que o colaborador passou do limite de hora extra da política, avisa o colaborador e o gerente e registra | Entrevista Fase 2 (FT-03) | M | O que o agente faz além de avisar: [PREENCHER]; o texto é [PROPOSTA], o usuário só citou o gatilho |
| RF-28 | Aviso de necessidade de hora extra | Entrevista Fase 2 (FT-03) | M | [PREENCHER: o usuário citou sem dizer o que dispara o aviso nem quem o recebe] |

## 3. Exceções (RX)

Cada exceção chega a uma fila com **motivo, evidência** (trecho da regra ou a mensagem), **opções com custo** e **quem decide**
(G§3, G§4, PDF§4). Os tipos e o destino de cada exceção **saem da política da empresa** (RF-22, [DEC-010](decisoes.md)). Prioridade: **M** para pelo menos 3 tipos na demo; quais, depende da política fictícia da demo (Q6, respondida). Candidatas: RX-01, RX-05 e RX-08. **S** para os demais.

| ID | Exceção | Destino | Fonte |
|---|---|---|---|
| RX-01 | Cláusula da convenção em conflito com a EC 141. Aplicar a mais restritiva é interpretação (ver conflito 2) | DP | PDF§4, EC141 art. 3º |
| RX-02 | Demanda acima da capacidade legal da equipe: recomenda contratação, com o cálculo | Gerente e DP | PDF§4 |
| RX-03 | Colaborador sem folga dominical há mais semanas do que a convenção permite | Gerente | PDF§4 |
| RX-04 | Jovem aprendiz em turno noturno | Gerente | PDF§4 |
| RX-05 | Falta sem substituto dentro da regra: hora extra, remanejamento entre lojas ou turno descoberto, cada um com custo | Gerente | PDF§4 |
| RX-06 | Ninguém aceita o turno no prazo | Gerente | PDF§4 |
| RX-07 | Troca pedida que viola a interjornada de 11h | Colaborador e gerente | PDF§4 |
| RX-08 | Atestado ilegível ou com data inconsistente: o agente não recusa, sinaliza | DP | PDF§4, PDF§3 |
| RX-09 | Colaborador não responde sobre o atraso (depende de RF-16, cortável em C1) | Gerente | PDF§4 |
| RX-10 | Mensagem de número fora do quadro | Registro e recusa no canal real; no simulador o número já é do quadro ([DEC-017](decisoes.md)) | PDF§4 |
| RX-11 | Cláusula ambígua ou regime 12x36: a regra fica pendente | DP | PDF§4, EC141 art. 7º §3º |
| RX-12 | Falha de ferramenta, modelo ou solver (API fora do ar, sem solução, saída malformada): escala com contexto, sem derrubar o fluxo | Gerente | G§4 |
| RX-13 | Leitura da escala falhou: arquivo ilegível, formato fora de XLSX, CSV e PDF, ou dado inconsistente; o agente informa o motivo | Gerente | Entrevista Fase 2 (FT-02), RF-23 |

## 4. Atos humanos e autonomia (RH)

| ID | Requisito | Fonte | Prio. |
|---|---|---|---|
| RH-01 | O gerente aprova a escala antes de publicar e decide as exceções | PDF§1 | M |
| RH-02 | O DP aprova o cartão de regras, qualquer mudança de regra e as regras pendentes | PDF§1 | M |
| RH-03 | O agente nunca contrata, desliga, altera salário, pune, recusa atestado, guarda diagnóstico nem muda regra sem aprovação | PDF§1, G§3 | M |
| RH-04 | Advertência e desconto são decisão humana; o agente só registra justificativas | PDF§3 | M |
| RH-05 | ~~Cobertura de turno sem o gerente só quando não gera hora extra e cumpre todas as regras; qualquer hora extra vai ao gerente~~. **Substituído (entrevista Fase 2):** a cobertura de falta exige a confirmação prévia do colaborador alocado e a validação do gerente, **sempre** | [DEC-003](decisoes.md) (a), substituído na entrevista | **Substituído** |
| RH-06 | Toda mensagem a colaborador (terceiro) fica registrada junto com a decisão que a gerou | REG 6 | M |

## 5. Requisitos não funcionais (RN)

| ID | Requisito | Fonte | Prio. | Critério de aceite |
|---|---|---|---|---|
| RN-01 | Rastro por decisão, desde a primeira hora: cada restrição cita a cláusula de origem e cada evento, a mensagem que o gerou | PDF§5, CLAUDE.md, DEC-005 (Langfuse self-hosted) | M | Dado um evento, dá para reconstruir regra, mensagem e decisão |
| RN-02 | O rastro é verificável por quem testa o link público (tela de auditoria no app), mesmo que o Langfuse rode só na máquina local | `INF` a partir de G§3 e DEC-005 | S, **incluída no escopo** (Q2: Sim) | Rastro de um evento em até 2 cliques |
| RN-03 | Custo por execução e latência medidos no trace; estimativa de tempo manual sempre rotulada como premissa | G§4, REG 7 | M | Painel mostra o número medido |
| RN-04 | Evals pequenos e honestos: cenários de escala com violação plantada e eventos difíceis, mais atestados sintéticos (legíveis, ruidosos, inconsistentes). Métricas: violações não detectadas (meta zero), cobertura, custo contra a planilha e acerto na leitura do atestado | PDF§5, CLAUDE.md | M | Rodam com um comando e imprimem as quatro métricas. **Mínimo decidido ([DEC-019](decisoes.md)): 30 cenários, 20 sem modelo e 10 com modelo (6 de atestado, 4 de injeção e leitura de escala); o relatório diz quantos usam modelo** |
| RN-05 | Confiabilidade: falha de ferramenta, modelo ou solver não derruba o fluxo e vira exceção (RX-12) | G§4 | M | Teste que derruba cada dependência |
| RN-06 | Privacidade do atestado: CID nunca persistido, logado nem enviado ao trace; imagem não persistida; aviso "use só dado fictício" no canal | PDF§3, DEC-003 (f), DEC-006 | M | Teste automático falha se CID ou imagem aparecer em banco, log ou trace |
| RN-07 | Toda a inferência via Featherless; outro provedor exige declaração e custo medido (o JEV foi descartado, [DEC-011](decisoes.md)) | DEC-005, DEC-006 | M | Painel de custo soma um provedor só, ou todos declarados |
| RN-08 | Interface e docs em português; código e commits em inglês | CLAUDE.md | M | |
| RN-09 | Nenhuma interpretação jurídica apresentada como certa: toda regra tem status (conferida, interpretação ou pendente) | PDF§9, REG 7 | M | O status aparece na tela |
| RN-10 | Link no ar da submissão (08/11 13h00) até o fim do Demo Day (17h30), inclusive durante o teste dos jurados | `INF` a partir de G§7 a G§9 | M | Depende da hospedagem (Q3) |
| RN-11 | Sempre que a regra de 42h ou 40h estiver ativa na demo, a tela mostra \"vigência simulada a partir de ≈16/12/2026 (conta nossa)\" | DEC-011, conflito 3 | M | O rótulo aparece junto à vigência ativa |

## 6. Critérios de aceite

**Demo de 3 minutos** (PDF§8; o bloco de ao vivo é de 0:50 a 2:15):

1. Trocar a regra de 44h para 42h: nova escala, impacto em custo e em contratações (RF-05, RF-07).
2. A colaboradora manda o atestado: um colega confirma o turno, o gerente valida e a escala muda (RF-09, RF-11; o gerente valida sempre, [DEC-014](decisoes.md)).
3. Uma exceção com opções e aprovação (RX, RH-01).
4. De 2:15 a 2:40, números do trace: custo por execução, % de faltas cobertas sem hora extra, tempo até a cobertura, violações
   evitadas (RF-14, RN-03). Todos medidos; nenhum sem rótulo.
5. Plano B: vídeo gravado do fluxo (PDF§10).

**Teste do jurado** (G§4, G§7): abre o link sem cadastro; escolhe ou recebe um papel (gerente ou colaboradora); completa um
fluxo em até [PREENCHER] min; não instala nada; o estado é reiniciável (RF-15); tudo está rotulado como sintético (RE-05).
Quantos jurados ao mesmo tempo o link aguenta: [PREENCHER].

**Núcleo:** 0 violações não detectadas nos evals (RN-04); troca de vigência sem refazer à mão (RF-07); pelo menos 3 tipos de
exceção ponta a ponta (seção 3).

## 7. Conflitos entre fontes (nenhum está decidido)

| # | Conflito | Fontes | Proposta do agente |
|---|---|---|---|
| 1 | O PDF modela "2 folgas por semana" e folga dominical como regra dura. O texto da emenda diz 2 dias, "preferencialmente" um no domingo, e permite compensação por convenção, com média de 2 no mês | PDF§2.4, EC141 art. 7º XV e §2º | Modelar a regra mais restritiva como padrão e a média compensável como regra pendente do DP, rotulada como interpretação |
| 2 | O PDF diz "aplica a mais restritiva". A emenda diz que cláusula incompatível fica "sem efeito" após 2 meses | PDF§4, EC141 art. 3º | O agente aplica a mais restritiva e escala ao DP, com o texto "interpretação". **Resolvido na entrevista (Fase 2, FT-01):** aplica a mais restritiva, provisória, e abre exceção ao DP; a política só restringe |
| 3 | A demo é em 07 e 08/11 e a vigência dos 42h começa em ≈16/12/2026 | PDF§8, EC141 | Mostrar "vigência simulada a partir de ≈16/12/2026 (conta nossa)" na tela |
| 4 | O Langfuse roda só na máquina local, mas o jurado testa por um link público | DEC-005, G§3, G§7 | Tela de auditoria no app (RN-02) ou aceitar o rastro só por vídeo |
| 5 | "Toda a inferência via Featherless" e "JEV: vamos ver" | DEC-005, DEC-006 | Decidir se o JEV entra antes da etapa técnica |
| 6 | O painel conta "% de faltas cobertas sem o gerente", mas atos a terceiros exigem aprovação por padrão | PDF§5, REG 6, DEC-003 (a) | ~~Manter RH-05 (só sem hora extra)~~. **Resolvido na entrevista (Fase 2):** o gerente valida sempre, o RH-05 está substituído e a métrica do painel será redefinida |
| 7 | O PDF não diz onde o fechamento (RF-13) entra na ordem de corte | PDF§2.8, PDF§7 | Tratar como S |
| 8 | 30 cenários de eval e 4 gates antes de implementar | PDF§5, DEC-005 | Definir um mínimo (Q5) |
| 9 | Link público estável sem servidor hoje | RE-07, RN-10, estado (pergunta 6) | Decidir a hospedagem na etapa técnica |

## 8. Perguntas para o usuário

| # | Pergunta | Recomendação do agente |
|---|---|---|
| Q1 | Conflito 1: a folga entra como regra dura "2 por semana", ou como média compensável? | ~~Dura, a mais restritiva~~. **Respondida:** é parâmetro da política da empresa (RF-22, DEC-010) |
| Q2 | Incluir a tela de auditoria no app (RN-02), que é trabalho a mais? | Sim, é a única prova que o jurado vê pelo link. **Respondida: Sim** |
| Q3 | Quando e como resolvemos a hospedagem (RE-07, RN-10)? | Na etapa técnica, com opções pesquisadas e com fonte. **Pesquisada; o usuário disse "vamos ver isso depois" ([DEC-021](decisoes.md)): `[PREENCHER]`, em aberto** ([arquitetura.md](arquitetura.md), seção 12) |
| Q4 | O JEV entra ou não (conflito 5)? | Não entra sem um uso concreto, pelo custo de um segundo provedor. **Respondida: não, JEV descartado** ([DEC-011](decisoes.md)) |
| Q5 | Mínimo de cenários de eval, além do alvo de 30 do PDF? | [PREENCHER]: sem parâmetro, escolho depois de ver o tempo da etapa técnica. **Respondida ([DEC-019](decisoes.md)): 30 cenários, 20 sem modelo e 10 com modelo** |
| Q6 | Quais 3 tipos de exceção são obrigatórios na demo? | RX-01, RX-05 e RX-08. **Respondida:** depende da política da empresa; escolher quando a política fictícia da demo existir |
| Q7 | O fechamento com ponto (RF-13) é desejável ou cortável? | Desejável. **Aceita como escrito pela aprovação** |
| Q8 | Aprova este documento, com as respostas acima? | **Respondida: aprovado** em 2026-11-07 13:13 |

## 9. Respostas do usuário (2026-11-07 13:10) e o que ainda está aberto

| Item | Resposta | Efeito |
|---|---|---|
| Conflito 1 e Q1 (folga) | Depende da política da empresa; a maioria dos pontos deve ser generalizável, conforme a política de cada empresa e a lei | RF-22 criado; a folga não é fixada |
| Conflito 2 (convenção em conflito) | "Vamos definir ainda"; o PDF é base, não a verdade | **Em aberto**. Hierarquia das fontes registrada em "Como ler" |
| Conflito 3 (demo antes da vigência) | Lembrou que "temos até 13h de amanhã para finalizar tudo" | **Resolvido** em [DEC-011](decisoes.md): o rótulo "vigência simulada" entra (RN-11) |
| Conflito 4 e Q2 (rastro e link) | "Ok" e "Sim" | RN-02 incluída no escopo |
| Conflito 5 (JEV) | Um colega do time tem acesso; depois: "esqueça o JEV" | **Resolvido** em [DEC-011](decisoes.md): JEV descartado |
| Q6 (exceções da demo) | Depende da política da empresa | RX derivadas da política; escolher com a política fictícia da demo |
| Q3, Q4, Q5, Q7, Q8 | Q4 e Q8 respondidas; Q7 aceita como escrito; Q3 e Q5 vão à etapa técnica | Q3 e Q5 **em aberto** para a etapa técnica |

## 10. Entradas do usuário depois do Gate 2 (2026-11-07 14:52)

O usuário enviou estes requisitos **depois** da aprovação do [produto.md](produto.md) ([DEC-016](decisoes.md)). Estão nas palavras
dele; onde contradizem uma decisão anterior, está marcado e **aguarda decisão dele**. Ele escreveu "deve" nos RF, mas não
disse a prioridade de cada um: `[PREENCHER]`. **Papel:** ele escreveu "gestor de RH", que não é um papel do produto (hoje:
gerente da unidade e DP). `[PREENCHER: é o gerente, o DP ou um papel novo?]`

### Do gestor

| ID | Requisito (do usuário) | Relação com o que já existe | Prio. |
|---|---|---|---|
| RF-29 | O gestor tem uma tela, com **controle de acesso**, para usar as funcionalidades do agente de escala | **Decidido ([DEC-017](decisoes.md)):** landing com login real e botões de demo (um clique por papel); cada papel vê só as telas e ações dele; isolamento por loja segue como roadmap. Substitui a persona sem login da [DEC-015](decisoes.md) | **v1** |
| RF-30 | O gestor faz **login** na plataforma a partir de uma **landing page** | **Decidido ([DEC-017](decisoes.md)):** login na landing, com botões de demo; o botão de demo cumpre o RE-07 (jurado sem cadastro) | **v1** |
| RF-31 | O gestor conversa com um agente, **somente leitura**, sobre a situação atual da escala, a escala em geral, as exceções, o cálculo de hora extra e as leis | **Contradiz** o P3 (o gerente só pede edição em texto, [DEC-014](decisoes.md)) e o "produto não é um chat" (PDF§6); "dúvidas sobre as leis" tensiona o "não dá parecer jurídico" do FT-01. **Decidido ([DEC-017](decisoes.md)):** feature **separada** (FT-08), um agente à parte do de otimização e do de acompanhamento; prioridade `[PREENCHER: o usuário disse "pode ser uma feature a mais"]`; enquanto isso, `[PROPOSTA]` desejável, cortada logo depois do FT-06, e sobre leis o agente só cita o cartão de regras e a emenda, com fonte e o aviso "não é parecer jurídico" | [PREENCHER] |
| RF-32 | O gestor entende o racional do cálculo e da definição da escala | Já coberto: RF-06 (justificativa de cada escolha) e FT-02 | M (já existe) |
| RF-33 | O gestor redefine a escala manualmente e **reotimiza quando quiser** | Edição manual: RF-26. "Reotimizar quando quiser" é gatilho **novo** do FT-02 (hoje: submissão e verificação semanal) | **v1** ([DEC-017](decisoes.md)) |
| RF-34 | O gestor diz quando a demanda será maior ou menor | = RF-24 e FT-06, hoje desejável e o 1º corte da [DEC-015](decisoes.md) | **Desejável** ([DEC-017](decisoes.md)); segue no 1º corte, com o FT-06 |
| RF-35 | O gestor autoriza uma exceção | Já coberto: RH-01 e FT-04 | M (já existe) |
| RF-36 | O gestor define o quadro de horários, os horários de funcionamento etc. | **Novo.** Hoje esses dados vêm "da empresa, por integração simulada" (FT-02, item 3) | **v1** ([DEC-017](decisoes.md)) |

### Do trabalhador

| ID | Requisito (do usuário) | Relação com o que já existe | Prio. |
|---|---|---|---|
| RF-37 | O trabalhador sabe a agenda da semana, do dia etc. | = RF-18 (consulta de horário), que sobe de cortável (C1) para v1 | **v1** ([DEC-017](decisoes.md)) |
| RF-38 | O trabalhador entende o motivo da escala | **Novo** (as justificativas hoje são para o gerente) | **v1** ([DEC-017](decisoes.md)) |
| RF-39 | O trabalhador questiona a escala, informando que tem algo no dia X | **Novo** (indisponibilidade); próximo da troca de turno, cortável | **Desejável** ([DEC-017](decisoes.md)) |
| RF-40 | O trabalhador informa ativamente uma consulta em um dia futuro, o que gera um remanejo | **Novo** gatilho do FT-03 (aviso antes da falta). `[PREENCHER: o usuário escreveu "consulta"; confirmar se é consulta médica ou outro compromisso]` | **Desejável** ([DEC-017](decisoes.md)) |
| RF-41 | O trabalhador recebe do agente uma mensagem aprovando ou não um remanejo | **Novo**; relaciona-se com a validação do gerente no FT-03 (passo 6) | **Desejável** ([DEC-017](decisoes.md)) |
| RF-42 | O sistema confere se o número de contato é de um trabalhador da empresa | **Contradiz** o RX-10 e o RF-12 (número fora do quadro vira persona de demo). **Decidido ([DEC-017](decisoes.md)):** no WhatsApp real, número fora do quadro é recusado e registrado; no celular simulado o jurado escolhe uma pessoa do quadro, então o número já é válido. RF-12 e RX-10 mudam | Segue o canal real (RF-21, cortável) |

### Não funcionais

| ID | Requisito (do usuário) | Relação com o que já existe | Prio. |
|---|---|---|---|
| RN-12 | Requisitos mínimos de segurança contra injeção de prompt, via WhatsApp e na plataforma | **Novo**; os mínimos saem da etapa técnica | [PREENCHER] |
| RN-13 | Restrito quanto à LGPD: o sistema não guarda certas coisas do trabalhador e não as informa ao gestor | Estende o RN-06 (CID e imagem do atestado). `[PREENCHER: quais dados além do CID e da imagem]` | [PREENCHER] |
| RN-14 | Os gestores configuram o tom de fala do agente com os trabalhadores, entre outros ajustes | **Novo**; no produto, as regras de comunicação (seção 5.3) eram `[PROPOSTA]` fixa | **Desejável** ([DEC-017](decisoes.md)) |

**Pergunta do usuário, sem resposta:** "Como lidar com bloqueio e etc. por parte do número?" (Q9). Depende da ponte do WhatsApp
(RF-21, cortável); encaminhada à etapa técnica.
