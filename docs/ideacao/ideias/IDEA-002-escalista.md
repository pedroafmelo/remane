# IDEA-002 · Escalista: digital worker de escala e jornada

> Ficha de ideia. Origem: [proposta_escalista_converge_1.pdf](../../proposta_escalista_converge_1.pdf) (documento de
> trabalho de 07/11/2026, versão 2), com os fatos corrigidos na Etapa 0 de 07/11/2026. Status e pontuação ficam em
> [backlog-ideias.md](../backlog-ideias.md), não aqui. Rótulos: **[FATO]** (com fonte), **[INFERÊNCIA]**, **[HIPÓTESE]**. O PDF é base, não a fonte da verdade ([DEC-010](../../decisoes.md)).

Última atualização: 2026-11-07 13:18 · Autoria: time (proposta); registro por Claude

**Escolhida como direção (provisória)** em [DEC-003](../../decisoes.md); concorre ao Desafio Tako (frente DP). Filtros e rubrica aplicados em 2026-11-07 13:18: **14/20, risco alto** (proposta do agente, a confirmar pelo time). Pontuação no [backlog](../backlog-ideias.md).

## Em uma frase

Um digital worker que monta, otimiza, mantém e audita a escala de trabalho de uma operação com turnos, dentro da CLT, da
convenção coletiva e da EC 141, e cobre faltas conversando com a equipe pelo WhatsApp; o gerente aprova a escala e decide só
as exceções. Quem paga (hipótese): diretoria de operações ou de RH/DP.

## Problema

- **Quem sofre e com que frequência:** o gerente de unidade, que refaz a escala toda semana numa operação que muda todo dia
  (faltas, atestados, picos). **[HIPÓTESE]**: sem conversa com cliente. Sinal indireto de fornecedor (fonte comercial, sem
  métrica): a Drogaria Araujo gerava escalas "conforme critérios de cada chefe de loja" antes de adotar um sistema
  ([Baguete](https://www.baguete.com.br/noticias/drogaria-araujo-gere-escalas-com-tlantic)).
- **Quanto custa não resolver:**
  - Hora extra: adicional "no mínimo 50%" sobre a hora normal ([CF art. 7º, XVI](https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm)) **[FATO]**;
    convenções podem elevar (80% na CCT de supermercados de BH, 2024, lida via notícia) **[FATO parcial]**.
  - Passivo: horas extras e intervalo intrajornada são os dois temas mais recorrentes no TST em 2024, com 70.508 e 48.283
    processos **julgados** (mede recursos no TST, não todas as ações; sem corte por setor)
    ([TST](https://www.tst.jus.br/radio/-/asset_publisher/0H7n/content/horas-extras-e-intervalo-intrajornada-lideram-ranking-dos-temas-mais-recorrentes-no-tst-em-2024-%7C-boletim-ao-vivo)) **[FATO]**.
  - Impacto da 6x1 no custo: as estimativas divergem muito (Ipea 7,84%; FecomercioSP 22%, sobre o projeto; Abras 15 a 20% na
    folha de supermercados, via terceiro) **[FATO como estimativas contraditórias]**. Nossa conta de +4,8% (42h) e +10% (40h) é
    só o custo da hora contratada, não o custo total **[INFERÊNCIA]**.
  - **Não encontrado:** número público do tempo do gerente por escala; peso das horas extras na folha do setor; taxa neutra de
    absenteísmo (o "7 a 10% no varejo" circulante não tem metodologia: **[HIPÓTESE]**, não usar).
- **Urgência (o que já fazem para evitar):** [PREENCHER]. Sinais: Pague Menos, RD Saúde e Savegnago testam 5x2 com horistas para
  cobrir folgas ([Correio da Manhã, mai/2026](https://www.correiodamanha.com.br/economia/2026/05/284138-varejo-testa-escala-5x2-e-enfrenta-desafios-para-adaptar-operacao.html)) **[FATO, declaração patronal]**.
  No food service, de 132 empresas ouvidas pelo IFB, 91% do quadro está em 6x1, só 9% decidiram como se adaptar e 59% das
  estimativas de impacto são "percepção, sem modelagem formal" ([Mercado & Consumo, 15/10/2026](https://mercadoeconsumo.com.br/15/10/2026/foodservice/ifb-questao-do-fim-da-6x1-agora-e-o-calendario-de-implementacao/amp/)) **[FATO]**.
- **Como resolvem hoje sem nós:** planilha e mensagens, ponto que registra, apps de escala, consultoria. Ver "Concorrência".

## Mercado e negócio

- **Quem paga e de qual orçamento:** diretoria de operações ou de RH/DP **[HIPÓTESE]**, sem validação. Existe orçamento de
  categoria vizinha: fornecedores de ponto cobram por colaborador, com preço publicado (ver "Preço").
- **Tamanho do mercado (âncoras, não é TAM; nenhuma conta de mercado foi feita):**
  - RAIS 2024: 57.132.156 vínculos e 4.700.860 estabelecimentos com empregados; comércio com 10.314.045 vínculos (outras
    reportagens citam 10.571.310) ([Agência Gov](https://agenciagov.ebc.com.br/noticias/202512/rais-de-2024-aponta-crescimento-de-3-3-no-numero-de-empregos-formais-no-pais)) **[FATO, com divergência]**.
  - Farmácias: 29 redes da Abrafarma somavam 11.688 pontos de venda no fim de 2025 ([Mercado & Consumo](https://mercadoeconsumo.com.br/31/03/2026/noticias-varejo/rd-saude-pague-menos-e-drogaria-sao-paulo-lideram-ranking-das-maiores-farmacias-do-brasil/)) **[FATO]**;
    o total de farmácias varia entre cerca de 90 mil e 99.816, conforme a fonte **[FATO, divergente]**.
  - 6x1: cerca de 14,8 a 14,9 milhões de trabalhadores, um terço dos ocupados com jornada identificada (MTE, via
    [Agência Senado](https://www12.senado.leg.br/noticias/materias/2026/10/16/congresso-promulga-o-fim-da-escala-6x1-e-aposentadoria-de-agentes-de-saude)) **[FATO reportado]**;
    incidência de 47,1% em serviços de alimentação e 42,2% no comércio (DIEESE, via
    [CUT](https://www.cut.org.br/noticias/escala-6x1-atinge-14-8-milhoes-de-pessoas-e-pesa-nos-setores-de-servicos-e-comer-cbd9)) **[FATO de segunda mão]**.
  - **Não encontrado:** número de empresas com várias unidades; vínculos por CNAE (varejo, restaurantes, farmácias); número de
    trabalhadores em 6x1 por setor.
- **Why now:** EC 141, promulgada em 16/10/2026 **[FATO, texto no Planalto]**; 42h e dois repousos em "2 meses da publicação"
  (≈16/12/2026) e 40h um ano depois **[FATO]**, com datas de calendário contadas por nós **[INFERÊNCIA]**. Os fornecedores de
  ponto já fazem campanha (o Pontotel tem contagem até 16/12 e FAQ da EC 141) **[FATO]**. Nenhuma pesquisa achada mostra
  empresas planejando comprar software de escala por causa da 6x1: só sinais qualitativos **[não encontrado]**.
- **Preço (âncoras, não é o nosso preço):**
  - Ponto, com preço publicado: Genyo de R$ 3,75 (anual, 51 a 100 colaboradores) a R$ 6,90 (mensal, 1 a 10) por colaborador
    ([Genyo](https://genyo.com.br/?p=30)) **[FATO]**. Pontotel: R$ 153,00 (1 a 10) até R$ 486,54 (1 a 50); a página não diz se é
    por colaborador ou por faixa, o que daria de R$ 15,30 a R$ 9,73 por colaborador **[INFERÊNCIA]** ([Pontotel](https://www.pontotel.com.br/planos.md)).
  - **Escala:** nenhum fornecedor brasileiro de escala achado tem preço publicado confiável (o único com preço, o Shiftflow,
    está em "$" sem moeda confirmada) **[não encontrado]**.
- **Modelo de receita (hipótese):** cobrança por colaborador escalado por mês **[HIPÓTESE]**; preço: [PREENCHER], sem número
  inventado.
- **Concorrência (resumo; tabela completa na pesquisa de 07/11):**

  | Alternativa | O que faz (de acordo com a página do fornecedor) | O que não achamos |
  |---|---|---|
  | Planilha e WhatsApp | O Pontotel e a GeoVictoria vendem a troca da planilha ([Pontotel](https://www.pontotel.com.br/planilha-de-escalas/)) | n/a |
  | **Escala Jornadas** | "Monte escalas 12x36, 6x1, 5x2 seguindo os limites trabalhistas automaticamente"; app do funcionário; trocas e ausências no sistema ([escala.app](https://escala.app)) | Convenção coletiva, WhatsApp, preço, menção à EC 141 |
  | Pontotel (Regularizador) | Aponta infrações, sugere ajustes e aplica a 5x2 com vigência; o gestor aceita ou rejeita. Não é gerador de escala ([Pontotel](https://www.pontotel.com.br/lp/regularizador-de-escalas-e-jornadas)) | Preço |
  | GeoVictoria, Buk | Ponto, turnos e planejamento de quadro; sem escala automática declarada | Preço, otimização |
  | Zebra, Quinyx, Legion, Deputy, UKG | Escala automática por demanda, em fontes externas ([Zebra](https://www.zebra.com/br/pt/software/workcloud-solutions/workcloud-workforce-optimization-suite/workcloud-scheduling.html)) | CLT, convenção coletiva e operação no Brasil |
  | Consultoria e BPO de DP | Conteúdo de diagnóstico | Preço, cases |

  **[INFERÊNCIA]**: o espaço livre pode ser otimização com convenção coletiva, EC 141 e canal de WhatsApp para faltas e trocas;
  nenhum fornecedor achado trata faltas, atestados e trocas pelo WhatsApp (o WhatsApp aparece só como canal comercial e para
  registro de ponto). **Ausência de evidência não é evidência de ausência**; não foram lidas páginas de Ahgora, Sólides,
  Tangerino e Convenia sobre escala.
- **Diferencial defensável:** [HIPÓTESE]. Candidatos: política da empresa parametrizável com cláusula de origem em cada regra
  ([DEC-010](../../decisoes.md)) e replanejamento diário pelo canal do trabalhador. Frágil no curto prazo: um fornecedor de
  ponto já vende "IA sugere ajustes" e pode somar um canal de mensagens.
- **Caminho de crescimento:** o canal com o trabalhador como porta para o resto do DP e novas regras (convenções, regimes
  diferenciados) **[HIPÓTESE]**.

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

## Avaliação (filtros e rubrica de [criterios.md](../criterios.md))

Proposta do agente em 2026-11-07 13:18; o time pontua junto e confirma. Só a IDEA-002 foi avaliada (IDEA-001 está descartada).

**Filtros eliminatórios: nenhum reprova, três passam com condição.**

| # | Filtro | Resultado | Por quê |
|---|---|---|---|
| G1 | IA central, agente que entrega trabalho | Passa, com cuidado | O agente conduz o processo (regras, escala, cobertura de falta, exceções) **[INFERÊNCIA]**. Risco de "IA decorativa": se o solver faz tudo e o modelo só explica. O modelo precisa fazer trabalho real: entender o evento da conversa, montar as opções de uma exceção e extrair regra de uma cláusula |
| G2 | Cabe em ~11 h | **Passa, condicionado** | Restam cerca de 6,5 h de construção (13h30 às 17h de sábado e 8h30 às 12h de domingo) **[INFERÊNCIA]**. Cabe só no recorte do PDF: solver parametrizável, grade, fila de exceções, simulador e trace. Depende do tamanho do time, ainda não registrado **[HIPÓTESE]** |
| G3 | Dados sintéticos honestos | Passa | O guia permite dados sintéticos e integrações simuladas no Desafio Tako **[FATO, guia §3]** |
| G4 | Jurado testa sozinho | **Passa, condicionado** | O link precisa de hospedagem, que o time não tem **[FATO, estado, pergunta 6]**. Ponte real do WhatsApp fica cortável; o simulador é o caminho |
| G5 | Clean room | Passa | Histórico recriado ([DEC-007](../../decisoes.md)); dados e regras são nossos ou públicos. Sem apoio em material de empregador ou cliente **[FATO, declaração do time]** |
| G6 | Humano nos atos de consequência | Passa | RH-01 a RH-06 em [requisitos.md](../../requisitos.md); a premissa de autonomia (RH-05) ainda é provisória |
| G7 | Custo mensurável | **Passa, condicionado** | Ninguém resgatou os US$ 25 da Featherless; o código vence em 08/11 **[FATO, guia §11]**. Custo sai do trace |

**Rubrica (1 a 5):**

| Critério | Nota | Justificativa |
|---|---|---|
| A. Protótipo e aderência | **4** | O desenho fecha o processo, trata exceções com contexto, tem rastro e custo medido **[INFERÊNCIA]**; nada foi construído nem medido, e o teto 5 exige custo e ganho medidos |
| B. Viabilidade como startup | **3** | Dor frequente e why now com fonte **[FATO]**, concorrência mapeada **[FATO]**, âncoras de mercado sem TAM; quem paga e quanto são **[HIPÓTESE]** e não há preço publicado de escala **[não encontrado]** |
| C. Criatividade e originalidade | **3** | Escala automática com CLT já existe **[FATO, Escala Jornadas]**; o ângulo novo (convenção citada por cláusula, política parametrizável, canal WhatsApp) é **[HIPÓTESE]** de diferencial |
| D. Pitch | **4** | Problema conhecido pela banca e demo visual (troca de 44h para 42h muda a escala) **[INFERÊNCIA]**; números medidos só existirão se trace e evals rodarem |
| **Total** | **14 / 20** | **Risco de execução: alto** (ponte não oficial, hospedagem sem solução, muitas peças em ~6,5 h) |

**Pré-mortem, a pergunta mais dura.** "O Escala Jornadas já promete gerar escala automática com a CLT, e o Pontotel vende
'IA sugere ajustes' e já faz campanha da EC 141. Por que um gerente trocaria, e o que impede um fornecedor de ponto de copiar
em um mês?" **Resposta hoje:** o único diferencial candidato é a política parametrizável com origem em cada cláusula e o
replanejamento pelo canal do trabalhador, que não achamos em nenhum fornecedor. Isso é ausência de evidência, não prova, e a
cópia é plausível. Sem conversa com cliente, a resposta é **[HIPÓTESE]**.

**Melhor argumento contra seguir com a IDEA-002:**
1. Execução: muitas peças em ~6,5 h, com hospedagem, créditos e ponte ainda em aberto.
2. Concorrência: já há produto de escala automática com CLT e fornecedores de ponto entrando no tema.
3. Sem validação com cliente: comprador, preço e tempo do gerente são todos hipótese.
4. A onda da 6x1 é pontual; o que fica é a necessidade semanal de escala **[INFERÊNCIA]**.

**Recomendação do agente:** seguir com a IDEA-002. Não há outra candidata avaliada, e trocar de ideia depois das 14h custa mais do
que seguir com uma ideia razoável ([como-ideiar.md](../como-ideiar.md)). A decisão é do time. Para defender melhor, o produto
precisa mostrar na demo o que a concorrência não mostra: política parametrizável e regra com origem.

**O núcleo é o solver ou o WhatsApp?** O solver e a política parametrizável ([requisitos.md](../../requisitos.md), RF-05,
RF-07, RF-22). O WhatsApp (simulado) é a segunda cena e mostra o agente agindo. A demo de 3 min mostra o núcleo nos primeiros
90 segundos. Pitch em [entrega.md](../../entrega.md) (seção 3.1).

## O que ainda é hipótese

| # | Hipótese | Como validar |
|---|---|---|
| H1 | Quem paga é operações ou DP | Uma conversa com gerente ou DP (hoje não há contato externo) |
| H2 | Cobrança por colaborador e por mês; preço: [PREENCHER] | Âncoras de ponto (R$ 3,75 a R$ 6,90) não valem como preço de escala |
| H3 | O gerente perde horas por semana com escala | Nenhum número público; medir em entrevista |
| H4 | Hoje o gerente usa planilha e WhatsApp | Sinal só de fonte comercial |
| H5 | Nenhum fornecedor trata faltas pelo WhatsApp | Ausência de evidência; ler Ahgora, Sólides, Tangerino, Convenia |
| H6 | Diferencial sobre o Escala Jornadas | Ler a documentação do Escala sobre convenção coletiva |
| H7 | CP-SAT resolve ≈60 colaboradores com replanejamento rápido | Medir no primeiro dia de construção |
| H8 | Regras da CLT e do ECA no cartão (interjornada 11h, aprendiz, domingo) | Conferir na fonte antes de entrar no cartão |
| H9 | Interpretação de conflito de cláusula com a emenda | Definir (conflito 2, em aberto) |
| H10 | Existe demanda por software de escala por causa da 6x1 | Nenhuma pesquisa achada; só sinais qualitativos |
| H11 | Hospedagem e créditos de inferência viáveis | Q3 e resgate da Featherless |

## Fontes

- Proposta (PDF), 07/11/2026: [proposta_escalista_converge_1.pdf](../../proposta_escalista_converge_1.pdf) (base, não a verdade: [DEC-010](../../decisoes.md)).
- EC 141, texto: https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm (lido por subagente em 07/11/2026; conferir o artigo antes de citar literalmente).
- Agência Senado e Agência Câmara, 16/10/2026; CUT, 22/09/2026 e 21/05/2026 (links acima e em [requisitos.md](../../requisitos.md)).
- Pesquisas de 07/11/2026 por subagentes sobre dor e custo, concorrência e preço e mercado: as URLs estão nas linhas acima. Várias
  fontes foram lidas só em resumo de busca ou em notícia, e os relatórios originais (BTG, FecomercioSP, Abras, CNC, Abrasce)
  não foram lidos.
- **Não encontrado:** publicação primária do MTE com o número de 6x1; preço publicado de software de escala; tempo do gerente por
  escala; peso da hora extra na folha do setor; passivo trabalhista por setor e por interjornada; nº de redes multiunidade;
  texto compilado dos arts. 59, 66 e 71 da CLT; verificação da matéria "JUS Braziliense, 15/10/2026" citada no PDF.
