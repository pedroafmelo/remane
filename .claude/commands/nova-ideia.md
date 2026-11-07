---
description: Registra uma nova ideia no backlog de ideação (ficha + linha na tabela + estado)
argument-hint: <ideia em uma frase>
---

Registre a ideia abaixo no processo de ideação do projeto.

Ideia: $ARGUMENTS

Passos:

1. Leia `docs/ideacao/backlog-ideias.md` e descubra o próximo ID (`IDEA-NNN`, sequencial, nunca reutilizar).
2. Crie `docs/ideacao/ideias/IDEA-NNN-<slug>.md` a partir de `docs/ideacao/_template-ideia.md`. Preencha só o que a
   frase do usuário permite. O resto fica como `[PREENCHER]`. Não invente dado de mercado, número ou fonte.
3. Adicione a linha na tabela do backlog com status `candidata` e pontuação `—` (pontuar é trabalho de
   `/avaliar-ideias`).
4. Adicione uma linha em "Registro de atualizações" de `docs/estado-do-projeto.md` e ajuste a data de
   "Última atualização".
5. Responda com: o ID criado, o que ficou em aberto na ficha e as 2 perguntas mais úteis para amadurecê-la
   (priorize as perguntas da frente de negócio do guia: quem sofre, quanto custa, quem paga, why now).
