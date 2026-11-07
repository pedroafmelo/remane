# Regras de elegibilidade e integridade

Última atualização: 2026-11-07 11:55. Fonte: guia, seções 5, 7 e 14 ([guia-converge-challenge.md](guia-converge-challenge.md)).
Em divergência, vale o guia original e os avisos do WhatsApp. **Fato** = está no guia; **interpretação do time** = como
aplicamos, sujeita a confirmação.

## O que o guia determina [FATO]

| Tema | Regra | Seção |
|---|---|---|
| Presença | Presencial nos dois dias, obrigatória | 1, 13 |
| Time | 2 a 4 pessoas; individual não compete | 5 |
| Antes do evento | Pesquisa, conversa com possíveis clientes, modelagem de negócio, arquitetura e preparação de ambiente | 5 |
| Só durante o evento | Código do projeto, build e material de apresentação. Hacking a partir das 10h30 de sábado | 5 |
| Reuso | Bibliotecas, frameworks e open source podem ser ponto de partida se não comprometerem a integridade | 5 |
| Histórico de commits | Organizadores podem pedir como evidência; começar o repositório no dia | 5 |
| IA | Obrigatória e central. APIs de terceiros e modelos pré-treinados permitidos se legais e **declarados na submissão** | 5 |
| Ferramentas de código com IA | Liberadas (Claude Code, Cursor, Codex, Copilot, opencode etc.) | 5 |
| Honestidade | Trapaça, desonestidade ou informação falsa levam à desqualificação | 5 |
| Submissão | Painel da Canastra até **dom 08/11, 13h00**; fora do prazo ou incompleta pode desqualificar | 7 |
| Propriedade intelectual | Do time. Organizadores recebem licença não exclusiva para uso promocional de nome, descrição, capturas, vídeos e demos | 14 |
| Imagem | Participação autoriza foto, vídeo e áudio pelos organizadores | 14 |
| Segredos | Código de resgate da Featherless é exclusivo e não pode ser publicado | 11 |
| Conduta | Tolerância zero a assédio; denúncias confidenciais pelo WhatsApp | 14 |
| Desafio Tako (RH) | Opcional. Se responder a ele, sinalizar na descrição. Decisões sobre pessoas ficam com humanos; só dados sintéticos; integrações podem ser simuladas | 3, 7 |

## Como o time aplica [INTERPRETAÇÃO]

1. **Clean room estrito.** Além do que o guia pede, o time proíbe qualquer dado, código, prompt, schema, critério ou
   documento de clientes ou empregadores dos integrantes, mesmo como referência ou inspiração. Aplica-se também ao
   scaffold do repositório (ver [declaracao-ferramentas.md](declaracao-ferramentas.md)).
2. **Dados sintéticos e simulações declarados.** O guia só os permite expressamente no Desafio Tako. No tema aberto, o time
   os usa **declarando** claramente e confirma a regra com os organizadores.
3. **Commits.** Pequenos, frequentes, em inglês, Conventional Commits, desde o início. Nada importado de outro histórico.
4. **Segredos.** `.env` ignorado pelo git; `.env.example` só com nomes de variável, sem valor.
5. **Atos de consequência com humano.** Definidos por ideia (ver [criterios.md](ideacao/criterios.md), filtro G6).
6. **Afirmações verificáveis.** O que é dito na submissão e no pitch (números, ganho, custo) precisa ter origem: medido,
   fonte citada, ou rotulado como estimativa.

## Pontos a confirmar com os organizadores

Ver a tabela "Perguntas em aberto" em [estado-do-projeto.md](estado-do-projeto.md). Ao receber resposta, registre aqui e lá.

## Créditos AWS (decisão do time)

O prêmio de AWS Activate exige site em domínio próprio, e-mail corporativo no mesmo domínio e conta AWS ativa; registro de
domínio não é coberto. Decisão sobre concorrer: ver [contexto-hackathon.md](contexto-hackathon.md).
