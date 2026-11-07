> **ARQUIVADO em 07/11/2026.** Material da IDEA-001 (recuperação de depósitos judiciais), preservado para consulta. A ideia não é mais a escolhida; ver [DEC-001](../../decisoes.md) e a [ficha](../../ideacao/ideias/IDEA-001-recuperacao-depositos.md). Só os links relativos foram ajustados.

# Analista de Recuperação de Depósitos: proposta de projeto

Proposta para o Converge Challenge powered by Tako (tema aberto: AI agents). Documento de trabalho do time,
07/11/2026. Versão em PDF: [proposta_converge_challenge.pdf](proposta_converge_challenge.pdf).

## 1. Posicionamento

Um **digital worker** com cargo definido, que conduz a recuperação de depósitos judiciais de ponta a ponta
para um escritório ou departamento jurídico. O advogado aprova só as exceções e os atos jurídicos. Competimos no
**tema aberto**, não no Desafio Tako (RH).

> "Dinheiro da sua empresa parado em processo arquivado. Um agente que acha, confere e deixa o pedido de alvará
> pronto, e só chama o advogado quando precisa."

- **Cliente:** escritório ou departamento jurídico que hoje faz a triagem à mão. O dono do dinheiro é a empresa,
  e a cobrança é por êxito (o guia pede "quem paga").
- **Por que não o ente público como caso principal:** a Lei 14.973/2024 já manda transferir ao Tesouro depósitos
  federais não levantados em 2 anos, então parte do problema é resolvida por lei.

Cargo do worker (o guia descreve digital worker como tendo função, escopo, metas e responsável):

| Item | Definição |
|---|---|
| Função | Triar e preparar a recuperação de depósitos judiciais |
| Escopo | Uma carteira de depósitos de um cliente |
| Meta | Custo por processo e erros sem revisão |
| Responsável | O advogado |
| Pode | Ler, classificar e redigir minutas |
| Não pode | Protocolar petição nem movimentar dinheiro |

## 2. Por que isso generaliza

A hipótese central: **há dinheiro esquecido em processos arquivados, e dá para recuperá-lo de forma
sistemática**. Ela vale para vários tipos de entidade, mas a dor e quem paga mudam. O projeto tem duas camadas:

- **Núcleo reutilizável (cerca de 55 a 65% do esforço, estimativa nossa):** ingestão e normalização, validação
  do número do processo, enriquecimento via tribunal, leitura de documentos, score, fila de exceções, auditoria
  e evals.
- **Específico por cliente (cerca de 35 a 45%):** critérios de recuperabilidade, fontes de dados e fluxo
  jurídico. O **onboarding por documentos de política** existe para reduzir esse trabalho a cada novo cliente.

| Entidade | A dor existe? | Quem paga | Generaliza? |
|---|---|---|---|
| **Empresas** (depósitos recursais e judiciais) | Sim. Na Justiça do Trabalho, a maioria dos donos do dinheiro esquecido são as reclamadas, isto é, empresas. Cerca de R$ 21 bi esquecidos em contas judiciais (reportagens de 2024) | A empresa, por êxito | **Alta.** Melhor cliente |
| **Escritórios de advocacia** | Sim. Já existe mercado de recuperação por success fee (Exitum, Numexato, Aurum e outros) | O escritório, em SaaS ou por processo | **Alta.** Canal natural |
| **Entes públicos** (União, estados, municípios) | Sim, mas os critérios mudam por ente. Na União, a Lei 14.973/2024 já manda transferir ao Tesouro depósitos não levantados em 2 anos | Procuradorias, com compra pública lenta | **Média** |
| **Bancos** | Outra dor: o banco é depositário, não dono do dinheiro. A pressão é por classificar corretamente os depósitos (TCU deu 90 dias à Caixa em 2025) | Improvável que paguem para "achar dinheiro para entregar" | **Baixa como cliente**; fonte de dados |
| **Pessoas físicas** | Sim (precatórios, RPV, alvarás), mas o Banco Central já oferece o SVR gratuitamente | Ticket baixo, custo de aquisição alto | **Média-baixa** |

**Leitura para o pitch:** o produto serve a empresas e escritórios, que são donos do dinheiro ou o recuperam por
conta de terceiros. A União entra como caso de entrada, não como mercado principal. Referências internacionais
mostram que o problema é global (nos EUA, os estados devolveram US$ 4,25 bi em 2025 via unclaimed property; o
Reino Unido tem o Dormant Assets Scheme), embora sejam sistemas de repasse ao Estado, não o mesmo modelo de
negócio.

**Ressalvas honestas:** os totais variam entre reportagens e não há número consolidado do que é realmente
recuperável; o mercado já é atendido por escritórios com success fee, então o diferencial deve ser custo por
processo e autonomia medida; e o alvará depende do tribunal e de advogado, por isso o agente prepara e o advogado
aprova.

## 3. Processo de ponta a ponta

1. **Onboarding:** o agente lê a política fictícia do cliente e gera um **cartão de regras**, com o trecho de
   origem de cada regra. O humano aprova uma vez.
2. **Entrada:** lote de depósitos (planilha).
3. **Filtros determinísticos:** custo zero.
4. **Verificação no tribunal simulado:** status do processo, via simulador no formato DataJud.
5. **Leitura dos documentos:** OCR barato primeiro; modelo de visão só quando a confiança é baixa.
6. **Score** de recuperabilidade com confiança calibrada.
7. **Roteamento:** o que é seguro segue sozinho; o resto vai para a fila de exceções.
8. **Minuta do pedido de alvará:** fica aguardando aprovação do advogado.
9. **Notificação** e registro completo no trace.

## 4. Exceções

O guia pede que o agente "trate a exceção de verdade". Cada item vira um caso do demo, com motivo, evidência e
recomendação prontos para o advogado decidir:

- número de processo inválido;
- planilha diz arquivado, tribunal diz ativo;
- documento ilegível;
- valor acima do teto definido no cartão de regras;
- titular ambíguo ou sucessão de parte;
- prazo de levantamento perto de vencer.

## 5. Como cada exigência do guia é atendida

| O guia pede | Entrega do projeto |
|---|---|
| Fecha o processo, não só um passo | Do lote até a minuta pronta |
| Trata a exceção | Fila de exceções com contexto pronto |
| Deixa rastro auditável | Trace por processo no Langfuse |
| Mostra o ganho (horas, custo por execução) | Painel de custo por processo, medido no trace, contra o tempo manual |
| Evals | 40 casos rotulados, com casos difíceis de propósito |
| Jurados testam a solução | Link com dados pré-carregados; o jurado faz o papel do advogado e aprova ou rejeita |
| Integrações podem ser simuladas | Tribunal, extrato bancário e sistema do escritório como mocks que o agente realmente chama |

O tempo manual por processo é **hipótese** do time: rotular como premissa na tela. O custo do agente deve ser o
número real medido no trace.

## 6. Dados e stack

- **Dados 100% sintéticos**, gerados durante o evento: saldos, partes, números de processo (com dígito
  verificador válido), PDFs, política do cliente fictício e respostas do tribunal simulado. Nenhum dado,
  critério ou código de terceiros.
- **Backend e agente:** Python, LangGraph e FastAPI.
- **Interface:** uma tela simples com a fila de exceções e o painel. Sem chat.
- **Modelos:** Featherless (US$ 25 por pessoa, cobrado pelo preço público de cada modelo). Modelo pequeno como
  padrão; o grande só entra nas dúvidas. O custo da cascata aparece no painel.
- **OCR real:** PDFs sintéticos com ruído de digitalização, para a cascata de OCR ter efeito sem dado real.
- **Rastreamento:** Langfuse, desde a primeira hora.
- **Publicação:** link público estável, exigido na submissão.

## 7. Divisão e plano de horas (~11 h úteis)

Com 4 pessoas: **Agente** (grafo), **Dados** (gerador sintético, mocks e evals), **Interface** (fila e painel),
**Negócio** (pitch, vídeo e submissão). Com menos pessoas, junte Dados com Agente e Interface com Negócio.

| Janela | Entrega |
|---|---|
| Sáb 10h30 - 13h30 | Esqueleto, ingestão e mocks |
| Sáb 13h30 - 16h30 | Documentos, cascata e score |
| Sáb 16h30 - 17h00 | Primeiro fluxo completo |
| Dom 8h30 - 10h30 | Exceções, minuta e evals |
| Dom 10h30 - 11h30 | Painel e deploy |
| Dom 11h30 - 13h00 | Vídeo, descrição e submissão (prazo final 13h) |

**Se o tempo apertar, corte:** OCR real (use texto sintético), notificação e polimento visual.
**Não corte:** exceções, rastro e evals.

## 8. Pitch de 3 minutos

| Tempo | Conteúdo |
|---|---|
| 0:00 - 0:25 | Problema: dinheiro parado em processos arquivados. Cite faixa com fonte (Justiça do Trabalho, cerca de R$ 21 bi esquecidos em contas judiciais, reportagens de 2024), nunca como número único |
| 0:25 - 0:50 | Alternativa de hoje: planilha, estagiário, escritório com success fee. Why now: modelos baratos e prazos legais mais rígidos. Generalização: a mesma dor vale para empresas e escritórios, e o onboarding por documentos adapta o agente a cada cliente |
| 0:50 - 2:15 | Demo ao vivo: onboarding, lote, uma exceção resolvida, minuta aprovada |
| 2:15 - 2:40 | Números do trace: custo por processo, % resolvido sozinho, erros sem revisão |
| 2:40 - 3:00 | Modelo de negócio: success fee, cliente-alvo e próximo passo |

## 9. O que evitar

- Dizer ou sugerir que os dados ou o tribunal são reais. Declarar o caráter sintético e simulado na submissão.
- Citar um percentual de success fee como fato: não há fonte, então é hipótese.
- Inventar tamanho de mercado. Partir de uma âncora com fonte e rotular como estimativa.
- Fazer seis funções pela metade. O guia diz que uma coisa muito bem feita vale mais.
- Fazer o agente protocolar algo. A aprovação do advogado é ponto forte do pitch, não limitação.
- Começar código antes das 10h30. Manter o histórico de commits desde o início do hacking.

## 10. Checklist de submissão (prazo: domingo 13h)

- [ ] Descrição: problema, para quem, solução e como o agente funciona.
- [ ] Vídeo de demonstração.
- [ ] Link de acesso testável.
- [ ] Material de apresentação para o pitch.
- [ ] Lista de ferramentas, modelos e APIs de terceiros (declarar todos).
