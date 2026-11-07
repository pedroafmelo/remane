---
description: Registra uma decisão do time e propaga o efeito para as docs afetadas
argument-hint: <decisão em uma frase>
---

Registre esta decisão do time: $ARGUMENTS

Passos:

1. Leia `docs/decisoes.md` e descubra o próximo `DEC-NNN`.
2. Acrescente a entrada (formato do arquivo): contexto, decisão, alternativas consideradas, consequências e
   quem decidiu. Registre só o que o usuário disse. Se o motivo não foi dito, escreva `[motivo não informado]` e
   pergunte.
3. Propague, conforme o tipo de decisão:
   - **Ideia escolhida:** status `escolhida` no backlog, as demais ideias viram `descartada` ou `arquivada` (nada é
     apagado). Preencha "Ideia escolhida" em `docs/estado-do-projeto.md`, mude a fase para "Definição" e crie
     `docs/produto.md` (problema, fluxo ponta a ponta, exceções, atos que exigem humano, dados sintéticos, métricas)
     e `docs/arquitetura.md` a partir da ficha da ideia. Ajuste `docs/plano-de-horas.md`.
   - **Stack, modelo, API ou serviço:** atualize `docs/declaracao-ferramentas.md`.
   - **Corte ou mudança de escopo:** atualize `docs/estado-do-projeto.md` e `docs/plano-de-horas.md`.
   - **Regra do evento:** atualize `docs/contexto-hackathon.md` e `docs/regras-e-integridade.md`.
4. Adicione uma linha em "Registro de atualizações" e ajuste a data de "Última atualização" no estado do projeto.
5. Responda com a lista de arquivos alterados.
