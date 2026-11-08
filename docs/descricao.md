# Remane: o engenheiro da sua escala de trabalho

## Problema
Toda empresa que trabalha com turnos precisa montar escala: da sanduicheria do bairro à startup em crescimento e à rede consolidada. Na prática, cada gestor faz de um jeito, em planilha, papel, sistema próprio ou mensagem. As regras ficam espalhadas entre a lei, a convenção coletiva e a política interna, e cada um interpreta do seu modo. Montar e conferir a escala vira burocracia: horas de trabalho manual e retrabalho a cada mudança. A falta de padrão gera hora extra que ninguém planejou, turno descoberto e regra trabalhista descumprida (repouso semanal, interjornada, domingo, limite de hora extra) sem que ninguém perceba. Quando alguém falta, começa a corrida para achar quem cubra, quase sempre com hora extra.

## Para quem
Qualquer operação com turnos, de um único ponto de venda a redes com dezenas de unidades. Atende o dono ou o gestor que monta a escala, o Departamento Pessoal que responde por ela e o colaborador que a recebe e avisa as faltas. A demo usa uma rede fictícia de 3 lojas e 60 colaboradores.

## Solução
O gestor envia a escala como ela já existe, em XLSX, CSV ou PDF, no formato que tiver. O Remane padroniza os dados, mostra o que entendeu e espera a confirmação. Em seguida, monta a melhor escala possível dentro da lei, da convenção coletiva e da política da empresa. A escala de antes e a nova aparecem lado a lado, com custo, hora extra e cobertura. Durante a semana, quando o colaborador avisa uma falta, o agente procura quem pode cobrir sem hora extra e leva ao gestor um cartão com as opções, o custo de cada uma e uma recomendação. Nada é publicado sem aprovação humana.

## Como o agente funciona
Um grafo LangGraph com paradas para decisão humana: ler, confirmar, otimizar, verificar, comparar, justificar, aprovar e publicar. 

O modelo de linguagem lê arquivos, conversa e explica, mas nunca calcula escala, hora ou custo. Quem calcula é um solver (OR-Tools CP-SAT), e um verificador independente confere cada regra antes da aprovação. 

As regras ficam num cartão de regras em dados, em três camadas (lei, convenção e política), e cada uma traz a cláusula de origem. Assim, toda escala segue o mesmo padrão, e trocar a política ou a lei muda a escala sem mexer no código. O que foge da regra vira um cartão de exceção, e quem decide é sempre uma pessoa. Cada passo fica num rastro auditável, com custo e tempo.

## Resultado medido (escala de exemplo, dados sintéticos, link público, 08/11/2026)
- **Violações de regra:** de 158 para 0
- **Horas extras:** de 216,5 h para 0
- **Custo da semana:** de R$ 33.989,15 para R$ 28.456,00, uma economia de R$ 5.533,15 (16,3%)
- **Cobertura:** O agente mostra que, dentro da regra, o quadro só dá conta de cerca de 80% da demanda da semana (2.400 de 2.774,5 pessoa-hora)
- **Performance:** A execução completa leva cerca de 61 s e gasta US$ 0,007 de modelo

## Por que agora
A EC 141 leva a jornada para 42 h com dois repousos semanais a partir de dezembro de 2026. Toda empresa com turnos vai precisar refazer as escalas, e a maioria ainda não sabe como.

## Como testar
No link, clique em "Testar a demo" e entre como gestor ou como colaborador, sem senha. A conversa com o colaborador acontece num celular simulado dentro do próprio app.

---
*Todos os dados são sintéticos. A convenção e a política são fictícias.*