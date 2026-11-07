> **ARQUIVADO em 07/11/2026.** Material da IDEA-001 (recuperação de depósitos judiciais), preservado para consulta. A ideia não é mais a escolhida; ver [DEC-001](../../decisoes.md) e a [ficha](../../ideacao/ideias/IDEA-001-recuperacao-depositos.md). Só os links relativos foram ajustados.

# Pesquisa: mercado, base legal, autonomia e custo

Pesquisa de preparação (07/11/2026). Rótulos: **[FATO]** tem fonte numerada, **[INFERÊNCIA]** é raciocínio do time,
**[HIPÓTESE]** precisa ser validada.

**Limites.** Só o guia do hackathon foi lido na íntegra. As demais fontes vieram de resultados de busca, não de
leitura integral. A wiki oficial da API do DataJud devolveu HTTP 403 e não foi lida. Números de mercado variam
entre reportagens: use sempre faixa com fonte, nunca um número único como fato.

## 1. Tamanho do problema

| Dado | Valor | Fonte | Observação |
|---|---|---|---|
| Esquecido em contas judiciais da Justiça do Trabalho (BB e Caixa, processos arquivados) | ~R$ 21 bi (reportagens de mar/2024) | [1] | Os totais variam: R$ 20 bi achados até 2021 e R$ 12,1 bi repassados a credores; outra reportagem fala em R$ 10,5 bi devolvidos de R$ 16 bi. Não há número único confiável |
| Quem é o dono do dinheiro (JT) | Maioria são reclamadas, isto é, empresas ou pessoas processadas | [1] | Sustenta a tese "empresa como cliente" |
| Caixa: repasse ao Tesouro de depósitos retidos | > R$ 12 bi; mapeou R$ 14,9 bi irregulares, parte sem nome ou CNPJ | [2] | Reportagens, não documento oficial |
| TCU | Em mar/2025 deu 90 dias à Caixa para plano de classificação correta de depósitos | [2] | Sinal de pressão regulatória |
| Valores a receber em bancos (SVR, Banco Central) | R$ 13,35 bi devolvidos até dez/2025; ~R$ 7,97 bi de pessoas físicas a receber | [3] | Contas bancárias, não depósitos judiciais [INFERÊNCIA]. Fontes divergem entre datas |
| Precatórios e RPV não levantados (Lei 13.463/2017) | Cancelamento automático declarado inconstitucional (ADI 5755, 6 a 5) | [4] | Modulação dos efeitos **não confirmada** |
| EUA (unclaimed property) | Estados devolveram US$ 4,25 bi no FY2025 (primário) | [5] | "~US$ 70 bi retidos" é fonte secundária; o primário não foi localizado |
| Reino Unido | £ 2,1 bi transferidos e £ 1,1 bi pagos ao fundo de causas sociais desde a origem do Dormant Assets Scheme | [6] | Fundo de instituições financeiras. Court Funds Office tem prazo de 30 anos para reclamar. Total não encontrado |

**Recuperável vs parado [INFERÊNCIA]:** nenhum número público separa as duas coisas. A fração recuperável depende de
(i) existir titular identificável, (ii) o prazo legal não ter corrido, (iii) o processo estar apto ao levantamento.
Validar com dados do cliente. [HIPÓTESE]

## 2. Por tipo de entidade

| Entidade | A dor existe? | Quem paga | Generaliza? |
|---|---|---|---|
| **Empresas** | Sim. Depósitos corrigidos pela Selic [7]; maioria dos titulares na JT são reclamadas [1] | A empresa, por êxito | **Alta** |
| **Escritórios** | Sim. Mercado de recuperação por success fee já existe [7] | O escritório (SaaS ou por processo) | **Alta** |
| **Entes públicos** | Sim, com critérios por ente. Na União, a Lei 14.973/2024 manda ao Tesouro depósitos não levantados em 2 anos [2] | Procuradorias; compra pública lenta [INFERÊNCIA] | **Média** |
| **Bancos** | Depositário, não dono do dinheiro. Pressão por classificação correta [2] | Improvável | **Baixa como cliente** |
| **Pessoas físicas** | Sim (precatórios, RPV, alvarás), mas o SVR é gratuito [3] | Ticket baixo, CAC alto [INFERÊNCIA] | **Média-baixa** |

## 3. Marco legal (o que é comum e o que muda)

- **Comum [FATO, parcial]:** depósitos ficam em instituição financeira oficial (LC 151/2015) [8]. O dinheiro pertence
  às partes, não ao banco nem ao tribunal. Em processos arquivados, tribunais têm rotinas de busca (na Justiça do
  Trabalho, o Projeto Garimpo, criado pelo Ato Conjunto CSJT 1/2019) [1][8]. Saldos sem titular localizável viram
  receita da União [1].
- **Justiça Federal:** depósitos não levantados em 2 anos da intimação vão à Conta Única do Tesouro (Lei
  14.973/2024). A Portaria MF 1.430/2025 regulamenta e define o IPCA como correção para depósitos a partir de
  01/01/2026; o IPCA é contestado na ADI 7905. Há ainda a Portaria MF 545/2026, **não verificada** [2].
- **Prescrição e prazos:** não há prazo único e confiável. Há decisões aplicando prescrição vintenária a expurgos
  em depósitos [8] e o STJ fixou prescrição quinquenal para nova requisição de precatório cancelado [4]. **Validar
  com advogado antes de codificar qualquer prazo como regra do agente.** [HIPÓTESE]
- **Não pesquisado:** CPC arts. 906 e seguintes (levantamento) e LC 172/2020.

## 4. Dados: o que é público e o que não é

| Dado | Público? | Observação |
|---|---|---|
| Classe, assuntos, órgão julgador, movimentos, datas | Sim, via API pública do DataJud (Elasticsearch, um índice por tribunal, chave pública no cabeçalho `Authorization: APIKey`) | Fontes secundárias [9]. Wiki oficial não lida (403) |
| Partes e CPF/CNPJ | Segundo fontes secundárias, não | O filtro por partes depende de dado do cliente [INFERÊNCIA] |
| Documentos dos autos (inteiro teor) | Não pela API | Exige credencial do cliente |
| Saldo do depósito | Não está no DataJud [INFERÊNCIA, não verificado] | Vem de extrato do cliente, do banco ou do tribunal |
| Movimento "Arquivamento Definitivo" | Sim | Na TPU, movimento 861 com complemento 246. "Baixa definitiva" é o código 22. Tribunais podem usar códigos locais [10] |

**Consequência:** a parte pública cobre bem *status processual e arquivamento*, mas não *saldo*, *partes* nem
*documentos*. A tese é "o cliente traz a lista dos depósitos e o agente cruza com dado do tribunal". No demo, tudo
é sintético e o tribunal é simulado.

## 5. Concorrência

**[FATO, 7]** Há escritórios e empresas que localizam e levantam depósitos judiciais e recursais, quase sempre por
success fee (Exitum, Numexato, Lotti e Araújo, Aurum/Themis, Recoup, Localiza Valor). Pessoas físicas são
atendidas por serviços como Meu Valor e LOVA. O gargalo operacional é o desarquivamento e a expedição de alvará,
que dependem do Judiciário. Um fornecedor declara R$ 25 bi recuperados desde 1997 (autodeclarado, não verificado).

**Não encontrado:** percentuais típicos de success fee, avaliações de mercado.

**[INFERÊNCIA]** O diferencial defensável é *custo por processo e autonomia medida*, não acesso a dados. A banca
pode perguntar "por que um escritório não faz isso com estagiários?".

## 6. Abordagens de autonomia

Os estudos citados vêm de resumos de busca, não de leitura integral.

| Abordagem | Maturidade | Esforço | Risco | Adequação ao hackathon |
|---|---|---|---|---|
| **A. Regras a partir de documentos de política** (extração para regra executável com LLM e verificador) [11] | Média | Médio | Médio (falha em cadeias de exceção) | **Alta**: ler uma política e gerar o cartão de regras |
| **B. Aprendizado de exemplos rotulados** | Alta em ML clássico | Médio (exige rótulos) | Médio | Média: rótulos sintéticos são prova fraca |
| **C. Agente que entrevista o cliente** | Média | Baixo a médio | Baixo se a saída for revisada | **Alta**, boa de mostrar |
| **D. Indução de regras / síntese de programa** | Baixa a média | Alto | Alto | Baixa para 11 h |
| **E. LLM-as-judge com rubricas geradas** | Média | Baixo | Médio (herda viés do modelo) | **Alta como eval**, não como decisor financeiro |
| **F. "Zero-config" combinado (A + C + E, revisão por exceção)** | Baixa para "zero" de fato | Médio | Médio | **Recomendada**, prometendo "configuração em minutos com aprovação" |

"Zero-config" total em contexto jurídico-financeiro é marketing, não realidade madura.

**Padrões de segurança:** humano por exceção, roteamento por incerteza (predição conforme e abstenção seletiva:
Prune 'n Predict, Conformal Selective Abstention, commCP [12]; as garantias assumem permutabilidade dos dados),
auto-verificação dos campos contra o texto-fonte, guardrails e trilha de auditoria.

## 7. Custo

| Estratégia | Ordem de grandeza | Observação |
|---|---|---|
| Filtrar antes de gastar (regras determinísticas, metadados) | Provavelmente a maior alavanca [HIPÓTESE] | Custo zero por processo descartado |
| Selecionar páginas relevantes antes de OCR e LLM | Reduz o volume de páginas de forma significativa [HIPÓTESE] | Medir no demo |
| Cascata de modelos (pequeno primeiro, grande só na dúvida) | FrugalGPT reporta até 98% menos custo, ou +4% de acurácia ao mesmo custo, **como melhor caso em benchmarks** [13] | Em outra carga pode ser bem menos |
| OCR de baixo custo | OCR básico em nuvem ~US$ 1,50 por 1.000 páginas (Textract, Google, Azure). Open source em GPU: US$ 0,05 a 1,06 por 1.000 páginas, medido em recibos, não em documentos jurídicos [14] | [INFERÊNCIA] Para 300 páginas o OCR básico custa ~US$ 0,45. O LLM costuma pesar mais. Validar |
| Modelos open source via Featherless (créditos do evento) | Suficientes para o demo [guia] | Permite "custo por processo em centavos" |

## 8. Métricas de autonomia

Os benchmarks encontrados são de blogs de fornecedores, não padrões [15]. Use métricas próprias: taxa de
intervenção, STP (straight-through processing), precision@k e recall ponderado por valor, **decisões erradas sem
revisão (a mais importante)**, calibração, custo por processo e tempo ponta a ponta. Blogs citam 35 a 40% de
escalonamento como alerta de cobertura baixa: regra empírica, não padrão.

## 9. Riscos jurídicos e éticos

- **LGPD e sigilo processual:** a publicidade processual é regra (Res. CNJ 121/2010), mas o tratamento de dados
  pessoais continua sujeito à LGPD; há tensão doutrinária e não encontrei orientação específica da ANPD [16].
  Dados sintéticos eliminam o risco no demo.
- **Segredo de justiça:** processos sigilosos não aparecem na API pública. Não tentar contornar.
- **Responsabilidade profissional (OAB):** a Recomendação 001/2024 trata a IA como apoio e mantém a
  responsabilidade com o advogado [17]. O agente prepara, não decide nem peticiona.
- **Resolução CNJ 615/2025:** regula IA *no Judiciário* [18]. [INFERÊNCIA] Não se aplica diretamente a um agente
  privado, mas indica a direção regulatória.
- **Erro financeiro:** falso positivo pode gerar petição indevida; falso negativo deixa dinheiro parado. Limiares
  devem refletir essa assimetria.
- **Exercício da advocacia:** a startup não pode se apresentar como quem levanta o dinheiro. O modelo é vender
  ferramenta a escritórios e departamentos jurídicos, ou operar com advogado parceiro. [HIPÓTESE]
- **Transparência no evento:** declarar modelos e APIs, e que dados e camada de tribunal são sintéticos e simulados.

## 10. Fontes (acesso em 07/11/2026)

Com exceção do guia, as fontes foram consultadas por resultados de busca.

1. Justiça do Trabalho (~R$ 21 bi): https://www.correiodamanha.com.br/nacional/2024/03/122907-justica-do-trabalho-procura-donos-de-rs-21-bi-esquecidos.html · https://www.bahianoticias.com.br/folha/noticia/270171-justica-do-trabalho-procura-donos-de-r-21-bi-esquecidos-em-contas-judiciais · https://diariodocomercio.com.br/legislacao/justica-procura-donos-21-bi-esquecidos-contas-judiciais/
2. Caixa, TCU e Lei 14.973/2024: https://www.poder360.com.br/economia/caixa-diz-que-repassara-r-126-bilhoes-ao-tesouro-nacional/ · https://www.band.com.br/economia/noticias/tcu-da-90-dias-para-caixa-elaborar-plano-sobre-classificacao-correta-de-depositos-judiciais-202503262000 · https://www.pwc.com.br/pt/consultoria-tributaria-societaria/thinking-about-taxes/tax-legis/2024/depositos-judiciais-e-extrajudiciais---alteracoes---lei-federal-.html · https://www.lex.com.br/portaria-mf-no-1-430-de-4-de-julho-de-2025/ · https://www.demarest.com.br/portaria-mf-n-o-1-430-2025-e-os-reflexos-na-correcao-dos-depositos-judiciais-federais-pelo-ipca/
3. Valores a receber (SVR): https://jovempan.com.br/noticias/economia/mais-de-49-milhoes-de-pessoas-podem-resgatar-dinheiro-esquecido-veja-como.html · https://www.opovo.com.br/noticias/economia/2025/12/09/valores-a-receber-mais-de-50-milhoes-de-beneficiarios-tem-rs-99-bilhoes-em-bancos.html
4. Lei 13.463/2017 e ADI 5755: https://www2.camara.leg.br/legin/fed/lei/2017/lei-13463-6-julho-2017-785161-publicacaooriginal-153301-pl.html · https://www.ibet.com.br/cancelamento-de-precatorio-sob-lei-de-2017-so-vale-com-inercia-do-credor/ · https://informativos.trilhante.com.br/julgados/stj-resp-1961642-ce
5. NAUPA FY25: https://unclaimed.org/wp-content/uploads/NAUPA-FY-25-Report.pdf
6. Reclaim Fund Ltd, relatório anual 2025: https://assets.publishing.service.gov.uk/media/687669a888da2e5804bb6a8f/RFL_AR2025.pdf · Court Funds Office: https://gov.uk/government/consultations/a-consultation-on-the-implementation-process-for-applying-a-30-year-time-limit-for-claims-on-the-unclaimed-balances-fund
7. Mercado de recuperação de depósitos: https://www.exitumpse.com.br/site/ · https://numexato.com.br/blog/recuperacao-de-depositos-judiciais-e-recursais/ · https://www.lotti.com.br/recuperacao-depositos-judiciais-recursais/ · https://www.aurum.com.br/blog/departamento-juridico-recuperou-milhoes-com-o-themis/ · https://diariodocomercio.com.br/opiniao/recuperacao-de-depositos-judiciais-e-recursais/ · https://www.recuperameuvalor.com.br/
8. LC 151/2015 e rotinas de arquivados: https://planalto.gov.br/ccivil_03/leis/lcp/lcp151.htm · https://www.klalaw.com.br/?p=21583 · https://www.trt14.jus.br/portal/sites/default/files/2021-08/PROVIMENTO%20N.%2005_2021%20-%20PROJETO%20GARIMPO.pdf
9. API pública DataJud: https://judit.io/blog/apis-dados-juridicos-integracoes/datajud-cnj-api-publica-x-privada-comparacao/ · https://arpensp.org.br/noticia/tjba-cnj-divulga-cronograma-para-saneamento-de-dados-do-datajud · https://www.cnj.jus.br/wp-content/uploads/2023/05/tutorial-api-publica-datajud-beta.pdf · wiki oficial https://datajud-wiki.cnj.jus.br/api-publica/ (não lida, HTTP 403)
10. Movimentos TPU: https://www.cnj.jus.br/wp-content/uploads/2025/09/glossario-mes-juri.pdf · https://portal.tjce.jus.br/uploads/atos-normativos-scon/2022/12/PORTARIA_N_2630_2022_35297.pdf
11. Regras a partir de políticas: https://arxiv.org/abs/2512.04408v1 · https://arxiv.org/abs/2606.32004 · https://arxiv.org/pdf/2609.19199 · https://arxiv.org/pdf/2607.23386 · https://icml.cc/virtual/2026/78632
12. Conformal e abstenção: https://arxiv.org/pdf/2501.00555 · https://ceur-ws.org/Vol-4307/paper33.pdf · https://pypi.org/project/commcp/
13. FrugalGPT: https://arxiv.org/abs/2305.05176
14. Preço de OCR: https://www.erpresearch.com/erp-add-ons/ocr/amazon-textract/pricing · https://www.activepieces.com/blog/google-document-ai-pricing-cost-per-page-2026-guide · https://imagetotable.ai/references/ocr-cost-per-1000-pages-benchmark
15. Métricas de agentes: https://arize.com/agent-evaluation-metrics/ · https://www.workfusion.com/blog/how-to-boost-automation-rates-using-targeted-ai-plus-an-llm/ · https://www.multimodal.dev/post/ai-agent-performance-metrics-for-leaders
16. LGPD e publicidade processual: https://jus.com.br/artigos/92053/protecao-de-dados-pessoais-e-publicidade-processual-estudo-sobre-as-bases-legais-previstas-no-codigo-de-processo-civil-e-na-lei-geral-de-protecao-de-dados · https://vlex.com.br/vid/resolucao-cnj-n-121-592801978
17. OAB, Recomendação 001/2024: https://www.oab.org.br/noticia/62704/oab-aprova-recomendacoes-para-uso-de-ia-na-pratica-juridica
18. Resolução CNJ 615/2025: https://atos.cnj.jus.br/files/original1302412025091268c419f14844f.pdf
19. Guia do Participante do Converge Challenge: https://canastraventures.notion.site/guia-converge-challenge (ver [guia-converge-challenge.md](../../guia-converge-challenge.md))
