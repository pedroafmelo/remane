---
description: Audita as docs contra o estado real do repositório e corrige a defasagem
---

Faça uma auditoria de sincronia entre a documentação e o repositório.

Passos:

1. Levante o estado real: `git status`, `git log --oneline` (últimos commits), conteúdo de `src/` e `tests/`,
   `pyproject.toml`, `.env.example` (só os nomes das variáveis) e a hora atual (`date`).
2. Compare com as docs e liste cada divergência:
   - `docs/estado-do-projeto.md`: fase, ideia escolhida, próximas ações, perguntas em aberto, métricas medidas.
   - `docs/declaracao-ferramentas.md`: toda dependência, modelo, API ou serviço de terceiros em uso está listado? Há
     item listado que não é mais usado?
   - `docs/plano-de-horas.md`: marcos concluídos e atrasos.
   - `docs/decisoes.md`: há decisão tomada na conversa ou no código sem registro?
   - `docs/ideacao/backlog-ideias.md`: os status refletem a realidade?
   - Links quebrados entre os arquivos de `docs/`.
3. Corrija o que for fato verificável. O que for ambíguo, **pergunte** em vez de escrever.
4. Registre a auditoria em "Registro de atualizações" de `docs/estado-do-projeto.md` e atualize a data.
5. Responda com o que mudou e o que ficou pendente de decisão humana.
