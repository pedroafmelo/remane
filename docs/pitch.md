# Pitch, vídeo e descrição da submissão

Última atualização: 2026-11-08 03:20 (Recife), por Claude (Opus 5.5). **Rascunho para o time revisar.** Os slides vão ser montados no
Canva pela manhã; este arquivo traz só o texto de cada slide, a fala e o que mostrar.

**Modelo:** a apresentação "Sprint Pitch: como criar um pitch de alto impacto", de Erica Marques (PDF na pasta do projeto, fora do
repositório). São 5 blocos: (1) explicação memorável, (2) equipe, (3) dor (+ ganho), (4) solução + o que é único e (5) chamada para ação.
Os slides de cada bloco seguem o desenho dela: uma frase grande, um visual e pouco texto.

**Regras que valem aqui** ([CLAUDE.md](../CLAUDE.md), [entrega.md](entrega.md)):

- São **3 minutos com tempo controlado**, cerca de 400 palavras faladas. As falas abaixo somam ~330, mais a da equipe; sobra folga para respirar.
- **Sem a 6x1 no centro** ([DEC-036](decisoes.md)): a EC 141 aparece só como o *why now*, uma regra entre outras.
- **Só número medido**, com a origem. Número de mercado tem fonte. Preço é **[HIPÓTESE]** e é dito como hipótese.
- **Os dados são sintéticos, e a convenção e a política são fictícias.** O celular é simulado. Isso precisa ser dito.
- `[PREENCHER]` é o que só o time sabe. `[DECIDIR]` depende de uma escolha pendente.

---

## 0. Números que podemos dizer

| Número | Valor | Como foi medido | Quando |
|---|---|---|---|
| Custo do modelo por execução | **US$ 0,001** (US$ 0,001047) | rastro da execução no link público (`llm.justify`, Qwen3.5-9B na Featherless) | 08/11, 03:00 |
| Tempo da execução completa | **~36 s**: solver 19,6 s + justificativa 16,3 s | rastro da mesma execução, no Railway | 08/11, 03:00 |
| Violações das regras na escala enviada → na proposta | **158 → 0** | verificador independente, mesma escala de exemplo (sintética) | 08/11 |
| Horas extras na escala enviada → na proposta | **216,5 h → 0 h** | mesma função de custo nas duas escalas | 08/11 |
| Cobertura da demanda | **95,2% → 100%** | idem | 08/11 |
| Economia na semana do exemplo | `[DECIDIR]`: **R$ 13.975** hoje, ou **~R$ 5.533** com o PR #16 | idem; o PR #16 corrige a carga do contrato (ver nota) | 08/11 |
| Evals sem modelo (E1) | **10/10** | `uv run python -m escalista.evals --suite e1` | 08/11 |
| Rede da demo | 3 lojas, 60 pessoas, 1 semana | dados sintéticos gerados pelo time | — |

**Nota sobre a economia:** hoje o solver deixa duas pessoas com 0 h, e a economia conta como ganho salário que continua sendo pago
(R$ 9.864,80 medidos). O PR #16 corrige isso. **Recomendação:** mergear o #16 antes do pitch e dizer o número menor. Um jurado de RH
pergunta "e a Quitéria, que não trabalhou, não recebe?", e o número maior não se sustenta.

**Números de mercado com fonte** (da [ficha da IDEA-002](ideacao/ideias/IDEA-002-escalista.md)):

- A EC 141, promulgada em 16/10/2026, leva a jornada para **42 h com dois repousos semanais a partir de ~16/12/2026** e para 40 h um
  ano depois. **[FATO]** (Planalto; as datas são contadas por nós)
- No food service, das 132 empresas ouvidas pelo IFB, **só 9% já decidiram como se adaptar**, e **59% das estimativas de impacto
  são "percepção, sem modelagem formal"**. **[FATO]** (Mercado & Consumo, 15/10/2026)
- Horas extras é **o tema mais recorrente no TST** em 2024 (70.508 processos). **[FATO]** (TST)
- Âncora de preço: o ponto eletrônico custa de **R$ 3,75 a R$ 6,90 por colaborador por mês** (Genyo, preço publicado). **[FATO]**
  Não é o nosso preço.

---

## 1. Slides e falas (3 min)

Tempo total previsto: 3:00. Ensaiar com cronômetro pelo menos 3 vezes.

### Slide 1 · Explicação memorável (0:00 – 0:15)

- **No slide:** logo Remane, grande, e a frase **"O engenheiro da sua escala de trabalho."**
- **Visual:** o painel em degradê da landing, com o Pat.
- **Fala:**
  > "Toda segunda-feira, um gerente de loja abre uma planilha e tenta encaixar 20 pessoas, a lei, a convenção e o movimento da
  > semana. O Remane é o engenheiro dessa escala."

Opções de frase (escolher uma; **recomendo a A**, que já é o título da landing):

- **A.** "O engenheiro da sua escala de trabalho."
- **B.** "A escala certa, montada e acompanhada por um agente."
- **C.** Analogia, no estilo do "tipo Google Maps das escolas" do PDF: "Um GPS da escala: traça a melhor semana e recalcula quando
  alguém falta."

### Slide 2 · Equipe (0:15 – 0:30)

- **No slide:** um título de equipe, as fotos, o nome e um mini-título de cada pessoa, e logos de empresas ou universidades.
- **Título `[PREENCHER]`:** o que mais impressiona na equipe à primeira vista. Formato sugerido: "Engenharia de otimização + RH +
  produto", ajustado ao que é verdade.
- **Pessoas `[PREENCHER]`:** Pedro Melo, Pedro Vieira, Pedro Veloso e a 4ª pessoa. Para cada uma, um mini-título que dê
  credibilidade ao problema (por exemplo: quem já viveu escala de loja, quem otimiza, quem cuida da parte trabalhista).
- **Fala `[PREENCHER]`:** uma frase sobre **por que nós** nos importamos com esse problema. Ela é mais forte se alguém já sofreu com
  escala na vida real.

### Slide 3 · Dor (+ ganho) (0:30 – 1:05)

- **No slide (título da oportunidade):** **"Toda semana, alguém monta a escala na mão. E toda semana ela quebra."** (frase da landing)
- **Visual:** uma planilha de escala à esquerda e um WhatsApp de gerente cheio de "não vou poder ir hoje" à direita. Usar imagem
  ilustrativa, nunca um print real de alguém.
- **Três dores, uma linha cada** (as da landing):
  - Hora extra que ninguém planejou
  - Turno descoberto no horário de pico
  - Regra trabalhista furada sem ninguém ver
- **Gráfico de mercado (o "gráfico incrível" do modelo):** uma barra só, com **"9% decidiram como se adaptar"** contra 91%, com a
  legenda "food service, 132 empresas, IFB, out/2026". Ao lado, o selo **"16/12: 42 h e dois repousos por semana (EC 141)"**.
- **Fala:**
  > "O problema é que a escala é feita na mão e consertada no improviso. Quem cobre a falta é quem atende o telefone, não quem sai
  > mais barato. Uma troca de última hora fura o descanso, e hora extra é o tema que mais chega ao TST. E a regra acabou de mudar: em
  > dezembro a jornada cai para 42 horas com dois repousos. No food service, só 9% das empresas já sabem como vão se adaptar."

### Slide 4 · Solução + o que é único (1:05 – 2:20)

Dois slides, no formato do modelo: título claro, subtítulo de como funciona e **uma captura de tela**.

**4a. O que é e como funciona (1:05 – 1:45)**

- **Título (o que é e o que substitui):** **"O Remane substitui a planilha e o WhatsApp do gerente por um agente que monta e acompanha a
  escala."**
- **Subtítulo (como funciona, sem siglas):** "Lê a escala atual → monta a melhor semana dentro da lei, da convenção e da política →
  um verificador independente confere → o gestor aprova → o Pat acompanha a semana e só chama o gestor quando precisa decidir."
- **Captura de tela:** a tela "Antes e depois" da plataforma (158 → 0 violações, horas extras → 0, custo lado a lado), com o Pat
  explicando. Alternativa: o cartão de exceção com opções e custo.
- **Fala:**
  > "O gestor envia a escala que já usa. O Pat, nosso agente, lê o arquivo e monta a melhor semana possível dentro da lei, da
  > convenção e da política da empresa, com um otimizador matemático, não com chute de IA. Um verificador independente confere
  > regra por regra. Na escala de exemplo: 158 violações viram zero, e 216 horas extras viram zero. O gestor aprova, e só então ela
  > é publicada. Durante a semana, quando alguém avisa uma falta, o Pat acha quem cobre sem hora extra e leva a decisão ao gestor,
  > com as opções e o custo de cada uma."

**4b. Por que confiar e o que é único (1:45 – 2:20)**

- **Título:** **"Cada turno com a regra que o justifica."**
- **Três blocos curtos:**
  - **Regras como dados, com origem:** lei, convenção e política viram regras com o artigo ou a cláusula de onde vieram. Trocar de
    empresa é trocar dados, não código.
  - **O agente prepara, o humano decide:** nada é publicado sem a aprovação do gestor, e decisões sobre pessoas ficam sempre com
    pessoas.
  - **Tudo auditável e medido:** cada passo fica no rastro, com custo e tempo. Uma execução completa custou **US$ 0,001 de modelo** e
    levou ~36 s.
- **Fala:**
  > "O que nos diferencia é a confiança. Cada regra tem origem: artigo da lei, cláusula da convenção ou item da política. O agente
  > nunca publica sozinho. E tudo fica num rastro auditável: uma execução completa custou um décimo de centavo de dólar em modelo."

### Slide 4c · Negócio (2:20 – 2:40)

O modelo da Erica não tem um slide de negócio, mas metade da nota é viabilidade ([CLAUDE.md](../CLAUDE.md)). Por isso entra como
parte do bloco 4, em "Relações / Parcerias".

- **No slide:**
  - **Para quem:** redes de varejo, food service e farmácia com 5 a 200 lojas que fazem escala em planilha.
  - **Quem paga:** a diretoria de operações ou de RH. **[HIPÓTESE]**
  - **Como cobra:** por colaborador escalado por mês, na faixa do que essas empresas já pagam pelo ponto (R$ 3,75 a R$ 6,90). **[HIPÓTESE
    de preço; âncora com fonte]**
  - **Para onde cresce:** o canal com o trabalhador é a porta para o resto do DP: trocas, atestados, banco de horas.
- **Fala:**
  > "Vendemos para redes de 5 a 200 lojas, cobrando por colaborador escalado por mês, na mesma faixa que elas já pagam pelo ponto.
  > E o canal com o trabalhador abre a porta para o resto do departamento pessoal."

### Slide 5 · Chamada para ação (2:40 – 3:00)

- **No slide:** **"Deixe a escala com quem entende de escala."** (frase de fechamento da landing), mais o **QR code e o link** da demo.
- **Pedido concreto `[DECIDIR]`:** "Procuramos uma rede para um piloto de 30 dias", ou "Testem agora: entrem como gestor e vejam o Pat
  montar a semana".
- **Fala:**
  > "Deixe a escala com quem entende de escala. O link está aí: entrem como gestor, mandem a escala e vejam o Pat trabalhar. E se
  > vocês conhecem uma rede que ainda faz escala em planilha, a gente quer conversar."

**Super dica do PDF:** respirar. Uma frase por vez, com pausa depois dos números.

### Riscos de pitch (o que a banca pode perguntar)

| Pergunta provável | Resposta curta |
|---|---|
| "Isso não é só um solver? Onde está o agente?" | O agente conduz o processo: lê o arquivo, chama o otimizador, confere, explica, acompanha a falta, monta as opções da exceção e pede a decisão. O solver é uma ferramenta dele. |
| "E se o modelo errar a regra?" | O modelo não decide regra nem publica: um verificador independente confere em código, e o gestor aprova. |
| "Os dados são reais?" | Não: dados sintéticos e convenção fictícia, declarados. O próximo passo é o piloto. |
| "Quanto custa rodar?" | US$ 0,001 de modelo por execução, medido no rastro. O solver roda no nosso servidor. |
| "Concorrentes?" | Existem apps de escala com CLT (ex.: Escala Jornadas). O nosso ângulo é convenção e política como regras citadas, exceção com decisão humana e rastro. Nunca dizer "ninguém faz". |

---

## 2. Roteiro do vídeo de demonstração (~2:30)

O guia pede o vídeo "do sistema rodando num caso real (sintético), mostrando também uma exceção" ([entrega.md](entrega.md)). Gravar a
tela do **link público**, com narração. Ele também é o plano B se a rede do evento cair.

**O que precisa estar pronto antes de gravar:** os PRs da plataforma mergeados e publicados no Railway (#15 e os de Exceções e de
Impacto/Regras) e, se o time decidir, o #16. Cenas que dependem de PR ainda aberto estão marcadas.

| # | Tempo | Tela | Narração |
|---|---|---|---|
| 1 | 0:00 – 0:10 | Landing, rolando a história do hero | "O Remane é o engenheiro da escala de trabalho. Tudo aqui usa dados sintéticos." |
| 2 | 0:10 – 0:20 | `/entrar` → "Entrar como gestor" | "O jurado entra sem senha, como gestor ou como colaborador." |
| 3 | 0:20 – 0:40 | Escala → "Usar escala de exemplo" → resumo da leitura | "O gestor envia a escala que já usa. O Pat lê: 60 pessoas, 3 lojas, 360 turnos, e mostra o que entendeu antes de seguir." |
| 4 | 0:40 – 1:00 | "Confirmar a leitura" → Pat trabalhando (cortar a espera de ~36 s na edição) | "Ele otimiza a semana dentro da lei, da convenção e da política, confere com um verificador independente e escreve a justificativa." |
| 5 | 1:00 – 1:25 | Antes e depois + justificativa do Pat + grade proposta | "158 violações viram zero; 216 horas extras viram zero; cobertura de 95 para 100%. Custo calculado pela mesma função nas duas escalas." |
| 6 | 1:25 – 1:35 | "Aprovar e publicar" → escala vigente | "Nada é publicado sem o gestor. A aprovação fica gravada com quem e quando." |
| 7 | 1:35 – 2:00 | **(PR de Exceções)** Sair → entrar como colaborador → celular simulado → "Avisar falta" | "No celular simulado, a colaboradora avisa a falta. O Pat procura quem cobre sem hora extra e respeitando o descanso." |
| 8 | 2:00 – 2:15 | **(PR de Exceções)** Gestor → Exceções → cartão com opções e custo → escolhe | "O gestor recebe a exceção com as opções, o custo e a recomendação, e decide. A escala é atualizada." |
| 9 | 2:15 – 2:25 | **(PR de Impacto/Regras)** Regras (origem de cada regra) e Impacto (rastro com custo) | "Cada regra tem a origem, e cada passo tem custo e tempo medidos: US$ 0,001 de modelo nesta execução." |
| 10 | 2:25 – 2:30 | Tela final com o link | "Teste você mesmo no link." |

Dicas: gravar em 1440 × 900 ou maior, com zoom do navegador em 110%. Cortar as esperas e manter o cronômetro do Pat visível por um
segundo, para não parecer truque. Sem música alta. Legenda "dados sintéticos" na tela inteira.

---

## 3. Descrição da submissão (texto pronto para colar)

> **Remane: o engenheiro da sua escala de trabalho.** Responde ao **Desafio Tako** (Digital Workers para RH, frente de
> departamento pessoal).
>
> **Problema.** Em redes de varejo, food service e farmácia, a escala da semana é montada à mão em planilha e consertada no
> improviso pelo WhatsApp do gerente. O resultado é hora extra que ninguém planejou, turno descoberto no pico e regra trabalhista
> furada sem ninguém ver. A EC 141 muda a jornada para 42 h com dois repousos semanais a partir de dezembro de 2026, e a maioria das
> empresas ainda não sabe como vai se adaptar.
>
> **Para quem.** Gestores de loja e o departamento pessoal de redes com 5 a 200 lojas.
>
> **Solução.** O Remane é um agente (o Pat) que monta a escala ótima e acompanha a semana. O gestor envia a escala que já usa. O
> agente lê o arquivo e mostra o que entendeu. Depois otimiza a semana com um solver de programação por restrições (OR-Tools CP-SAT)
> dentro da lei, da convenção e da política da empresa, que entram como dados, com a origem de cada regra. Um verificador independente
> confere regra por regra, a mesma função de custo compara o antes e o depois, e um modelo de linguagem escreve a justificativa
> citando as regras. **Nada é publicado sem a aprovação do gestor.** Durante a semana, o colaborador avisa uma falta pelo celular
> simulado; o agente procura quem cobre sem hora extra e leva ao gestor um cartão de exceção com opções, custo e recomendação.
>
> **Como o agente funciona.** Grafo LangGraph com paradas humanas: ler → (gestor confirma) → otimizar → verificar → comparar →
> justificar → (gestor aprova) → publicar. A ferramenta de publicar recusa sem aprovação, e isso é conferido em código. Falha do
> modelo vira exceção visível (nunca texto inventado). Cada passo vai para um rastro auditável com custo e latência, visível na
> plataforma.
>
> **Medido** (dados sintéticos, link público, 08/11/2026): na escala de exemplo (3 lojas, 60 pessoas), 158 violações → 0, 216,5 h
> de hora extra → 0, cobertura de 95,2% → 100%, economia de `[DECIDIR: R$ 5.533 com o PR #16]` na semana. Execução completa em ~36
> s, com US$ 0,001 de modelo. Evals sem modelo: 10/10.
>
> **Teste:** `https://escalista-converge-production.up.railway.app` → "Testar a demo" → entrar como gestor ou como colaborador,
> sem senha.
>
> **Declarações.** Todos os dados são sintéticos, gerados pelo time. A convenção coletiva e a política da empresa são fictícias. O
> celular do colaborador é simulado, não é WhatsApp. Decisões sobre pessoas ficam sempre com humanos. Ferramentas, modelos e APIs de
> terceiros: Featherless (Qwen3.5-9B e Gemma 4 31B), OR-Tools, LangGraph, FastAPI, Next.js, SQLite e Railway. A lista completa com
> licenças está em `docs/declaracao-ferramentas.md`. O código foi escrito durante o evento, com apoio do Claude Code.

Antes de colar: conferir cada número com a versão publicada, trocar o `[DECIDIR]` e confirmar se o Gemma 4 31B foi mesmo usado (hoje
o rastro só mostra o Qwen3.5-9B). Se não foi, tirar da lista.

---

## 4. Pendências

- `[PREENCHER]` Equipe: nomes completos, mini-títulos, logos e a frase do "por que nós".
- `[DECIDIR]` O PR #16 (carga do contrato) e, com ele, o número da economia no slide 4a, no vídeo e na descrição.
- `[DECIDIR]` A chamada para ação: piloto ou "teste agora".
- `[DECIDIR]` Quem fala cada bloco. Sugestão: uma pessoa nos blocos 1 a 3 e outra nos blocos 4 e 5.
- Gravar o vídeo depois do merge dos PRs da plataforma e do deploy.
- Imprimir ou ter à mão o QR code do link.
