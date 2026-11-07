# Como ideiar: funil com tempo marcado

Última atualização: 2026-11-07 11:55.

Objetivo: sair com **uma ideia decidida e registrada**, sem gastar mais do que o necessário das ~11 horas de hacking.
Orçamento sugerido: **60 a 75 minutos** no total. Se estourar, vale o passo 5 com o que houver (ver "Plano de
contingência").

O guia diz que o desafio é um só: construir algo real com AI agents, sem vertical definida, e que a pergunta "isso poderia
virar uma startup?" pesa tanto quanto "isso funciona?". O funil abaixo serve a essas duas perguntas.

## Passo 1 · Alinhar restrições (5 min)

Responda em voz alta e registre no [estado](../estado-do-projeto.md):

- Quem está no time, o que cada pessoa faz melhor e o que quer aprender? (Perfil técnico forte é recomendado.)
- Em que mercados alguém do time **tem conhecimento de domínio legítimo e próprio** (não de empregador ou cliente)?
- O que está fora de questão (tecnologia, setor, risco)?
- Queremos concorrer ao Desafio Tako (RH) ou ao tema aberto geral? E aos créditos AWS?

**Cerca do clean room:** nenhuma ideia pode se apoiar em dado, código, prompt, critério ou documento de cliente ou
empregador. Experiência pessoal e conhecimento geral de domínio podem inspirar um problema; material proprietário não.

## Passo 2 · Divergir (15 min)

Meta: **8 a 12 candidatas**, uma linha cada, sem julgar. Registre com `/nova-ideia`. Use as lentes:

1. **Direções do guia:** back-office que fecha conciliação, faturamento ou compliance de ponta a ponta; vendas que
   pesquisa contas, escreve a abordagem e atualiza o CRM; suporte que resolve tickets e escala o complexo; operações que
   detecta falha e dispara a correção; digital worker de RH (Desafio Tako).
2. **O humano virou a cola entre sistemas.** Onde alguém copia dado entre telas, confere, cobra e redigita? (É a tese do
   Desafio Tako, e vale para qualquer área.)
3. **Regra + exceção + documento.** Processos com regra clara, muita exceção e papel ou PDF no meio são o terreno em que
   RPA quebra e agente brilha.
4. **Quem já paga alguém para isso hoje?** Orçamento existente (terceirizado, estagiário, consultoria, planilha cara) é
   o melhor indício de "quem paga".
5. **Prazos e multas.** Mercados regulados com prazo legal e custo de errar criam urgência e dão motivo para auditoria.
6. **Why now.** O que existe hoje que não existia há dois anos (modelos baratos, regulação, APIs abertas, mudança de
   comportamento) e destrava um problema antigo?
7. **Inversões.** Pegue uma ideia óbvia e pergunte: e se o cliente fosse outro? e se o agente fizesse o passo caro, não
   o barato? e se o ganho viesse de **evitar** perda em vez de ganhar tempo?

## Passo 3 · Filtrar (10 min)

Aplique os **filtros eliminatórios** (G1 a G7 em [criterios.md](criterios.md)). Quem reprova sai, com o motivo anotado.
Fique com **no máximo 4 finalistas**; mude o status para `finalista`.

## Passo 4 · Aprofundar e pontuar (20 a 30 min)

Para cada finalista, preencha a ficha ([_template-ideia.md](_template-ideia.md)) até onde der em ~7 minutos e rode
`/avaliar-ideias`. Três testes rápidos:

- **Teste dos 30 segundos:** dá para dizer, em uma frase, quem sofre, o que o agente entrega e quem paga?
- **Teste do jurado:** qual a pergunta mais dura que a banca faria? Há resposta hoje?
- **Teste da demo:** o jurado, sozinho e em poucos minutos, consegue **usar** isso e ver trabalho feito? Os dados
  sintéticos são críveis? O fluxo mínimo ponta a ponta cabe em ~6 horas de construção?

## Passo 5 · Decidir (10 min)

- A ideia com maior total na rubrica ganha, **salvo veto fundamentado** do time.
- Empate: prefira a de **melhor demonstrabilidade** e menor risco de execução.
- Registre com `/decisao`: ideia escolhida, alternativas, motivo, riscos assumidos. As demais ficam `descartada` ou
  `arquivada` (nada é apagado).
- Em seguida o agente cria `docs/produto.md` e `docs/arquitetura.md` a partir da ficha, e a fase passa a **2 · Definição**.

## Plano de contingência

Se às **13h00** de sábado não houver decisão: escolha a finalista com maior total, registre como decisão provisória
(`DEC-NNN`, status `provisória`) e comece a construir o fluxo central. Trocar de ideia depois das 14h custa mais do que
seguir com uma ideia 90% boa.

## Armadilhas comuns

- **Wrapper de chat.** Se o produto é uma caixa de conversa sobre um documento, é chatbot. O guia pede agente que fecha o
  processo.
- **Depende de dado real que não temos.** Se a graça só aparece com dado de cliente, a demo não se sustenta.
- **Integração impossível.** Se exige acesso a sistema fechado, só funciona simulada. Simular é permitido quando o agente
  de fato opera sobre o mock e isso é declarado; ainda assim confirme a regra (pergunta 2 do estado).
- **Mercado "grande" sem comprador.** Sem alguém com orçamento e urgência, vira feature.
- **Seis funções pela metade.** Escolha onde ir fundo.
- **Ideia sem exceção.** Se o caminho feliz basta, não demonstra julgamento de agente.

## O que vem depois da decisão

Documentos criados **só após a decisão** (por `/decisao`): `docs/produto.md` (problema, fluxo, exceções, atos com humano,
dados sintéticos, métricas), `docs/arquitetura.md` (componentes, pontos de intervenção humana, integrações simuladas) e,
quando houver código, a seção de evals e custo no [estado](../estado-do-projeto.md).
