# Requisitos do Escalista (IDEA-002)

Última atualização: 2026-11-07 13:01 · Etapa: definição de requisitos ([DEC-005](decisoes.md)) · **Aprovação do usuário: pendente**

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
  vêm do PDF e do guia; não são decisão nova.
- Número entre colchetes, como `[PREENCHER]`, é medida ou escolha que ainda não existe.

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
| RF-02 | Regras duras do solver: jornada semanal, repouso semanal, interjornada de 11h, folga dominical, aprendiz sem turno noturno | PDF§2.4. As três últimas ainda sem conferência na CLT e no ECA (`INF`) | M | Escala gerada com 0 violações pelo verificador independente |
| RF-03 | Entrada: quadro de pessoal (com telefone), demanda por faixa de 30 min, disponibilidade, banco de horas, férias, afastamentos | PDF§2.2, PDF§6 | M | Carga de uma rede pré-carregada, sem digitação |
| RF-04 | Validação determinística dos dados, sem custo de modelo | PDF§2.3 | M | Dado inconsistente é recusado com o motivo |
| RF-05 | Otimização: o solver cobre a demanda ao menor custo de hora extra sem violar regra dura; o modelo não calcula escala nem horas | PDF§2.4, PDF§9 | M | Mesma entrada gera a mesma escala; custo e cobertura vêm do solver |
| RF-06 | Diagnóstico: custo, cobertura, lacunas, justificativa em linguagem natural e contratações que faltam quando a demanda não cabe na lei | PDF§2.5 | M | Cada escolha do solver tem justificativa legível |
| RF-07 | Trocar a versão da regra (44h para 42h) ao vivo: nova escala, impacto em custo e em contratações | PDF§7, PDF§8 | M | Em até [PREENCHER, a medir] s, com diferença de custo e de contratações na tela |
| RF-08 | Aprovação do gerente e publicação da escala em grade semanal | PDF§2.6 | M | Nada é publicado sem aprovação |
| RF-09 | Falta com atestado: receber o aviso e o atestado, registrar o abono (simulado), nunca guardar o CID, replanejar o trecho, listar elegíveis, oferecer o turno começando por quem não gera hora extra, registrar o aceite e resumir ao gerente | PDF§3 | S | Ciclo completo registrado; o gerente vê "válido, N dias", sem diagnóstico |
| RF-10 | Troca de turno pedida pelo colaborador: validar regras e custo antes de pedir o aceite do colega e a aprovação do gerente | PDF§3 | S | Troca que viola regra nunca chega ao gerente como válida |
| RF-11 | Canal atrás de um adapter `send_message` e `on_message`, com celular simulado no app como caminho garantido | PDF§3, DEC-003 (e) | M | O mesmo fluxo roda no simulador e, se existir, na ponte real |
| RF-12 | Modo demo: usuário ou número desconhecido assume uma persona ("você está testando como a Joana") | PDF§3 | S | Jurado novo entra sem cadastro e já tem papel |
| RF-13 | Fechamento: comparar o ponto realizado (simulado) com a escala e as regras, pedir justificativa de atraso aberto, sinalizar risco antes da folha | PDF§2.8 | S (`INF`: o PDF não o põe na ordem de corte) | Desvios plantados aparecem no relatório |
| RF-14 | Painel de impacto: hora extra evitada, violações evitadas, tempo da falta até a cobertura, % de faltas cobertas sem o gerente, custo por execução; tempo do gerente por escala como premissa rotulada | PDF§5 | M | Números vêm do trace; premissa aparece rotulada na tela |
| RF-15 | Reiniciar o estado da demo para o próximo jurado | `INF` a partir de G§4 (jurados testam) | S | Um clique restaura a rede pré-carregada |
| RF-16 | Atraso proativo (sem batida 15 min após o início) | PDF§3 | C1 | |
| RF-17 | Lembretes de turno, escala nova e troca confirmada | PDF§3 | C1 | |
| RF-18 | Consulta do colaborador ("qual meu horário amanhã?") | PDF§3 | C1 | |
| RF-19 | Ler o atestado por imagem (OCR barato e visão só com baixa confiança) | PDF§3 | C2 | Sem isso, o atestado entra como texto |
| RF-20 | Ler a convenção em PDF para gerar o cartão de regras | PDF§2.1 | C3 | Sem isso, as regras entram em YAML |
| RF-21 | Ponte real do WhatsApp (whatsapp-web.js, chip dedicado, nunca número pessoal) | PDF§3, DEC-003 (e) | C4 | Sem isso, só o simulador |

## 3. Exceções (RX)

Cada exceção chega a uma fila com **motivo, evidência** (trecho da regra ou a mensagem), **opções com custo** e **quem decide**
(G§3, G§4, PDF§4). Prioridade: **M** para pelo menos 3 tipos, propostos como RX-01, RX-05 e RX-08 (Q6); **S** para os demais.

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
| RX-10 | Mensagem de número fora do quadro | Registro, ou modo demo (RF-12) | PDF§4 |
| RX-11 | Cláusula ambígua ou regime 12x36: a regra fica pendente | DP | PDF§4, EC141 art. 7º §3º |
| RX-12 | Falha de ferramenta, modelo ou solver (API fora do ar, sem solução, saída malformada): escala com contexto, sem derrubar o fluxo | Gerente | G§4 |

## 4. Atos humanos e autonomia (RH)

| ID | Requisito | Fonte | Prio. |
|---|---|---|---|
| RH-01 | O gerente aprova a escala antes de publicar e decide as exceções | PDF§1 | M |
| RH-02 | O DP aprova o cartão de regras, qualquer mudança de regra e as regras pendentes | PDF§1 | M |
| RH-03 | O agente nunca contrata, desliga, altera salário, pune, recusa atestado, guarda diagnóstico nem muda regra sem aprovação | PDF§1, G§3 | M |
| RH-04 | Advertência e desconto são decisão humana; o agente só registra justificativas | PDF§3 | M |
| RH-05 | Cobertura de turno sem o gerente só quando não gera hora extra e cumpre todas as regras; qualquer hora extra vai ao gerente | [DEC-003](decisoes.md) (a), **provisória** | M |
| RH-06 | Toda mensagem a colaborador (terceiro) fica registrada junto com a decisão que a gerou | REG 6 | M |

## 5. Requisitos não funcionais (RN)

| ID | Requisito | Fonte | Prio. | Critério de aceite |
|---|---|---|---|---|
| RN-01 | Rastro por decisão, desde a primeira hora: cada restrição cita a cláusula de origem e cada evento, a mensagem que o gerou | PDF§5, CLAUDE.md, DEC-005 (Langfuse self-hosted) | M | Dado um evento, dá para reconstruir regra, mensagem e decisão |
| RN-02 | O rastro é verificável por quem testa o link público (tela de auditoria no app), mesmo que o Langfuse rode só na máquina local | `INF` a partir de G§3 e DEC-005 | S | Rastro de um evento em até 2 cliques (Q2) |
| RN-03 | Custo por execução e latência medidos no trace; estimativa de tempo manual sempre rotulada como premissa | G§4, REG 7 | M | Painel mostra o número medido |
| RN-04 | Evals pequenos e honestos: cenários de escala com violação plantada e eventos difíceis, mais atestados sintéticos (legíveis, ruidosos, inconsistentes). Métricas: violações não detectadas (meta zero), cobertura, custo contra a planilha e acerto na leitura do atestado | PDF§5, CLAUDE.md | M | Rodam com um comando e imprimem as quatro métricas. Alvo do PDF: 30 cenários (Q5) |
| RN-05 | Confiabilidade: falha de ferramenta, modelo ou solver não derruba o fluxo e vira exceção (RX-12) | G§4 | M | Teste que derruba cada dependência |
| RN-06 | Privacidade do atestado: CID nunca persistido, logado nem enviado ao trace; imagem não persistida; aviso "use só dado fictício" no canal | PDF§3, DEC-003 (f), DEC-006 | M | Teste automático falha se CID ou imagem aparecer em banco, log ou trace |
| RN-07 | Toda a inferência via Featherless; outro provedor (por exemplo o JEV) exige declaração e custo medido | DEC-005, DEC-006 | M | Painel de custo soma um provedor só, ou todos declarados |
| RN-08 | Interface e docs em português; código e commits em inglês | CLAUDE.md | M | |
| RN-09 | Nenhuma interpretação jurídica apresentada como certa: toda regra tem status (conferida, interpretação ou pendente) | PDF§9, REG 7 | M | O status aparece na tela |
| RN-10 | Link no ar da submissão (08/11 13h00) até o fim do Demo Day (17h30), inclusive durante o teste dos jurados | `INF` a partir de G§7 a G§9 | M | Depende da hospedagem (Q3) |

## 6. Critérios de aceite

**Demo de 3 minutos** (PDF§8; o bloco de ao vivo é de 0:50 a 2:15):

1. Trocar a regra de 44h para 42h: nova escala, impacto em custo e em contratações (RF-05, RF-07).
2. A colaboradora manda o atestado: um colega cobre o turno e o gerente recebe o resumo (RF-09, RF-11).
3. Uma exceção com opções e aprovação (RX, RH-01).
4. De 2:15 a 2:40, números do trace: custo por execução, % de faltas cobertas sem o gerente, tempo até a cobertura, violações
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
| 2 | O PDF diz "aplica a mais restritiva". A emenda diz que cláusula incompatível fica "sem efeito" após 2 meses | PDF§4, EC141 art. 3º | O agente aplica a mais restritiva e escala ao DP, com o texto "interpretação" |
| 3 | A demo é em 07 e 08/11 e a vigência dos 42h começa em ≈16/12/2026 | PDF§8, EC141 | Mostrar "vigência simulada a partir de ≈16/12/2026 (conta nossa)" na tela |
| 4 | O Langfuse roda só na máquina local, mas o jurado testa por um link público | DEC-005, G§3, G§7 | Tela de auditoria no app (RN-02) ou aceitar o rastro só por vídeo |
| 5 | "Toda a inferência via Featherless" e "JEV: vamos ver" | DEC-005, DEC-006 | Decidir se o JEV entra antes da etapa técnica |
| 6 | O painel conta "% de faltas cobertas sem o gerente", mas atos a terceiros exigem aprovação por padrão | PDF§5, REG 6, DEC-003 (a) | Manter RH-05 (só sem hora extra) |
| 7 | O PDF não diz onde o fechamento (RF-13) entra na ordem de corte | PDF§2.8, PDF§7 | Tratar como S |
| 8 | 30 cenários de eval e 4 gates antes de implementar | PDF§5, DEC-005 | Definir um mínimo (Q5) |
| 9 | Link público estável sem servidor hoje | RE-07, RN-10, estado (pergunta 6) | Decidir a hospedagem na etapa técnica |

## 8. Perguntas para o usuário

| # | Pergunta | Recomendação do agente |
|---|---|---|
| Q1 | Conflito 1: a folga entra como regra dura "2 por semana", ou como média compensável? | Dura, a mais restritiva, rotulada como interpretação |
| Q2 | Incluir a tela de auditoria no app (RN-02), que é trabalho a mais? | Sim, é a única prova que o jurado vê pelo link |
| Q3 | Quando e como resolvemos a hospedagem (RE-07, RN-10)? | Na etapa técnica, com opções pesquisadas e com fonte |
| Q4 | O JEV entra ou não (conflito 5)? | Não entra sem um uso concreto, pelo custo de um segundo provedor |
| Q5 | Mínimo de cenários de eval, além do alvo de 30 do PDF? | [PREENCHER]: sem parâmetro, escolho depois de ver o tempo da etapa técnica |
| Q6 | Quais 3 tipos de exceção são obrigatórios na demo? | RX-01, RX-05 e RX-08 |
| Q7 | O fechamento com ponto (RF-13) é desejável ou cortável? | Desejável |
| Q8 | Aprova este documento, com as respostas acima? | |
