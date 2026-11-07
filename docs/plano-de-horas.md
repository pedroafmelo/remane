# Plano de horas

Última atualização: 2026-11-07 16:11 (gate da primeira fatia às 21h30 e noite com 4 pessoas, [DEC-027](decisoes.md) e [DEC-028](decisoes.md); camadas em [plano-implementacao.md](plano-implementacao.md)). **Sugestão**, não compromisso: ajuste ao decidir a ideia e registre em
[estado-do-projeto.md](estado-do-projeto.md). Horário de Brasília. Prazo duro: **dom 13h00**.

## Linha do tempo com gates

| Janela | Fase | Entrega | Gate (se falhar, faça isto) |
|---|---|---|---|
| Sáb 10h30 - 13h00 | 1 · Ideação | Ideia decidida (`DEC-NNN`) | **13h00:** sem consenso, aplicar a contingência de [como-ideiar.md](ideacao/como-ideiar.md) |
| Sáb 14h57 - 15h30 | 2 · Definição (Gate 3, técnica) | `arquitetura.md` (**criado até 15h14 e aprovada às ~15h19**, [DEC-022](decisoes.md)): stack, solver, contratos, evals mínimos (Q5, resolvido). **Ficaram para depois:** hospedagem (Q3, `[PREENCHER]`), divisão de tarefas, esqueleto do repositório, teste de fumaça do modelo e tracing | Sem modelo respondendo e sem tracing: resolver antes de escrever lógica |
| Sáb 15h30 - 19h00 | 3 · Construção | Recorte mínimo: FT-02 (leitura de um formato, solver, verificador, antes e depois) e FT-04 (aprovação), com dados sintéticos e trace desde o início | ~~19h00~~ **21h30 ([DEC-028](decisoes.md)):** primeira fatia vertical no deploy de teste (seção 2 do [plano macro](plano-implementacao.md)); sem ela, aplicar a ordem de corte. **19h:** política fictícia (Pedro Veloso) |
| Sáb 19h00 - Dom 08h30 | 3 · Construção (noite) | Extensões e as outras features (FT-03, FT-01, FT-05, FT-07), na ordem inversa à de corte | 4 pessoas até a madrugada ([DEC-027](decisoes.md)); camadas C6 a C8 em paralelo ([plano macro](plano-implementacao.md)) |
| Dom 08h30 - 10h30 | 3/4 · Construção e medição | Exceções, evals pequenos, rastro, custo por execução | |
| Dom 10h30 - 11h30 | 4 · Polimento | Link público estável com dados pré-carregados; teste como jurado | **11h30:** sem link público funcionando, parar de adicionar funções |
| Dom 11h30 - 13h00 | 5 · Submissão | Vídeo, descrição, material do pitch, declaração de ferramentas, envio | **12h00:** congelar código; só correção de bug crítico depois disso |
| Dom 13h00 | | **Prazo final de submissão** | |
| Dom 16h00 | 6 · Demo Day | Pitch de 3 minutos com demo ao vivo e plano B gravado | |
| Dom 17h30 | | Premiação | |

**Cronograma reescrito às 14h47 a pedido do usuário ([DEC-016](decisoes.md)), como `[PROPOSTA]`.** As janelas fixas do evento (guia)
não mudam: submissão dom 13h00, Demo Day 16h00, premiação 17h30. Os gates de domingo (11h30 link e 12h congelamento) ficam como
estavam. O cronograma anterior previa Definição de 13h a 14h, Construção de 14h a 16h30 e o primeiro ponta a ponta com gate
duro às 17h; foi substituído porque a Definição se estendeu até 14h47 e o v1 cresceu.

Sábado 17h00 a domingo 08h30: o usuário informa que o time **pode continuar** depois das 17h. O guia não diz isso e os
organizadores não confirmaram (pergunta 3 do [estado](estado-do-projeto.md)). O 17h deixa de ser gate duro.

## Divisão sugerida por papéis (ajustar ao tamanho do time)

Com 4 pessoas: **Agente** (lógica, prompts, ferramentas), **Dados e evals** (gerador sintético, mocks, casos rotulados),
**Interface e deploy** (tela e link público), **Negócio** (pitch, vídeo, descrição, submissão e declaração de ferramentas). Com
menos pessoas, junte Dados com Agente e Interface com Negócio. Registrar a divisão real em [estado](estado-do-projeto.md).

## Se o tempo apertar

**Corte primeiro:** polimento visual, notificações, integrações que não aparecem na demo, otimização de custo além do básico.
**Nunca corte:** tratamento de exceções, rastro auditável, evals e o link público testável.

**Para as features do Escalista vale a ordem de corte de [produto.md](produto.md), seção 2** ([DEC-015](decisoes.md)): FT-06, gatilhos
de hora extra, foto do atestado, convenção em PDF, reotimização semanal.

## Situação em 07/11 às 14h42 (auditoria)

- **Atraso verificável:** a fase 2 · Definição estava prevista para 13h00 a 14h00, com `produto.md` e `arquitetura.md`. Às 14h42 o
  `produto.md` está consolidado e aguarda o "aprovado" do Gate 2, a `arquitetura.md` **não existe** e `src/` e `tests/` estão vazios.
  A fase 3 · Construção, prevista a partir das 14h00, não começou. Faltam 2h18 para o gate das 17h00.
- **Escopo:** o v1 cresceu na entrevista ([DEC-014](decisoes.md)). As janelas foram reescritas às 14h47 como `[PROPOSTA]` (ver o
  cronograma acima); o time confirma.

## Itens técnicos a encaixar na construção (Gate 3, `[PROPOSTA]`)

Não mudei as janelas acima (o time ainda não confirmou o cronograma). Itens novos da [arquitetura](arquitetura.md) que precisam de hora:
resgatar o crédito da Featherless (hoje, ação humana); `uv add` e esqueleto; **teste de fumaça dos 2 modelos** e **primeiro benchmark do
solver (60 × 7)**, ambos antes de escrever lógica sobre eles; **deploy de teste da hospedagem** no fim da C0, ainda no sábado ([DEC-027](decisoes.md); antes era "antes de dom 08h30"), com a hospedagem a
decidir nesse momento; SPA React com login e botões de demo; spike de 1 h do WhatsApp só se sobrar horário e houver chip. Cortes técnicos extras em
[arquitetura.md](arquitetura.md), seção 18.

## Marcos concluídos

| Marco | Concluído em |
|---|---|
| Ideia decidida | 2026-11-07 12:16 (DEC-003, provisória) |
| Gate 1: ambiente | 2026-11-07 13:01 (DEC-009) |
| Gate de requisitos | 2026-11-07 13:13 (DEC-011) |
| `produto.md` consolidado | 2026-11-07 14:39 (DEC-015) |
| Gate 2: negócio (`produto.md` aprovado) | 2026-11-07 14:47 (DEC-016) |
| `arquitetura.md` criado | 2026-11-07 15:14 (DEC-018 a DEC-021) |
| Gate 3: técnica (`arquitetura.md` aprovada) | 2026-11-07 ~15:19 (DEC-022) |
| C0a e G0 (esqueleto, contratos v0, teste de fronteiras, `/health`) | 2026-11-07 16:41 (plano da C0) |
| Modelo e tracing funcionando | |
| Plano macro de implementação | 2026-11-07 16:11 (aprovado, DEC-029) |
| Primeiro fluxo ponta a ponta | |
| Evals rodando | |
| Link público estável | |
| Submissão enviada | |
