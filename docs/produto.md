# Produto: Escalista (IDEA-002)

Última atualização: 2026-11-07 14:57 · Etapa: definição de negócio ([DEC-012](decisoes.md)) · **Aprovado pelo usuário em 2026-11-07 14:47 ([DEC-016](decisoes.md)), com as pendências da seção 12. Depois da aprovação o usuário enviou novos requisitos (seção 13), decididos na [DEC-017](decisoes.md): Gate de negócio fechado com eles.** Consolidado na entrevista (Fases 1 a 3: [DEC-013](decisoes.md), [DEC-014](decisoes.md), [DEC-015](decisoes.md))

Este documento define **o que o produto é e como ele se comporta**: features, capacidade de cada uma, entradas e saídas, fluxos, o
que fica com o agente e o que fica com o humano, como os dois se falam e como o produto se generaliza. Não define stack nem
arquitetura (etapa técnica). Os IDs `RF-`, `RX-`, `RH-` e `RN-` vêm de [requisitos.md](requisitos.md). A ficha da ideia, com
mercado, concorrência e hipóteses, está em [IDEA-002](ideacao/ideias/IDEA-002-escalista.md). O PDF do Escalista é base, não a
verdade ([DEC-010](decisoes.md)): a verdade é o que saiu desta entrevista.

**Como ler os rótulos:** o que não tem rótulo é **resposta do usuário** na entrevista. **[DERIVADO]** vem dos requisitos aprovados
e foi confirmado por ele. **[PROPOSTA]** é suposição do agente, **ainda não confirmada**. `[PREENCHER]` é o que falta, com o motivo.

## 1. O produto em uma frase e os papéis

O Escalista é um digital worker que **otimiza, publica e acompanha a escala de trabalho de uma operação com turnos, conforme a lei,
a convenção coletiva e a política de cada empresa**, e cobre faltas conversando com a equipe. O gerente aprova a escala, valida
cada cobertura e decide as exceções.

**Primeiro momento de valor para o jurado:** "escala pronta, legal e ao menor custo".

| Papel | Quem é | O que faz no produto | Onde interage |
|---|---|---|---|
| **Agente** | O Escalista | Lê, valida, otimiza, replaneja, conversa, explica, abre exceção e registra tudo | Todos os pontos |
| **Gerente** | Responsável pela unidade | Confirma a leitura da escala, aprova e publica, edita ou pede edição, valida cada cobertura, decide exceções de escala e de cobertura | App (grade, fila, resultado) e texto ao agente para pedir edição |
| **DP** | Departamento Pessoal | Aprova o cartão de regras e qualquer mudança; decide regras pendentes e comprovações inconsistentes; confirma o abono | App (cartão de regras e fila) |
| **Colaborador** | Pessoa escalada | Avisa falta ou atraso, envia a comprovação, confirma ou recusa um turno | Celular simulado |
| **Jurado** | Quem testa o link | Escolhe uma persona (gerente, DP ou colaboradora), sem login | App público |

**Atualização ([DEC-044](decisoes.md), 08/11):** na demo, **gerente e DP viram um papel só, o gestor**; ficam gestor e colaborador.

## 2. Lista de features, prioridade e ordem de corte

A lista nasceu das features que o usuário escreveu (resumo na seção 11) e foi fechada na [DEC-013](decisoes.md) e na
[DEC-014](decisoes.md).

| ID | Feature | Prioridade | Situação |
|---|---|---|---|
| FT-01 | Política e cartão de regras | **v1** | Fechado, 12 itens |
| FT-02 | Otimização de escala, com leitura da escala existente (XLSX, CSV, PDF) | **v1, núcleo** | Fechado, 12 itens |
| FT-03 | Acompanhamento de escala: passivo completo e 3 gatilhos ativos | **v1** | Fechado, 12 itens |
| FT-04 | Aprovação e fila de exceções | **v1** | Fechado, 12 itens |
| FT-05 | Painel de impacto e auditoria | **v1** | Fechado, 12 itens |
| FT-07 | Simulação de vigência e de política ("e se" 44h para 42h) | **v1**, por ser o RF-07 (M) `[DERIVADO]` | **Esboço, a confirmar**; o usuário só disse que é feature própria |
| FT-06 | Eventos de demanda | **Desejável** | Esboço |
| FT-08 | Assistente do gestor: conversa somente leitura sobre a escala, as exceções, a hora extra e as leis; **agente separado** dos de otimização e de acompanhamento | `[PREENCHER]`; `[PROPOSTA]` desejável, cortado logo depois do FT-06 | Novo ([DEC-017](decisoes.md)), sem detalhe |
| (sem ID) | Troca de turno pedida pelo colaborador | Cortável `[PROPOSTA]`: o usuário não a marcou | Fora desta fase |
| (sem ID) | Ponte real do WhatsApp; lembretes de turno; consulta de horário | Cortáveis (RF-21, RF-17, RF-18); não revistos na entrevista | Fora desta fase |

**Ordem de corte se o tempo estourar ([DEC-015](decisoes.md) e [DEC-017](decisoes.md)):** (1) FT-06; (2) os desejáveis novos da
DEC-017 (FT-08 `[PROPOSTA]`, questionar a escala, consulta futura, aprovar remanejo, demanda maior ou menor, tom configurável; a
ordem entre eles: `[PREENCHER]`); (3) os gatilhos de hora extra, ficando falta ou atraso; (4) a foto do atestado, ficando o PDF;
(5) a leitura da convenção em PDF, que vira YAML; (6) a reotimização semanal. Esta ordem substitui a do PDF. **Não cortamos** exceções, rastro e evals (CLAUDE.md).

## 3. Features

Cada feature segue os 12 itens da entrevista.

### FT-01 · Política e cartão de regras

1. **Objetivo e quem ganha o quê.** Transformar lei, convenção e política da empresa em regras executáveis, cada uma com a origem
   (RF-01, RF-22). O **DP** tem controle e rastro das regras; o **gerente** recebe escala dentro da regra; a **empresa** não
   depende de regra fixa no código.
2. **Gatilho.** O **DP** carrega as fontes; de novo quando muda a vigência ou a política.
3. **Entradas.** Convenção coletiva fictícia em **PDF**; texto da lei (EC 141, CLT); política da empresa (parâmetros); vigência.
4. **Fluxo principal.** (1) **DP** carrega as fontes. (2) **Agente** lê a convenção em PDF e propõe cada regra com a cláusula de
   origem, a vigência e o status (conferida, interpretação ou pendente). (3) **Agente** confere conflito entre camadas e ambiguidade.
   (4) Em conflito ou ambiguidade, **aplica a mais restritiva, de forma provisória, e abre exceção ao DP** (RX-01, RX-11). (5)
   **DP** aprova uma vez; o cartão fica ativo e versionado. Qualquer mudança de regra passa pelo DP.
5. **Exceções.** (a) Cláusula em conflito com a lei, **ao DP** (RX-01); (b) cláusula ambígua ou regime 12x36, regra pendente,
   **ao DP** (RX-11). As opções de cada uma saem da política da empresa (RF-22). Na demo, as da RX-01 estão em
   [politica_ficticia.yaml](../data/regras/politica/politica_ficticia.yaml) (`excecoes_demo`); a RX-11 não tem opções: a regra fica pendente para o DP.
6. **Regras de negócio.** *Parâmetro da política:* todas as regras de escala, de hora extra, prazos e destino das exceções.
   *Fixas no produto:* a política só **restringe** a lei e a convenção, nunca as afrouxa; em conflito vale a mais restritiva,
   provisória; toda regra tem origem, vigência e status; só o DP muda regra.
7. **Fronteira agente e humano.** *Agente:* propõe a regra e a origem, detecta conflito e ambiguidade; não dá parecer jurídico.
   *Só o humano (DP):* aprova, decide a pendência e muda regra (RH-02).
8. **Interação com o humano.** O DP no app: tela do cartão com as pendências; cada pendência é um cartão de exceção (FT-04). Se o
   DP não decide no prazo: escala ao próximo decisor (seção 5.4); enquanto isso a regra fica provisória e mais restritiva
   `[PROPOSTA]`.
9. **Saídas e registros.** Cartão de regras versionado, lista de pendências, diferença entre versões, trace.
10. **Capacidade e limites.** Não dá parecer jurídico; regime 12x36 fica pendente; convenção só em PDF digital `[PROPOSTA]`;
    tamanho da convenção `[PREENCHER, a medir na etapa técnica]`.
11. **Critério de aceite (negócio).** O jurado vê o agente ler a convenção fictícia e propor as regras com a cláusula de origem;
    vê uma cláusula em conflito virar regra provisória mais restritiva e uma exceção ao DP; trocar a política muda a escala sem
    alterar o código (RF-22).
12. **Dados sintéticos.** Convenção fictícia em PDF **escrita por nós** (nada copiado de convenção real) com 1 cláusula em conflito
    com a emenda e 1 ambígua; uma política fictícia da demo. `[PROPOSTA]`, confirmada pelo usuário.

### FT-02 · Otimização de escala (núcleo)

1. **Objetivo e quem ganha o quê.** O **gerente** recebe uma escala nova, pronta, legal e ao menor custo, com custo total, total de
   horas escaladas, horas extras, cobertura, violações e **economia**. O **colaborador** recebe a escala publicada. A **empresa**
   ganha a economia: o custo da escala enviada menos o custo da otimizada, **ambos calculados pelo solver** com as mesmas regras
   (medido, não estimado). O "tempo total" do usuário é lido como o total de horas escaladas (definição da opção que ele escolheu).
2. **Gatilho.** (a) A primeira otimização nasce quando o **gerente submete uma escala existente**. (b) Depois, a escala passa a
   ser **nativa da plataforma** e o **agente** a verifica toda semana; o critério para decidir se é preciso reotimizar é
   `[PREENCHER: o usuário disse "ainda a definir"]`.
3. **Entradas.** Escala existente em **XLSX, CSV ou PDF** (PDF digital, não escaneado `[PROPOSTA]`); demanda por faixa de
   horário, quadro de pessoal, disponibilidade, férias e regras da empresa (a política do FT-01). **Tudo é fornecido pela
   empresa**, "supondo uma integração de sistemas", simulada na demo (RE-11). Formato fora desses vira exceção.
4. **Fluxo principal.**
   1. **Gerente** submete a escala existente.
   2. **Agente** lê e padroniza em dados e variáveis (o modelo lê; a validação dos dados é determinística, sem modelo, RF-04).
   3. **Agente** mostra um **resumo curto** do que entendeu e o **gerente confirma, sempre**.
   4. **Agente** roda o solver com as regras do cartão (FT-01) e o verificador independente confere 0 violações.
   5. **Agente** calcula o antes e o depois e escreve as justificativas.
   6. **Gerente** aprova, edita direto na grade ou **pede a edição em texto ao agente**. O agente revalida a cada edição e
      **bloqueia** a que viola regra dura, mostrando a regra; o gerente pode abrir uma exceção ao DP.
   7. Aprovada, a escala é publicada ao colaborador (FT-04) e fica nativa.
   - **Rotina semanal:** o agente verifica o critério `[PREENCHER]`; se for preciso reotimizar, informa o gestor o que achou e
     pede confirmação; confirmando, reotimiza e volta ao passo 4; se não for preciso, ignora. A aprovação do passo 6 continua
     valendo (RH-01).
5. **Exceções.** Cada uma chega ao decisor com motivo, evidência, opções com custo e a recomendação (cartão do FT-04): (a)
   arquivo ilegível, formato fora de XLSX, CSV e PDF ou dado inconsistente, **ao gerente**, com o motivo (RX-13); (b) demanda que
   não cabe nas regras, recomenda contratação com o cálculo, **ao gerente e ao DP** (RX-02); (c) falha do solver ou do modelo,
   **ao gerente** (RX-12). *Não é exceção:* a escala enviada que viola regra aparece no "antes" e não bloqueia. As opções de cada
   exceção: `[PREENCHER com a política fictícia da demo]`.
6. **Regras de negócio.** *Parâmetro da política (RF-22):* todas as regras da escala. *Fixas no produto:* o solver calcula (não o
   modelo); o verificador independente exige 0 violações; nada é publicado sem aprovação; edição que viola regra dura é bloqueada.
7. **Fronteira agente e humano.** *Agente sozinho:* ler, padronizar, validar, otimizar, verificar, calcular antes e depois,
   justificar, checar toda semana. *Agente propõe:* a escala nova e a reotimização semanal (pede confirmação). *Só o humano:*
   confirmar a leitura, aprovar, editar ou pedir edição; a publicação só acontece com a aprovação.
8. **Interação com o humano.** Gerente no app: resumo de leitura, tela antes e depois, grade editável; e **texto ao agente** para
   pedir edição. Aviso semanal ao gestor: no app, na fila `[PROPOSTA]`; o prazo é parâmetro da política e, sem resposta, escala ao
   próximo decisor (seção 5.4).
9. **Saídas e registros.** Escala em rascunho, aprovada e publicada, versionada; comparativo antes e depois; justificativas;
   exceções; trace de cada etapa (leitura, solver, verificador, custo do modelo e latência). O painel (FT-05) mostra custo por
   execução, economia e violações evitadas. `[DERIVADO]` RF-14, RN-01, RN-03
10. **Capacidade e limites.** Cerca de 3 lojas e 60 colaboradores; tempo do solver `[PREENCHER, a medir na etapa técnica]`.
    *Não faz:* publicar sem aprovação, calcular com o modelo, ler PDF escaneado, aceitar formato fora de XLSX, CSV e PDF, folha de
    pagamento e decisão sobre pessoas. `[DERIVADO]`; o PDF digital é `[PROPOSTA]`
11. **Critério de aceite (negócio).** O jurado envia uma escala (XLSX, CSV ou PDF), confirma o resumo e vê **antes e depois**
    com custo, total de horas escaladas, horas extras, cobertura, violações e economia, medidos pelo solver; o "depois" tem 0
    violações; um pedido de edição em texto é cumprido respeitando as regras, e um que as viola é bloqueado com a regra à mostra.
12. **Dados sintéticos.** Uma rede fictícia com a escala atual em XLSX, CSV e PDF de layouts diferentes; demanda por faixa,
    quadro, disponibilidade e férias; um arquivo com defeito plantado (para a exceção de leitura); e uma escala enviada com
    violações plantadas (para o "antes"). `[PROPOSTA]`, confirmada pelo usuário.

### FT-03 · Acompanhamento de escala

1. **Objetivo e quem ganha o quê.** Acompanhar presença, horas e faltas, gerar registros e avisos e remanejar a escala de forma
   otimizada. O **gerente** vê a falta ou o atraso virar um turno coberto, com registro e aviso, sem montar a cobertura. O
   **colaborador** avisa e justifica pelo canal que usa. A **empresa** cobre mais rápido e controla a hora extra.
2. **Gatilho.** *Passivo:* o colaborador avisa atraso ou falta, ou envia a justificativa. *Ativo (agente, 3 gatilhos no v1):*
   (a) falta ou atraso detectado pelo ponto simulado; (b) hora extra estourando o limite; (c) aviso de necessidade de hora extra
   `[PREENCHER: o usuário citou sem dizer o que dispara o aviso nem quem o recebe]`.
3. **Entradas.** Mensagem do colaborador; **comprovação em PDF ou em foto**; ponto simulado; escala vigente; política (limite de
   atraso, limite de hora extra, prazo de oferta, ordem de oferta); banco de horas.
4. **Fluxo principal.**
   - *Passivo:* (1) **colaborador** avisa e o **agente** confirma o recebimento; (2) **agente** lê a comprovação e valida; dado
     ilegível ou inconsistente vai ao **DP** e o agente não recusa (RX-08); (3) **agente** registra e avisa o gestor; (4) **agente**
     replaneja o trecho e acha quem possa cobrir, pelas regras; (5) **agente** oferece o turno e o **colega confirma antes**; (6) o
     **gerente valida, sempre**; (7) **agente** atualiza a escala, avisa os dois e registra.
   - *Ativo:* o agente percebe o gatilho, comunica o funcionário envolvido, recebe a justificativa (ou não), comunica o gestor,
     gera registro e aviso e, se precisar remanejar, **dispara um gatilho com o detalhe para o FT-02** replanejar.
   - *Sem resposta:* o colega não responde no prazo, o agente oferece ao próximo; sem mais ninguém, exceção ao gerente (RX-06 e
     RX-05).
5. **Exceções.** (a) Comprovação ilegível ou com data inconsistente, **ao DP**, o agente não recusa (RX-08); (b) sem colega elegível
   ou ninguém aceita, **ao gerente**, com opções e custo (RX-05, RX-06); (c) número fora do quadro é recusado e registrado no canal real (RX-10, [DEC-017](decisoes.md)); no simulador o número já é do quadro;
   (d) colaborador que não responde ao aviso de falta ou atraso, **ao gerente** (RX-09). Opções de cada uma: na demo, as da
   RX-05 estão em `excecoes_demo` de [politica_ficticia.yaml](../data/regras/politica/politica_ficticia.yaml); prazos e limites de
   RX-06 e RX-09 estão em `pol_oferta_turno` e `pol_atraso`.
6. **Regras de negócio.** *Parâmetro da política:* prazo de cada oferta, limite de atraso, ordem de oferta (quem não gera hora
   extra primeiro), limite de hora extra. *Fixas:* nunca recusar atestado, nunca guardar CID nem a imagem, nada irreversível sem
   humano, e **o gerente valida sempre a cobertura** (substitui o RH-05).
7. **Fronteira agente e humano.** *Sozinho:* confirmar o recebimento, ler a comprovação, registrar, avisar o gestor, achar os
   elegíveis, oferecer o turno e detectar os gatilhos. *Propõe:* a cobertura (colega e turno). *Só o humano:* o colega aceita, o
   gerente valida, o DP decide a comprovação inconsistente e **confirma o abono, que nasce provisório**; advertência e desconto
   ficam com humanos (RH-04).
8. **Interação com o humano.** Colaborador: celular simulado (a ponte real do WhatsApp é cortável). Gerente: validação na fila do
   app e resumo. Regras de comunicação: seção 5.3 `[PROPOSTA]`. Se o colega não responde, vai ao próximo; se o gerente não valida
   no prazo, escala ao próximo decisor (seção 5.4).
9. **Saídas e registros.** Turno coberto e escala atualizada; registros de falta, atraso e hora extra; avisos; abono provisório
   para o DP; toda mensagem ao colaborador registrada junto com a decisão (RH-06); resumo ao gerente; trace. O painel (FT-05)
   mostra o tempo da falta até a cobertura.
10. **Capacidade e limites.** Só assuntos de escala (falta, atraso, atestado, hora extra); não faz holerite nem férias. Não faz:
    recusar atestado, guardar CID ou imagem, decidir hora extra ou remanejamento, advertir ou descontar. Capacidade:
    `[PREENCHER, a medir na etapa técnica]`.
11. **Critério de aceite (negócio).** O jurado vê o agente detectar sozinho uma falta ou atraso no ponto simulado, ou envia um
    atestado (PDF ou foto); o colega confirma; o gerente valida; a escala se atualiza; nenhum CID aparece em lugar algum; os outros
    dois gatilhos também funcionam.
12. **Dados sintéticos.** Ponto simulado com falta, atraso e hora extra plantados; atestados sintéticos em PDF e em foto, legíveis,
    ruidosos e inconsistentes; colaboradores com telefone fictício e elegíveis variados. `[PROPOSTA]`, confirmada pelo usuário.

### FT-04 · Aprovação e fila de exceções

1. **Objetivo e quem ganha o quê.** Nada vai à equipe sem um humano aprovar, e todo caso fora da regra chega ao decisor com o
   contexto pronto. O **gerente** decide só o que importa, com opções e custo; o **DP** decide regras e pendências; o
   **colaborador** só recebe escala aprovada.
2. **Gatilho.** O **agente**, ao gerar um rascunho (FT-02), uma cobertura (FT-03), uma regra pendente (FT-01) ou uma falha.
3. **Entradas.** Eventos das outras features.
4. **Fluxo principal.** *Aprovação:* o gerente revê o rascunho, aprova, edita na grade ou pede edição em texto (FT-02); o agente
   publica e registra a versão. *Exceção:* o agente detecta, monta o cartão e notifica o decisor; o decisor escolhe uma opção ou
   ajusta; o agente executa e registra. **Sem resposta até o prazo da política:** escala ao próximo decisor; se ninguém decidir, o
   turno fica **descoberto**, sem ação irreversível.
5. **Exceções (da própria fila).** Falha de ferramenta, modelo ou solver (RX-12). Mínimo de **3 tipos de exceção ponta a ponta na
   demo**; quais: `[PREENCHER: escolher com a política fictícia da demo, DEC-010]`.
6. **Regras de negócio.** *Parâmetro da política:* os tipos de exceção, o destino, o prazo e as opções permitidas de cada uma.
   *Fixas:* nada publicado sem aprovação; nada irreversível nem dirigido a terceiros sem humano; o agente nunca decide uma
   exceção.
7. **Fronteira agente e humano.** *Agente:* detecta, monta as opções com custo, recomenda, executa a decisão e registra.
   *Humano:* decide.
8. **Interação com o humano.** Gerente e DP no app, na fila e na grade. O **cartão de exceção** traz tipo, quem decide, prazo,
   motivo, evidência (trecho da regra ou a mensagem), opções com custo, recomendação do agente, o que ocorre sem resposta e
   histórico.
9. **Saídas e registros.** Decisão registrada, execução, escala publicada e versionada, mensagens aos colaboradores, trace.
10. **Capacidade e limites.** O agente não decide e não executa ato irreversível; capacidade da fila
    `[PREENCHER, a medir na etapa técnica]`.
11. **Critério de aceite (negócio).** Pelo menos 3 tipos de exceção ponta a ponta, cada um com opções e custo, e a decisão do
    jurado executada pelo agente; nada é publicado sem aprovação.
12. **Dados sintéticos.** Casos plantados que gerem pelo menos 3 tipos de exceção; um gerente e um DP fictícios. `[PROPOSTA]`,
    confirmada pelo usuário.

### FT-05 · Painel de impacto e auditoria

1. **Objetivo e quem ganha o quê.** Provar o ganho e mostrar por que o agente fez o que fez. O **jurado**, o **gerente** e o **DP**
   veem números medidos e podem conferir cada decisão.
2. **Gatilho.** Sempre disponível; atualiza a cada execução.
3. **Entradas.** Trace e eventos.
4. **Fluxo principal.** Quem abre o painel vê os números; de qualquer evento chega à auditoria em **até 2 cliques**: regra de
   origem, mensagem, decisão e custo (RN-02).
5. **Exceções.** Número sem medida não aparece sem rótulo de premissa.
6. **Regras de negócio.** *Fixas:* todo número vem do trace (medido); estimativa é premissa e vai rotulada (CLAUDE.md, regra 7).
7. **Fronteira agente e humano.** Só leitura; tudo é do agente.
8. **Interação com o humano.** Painel e tela de auditoria no app, para gerente, DP e jurado. O Langfuse local não é acessível
   pelo link público, então a tela do app é a prova.
9. **Saídas e registros.** Custo por execução, **economia** (FT-02), hora extra evitada, violações evitadas, tempo da falta até a
   cobertura e **% de faltas cobertas sem hora extra**; tela de auditoria.
10. **Capacidade e limites.** Não mostra estimativa sem rótulo; o tempo do gerente por escala, se aparecer, é premissa rotulada.
    Capacidade `[PREENCHER, a medir na etapa técnica]`.
11. **Critério de aceite (negócio).** O jurado clica num evento e, em até 2 cliques, vê regra de origem, mensagem, decisão e
    custo; os números do painel batem com o trace.
12. **Dados sintéticos.** Execuções pré-carregadas dos FT-02 e FT-03 suficientes para o painel não abrir vazio. `[PROPOSTA]`

### FT-07 · Simulação de vigência e de política (esboço derivado, **a confirmar**)

O usuário só decidiu que é **feature própria**. O resto vem dos requisitos aprovados (`[DERIVADO]` RF-06, RF-07, RN-11) e não foi
detalhado na entrevista. *Objetivo:* mostrar o que muda com outra vigência (44h, 42h, 40h) ou política, em custo, cobertura e
contratações. *Gatilho:* o gerente ou o DP escolhe a alternativa. *Fluxo:* o agente monta o cartão alternativo, o solver
reotimiza, o agente calcula a diferença e mostra o antes e o depois; se a demanda não couber, abre RX-02 com o cálculo.
*Fronteira:* o agente calcula e recomenda; gerente e DP decidem adotar ou contratar. A tela mostra "vigência simulada a partir de
≈16/12/2026 (conta nossa)" (RN-11). *Aceite:* trocar 44h por 42h ao vivo em até `[PREENCHER, a medir]` s.

### FT-06 · Eventos de demanda (esboço, desejável, primeiro a cortar)

O gerente informa um evento que aumenta a demanda (promoção, feriado) e o agente ajusta a demanda e replaneja pelo FT-02. Regra
de ajuste: `[PREENCHER]`. Cortável; sem mais detalhe.

## 4. Quem decide o quê

| Ato | Agente sozinho | Agente propõe, humano decide | Só humano |
|---|---|---|---|
| Ler a escala enviada, validar dados, otimizar e verificar | ✔ | | |
| **Confirmar** a leitura da escala | | ✔ gerente, sempre | |
| **Aprovar e publicar** a escala | | ✔ gerente | |
| Editar a escala (grade ou texto) | revalida e bloqueia a violação | ✔ gerente edita; exceção ao DP se violar | |
| Propor regra do cartão e a origem | ✔ | | |
| **Aprovar ou mudar** regra, resolver regra pendente | | ✔ DP | |
| Aplicar a regra mais restritiva num conflito de cláusula | provisório | ✔ DP | |
| **Reotimização semanal** | verifica e propõe | ✔ gerente confirma e depois aprova a escala | |
| **Cobertura de falta**: achar elegíveis e oferecer o turno | ✔ | colega confirma; **gerente valida sempre** | |
| Hora extra, remanejamento entre lojas, turno descoberto | | ✔ gerente | |
| Registrar o recebimento da comprovação e o abono | provisório | ✔ DP confirma o abono | |
| Comprovação ilegível ou inconsistente | sinaliza | ✔ DP | |
| Recomendar contratação, com o cálculo | ✔ | decidir contratar: gerente e DP | |
| Advertência, desconto, recusa de atestado, salário, demissão, promoção | | | ✔ |

## 5. Como o agente interage com o humano

### 5.1 Canais por papel

- **Gerente e DP:** no app, com **grade**, **fila** (aprovações e exceções), tela de resultado e painel. O **gerente também escreve ao
  agente em texto** para pedir edição da escala (FT-02). Para o **DP** o texto livre não foi definido: `[PREENCHER]`.
- **Colaborador:** pelo celular simulado. A ponte real do WhatsApp é cortável (RF-21).
- **Resumo ao gerente:** uma linha por evento resolvido; só o que exige decisão vira cartão.

### 5.2 O cartão de exceção

Todo caso que chega a um humano traz: tipo; quem decide; prazo; motivo; evidência (trecho da regra ou a mensagem original);
opções com custo; a recomendação do agente e por quê; o que acontece se ninguém responder; histórico. O humano escolhe uma opção,
ajusta ou recusa, e o agente executa e registra. (FT-04)

### 5.3 Regras de comunicação com o colaborador `[PROPOSTA]`

O agente se identifica como assistente automático e confirma o recebimento; mensagens curtas, em português, uma pergunta por vez;
nunca mostra nem repete diagnóstico (ao gerente diz só "válido, N dias"); nunca promete o que depende de um humano; quando falha
uma ferramenta, o modelo ou o solver, diz o que aconteceu e abre exceção (RX-12), sem inventar resposta. Este bloco não foi
discutido na entrevista.

### 5.4 Tempo e escalada

O prazo de resposta de cada exceção, aprovação e oferta de turno é **parâmetro da política**. Vencido o prazo, o agente **escala ao
próximo decisor**; se ninguém decidir, o turno fica **descoberto**, sem ação irreversível. O valor dos prazos:
na demo, em `pol_prazos_e_escalada` e `excecoes_demo` de [politica_ficticia.yaml](../data/regras/politica/politica_ficticia.yaml)
(aprovação da escala em 24h; RX-01 em 48h, RX-05 em 30 min e RX-08 em 24h, em relógio simulado).

## 6. Como o produto se generaliza

O produto **não codifica uma política**: a política da empresa e a lei entram como dados ([DEC-010](decisoes.md), RF-22).

**6.1 Camadas de regra (P1, respondida).** (1) **Lei** (EC 141, CLT): o piso. (2) **Convenção coletiva**. (3) **Política da
empresa**: escolhe o que as duas anteriores deixam em aberto. (4) **Parâmetros da unidade**: demanda, quadro, horários. A política
**só restringe** a lei e a convenção, nunca as afrouxa. Em conflito ou ambiguidade, o agente aplica a mais restritiva,
**provisoriamente**, e abre a exceção ao DP.

**6.2 O que é parâmetro e o que é produto:**

| É parâmetro (muda por empresa) | É produto (igual para todas) |
|---|---|
| Jornada semanal e vigência (44h, 42h, 40h) | O solver e o verificador independente |
| Repouso mínimo por semana ou média no mês; regime de domingo | O cartão de regras, sua versão e seu status |
| Interjornada, trabalho noturno, regras de aprendiz | O cartão de exceção e a fila |
| Hora extra: adicional, limite e ordem de preferência | A regra "nada publicado sem aprovação" e "gerente valida a cobertura" |
| Banco de horas, prazos, limite de atraso, destino de cada exceção | Rastro, custo por execução e painel |
| Demanda por faixa, quadro, lojas e horários | O canal (adaptador) e as regras de comunicação |

**6.3 Como uma empresa nova entra `[PROPOSTA]`:** (1) o DP carrega a convenção em PDF e escolhe a vigência; (2) o agente propõe o
cartão com as origens; (3) o DP aprova e resolve as pendências; (4) o gerente submete a escala existente (XLSX, CSV ou PDF) e a
empresa fornece quadro e demanda; (5) o agente otimiza e o gerente confirma, aprova e publica. Nenhum passo exige mudança de código.

**6.4 Verticais e regimes:** varejo, alimentação e farmácia são o alvo (ficha). Regimes diferenciados e 12x36 ficam como regra
**pendente** até haver lei ou convenção (EC 141, art. 7º §3º). O produto não decide interpretação jurídica nem cuida de folha.

**6.5 Na demo:** a rede fictícia (≈3 lojas, ≈60 colaboradores) é **um exemplo de política**. A demo troca a política ou a vigência
ao vivo (FT-07) para provar que o motor não é fixo.

## 7. Papéis e permissões

A **landing page** tem login real e, ao lado, botões de demo que entram com um clique como gerente, DP ou colaboradora, sem digitar
nada ([DEC-017](decisoes.md); o botão cumpre o RE-07, jurado sem cadastro). **Cada papel vê só as telas e as ações dele** (controle
de acesso, RF-29). **O v1 não demonstra isolamento por loja** (gerente só da própria loja, colaborador só da própria escala): fica
como roadmap. A [DEC-015](decisoes.md) (persona sem login, rede toda visível) está substituída nesse ponto. Quem faz o quê está
na seção 4.

## 8. Entradas e saídas consolidadas

| Entrada | De onde vem | Usada em |
|---|---|---|
| Convenção (PDF), lei e política | DP | FT-01, FT-02, FT-03 |
| Escala existente (XLSX, CSV, PDF) | Gerente | FT-02 |
| Quadro de pessoal (com telefone), demanda por faixa, disponibilidade, banco de horas, férias e afastamentos | Empresa, por integração simulada | FT-02, FT-03 |
| Mensagens e comprovações (PDF ou foto) | Colaborador | FT-03 |
| Ponto realizado (simulado) | Sistema de ponto simulado | FT-03 |
| Evento de demanda | Gerente | FT-06 |
| Decisões, confirmações e pedidos de edição | Gerente e DP | FT-02, FT-04 |

| Saída | Para quem | Gerada em |
|---|---|---|
| Cartão de regras versionado e pendências | DP | FT-01 |
| Resumo de leitura; escala em rascunho, aprovada e publicada (versionada); antes e depois com economia | Gerente, colaboradores | FT-02, FT-04 |
| Comparativo de vigência | Gerente, DP | FT-07 |
| Registros, avisos, mensagens curtas, abono provisório, resumo de evento | Gerente, colaborador, DP | FT-03 |
| Cartão de exceção | Gerente ou DP | FT-04 |
| Painel de impacto, auditoria e trace | Gerente, DP, jurado | FT-05 |

## 9. Capacidade e limites do produto

- **Tamanho-base da demo:** ≈3 lojas e ≈60 colaboradores (PDF§6). Tamanho máximo do produto: `[PREENCHER, a medir]`.
- **Tempo do solver** (gerar e replanejar), **custo por execução** e **evals:** a medir na etapa técnica (Q5 de [requisitos.md](requisitos.md)).
- **O que o produto não faz (v1):** folha, férias, benefícios, holerite, decisão sobre pessoas, parecer jurídico, PDF escaneado
  como escala `[PROPOSTA]`, isolamento de dados por papel.

## 10. Decisões P1 a P7

| # | Decisão | Resposta |
|---|---|---|
| P1 | A política só restringe a lei e a convenção? | **Sim.** Em conflito ou ambiguidade vale a mais restritiva, provisória, com exceção ao DP ([DEC-014](decisoes.md)) |
| P2 | O abono é provisório até o DP confirmar? | **Sim** ([DEC-015](decisoes.md)) |
| P3 | Gerente e DP não conversam em texto livre? | **Em parte:** o gerente escreve pedidos de edição ao agente ([DEC-014](decisoes.md)). Para o DP: `[PREENCHER]`. O gerente também conversa em leitura com o agente do FT-08 ([DEC-017](decisoes.md)) |
| P4 | Prazo é da política e vencido escala ao próximo? | **Sim:** escala ao próximo decisor e, sem ninguém, turno descoberto ([DEC-014](decisoes.md)) |
| P5 | O agente revalida a edição do gerente? | **Sim**, e bloqueia a que viola regra dura; exceção ao DP ([DEC-015](decisoes.md)) |
| P6 | Quais features entram no v1? | FT-01 a FT-05 e FT-07; FT-06 desejável ([DEC-013](decisoes.md)) |
| P7 | A regra de autonomia (RH-05) vale? | **Não.** O colega confirma e o gerente valida sempre; o RH-05 está substituído ([DEC-014](decisoes.md)) |

## 11. O que o usuário listou no início (arquivo temporário `features.md`, não versionado, já apagado pelo usuário)

- **#1 Otimização de escala.** Otimizar pensando no menor custo e na maior cobertura. Recebe a escala atual **em qualquer formato**,
  padroniza, estrutura dados e variáveis, usa ferramentas com os critérios e o contexto da empresa e pesquisa operacional, e
  prepara a nova escala.
- **#2 Acompanhamento de escala.** Acompanhar presença, horas e faltas, gerar registros e avisos e remanejar de forma otimizada.
  Agente **passivo e ativo**. Ativo: identifica atraso, falta ou hora extra, comunica o funcionário, recebe justificativa (ou não),
  comunica o gestor, gera registro e aviso e, se precisar remanejar, dispara um gatilho com o detalhe para o agente da escala.
  Passivo: o funcionário avisa e envia a justificativa (com comprovação, como um atestado); o agente valida, comunica o gestor e
  segue o mesmo caminho.
- **#3 Sazonalidade e demanda** ("talvez, se viável"; como funciona: a definir). Levar em conta a sazonalidade e eventos que pedem
  mais gente, como fator da otimização.

## 12. Pendências, contradições e o que foi para a etapa técnica

**Ficou `[PREENCHER]`:**

1. Critério da reotimização semanal (FT-02): o usuário disse "ainda a definir".
2. O que dispara o "aviso de necessidade de hora extra" e quem o recebe (RF-28); o que o agente faz além de avisar quando a hora
   extra estoura (RF-27).
3. Regra de ajuste do FT-06 (cortável).
4. Opções de cada exceção, os 3 tipos de exceção da demo, os prazos e o limite de atraso: saem da **política fictícia da demo**
   (DEC-010), que ainda não existe.
5. Texto livre do DP com o agente (P3).
6. Prioridade de RF-26 (pedido de edição em texto); RF-25 entra na ordem de corte (último), então é v1 cortável `[DERIVADO]`.
7. **RF-13 (fechamento com o ponto, S):** não foi tratado na entrevista; os gatilhos de atraso e hora extra do FT-03 cobrem parte. O
   relatório de desvios antes da folha: manter como desejável ou cortar `[PREENCHER]`.
8. FT-07 só em esboço derivado.

**Ainda `[PROPOSTA]`, sem confirmação:** troca de turno cortável; regras de comunicação (5.3); entrada de empresa nova (6.3);
aviso semanal no app; PDF e convenção só digitais; a regra provisória enquanto o DP não decide (FT-01).

**Empurrado para a etapa técnica (a técnica tratou quase tudo em [arquitetura.md](arquitetura.md), [DEC-018](decisoes.md) a [DEC-021](decisoes.md); segue aberto: hospedagem, o tempo do solver, que só se mede com código, e o tamanho máximo e a capacidade da fila):** hospedagem e link público estável (Q3); mínimo de evals (Q5); tempo do solver, tamanho máximo e
capacidade da fila; como ler PDF, foto e convenção (OCR, visão, custo do modelo) e a regra de não persistir imagem nem CID; agendador
da verificação semanal; simulador do ponto e relógio de demo; stack, solver e Langfuse (RN-02 pede tela no app).

**Contradições com requisitos aprovados, todas decididas pelo usuário e já refletidas em [requisitos.md](requisitos.md):** RF-03
ampliado; RH-05 substituído; RF-09 de S para M; RF-14 com métrica trocada; RF-16 com os 3 gatilhos; RF-19 e RF-20 de C2 e C3 para M;
conflitos 2 e 6 resolvidos; ordem de corte do PDF substituída. **O v1 ficou bem maior que o plano original** (risco G2 na
[ficha](ideacao/ideias/IDEA-002-escalista.md)); a ordem de corte da seção 2 é a salvaguarda.

## 13. Entradas do usuário depois da aprovação (2026-11-07 14:52)

O usuário enviou requisitos de gestor, de trabalhador e não funcionais depois do "aprovado". Estão em
[requisitos.md, seção 10](requisitos.md) (RF-29 a RF-42, RN-12 a RN-14), nas palavras dele. As 3 contradições foram decididas
em 14:57 ([DEC-017](decisoes.md)): o efeito está nas seções 2, 3 (FT-03, item 5), 5 e 7 e na tabela abaixo. **FT-02 e FT-03 não
foram reescritos** para os novos fluxos (reotimizar quando quiser, quadro e horários, agenda e motivo do trabalhador) e o FT-08
segue sem detalhe: isso fica para a etapa técnica ou para um novo bloco de negócio, a decidir.

| Entrada | Efeito provável no produto | Situação |
|---|---|---|
| Login por landing page e controle de acesso (RF-29, RF-30) | Muda a seção 7 (persona sem login, rede toda visível) e o RE-07 | **Decidido ([DEC-017](decisoes.md))** |
| Conversa somente leitura do gestor com o agente (RF-31) | Feature nova; muda o P3 e a frase "o produto não é um chat" | **Decidido ([DEC-017](decisoes.md))** |
| Conferir se o número é de trabalhador (RF-42) | Muda o RX-10 e o RF-12 (persona de demo para número desconhecido) | **Decidido ([DEC-017](decisoes.md))** |
| Reotimizar quando quiser, definir quadro e horários (RF-33, RF-36) | FT-02: novo gatilho manual e cadastro de quadro e horários | Prioridade decidida ([DEC-017](decisoes.md)): v1 ou desejável, ver [requisitos.md](requisitos.md), seção 10 |
| Gestor diz quando a demanda muda (RF-34) | = FT-06, que era o 1º corte | Revisar a ordem de corte |
| Agenda, motivo, questionar, consulta futura e aprovação de remanejo do trabalhador (RF-37 a RF-41) | FT-03 e canal: novos fluxos do trabalhador | Prioridade decidida ([DEC-017](decisoes.md)): v1 ou desejável, ver [requisitos.md](requisitos.md), seção 10 |
| Segurança contra injeção de prompt, LGPD ampliada, tom configurável (RN-12 a RN-14) | Transversais; RN-06 se estende | A confirmar; mínimos na etapa técnica |
| Bloqueio do número do WhatsApp (Q9) | Etapa técnica, junto da ponte (RF-21, cortável) | Sem resposta |
