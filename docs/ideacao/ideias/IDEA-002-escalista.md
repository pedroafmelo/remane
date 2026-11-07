# IDEA-002 · Escalista: digital worker de escala e jornada

> Ficha de ideia. Origem: [proposta_escalista_converge_1.pdf](../../proposta_escalista_converge_1.pdf) (documento de
> trabalho de 07/11/2026, versão 2), com os fatos corrigidos na Etapa 0 de 07/11/2026. Status e pontuação ficam em
> [backlog-ideias.md](../backlog-ideias.md), não aqui. Rótulos: **[FATO]** (com fonte), **[INFERÊNCIA]**, **[HIPÓTESE]**. O PDF é base, não a fonte da verdade ([DEC-010](../../decisoes.md)).

Última atualização: 2026-11-07 13:10 · Autoria: time (proposta); registro por Claude

**Escolhida como direção (provisória)** em [DEC-003](../../decisoes.md); concorre ao Desafio Tako (frente DP). Filtros
eliminatórios e rubrica ainda não foram aplicados: o Gate 2 faz isso. Pontuação no [backlog](../backlog-ideias.md).

## Em uma frase

Um digital worker que monta, otimiza, mantém e audita a escala de trabalho de uma operação com turnos, dentro da CLT, da
convenção coletiva e da EC 141, e cobre faltas conversando com a equipe pelo WhatsApp; o gerente aprova a escala e decide só
as exceções. Quem paga (hipótese): diretoria de operações ou de RH/DP.

## Problema

- **Quem sofre e com que frequência:** o gerente de unidade, que refaz a escala toda semana numa operação que muda todo
  dia (faltas, atestados, picos). Frequência semanal e diária. **[HIPÓTESE]**: não há conversa com cliente nem fonte.
- **Quanto custa não resolver (tempo, dinheiro, risco):** [PREENCHER]. O PDF cita hora extra cara, turno descoberto e
  passivo trabalhista, sem número. O tempo do gerente por escala é premissa do time e deve aparecer rotulado na tela.
- **Urgência (o que já fazem para evitar):** [PREENCHER]
- **Como resolvem hoje sem nós:** planilha e mensagens soltas no WhatsApp, sistema de ponto que só registra e consultoria
  **[HIPÓTESE]**, sem fonte. Fornecedores de ponto e RH já publicam conteúdo sobre 6x1; pesquisa de concorrência na Etapa 2.

## Mercado e negócio

- **Quem paga e de qual orçamento:** diretoria de operações ou de RH/DP **[HIPÓTESE]**. Orçamento: [PREENCHER].
- **Tamanho do mercado (faixa, âncora, fonte e data):** [PREENCHER]. Âncora disponível, que **não é tamanho de
  mercado**: cerca de 14,9 milhões de trabalhadores em 6x1, de 44,7 milhões com jornada identificada, segundo levantamento
  do MTE citado pela [Agência Senado](https://www12.senado.leg.br/noticias/materias/2026/10/16/congresso-promulga-o-fim-da-escala-6x1-e-aposentadoria-de-agentes-de-saude)
  em 16/10/2026 **[FATO reportado, fonte secundária]**. O dataset e a data de referência não são informados; a CUT fala
  em 14,8 milhões, só celetistas. Não foi encontrada a publicação primária do MTE.
- **Why now:** a [EC 141](https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm) foi promulgada em
  16/10/2026 e publicada no DOU de 16/10/2026, edição extra **[FATO]**. Dois repousos semanais e 42h semanais após
  "2 meses da publicação" (≈16/12/2026), e 40h um ano depois disso (≈dez/2027): datas de calendário são conta nossa
  **[INFERÊNCIA]**. Redução salarial vedada, inclusive pisos (art. 2º) **[FATO]**. Custo da hora, com salário mensal fixo:
  +4,8% em 42h (44/42) e +10% em 40h (44/40), **conta nossa [INFERÊNCIA]**; não vale para quem já trabalha 40h ou
  menos nem para horista.
- **Modelo de receita (hipótese):** cobrança por colaborador escalado por mês **[HIPÓTESE]**. Preço: [PREENCHER], sem
  número inventado.
- **Concorrência e diferencial defensável:** [PREENCHER]. O diferencial declarado no PDF é o solver com a regra citada
  por cláusula e o canal com o trabalhador; falta pesquisa.
- **Caminho de crescimento:** o canal com o trabalhador como porta para o resto do DP (holerite, férias, benefícios) e novas
  regras (convenções, regimes diferenciados) **[HIPÓTESE]**.

## O agente

- **Papel e escopo:** monta, otimiza, mantém e audita a escala; coordena a equipe pelo WhatsApp. Escopo: as unidades e
  equipes de um cliente. **Não pode:** contratar, desligar, alterar salário, punir, recusar atestado, guardar diagnóstico ou
  mudar regra sem aprovação.
- **Entrada:** quadro de pessoal (com telefone), demanda por faixa horária, disponibilidade, banco de horas, férias e
  afastamentos, convenção coletiva (fictícia), EC 141 e CLT. **Saída:** escala otimizada e publicada, diagnóstico de custo e
  cobertura, turno de falta coberto, fila de exceções com opções e custo.
- **Fluxo ponta a ponta:** (1) cartão de regras versionado, com trecho de origem, aprovado uma vez pelo DP; (2) entrada de
  dados; (3) validação determinística; (4) solver (OR-Tools CP-SAT) com restrições duras, otimizando cobertura, hora extra e
  preferências; (5) diagnóstico, inclusive contratações que faltam; (6) aprovação do gerente e publicação pelo WhatsApp;
  (7) operação diária (falta, atraso, atestado, troca) com replanejamento parcial e oferta de turno; (8) fechamento contra o
  ponto realizado (mock); (9) trace e painel.
- **Ferramentas e sistemas (reais ou simulados):** ponto e HRIS simulados; WhatsApp real via whatsapp-web.js (não oficial) e
  simulador de celular atrás do mesmo adapter. Ferramentas do agente no PDF: ler_regras, gerar_escala, replanejar,
  ler_atestado, oferecer_turno, consultar_ponto, enviar_mensagem, abrir_excecao.
- **Onde o modelo pequeno basta e onde precisa do grande:** pequeno para mensagens; grande só para regras, atestados
  difíceis e exceções. O solver calcula; o LLM interpreta e explica. Custo: o medido no trace.

## Exceções

1. **Cláusula da convenção em conflito com a EC 141.** Evidência: trecho da cláusula e artigo da emenda. O PDF propõe
   aplicar a mais restritiva e alertar o DP; o art. 3º da EC diz que, após 2 meses, cláusulas incompatíveis ficam "sem
   efeito". **[HIPÓTESE]** jurídica: a regra fica pendente para o DP.
2. **Falta sem substituto dentro da regra.** Opções com custo: hora extra, remanejamento entre lojas ou turno descoberto.
3. **Atestado ilegível ou com data inconsistente.** O agente não recusa: sinaliza ao DP.
4. Outras do PDF: demanda acima da capacidade legal (recomenda contratação), aprendiz em turno noturno, troca que viola
   a interjornada, ninguém aceita o turno, número fora do quadro, regime 12x36 ou cláusula ambígua. Detalhar na Etapa 3.

## Humano no loop

Atos que **exigem aprovação humana**: publicação da escala (gerente); mudança de regra (DP); advertência, desconto, recusa
de atestado e qualquer decisão sobre pessoas (humano, sempre).
Autonomia do agente: o PDF deixa o agente cobrir um turno sem o gerente. **Padrão adotado até decisão contrária: só sem
hora extra e dentro de todas as regras; qualquer hora extra vai ao gerente.** [PREENCHER: confirmar com o time.]

## Dados sintéticos e integrações simuladas

- **O que geramos e como:** rede fictícia (≈3 lojas, ≈60 colaboradores), demanda por faixa de 30 minutos com
  sazonalidade semanal, convenção coletiva fictícia em PDF, atestados sintéticos com ruído e ponto com desvios plantados.
  Tudo gerado no evento, 100% fictício, a declarar na submissão.
- **Mocks que o agente realmente chama:** ponto e HRIS. WhatsApp: ponte real, com simulador como plano B.

## Demo de 3 minutos e teste do jurado

- **Roteiro:** (1) trocar a regra de 44h para 42h e ver a nova escala, o impacto em custo e em contratações; (2) a colaboradora
  manda o atestado pelo WhatsApp, um colega cobre o turno e o gerente recebe o resumo; (3) uma exceção com opções e aprovação.
  Link público com rede pré-carregada; o jurado faz o gerente na tela ou a colaboradora no WhatsApp.
- **Caso difícil de propósito:** [PREENCHER]
- **Pendente:** o jurado pode enviar dado pessoal real ao número do bot. Padrão: aviso "use só dado fictício" e não
  persistir a imagem.

## Medição

- **Evals:** 30 cenários de escala com violação plantada e eventos difíceis, mais atestados sintéticos; métricas: violações
  não detectadas (meta zero), cobertura, custo contra a planilha e acerto na leitura do atestado (proposta do PDF).
- **Custo e latência por execução:** a medir no trace (Langfuse). Latência do solver e do replanejamento: **[HIPÓTESE]**, a
  medir.
- **Ganho versus o manual:** premissa do time, rotulada na tela. [PREENCHER]

## Riscos, premissas e cortes

- **Risco de execução:** alto **[INFERÊNCIA]**: ponte não oficial do WhatsApp (banimento, queda de sessão, servidor sempre
  ligado com Chromium), solver com regras jurídicas reais e muitas peças em cerca de 11 horas. Mitigação do PDF: simulador.
- **Premissas a validar:** regras da CLT (interjornada, aprendiz, folga dominical) conferidas na fonte; folga modelada como
  média compensável por convenção (art. 7º, §2º) e não como "2 por semana" fixo; CP-SAT resolve ≈60 pessoas com replanejamento
  rápido; OCR barato basta para a maioria dos atestados.
- **Se o tempo apertar, cortamos** (ordem do PDF): atraso proativo, lembretes e consulta; atestado por imagem; leitura da
  convenção em PDF (usar YAML); WhatsApp real (só simulador); polimento. **Não cortamos:** exceções, rastro, evals.

## Pergunta mais dura do jurado e nossa resposta hoje

"Por que o gerente pagaria por isso se já usa planilha e um sistema de ponto?" Resposta hoje: [PREENCHER]. Sem cliente
ouvido e sem pesquisa de concorrência, a resposta é **[HIPÓTESE]**.

## Fontes

- Proposta (PDF), 07/11/2026: [proposta_escalista_converge_1.pdf](../../proposta_escalista_converge_1.pdf).
- EC 141, texto: https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm (lido em 07/11/2026, por subagente,
  com citações curtas; conferir o artigo antes de citar literalmente).
- Agência Senado, 16/10/2026: https://www12.senado.leg.br/noticias/materias/2026/10/16/congresso-promulga-o-fim-da-escala-6x1-e-aposentadoria-de-agentes-de-saude
- Agência Câmara, 16/10/2026: https://www.camara.leg.br/noticias/1311797-congresso-promulga-emenda-que-acaba-com-escala-6x1-e-estabelece-jornada-maxima-de-40-horas-semanais
- CUT, 22/09/2026 (14,8 milhões, só celetistas): https://www.cut.org.br/noticias/escala-6x1-atinge-quase-15-milhoes-flavio-bolsonaro-e-contra-aprovacao-da-pec-0511/
- **Não encontrado:** publicação primária do MTE com o número de 6x1; dataset e data de referência; fonte para preço,
  tamanho de mercado e concorrência; verificação da matéria "JUS Braziliense, 15/10/2026" citada no PDF; conferência das
  regras da CLT e do ECA citadas no PDF.
