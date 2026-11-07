# Contexto do hackathon

Resumo operacional do **Converge Challenge powered by Tako**. Fonte: guia oficial
([guia-converge-challenge.md](guia-converge-challenge.md)), lido em 07/11/2026. Quando houver dúvida, vale o guia e os
avisos no WhatsApp do evento. Última atualização: 2026-11-07 12:16.

## O evento

- **O quê:** hackathon presencial de AI Agents, com Demo Day e premiação.
- **Quando:** sábado 07/11 e domingo 08/11/2026. Presença obrigatória nos dois dias.
- **Onde:** Porto Digital, Av. Cais do Apolo, 222, 8º andar, Bairro do Recife, Recife/PE.
- **Organização:** Ligia (CIn-UFPE) e TAIL (UFPB), em parceria com a Canastra Ventures (fundo de VC). Patrocinadora
  master: Tako.
- **Canais oficiais:** grupo de WhatsApp e página do evento no Luma (https://luma.com/gfou18h1).

## Programação (horário de Brasília)

| Quando | O quê |
|---|---|
| Sáb 08h30 | Credenciamento e café |
| Sáb 09h30 | Abertura, briefing do desafio, apresentação do Desafio Tako e regras |
| **Sáb 10h30** | **Início do hacking** |
| Sáb 17h00 | Encerramento do 1º dia |
| Dom 08h30 | Café |
| **Dom 13h00** | **Prazo final de submissão** |
| Dom 16h00 | Demo Day (pitch de 3 minutos por time) |
| Dom 17h30 | Premiação e encerramento |

O FAQ do guia diz "10h" para o início do código, enquanto a programação diz 10h30. Trate **10h30** como oficial e confirme no
WhatsApp.

## O desafio

Tema aberto: **construir algo real com AI agents**. Um agente (ou sistema multiagente) que entregue trabalho feito de
verdade, resolvendo uma dor real em um mercado grande. Querem sistemas úteis, prontos para produção e que funcionem na
demo. **Os jurados vão testar as soluções.**

**Modelo de referência: digital worker.** Agente com papel definido que executa um processo de ponta a ponta, opera os
sistemas do time, tem permissões próprias e **chama um humano quando sai do roteiro**.

| Tipo | O que faz | Lida com exceção? |
|---|---|---|
| Chatbot | Responde dúvidas | Não |
| RPA | Repete um fluxo fixo | Não, quebra quando o fluxo muda |
| Copilot | Sugere, resume, rascunha. O humano decide | O humano decide |
| **Digital worker** | Recebe um objetivo e conduz o processo, com humano no loop | Sim, decide ou escala |

O guia valoriza: fechar o processo e não só um passo, tratar exceção de verdade, deixar rastro auditável e mostrar o ganho
(horas, retrabalho, custo por execução versus o trabalho manual). O guia **não usa o termo "AI Worker"**; o mais próximo é
"digital worker".

### Desafio Tako: Digital Workers para RH (opcional; o time concorre, [DEC-003](decisoes.md), provisória)

Quem escolher concorre à premiação geral pelos mesmos critérios, com acompanhamento da Tako (Pedro Stanzani na banca). Frentes:
recrutamento, admissão e onboarding, DP e folha, atendimento ao colaborador, desligamento. **Restrições:** decisões sobre
pessoas (demissão, promoção, salário, avaliação) ficam com humanos; dados sintéticos, nunca pessoais reais; integrações com
ATS, HRIS ou folha podem ser simuladas desde que o agente realmente opere sobre elas. Se escolhermos, **sinalizar na
descrição da submissão**.

## Critérios de avaliação (4, pesos iguais)

1. Qualidade do protótipo e aderência ao desafio.
2. Viabilidade como startup.
3. Criatividade e originalidade.
4. Pitch.

Tradução em nota interna: [ideacao/criterios.md](ideacao/criterios.md). Os critérios podem ser ajustados até o início do
evento, com aviso no WhatsApp.

## Regras que mais importam

Ver [regras-e-integridade.md](regras-e-integridade.md).

## Submissão (painel https://hackathons.canastra.ventures/, prazo domingo 13h)

Descrição (problema, para quem, solução, como o agente funciona), vídeo de demonstração, link de acesso navegável e
testável, material de apresentação para o pitch, e lista de ferramentas, modelos e APIs de terceiros. Checklist em
[entrega.md](entrega.md).

## Premiação

| Colocação | Prêmios |
|---|---|
| 1º | R$ 3.000, US$ 10.000 em créditos AWS Activate, US$ 300 em créditos Featherless, call com os sócios da Canastra para a AI Residency (fast track) ou vaga garantida no Matchmaking 5 |
| 2º | US$ 5.000 em créditos AWS Activate e vaga garantida no Matchmaking 5 |
| 3º | US$ 5.000 em créditos AWS Activate |

**Condição para receber os créditos AWS:** site institucional no ar em domínio próprio, e-mail corporativo no mesmo domínio,
conta AWS ativa, e empresa com menos de 10 anos e antes da Série B. Registro de domínio não é coberto pelos créditos.
**Decisão do time sobre concorrer: em aberto** ([estado](estado-do-projeto.md)).

## Benefício para todos: Featherless

US$ 25 em inferência por participante aprovado (mais de 40 mil modelos open source, API compatível com OpenAI, base URL
`https://api.featherless.ai/v1`). Cada pessoa resgata na própria conta; um time de 4 tem US$ 100. Exige cartão de crédito; o
primeiro mês não é cobrado, então **cancele o plano antes da primeira cobrança** se não for continuar. Modelo menor para
tarefas simples, o maior só para as difíceis. O código de resgate é exclusivo dos participantes e **não deve ser
publicado**: consulte o guia original. O uso das ferramentas dos parceiros é opcional e não conta a favor nem contra.

## Divergências e pontos a confirmar

Ver "Perguntas em aberto" em [estado-do-projeto.md](estado-do-projeto.md): horário de início (10h ou 10h30), dados
sintéticos e simulações no tema aberto, trabalho fora do local depois das 17h de sábado. O guia pode ter sido editado após o
carimbo de 31/10/2026.
