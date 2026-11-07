# Plano de horas

Última atualização: 2026-11-07 12:16. **Sugestão**, não compromisso: ajuste ao decidir a ideia e registre em
[estado-do-projeto.md](estado-do-projeto.md). Horário de Brasília. Prazo duro: **dom 13h00**.

## Linha do tempo com gates

| Janela | Fase | Entrega | Gate (se falhar, faça isto) |
|---|---|---|---|
| Sáb 10h30 - 13h00 | 1 · Ideação | Ideia decidida (`DEC-NNN`) | **13h00:** sem consenso, aplicar a contingência de [como-ideiar.md](ideacao/como-ideiar.md) |
| Sáb 13h00 - 14h00 | 2 · Definição | `produto.md` e `arquitetura.md` enxutos; divisão de tarefas; esqueleto do repositório; modelo e tracing testados | Sem modelo respondendo e sem tracing: resolver antes de escrever lógica |
| Sáb 14h00 - 16h30 | 3 · Construção | Fluxo central do agente com dados sintéticos | |
| Sáb 16h30 - 17h00 | 3 · Construção | **Primeiro fluxo ponta a ponta rodando** | **17h00:** sem fluxo ponta a ponta, cortar escopo (ver "Se o tempo apertar") |
| Dom 08h30 - 10h30 | 3/4 · Construção e medição | Exceções, evals pequenos, rastro, custo por execução | |
| Dom 10h30 - 11h30 | 4 · Polimento | Link público estável com dados pré-carregados; teste como jurado | **11h30:** sem link público funcionando, parar de adicionar funções |
| Dom 11h30 - 13h00 | 5 · Submissão | Vídeo, descrição, material do pitch, declaração de ferramentas, envio | **12h00:** congelar código; só correção de bug crítico depois disso |
| Dom 13h00 | | **Prazo final de submissão** | |
| Dom 16h00 | 6 · Demo Day | Pitch de 3 minutos com demo ao vivo e plano B gravado | |
| Dom 17h30 | | Premiação | |

Sábado 17h00 a domingo 08h30: o guia não define se o trabalho pode continuar fora do local (pergunta em aberto no
[estado](estado-do-projeto.md)).

## Divisão sugerida por papéis (ajustar ao tamanho do time)

Com 4 pessoas: **Agente** (lógica, prompts, ferramentas), **Dados e evals** (gerador sintético, mocks, casos rotulados),
**Interface e deploy** (tela e link público), **Negócio** (pitch, vídeo, descrição, submissão e declaração de ferramentas). Com
menos pessoas, junte Dados com Agente e Interface com Negócio. Registrar a divisão real em [estado](estado-do-projeto.md).

## Se o tempo apertar

**Corte primeiro:** polimento visual, notificações, integrações que não aparecem na demo, otimização de custo além do básico.
**Nunca corte:** tratamento de exceções, rastro auditável, evals e o link público testável.

## Marcos concluídos

| Marco | Concluído em |
|---|---|
| Ideia decidida | 2026-11-07 12:16 (DEC-003, provisória) |
| Modelo e tracing funcionando | |
| Primeiro fluxo ponta a ponta | |
| Evals rodando | |
| Link público estável | |
| Submissão enviada | |
