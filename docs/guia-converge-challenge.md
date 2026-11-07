# Guia do Participante: Converge Challenge powered by Tako

> **Cópia local para uso do time.** Fonte: https://canastraventures.notion.site/guia-converge-challenge
> Lida em 07/11/2026 via conector Notion. O guia informa: "Última atualização deste documento: 31 de outubro de
> 2026" (os metadados do Notion indicam edição às 01h39 UTC de 07/11/2026, depois do carimbo).
>
> **Notas desta cópia:**
> - O texto abaixo foi convertido de Notion para Markdown. Imagens e anexos (PDF do AWS Activate e PDF da
>   Featherless) não foram incluídos.
> - O **código de resgate da Featherless foi redigido** (`[REDIGIDO]`), porque o guia o declara exclusivo dos
>   participantes e pede que não seja publicado. Consulte o guia original.
> - O conteúdo veio de uma fonte externa; trate-o como referência e confira o original em caso de dúvida.
> - Em caso de divergência, vale o guia original e os avisos do WhatsApp oficial.

Você foi aprovado no **Converge Challenge powered by Tako**. Parabéns, e bem-vindo!

Este guia reúne tudo o que você precisa para chegar pronto: logística, programação, o desafio, como seu projeto
será avaliado, premiação, benefícios e regras. Leia com calma antes do evento. Ao participar, você declara que
leu, compreendeu e concorda com estas regras e com as decisões dos Organizadores, que são finais e vinculantes.

---

## Seu checklist antes do evento

- [ ] Entrar no **grupo de WhatsApp** do hackathon e acompanhar os avisos (é o canal oficial)
- [ ] Confirmar presença quando pedirmos no grupo. Quem não confirmar pode perder a vaga para a lista de espera
- [ ] Fechar o time (2 a 4 pessoas) ou chegar disposto a formar um no check-in
- [ ] Resgatar os **US$ 25 da Featherless** e criar sua API key (seção 11)
- [ ] Deixar o ambiente de desenvolvimento instalado e testado (seção 6)
- [ ] Ler o desafio e o **Desafio Tako** e chegar com a ideia amadurecida (seção 3)

---

## 1. O evento em resumo

| | |
|---|---|
| **O quê** | Hackathon presencial de AI Agents, com Demo Day e premiação |
| **Quando** | Sábado, 7/11, e domingo, 8/11 de 2026. Presença **obrigatória** nos dois dias |
| **Onde** | Porto Digital, Av. Cais do Apolo, 222, 8º andar, Bairro do Recife, Recife/PE |
| **Organização** | Ligia (CIn-UFPE) e TAIL (UFPB), em parceria com a Canastra Ventures |
| **Canais oficiais** | Grupo de WhatsApp (obrigatório) e página do evento no [Luma](https://luma.com/gfou18h1) |

Toda atualização, mudança de programação ou esclarecimento sai só por esses dois canais. Acompanhá-los é
responsabilidade de cada participante.

---

## 2. Programação

Todos os horários em horário de Brasília. São mais de 10 horas de construção em dois dias.

| Horário | Sábado, 7/11 |
|---|---|
| 08h30 | Credenciamento e café da manhã |
| 09h30 | Abertura, briefing do desafio, apresentação do Desafio Tako e regras |
| 10h30 | Início do hacking. Ninguém escreve código do projeto antes deste horário |
| Ao longo do dia | Almoço no local e rodadas de mentoria |
| 17h00 | Encerramento do 1º dia |

| Horário | Domingo, 8/11 |
|---|---|
| 08h30 | Café da manhã |
| Ao longo do dia | Almoço no local e rodadas de mentoria |
| 13h00 | **Prazo final de submissão dos projetos** |
| 16h00 | Demo Day |
| 17h30 | Premiação e encerramento |

A ordem de apresentação e os detalhes operacionais do Demo Day serão divulgados no WhatsApp no domingo. Os
Organizadores podem ajustar a programação, com aviso pelos canais oficiais.

---

## 3. O desafio: construir AI Agents

A era do copiloto ficou em 2025. Agora é a vez de sistemas autônomos que tomam decisões por conta própria.

Agentes planejam, executam e iteram sozinhos, usando ferramentas, APIs e fluxos de trabalho reais. A pergunta
deixou de ser como a IA ajuda você a trabalhar e passou a ser como construir sistemas que trabalham sem você.

**O desafio é um só: construir algo real com AI agents.** Não há vertical nem problema definido. O único requisito
é que um agente (ou um sistema multiagente) entregue trabalho feito de verdade, resolvendo uma dor real em um
mercado grande.

Algumas direções que valem explorar:

- Um agente de back-office que fecha conciliação, faturamento ou compliance de ponta a ponta
- Um agente de vendas que pesquisa contas, escreve a abordagem e atualiza o CRM sozinho
- Um sistema de suporte em que agentes resolvem tickets, escalam o que é complexo e aprendem com o histórico
- Um agente de operações que monitora um fluxo, detecta falha e dispara a correção sem esperar um humano
- Um digital worker para RH, como propõe o Desafio Tako logo abaixo

> Queremos ver sistemas *úteis*, prontos para produção e que funcionem na demo.

Como o evento tem um fundo de venture capital na banca, a pergunta "isso poderia virar uma startup?" pesa tanto
quanto "isso funciona?". Um protótipo bonito para três minutos de pitch não basta. A seção 4 explica como pensar
nas duas frentes.

### Desafio Tako: Digital Workers para RH

> Desafio proposto pela **Tako**, patrocinadora master do Converge. Encará-lo é **opcional**: o tema aberto de AI
> Agents continua valendo, e quem escolher o Desafio Tako concorre à premiação geral pelos mesmos critérios. A
> Tako acompanha de perto os times que toparem, com Pedro Stanzani na banca.

#### Quem propõe

A [Tako](https://tako.ai/pt/) está repensando como as empresas recrutam no Brasil com agentes de IA. O produto
mais conhecido é a Nara, uma recrutadora por voz. O desafio nasce do que o time deles vê todo dia dentro dos
departamentos de RH.

#### O que é um digital worker

Um digital worker é um agente de IA com papel definido que executa um processo de ponta a ponta, em vez de só
responder perguntas. Ele opera os sistemas que o time já usa (ATS, HRIS, folha, e-mail, Slack), tem permissões
próprias e chama um humano quando sai do roteiro. Na prática, é tratado como membro do time: tem função, escopo,
metas e um responsável.

| Tipo | O que faz | Quem executa | Lida com exceção? |
|---|---|---|---|
| Chatbot | Responde dúvidas a partir de uma base | Humano | Não |
| RPA | Repete um fluxo fixo em telas e sistemas | Robô, sem julgamento | Não, quebra quando o fluxo muda |
| Copilot | Sugere, resume, rascunha | Humano, com ajuda | O humano decide |
| **Digital worker** | Recebe um objetivo e conduz o processo | Agente, com humano no loop | Sim, decide ou escala |

#### O problema

O RH não sofre por falta de ferramenta. Sofre porque o humano virou a cola entre as ferramentas. Uma pesquisa da
Eagle Hill de setembro de 2026, citada pela Tako, dá a dimensão:

- 51% dos profissionais de RH passam pelo menos metade da semana em trabalho rotineiro e de baixo valor
- 91% usam dois ou mais sistemas para concluir uma única tarefa, e 78% redigitam a mesma informação em sistemas
  diferentes
- 84% dos líderes de negócio dizem que pedidos ao RH costumam exigir follow-up ou retrabalho

No Brasil o quadro piora. CLT, eSocial, convenções coletivas e prazos legais de férias, admissão e rescisão
fazem do Departamento Pessoal um trabalho de regra com muita exceção, justamente o tipo de fluxo que RPA não
aguenta e que hoje cai no colo de alguém do time. O resultado é um RH que contrata gente para operar processo,
não para cuidar de pessoas.

#### Onde um digital worker se encaixa

O ganho real hoje está no trabalho operacional e repetitivo. Escolha uma frente e vá fundo:

| Frente | O que o digital worker faz | Onde o humano entra |
|---|---|---|
| **Recrutamento** | Triagem, agendamento, entrevista inicial, retorno ao candidato | Decisão de avançar e de contratar |
| **Admissão e onboarding** | Coleta e validação de documentos, cadastro, acessos, checklist | Aprovação da admissão e exceções |
| **DP e folha** | Conferência de lançamentos, variações fora do padrão, prazos de férias e eSocial | Fechamento e assinatura da folha |
| **Atendimento ao colaborador** | Dúvidas de holerite, férias, benefícios e políticas resolvidas de ponta a ponta | Casos sensíveis ou fora da política |
| **Desligamento** | Checklist, prévia de rescisão, prazos legais, revogação de acessos | A decisão de desligar |

#### O que separa uma boa solução

- **Fecha o processo, não só um passo.** No caminho feliz, o agente vai do pedido ao resultado sem ninguém
  empurrar.
- **Trata a exceção de verdade.** Documento ilegível, férias vencendo, lançamento fora do padrão, pergunta fora
  da política. O agente resolve dentro da regra ou escala para o humano com o contexto pronto para decidir.
- **Deixa rastro.** Dá para auditar rápido o que o agente fez e por quê.
- **Mostra o ganho.** Horas, retrabalho ou prazo perdido que deixam de existir, e quanto custa cada execução
  comparada ao trabalho manual que ela substitui.

#### Restrições

- Decisões sobre pessoas ficam com humanos: demissão, promoção, salário e avaliação de desempenho. O agente pode
  preparar a decisão, nunca tomá-la.
- Use dados sintéticos. Nada de dados pessoais reais de candidatos ou colaboradores.
- Integrações com ATS, HRIS ou folha podem ser simuladas (mocks ou APIs de teste), desde que o agente realmente
  opere sobre elas na demo.

---

## 4. Como pensar seu projeto

Um bom projeto de hackathon se sustenta em duas frentes. A de negócio pergunta se o que você constrói resolve um
problema que alguém pagaria para resolver. A técnica pergunta se o agente se sustenta fora da demo. Cuide das
duas desde a primeira hora.

### Frente de negócio

Boa parte de quem constrói nunca parou para olhar o projeto como oportunidade de negócio, e essa costuma ser a
maior lacuna, mais do que a execução técnica. Reflita sobre as perguntas abaixo antes de sair codando. É a mesma
lente que a Canastra usa para avaliar startups.

**Problema**

- É uma dor latente em um mercado grande ou um incômodo pontual?
- É urgente? As pessoas já gastam tempo, dinheiro ou energia tentando evitar esse problema?
- Você consegue dizer quem sofre essa dor, com que frequência e quanto custa não resolvê-la?

> Se a resposta for "seria legal ter isso", provavelmente não é um problema. É uma feature.

**Oportunidade de mercado**

- Qual o tamanho do mercado que você está endereçando? Dá para chegar em um número, mesmo estimado?
- O que está mudando nesse mercado agora: crescimento, consolidação, regulação?
- Como a concorrência se posiciona? Inclua a alternativa mais comum: como o cliente resolve isso hoje sem você
  (planilha, processo manual, consultoria).

**Why now**

- O que existe agora que não existia há dois anos: tecnologia, regulação, infraestrutura, comportamento?
- Se o problema já existia, por que ninguém resolveu antes?
- A janela está aberta, ou é cedo demais ou tarde demais?

### Frente técnica

Fazer um agente rodar uma vez é fácil. O que separa um protótipo de demo de algo pronto para virar produto é como
ele se comporta fora dela:

- **Confiabilidade.** O que o agente faz quando uma ferramenta falha, a API não responde ou a instrução é
  ambígua?
- **Medição.** Que métricas mostram que ele vai bem? Um conjunto pequeno de evals separa um agente sólido de um
  que teve sorte numa execução.
- **Custo e latência.** Quanto custa cada execução, em tempo e tokens? Uma solução mais cara que o processo
  manual que substitui não se sustenta.
- **Autonomia com auditoria.** O agente trabalha sozinho, mas o rastro do que ele fez precisa ser claro quando um
  humano quiser entender o porquê.

Instrumentar o agente com tracing desde o começo (Langfuse, por exemplo) ajuda nas quatro: gera material para
medir, mostra onde está o custo e deixa o rastro auditável.

### Escopo e Demo Day

- **Escolha onde ir fundo.** Um projeto que faz uma coisa muito bem vale mais do que um que faz seis pela metade.
- **Prove, não afirme.** No Demo Day, mostre o sistema rodando num caso real. Evidência ao vivo convence mais do
  que um slide dizendo que funciona.

Queremos ver a solução em operação, mesmo que com dados sintéticos. Os jurados irão testar as soluções, garanta
que esteja funcional.

---

## 5. Elegibilidade, times e regras de participação

### Quem pode participar

- Aprovadas no processo de seleção. Inscrição não garante vaga
- Presentes no Porto Digital **nos dois dias**

Não há restrição de universidade, estado ou nacionalidade. Funcionários e representantes dos Organizadores podem
ter a participação restrita em caso de conflito de interesses.

### Times

- **Mínimo de 2 e máximo de 4 pessoas.** Participação individual não é permitida na competição.
- Quem foi aprovado sozinho pode formar time ao longo da semana que antecede o evento pelo grupo do WhatsApp, ou
  formar o time no check-in. Vamos ajudar nessa conexão.
- Times podem misturar pessoas de universidades, cidades e perfis diferentes. Recomendamos ao menos uma pessoa
  com perfil técnico forte por time.

### O que pode ser feito antes e o que só vale durante

**Antes do evento, à vontade:** pesquisa, conversa com potenciais clientes, modelagem de negócio, arquitetura da
solução e preparação de ambiente (contas, SDKs, bibliotecas, repositório vazio). Chegar com a ideia redonda é
bem-vindo.

**Só durante o evento:** o código do projeto, o build e o material de apresentação. O desenvolvimento começa às
10h30 de sábado, 7/11. Bibliotecas, frameworks e projetos open source podem ser usados como ponto de partida,
desde que não comprometam a integridade da competição. Os Organizadores podem pedir histórico de commits como
evidência, então comece o repositório no dia.

### Uso de IA

O uso de IA é obrigatório e deve ser central no projeto. APIs de terceiros, modelos pré-treinados e plataformas
de IA são permitidos, desde que usados de forma legal e declarados na submissão. Ferramentas de código com IA
(Claude Code, Cursor, Codex, Copilot, opencode ou outras) estão liberadas.

### Participação

A participação é presencial, gratuita, pessoal e intransferível. Trapaça, desonestidade ou informação falsa
levam à desqualificação.

---

## 6. O que levar e como chegar pronto

- **Notebook:** obrigatório. Não haverá computadores no local.
- **Carregador, adaptadores e *extensões*:** haverá tomadas mas não o suficiente para cada um dos participantes.
  Traga extensões!
- **Contas configuradas:** GitHub e qualquer API que você pretenda usar. Não haverá tempo de setup no evento.
- **Ambiente testado:** runtime, gerenciador de pacotes, containers e o que mais a sua stack exigir, instalados e
  rodando.
- **Downloads pesados feitos em casa:** modelos locais, imagens de container, ferramentas de automação de browser
  e dependências grandes. A rede do evento é compartilhada por dezenas de pessoas.
- **Créditos e chaves:** o evento oferece US$ 25 em inferência pela Featherless para cada participante (seção 11).
  Outras chaves, créditos e assinaturas ficam por sua conta, e precisam estar ativos antes de você chegar.

---

## 7. Submissão do projeto

Todos os projetos são submetidos pelo painel de hackathons da Canastra, com as instruções que vamos passar no
WhatsApp durante o evento.

> **Painel de submissão:** [Canastra Hackathons - Canastra Ventures](https://hackathons.canastra.ventures/)
> **Prazo final:** domingo, 8/11, às **13h00**

A submissão precisa conter:

- Descrição do projeto: problema, para quem, solução e como o agente funciona
- Vídeo de demonstração
- Link de acesso ao projeto (plataforma navegável e testável)
- Material de apresentação para o Pitch
- Ferramentas, modelos e APIs de terceiros utilizados

Submissões fora do prazo ou incompletas podem ser desqualificadas. Se o seu projeto responde ao Desafio Tako,
sinalize isso na descrição.

---

## 8. Critérios de avaliação

Os projetos são avaliados em quatro critérios, com pesos iguais:

1. **Qualidade do protótipo e aderência ao desafio:** o agente faz trabalho real, funciona na demo e se sustenta
   fora dela
2. **Viabilidade como startup:** existe um mercado, alguém que pagaria e um caminho de crescimento
3. **Criatividade e originalidade**
4. **Pitch:** clareza sobre problema, solução e potencial de mercado

Metade da régua é negócio, não só código. Os critérios ou sua interpretação podem ser ajustados até o início do
evento, com aviso no WhatsApp.

---

## 9. Pitch e avaliação

- A avaliação acontece no domingo, 8/11, com base nas apresentações ao vivo e no material submetido.
- Cada time tem **3 minutos** para apresentar. O tempo é controlado.
- A banca reúne profissionais selecionados pelos Organizadores, incluindo representantes da Canastra e da Tako.
- As decisões dos jurados são finais e irrecorríveis.

---

## 10. Premiação

| Colocação | Prêmios |
|---|---|
| 1º lugar | R$ 3.000 para a equipe vencedora · US$ 10.000 em créditos AWS Activate · US$ 300 em créditos Featherless · acesso direto à call com os sócios da Canastra para a [AI Residency](https://www.canastra.ventures/ai-residency) (fast track) ou vaga garantida no [Matchmaking 5](https://matchmaking.canastra.ventures/) |
| 2º lugar | US$ 5.000 em créditos AWS Activate · vaga garantida no [Matchmaking 5](https://matchmaking.canastra.ventures/) da Canastra |
| 3º lugar | US$ 5.000 em créditos AWS Activate |

Novos prêmios podem entrar até o evento, conforme novos parceiros se juntarem. A lista final fica sempre na
página do [Luma](https://luma.com/gfou18h1). Impostos, taxas e logística de entrega dos prêmios são tratados
caso a caso diretamente com os vencedores.

> **Condição para receber os créditos AWS: o time precisa ter domínio profissional próprio.**
>
> Os créditos do prêmio são liberados pelo programa AWS Activate, na modalidade Portfolio. A AWS valida
> automaticamente o domínio do e-mail contra o domínio do site. Sem os itens abaixo, a aplicação é recusada e o
> prêmio fica travado:
>
> 1. **Site institucional no ar, em domínio próprio** (ex.: `suastartup.com.br`). Uma página simples basta,
>    desde que esteja funcionando.
> 2. **E-mail corporativo no mesmo domínio do site** (ex.: `voce@suastartup.com.br`). E-mails de Gmail, Hotmail,
>    Outlook e endereços `.edu` são recusados.
> 3. **Conta AWS ativa**, em nome do time ou da empresa que vai usar os créditos.
> 4. Empresa com menos de 10 anos e ainda antes da Série B (é o caso de qualquer time de hackathon).

Não deixe isso para depois do anúncio. Dá para resolver em poucas horas: registrar o domínio, publicar uma
landing page e criar o e-mail no domínio. Se o time ainda não tem nada disso, use parte do tempo do evento para
resolver. Um detalhe: o registro de domínio não é coberto pelos créditos.

**Como os vencedores resgatam os créditos AWS**

1. Depois do evento, a Canastra envia ao time vencedor o código (OrgID) da premiação.
2. Acesse aws.amazon.com/startups/credits e clique em **Apply Now**.
3. Crie um **BuilderID**, o login pessoal no portal Startups.aws (é diferente da conta AWS).
4. Selecione **Portfolio** como tipo de crédito.
5. Preencha o formulário com o **e-mail corporativo** (mesmo domínio do site).
6. Informe o estágio e a data da última rodada de investimento, se houver.
7. Insira o **OrgID** exatamente como recebeu. Ele diferencia maiúsculas de minúsculas.
8. Avise a Canastra que aplicou, para confirmarmos a afiliação junto à AWS.
9. A aprovação leva de 7 a 10 dias úteis. Depois disso, os créditos aparecem na conta em até 7 dias.

Bom saber:

- Os créditos valem por 2 anos e não são renovados depois de expirar.
- O saldo fica em **AWS Console, Billing and Cost Management, Credits**.
- Cobrem a maioria dos serviços AWS, incluindo EC2, S3, Lambda, SageMaker, Bedrock e RDS. **Não cobrem** AWS
  Marketplace, Mechanical Turk, Managed Services, Professional Services, Training & Certification, registro de
  domínio no Route 53, Savings Plans, Reserved Instances nem mineração de criptomoedas.
- Se a aplicação for recusada por inconsistência entre site e e-mail, responda o e-mail de recusa a partir do
  endereço corporativo e anexe documentos de registro da empresa. O caminho para recurso é
  aws.amazon.com/activate/contact-us.
- O guia anexa um PDF "Guia completo AWS Activate para Founders" e cita um guia visual da AWS (não incluídos aqui).

**Como o 1º lugar recebe os US$ 300 da Featherless**

Depois do evento, a Canastra informa à Featherless o time vencedor e o e-mail das contas usadas no hackathon. A
Featherless faz a distribuição direto nas contas. Por isso, use no resgate dos créditos o mesmo e-mail com que
você se inscreveu.

---

## 11. Benefício para todos: US$ 25 em inferência na Featherless

Todo participante aprovado recebe **US$ 25 em créditos de inferência na [Featherless](https://featherless.ai/)**,
com acesso a mais de 40 mil modelos open source, sem limite de tamanho de modelo e com contexto de até 256K. A API
é compatível com a da OpenAI, então funciona com quase qualquer SDK ou agente de código.

> O código do guia é exclusivo dos participantes aprovados do Converge, tem limite de resgates e vence em
> **8/11**. Não publique nem compartilhe fora do evento. Se ele vazar e os resgates acabarem, não há reposição.

**Passo a passo para resgatar e configurar**

1. **Resgate o crédito.** Abra o link de resgate do guia original. O código já vai aplicado no checkout.
   - Código: `[REDIGIDO: ver o guia original]`
   - Link de resgate: `[REDIGIDO: ver o guia original]`

   Se a página der erro ou o código não aparecer aplicado, recarregue uma vez. Depois do checkout, o plano
   **Feather Per-Request** aparece como Active, com saldo de US$ 25.
2. **Sobre o cartão.** O cadastro pede um cartão de crédito. Ele serve para evitar abuso e o primeiro mês não é
   cobrado. **Se você não for continuar usando a Featherless depois do evento, cancele o plano antes da primeira
   cobrança.** Essa parte é responsabilidade de cada participante.
3. **Crie sua API key.** Clique no seu perfil, no canto superior direito, e abra **API Keys**. Crie uma chave e
   trate como senha: guarde em variável de ambiente e nunca faça commit no repositório.

   ```bash
   export FEATHERLESS_API_KEY=fw-...
   # toda requisição usa: Authorization: Bearer $FEATHERLESS_API_KEY
   ```

4. **Conecte ao seu agente de código.** Dois valores servem para qualquer ferramenta:

   ```txt
   base URL   https://api.featherless.ai/v1
   modelo     zai-org/GLM-5.2
   ```

   - **Claude Code:** conecte a Featherless como LLM gateway usando a sua chave.
   - **opencode:** rode `/connect`, escolha **Other**, informe a base URL e cole a chave.
5. **Teste antes de sábado.** Faça uma chamada simples e confira em **Subscription** que o request aparece
   cobrado, com modelo, tokens e custo.

**Como os créditos funcionam (e como fazer render)**

- **Cada pessoa resgata na própria conta.** Cada integrante tem seus US$ 25 e sua chave. Um time de 4 tem US$ 100
  no total.
- **Crédito único, sem renovação.** O que não for usado fica na conta e não expira.
- **Cobrança pelo preço público de cada modelo**, por milhão de tokens de entrada e saída. Só requisições
  bem-sucedidas são cobradas.
- **Não há teto por chave.** O limite é o saldo: quando zera, as requisições param.
- **Para economizar:** use um modelo menor para geração de texto simples (o Gemma 4 31B é uma boa opção) e guarde
  o GLM mais recente para as tarefas difíceis, como código e raciocínio longo.
- **Agente pronto em um clique:** o plano inclui um sandbox. Em **Agents, Marketplace** dá para subir Open WebUI,
  Hermes, OpenClaw e outros, já ligados à inferência da Featherless.

**Se algo der erro**

| Erro | O que fazer |
|---|---|
| **401 Unauthenticated** | Chave não reconhecida. Confira se copiou certo ou crie uma nova |
| **403 Unauthorized** | Modelo com acesso restrito. Abra a página do modelo, clique em Unlock Model e aceite a licença |
| **500 Internal Server Error** | Confira se você enviou algum parâmetro não suportado, na documentação |
| **503 Service Unavailable** | Modelo frio ou capacidade cheia. Tente de novo; se persistir depois de três tentativas, avise no WhatsApp |

**Materiais da Featherless:** catálogo de modelos https://featherless.ai/models · documentação
https://featherless.ai/docs · vídeos de Hermes Agent, Open WebUI e OpenClaw (links no guia original).

O uso das ferramentas dos parceiros é opcional e não conta a favor nem contra na avaliação.

---

## 12. Mentores e jurados

A lista final de juízes e mentores estará publicada na página oficial do evento no
[Luma](https://luma.com/gfou18h1). Novos nomes poderão ser anunciados.

Os mentores circulam pelas mesas ao longo dos dois dias. Aproveite: chegue nelas com uma pergunta concreta, não
com um "o que você acha?".

---

## 13. Perguntas frequentes

**Posso ir só em um dos dias?** Não. A presença nos dois dias é obrigatória para todos os aprovados.

**Fui aprovado sozinho. Como acho um time?** No grupo do WhatsApp ou no check-in de sábado. Vamos ajudar a juntar
quem chegou sem time antes do início do hacking.

**Posso começar a programar antes do evento?** Não. Ideia, pesquisa, arquitetura e preparação de ambiente podem
vir prontas. O código do projeto começa às 10h de sábado. *(Nota do time: a programação do mesmo guia diz 10h30.)*

**Preciso escolher o Desafio Tako?** Não. É opcional. O tema aberto de AI Agents continua valendo e os critérios
de avaliação são os mesmos para todos.

**Preciso de cartão de crédito para a Featherless?** Sim, como proteção contra abuso. O primeiro mês não é
cobrado. Cancele antes da primeira cobrança se não for continuar usando.

**Meu time ainda não tem empresa nem site. Pode ganhar os créditos AWS?** Pode ganhar a colocação, mas o resgate
dos créditos exige site em domínio próprio e e-mail corporativo no mesmo domínio. Sem isso, a AWS recusa a
aplicação. Por isso recomendamos resolver durante o evento. Em caso de recusa, a AWS pode pedir documento de
registro da empresa no recurso.

**Quem fica com o que construímos?** O time. Toda a propriedade intelectual criada no hackathon pertence aos
participantes (veja a seção 14).

**Para onde mando minhas dúvidas?** No grupo de WhatsApp. Para assuntos pessoais ou denúncias, fale diretamente
com os Organizadores pelo WhatsApp.

---

## 14. Regras gerais

**Competição baseada em mérito.** Nenhuma compra, pagamento ou contrapartida é necessária para participar. O
Converge é uma competição de habilidade, não uma loteria, rifa ou jogo de azar. Os vencedores são definidos
exclusivamente pelos critérios de avaliação deste guia.

**Código de conduta e política antiassédio.** O Converge tem o compromisso de oferecer um ambiente seguro,
inclusivo e respeitoso para participantes, organizadores, mentores, jurados, patrocinadores e equipe. O código
vale no local do evento, no grupo de WhatsApp, durante pitches e demos e nos materiais submetidos.

Não toleramos assédio, discriminação, intimidação ou exclusão de qualquer tipo, inclusive com base em gênero,
identidade de gênero, orientação sexual, idade, deficiência, aparência, raça, etnia, nacionalidade, religião ou
formação técnica. Isso inclui linguagem ofensiva, assédio verbal, físico ou digital, contato físico inapropriado,
perturbação do evento, bullying e compartilhamento de conteúdo sexualizado ou violento.

A política para assédio é de tolerância zero. Os Organizadores podem advertir, remover do evento, desqualificar
ou banir de edições futuras. Denúncias podem ser feitas de forma confidencial aos Organizadores pelo WhatsApp e
serão tratadas com rapidez e discrição.

**Propriedade intelectual.** Os participantes mantêm a propriedade integral do que criarem durante o hackathon.
Ao participar, os times concedem aos Organizadores uma licença não exclusiva, mundial e livre de royalties para
usar nomes de projetos, descrições, capturas de tela, vídeos, demos e materiais de apresentação para fins
promocionais, educacionais ou de documentação, com a devida atribuição. Nenhuma transferência de propriedade
está implícita.

**Mídia e direito de imagem.** Ao comparecer, você autoriza fotografia, gravação de vídeo e áudio e o uso de sua
imagem, voz, demos e apresentações pelos Organizadores, para fins promocionais ou de arquivo, sem necessidade de
consentimento adicional ou compensação.

**Dados.** Os dados de inscrição são compartilhados com a Ligia, a TAIL, a Canastra Ventures e os patrocinadores
e parceiros do evento, conforme aceito no formulário do Luma.

**Responsabilidade e isenção.** O hackathon é oferecido no estado em que se encontra. Os Organizadores não se
responsabilizam por falhas técnicas, perda de dados ou equipamentos, lesões pessoais, transporte ou hospedagem.
Os participantes assumem os riscos associados à participação.

**Conformidade legal e disposições gerais.** Os participantes devem cumprir as leis e regulamentos aplicáveis, e
qualquer violação pode levar à desqualificação. Os Organizadores podem alterar programação, formato, critérios e
premiação, com aviso pelos canais oficiais. Se alguma disposição deste guia for considerada inválida, as demais
continuam valendo. Este guia é regido pelas leis da República Federativa do Brasil, com foro na cidade do
Recife, PE.

Nos vemos no Porto Digital. Venha com a ideia afiada, o ambiente pronto e disposição para colocar algo de pé em
dois dias.
