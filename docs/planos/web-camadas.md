# Plano por camadas: o que falta da interface web (Remane)

Última atualização: 2026-11-08 09:37 (Recife), por Claude (Opus 5.5). **Status: aprovado pelo usuário em 08/11.** W2 no PR #23;
W8: link trocado nos docs e pitch com a medição do link público (09:44). Falta o percurso no celular no link público e limpar o banco.

Base: `origin/main` em **b6f4a01** (merge do PR #22, depois de #16, #20 e #21), buscado por HTTPS às 09:05 (o SSH do GitHub recusou
a conexão). Branch local `docs/web-camadas`.

Gates do `web/` nessa base, tal como saíram: `npm run typecheck` exit 0; `npm run lint` exit 0; `npm test` 48 testes, 48 passam;
`npm run build` exit 0, 9 rotas estáticas (`/`, `/entrar`, `/plataforma`, `/plataforma/excecoes`, `/plataforma/impacto`,
`/plataforma/regras`, `/colaborador`, `/icon.svg`, `/_not-found`).

**Resumo:** a interface já cobre todas as rotas da API e todos os fluxos v1 que têm backend. O que falta é pouco e é de polimento,
de verificação no link público e de narrativa. Por isso este plano tem **3 camadas, não 9**: W1–W7 do ponto de partida foram
descartadas ou reduzidas por não terem lacuna (seção 2).

---

## 1. Mapa de lacunas

### 1.1 Rotas da API × interface

Toda rota da API tem cliente em `web/lib/` e uma tela que a chama **[FATO]** (conferido por busca no código):

| Rota | Cliente | Tela |
|---|---|---|
| `POST /auth/demo/{papel}`, `/auth/logout`, `GET /api/me` | `lib/api.ts` | `/entrar`, `Shell` |
| `POST /api/runs`, `/runs/next-week`, `/runs/{id}/confirm`, `/approve`; `GET /runs/{id}`, `/schedule`, `/trace` | `lib/api.ts` | `/plataforma` (Escala); `trace` também em Impacto |
| `GET /api/schedules/published`, `/api/roster`, `/api/demo/files/{nome}` | `lib/api.ts`, `lib/confirm.ts` | `/plataforma` |
| `GET /api/exceptions`, `POST /api/exceptions/{id}/decide` | `lib/api-excecoes.ts` | `/plataforma/excecoes` |
| `GET /api/colaborador/escala`, `POST /api/colaborador/falta` | `lib/api-excecoes.ts` | `/colaborador` |
| `GET /api/rules`, `POST /api/simulate/vigencia`, `GET /api/impact` | `lib/api-insights.ts` | Regras, Impacto |

### 1.2 Percurso no navegador (08/11, 09:10–09:15)

Feito na **main local** (b6f4a01, `DEMO_MODE=1`, banco novo, **sem chave da Featherless**), em 1440 px e em 375 × 812 (celular).
O link público não serviu para isso: às 09:11 o bundle de `remane.up.railway.app` ainda não tinha as telas do C6 (o deploy de
b6f4a01 aparecia como pendente no GitHub). Fluxos percorridos: gestor envia o exemplo XLSX, confirma a leitura, aprova e publica;
Exceções; Impacto; Regras; colaborador avisa falta; landing.

| # | Lacuna | Fonte | Rótulo |
|---|---|---|---|
| L1 | A loja aparece pelo id interno: "Loja l-loja-sintetica-centro" nas abas e no título da grade, e "l-loja-sintetica-centro" na cobertura-alvo da confirmação. O celular do colaborador mostra o nome certo ("Loja Sintética Norte"). | `web/components/plataforma/ScheduleView.tsx:35` e `:42` usam `storeId`; `web/lib/confirm.ts:177` cai no id quando o nome não vem | [FATO] na tela |
| L1b | Causa, medida pela API às 09:40: (a) a grade nunca usa nome, só `storeId`; (b) num banco novo, `GET /api/roster` responde 404 até a primeira confirmação, então a cobertura-alvo da primeira execução só tem o id; (c) o CSV padrão traz ids `L1`–`L3`, que não batem com os do quadro (`l-loja-sintetica-*`, com nome). O resumo já traz `store_ids`; o comentário "PEDIDO ao backend" em `web/lib/types.ts` está desatualizado. | `scratchpad/measure.py`, saída de 08/11 09:40 | [FATO] |
| L2 | O id longo da execução aparece no cabeçalho: "Execução run-1f67…". | `web/app/plataforma/page.tsx:188` | [FATO] |
| L3 | Com a main atual, o exemplo XLSX dá economia de **R$ 5.533,15**, mas a cobertura **cai de 95,69% para 84,39%** (faixas sem cobertura de 42 para 401). O painel de capacidade avisa que o quadro só cobre cerca de 80% da demanda inferida. O `docs/pitch.md` (vídeo, cena 5) ainda diz "cobertura de 95 para 100%". A tela é honesta ("cobrir menos custa menos"); o problema é a narrativa. | tela Antes e depois; `docs/pitch.md`, seção 2 | [FATO] local, sem modelo; no Railway, com modelo, **não verificado** |
| L3b | A régua da cobertura mudou: antes do C6, 1.704 h normais cobriam 100% da demanda; agora 2.400 h cobrem 84,39%. A demanda passou a ser inferida da escala antiga (2.774,5 pessoa-hora), então a queda parece vir dessa régua nova, e não só do piso de contrato do #16. | tela Antes e depois de hoje cedo × a de agora | [INFERÊNCIA] |
| L3c | Medição dos 3 cenários pela API (main local b6f4a01, sem modelo, texto livre vazio, 08/11 09:40). Ver a tabela abaixo. O custo e as horas são **iguais** nos três: a economia não depende do alvo. | `scratchpad/measure.py` | [FATO] local; **confirmado no link público em 08/11 09:44** (com modelo): mesmos custos e coberturas, 393 faixas em vez de 401; XLSX completo em ~61 s e US$ 0,0069 de modelo |
| L4 | Os docs ainda apontam o link antigo (`escalista-converge-production.up.railway.app`, que agora responde 404 "Application not found"). | `docs/entrega.md`, `docs/estado-do-projeto.md`, `docs/pitch.md`, `docs/plano-implementacao.md`, `docs/planos/whatsapp-cloud-api.md` | [FATO] |
| L5 | O deploy de b6f4a01 no link novo não estava concluído às 09:11. | status do commit no GitHub: `pending`; bundle sem os textos do C6 | [FATO] às 09:11; o estado atual não foi conferido |
| L6 | O banco do link público guarda dados de teste: escala publicada antes do #16 (R$ 13.975, cobertura 100%), uma falta decidida e uma execução parada em "Aguardando a aprovação". O Impacto mostra esses números até alguém publicar de novo. | `remane.up.railway.app/plataforma/` às 09:10 | [FATO] |
| L7 | Textos com id interno vindos do backend: "Gatilho: cct_repouso_semanal" no cartão RX-01; títulos de regra sem acento ("Pol aviso hora extra estourando"), gerados a partir do id. | `src/escalista/api/excecoes.py:215`; `src/escalista/api/insights.py:73` | [FATO]; o conserto é no backend, fora deste plano |
| L8 | Sem chave da Featherless, a justificativa do Pat não aparece e a leitura do XLSX abre RX-12 ("li sem o modelo"). No Railway há chave. | tela local | [FATO] local; no Railway com C6, **não verificado** |

**Medição L3c** (demanda inferida 2.774,5 pessoa-hora; capacidade do quadro 2.400 pessoa-hora; cabe no máximo 80%; otimização
de 4,0 a 4,7 s localmente):

| Cenário | Custo antes → depois | Horas normais | Horas extras | Cobertura antes → depois | Faixas sem cobertura | Violações |
|---|---|---|---|---|---|---|
| XLSX, alvo 100% (padrão) | R$ 33.989,15 → R$ 28.456,00 | 2.520 → 2.400 | 216,5 → 0 | 95,69% → 84,39% | 42 → 401 | 158 → 0 |
| XLSX, ajustado para caber (80%) | R$ 33.989,15 → R$ 28.456,00 | 2.520 → 2.400 | 216,5 → 0 | 97,04% → 98,5% *da demanda-alvo* | 40 → 66 | 158 → 0 |
| CSV padrão | R$ 33.989,15 → R$ 28.456,00 | 2.520 → 2.400 | 216,5 → 0 | 95,69% → 84,39% | 42 → 401 | 158 → 0 |

Economia nos três: R$ 5.533,15. Com 80%, a cobertura é medida contra a demanda reduzida, não contra a demanda inteira.

**Sem lacuna encontrada [FATO]:** em 375 px nenhuma página (Escala, Exceções, Impacto, Regras, landing, colaborador) tem rolagem
horizontal (`scrollWidth = 375`); a grade rola dentro do próprio quadro. Os 6 campos da confirmação têm `<label>`. Colaborador:
semana, aviso de falta e espera pela decisão funcionam no celular. Exceções: o contador da aba aparece.

**Não verificado:** movimento reduzido; leitor de tela; PDF; exemplo com defeitos (RX-13); "planejar próxima semana"; decisão da
RX-01; simulação 44 h × 42 h na main atual; texto livre "Algo a considerar nesta semana?"; nada disso no link público com o C6.

---

## 2. Camadas

O ponto de partida tinha W0–W8. Ficam **W0 (feita), W2 reduzida e W8**:

| Camada | Decisão | Por quê |
|---|---|---|
| W0 · Base e verificação | **Feita** neste plano | Base, gates e mapa nas seções 0 e 1 |
| W1 · Fundações | Descartada | Todas as rotas têm cliente e tela; os gates passam. Sem lacuna compartilhada. |
| W2 · Escala | **Reduzida a L1 e L2** | Únicas lacunas de front na Escala |
| W3 · Exceções | Descartada | Funciona; L7 é texto do backend |
| W4 · Impacto e Regras | Descartada | Funciona; L7 é texto do backend |
| W5 · Colaborador | Descartada | Funciona no celular |
| W6 · Landing e entrada | Descartada | Sem lacuna no percurso; CTA "Testar a demo" leva a `/entrar` |
| W7 · Transversal | Absorvida pela W8 | Responsivo conferido; o que falta conferir (movimento reduzido) é verificação |
| W8 · Verificação final | **Mantida** | L3–L6 e o "não verificado" acima |

### W2 · Escala: nome das lojas e cabeçalho da execução

- **Objetivo e o que o jurado vê:** "Loja Sintética Centro" no lugar de "Loja l-loja-sintetica-centro" (abas, título da grade,
  cobertura-alvo), e um cabeçalho de execução sem o id longo (só a fase e a hora de início).
- **Pode criar ou editar (dono exclusivo):** `web/components/plataforma/ScheduleView.tsx`, `web/lib/grid.ts`,
  `web/lib/grid.test.ts` (ou um teste novo `web/lib/store-names.test.ts`), e só a linha 188 de `web/app/plataforma/page.tsx`.
- **Não pode tocar:** `web/lib/types.ts`, `web/lib/api.ts`, `Shell.tsx`, `session.tsx`, `ui.tsx`, `Summary.tsx`, `confirm.ts`
  (é do C6), backend, contratos.
- **Dependências:** a pergunta P1 (seção 5). Se os ids do XLSX não baterem com os do quadro, não há nome a mostrar sem mudança no
  backend. Nesse caso a W2 faz só L2 e o resto vira pedido ao backend.
- **Pronto quando:** `npm run typecheck && npm run lint && npm test && npm run build` passam; no navegador, gestor → exemplo XLSX
  → confirmar → as abas e o título mostram o nome da loja; a escala vigente também; o cabeçalho não mostra `run-…`.
- **Estimativa [PROPOSTA]:** 30 a 60 min, se P1 for resolvida no front; 15 min só para L2.
- **Contra:** é cosmético, e `page.tsx` foi muito mexido pelo C6, então qualquer edição ali pode conflitar com quem ainda mexe na
  Escala. Se o tempo apertar, L2 é a primeira a cair.

### W8 · Verificação final no link público e docs

- **Objetivo e o que o jurado vê:** o link `remane.up.railway.app` rodando b6f4a01 (ou o que vier depois), com o banco limpo, um
  fluxo completo que funciona, e docs, pitch e vídeo com os números que a tela mostra.
- **Pode editar (dono exclusivo):** `docs/pitch.md` (números e cena 5), a linha do link em `docs/entrega.md`, e a linha própria
  no topo do registro de `docs/estado-do-projeto.md`. Troca do link antigo nos outros 3 docs da L4.
- **Não pode tocar:** código (`web/`, `src/`), `docs/decisoes.md` (só se P2 virar decisão, com o próximo número livre conferido em
  `origin/main` na hora).
- **Dependências:** W2 mergeada (se entrar); deploy concluído; banco limpo pelo dono do Railway (P3); P2 decidida.
- **Pronto quando:**
  1. `curl https://remane.up.railway.app/health` responde `ok`, e o bundle tem o texto "Como o arquivo foi entendido".
  2. No navegador: gestor → exemplo → confirmar → aprovar → colaborador avisa falta → gestor decide → grade e celular atualizados →
     Impacto → Regras com a simulação. Tempos medidos com cronômetro e anotados com data e hora.
  3. Repetir o passo 2 em 375 px.
  4. `docs/pitch.md` com a economia, a cobertura e o tempo medidos no passo 2; nenhum doc com o link antigo
     (`grep -r escalista-converge-production docs` só acha registros históricos e este plano).
- **Estimativa [PROPOSTA]:** 30 a 45 min, sem contar a espera do deploy.
- **Contra:** depende de gente fora do front (Railway, decisão de narrativa). Se o deploy atrasar, os números do pitch ficam
  sem medição no link público até perto das 13h.

### Grafo e paralelismo

```
P1 ──► W2 ──► (merge pelo dono) ──► deploy ──► W8
P2 ───────────────────────────────────────────► W8 (pitch.md)
P3 (limpar banco) ────────────────────────────► W8
```

W2 e a parte de docs da W8 (L4, link antigo) rodam em paralelo com segurança: não compartilham arquivo. A verificação da W8
(passos 1–3) espera o deploy final.

---

## 3. Riscos de conflito encontrados

- **`web/app/plataforma/page.tsx`:** o C6 (#21) mudou 63 linhas aqui, e é o arquivo da Escala. A W2 toca uma linha; quem estiver
  mexendo na Escala deve saber.
- **`docs/pitch.md`:** o PR #22 já mexeu nas pendências (economia de R$ 5.533). Os números da cena 5 e do slide 4a são do mesmo
  dono que a W8; ninguém mais deve editá-los ao mesmo tempo.
- **`docs/estado-do-projeto.md` e `docs/decisoes.md`:** três PRs (#20, #21, #22) escreveram neles em menos de 2 horas. Reler logo
  antes de editar e só acrescentar a própria linha.
- **`.claude/launch.json` (pasta acima do repositório):** a configuração `app-local` agora apaga `var/local-preview.db` ao subir.
  Ela não está no git.

---

## 4. Perguntas que travam a execução

| # | Pergunta | Recomendação |
|---|---|---|
| P1 | ~~De onde vem o nome da loja?~~ Respondida pela medição (L1b): no exemplo XLSX, a W2 resolve no front usando o nome do quadro quando existir (grade e cobertura). O 404 do quadro na primeira execução e os ids `L1`–`L3` do CSV ficam com o dono do C6. | W2 faz o front; levar (b) e (c) ao dono do C6, sem bloquear. |
| P2 | Qual cenário mostrar no vídeo e no pitch? | **Recomendação: XLSX com alvo 100% (padrão).** É o que o jurado vai ver se testar sozinho, e conta a história mais forte: zero violação, zero hora extra, R$ 5.533 a menos, e o Remane mostra que **o quadro não fecha** (a demanda pede 2.774,5 pessoa-hora; as 60 pessoas dão 2.400; a escala antiga cobria a diferença com 216,5 h de hora extra e 158 violações). O cenário de 80% dá "98,5%", mas de uma demanda reduzida: é fácil de derrubar numa pergunta da banca. Remedir no link público depois do deploy. |
| P3 | Quem limpa o banco do Railway e quando? | O dono do Railway, logo depois do último merge e antes de gravar o vídeo. |
| P4 | ~~O link antigo deve voltar a funcionar?~~ | **Decidido (08/11):** fica só `remane.up.railway.app`; a W8 troca o link nos docs. |
