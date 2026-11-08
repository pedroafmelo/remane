# Remane

> **Design system do Remane**, copiado do artefato do claude.ai (<https://claude.ai/artifact/8Bg2WxFALVjNyQ34zZU3Jf>) em 08/11.
> **O código de verdade está em `web/`:** tokens em `web/app/globals.css`, componentes em `web/components/` (mesmos nomes).
> **Copy desatualizada:** "Sua escala se remaneja sozinha", a Joana e o selo da EC 141 que aparecem aqui e nos previews foram
> substituídos pela [DEC-036](../decisoes.md) ("O engenheiro da sua escala de trabalho.", Patrick, sem a 6x1 no centro).
> Para ver um componente, abra `components/<Nome>/preview.html` no navegador; o guia de uso no Next está em [desenvolvimento.md](desenvolvimento.md).


Sua escala se remaneja sozinha.

Remane é um agente que monta a escala de trabalho dentro da CLT, da convenção coletiva e da EC 141, e cobre faltas conversando com a equipe pelo WhatsApp. O nome vem de **remanejar**, o verbo que todo gestor de loja usa quando alguém falta.

Este sistema vale para a landing page, a plataforma (Regras, Escala, Exceções, Impacto) e o canal do WhatsApp. Ele nasceu da direção "Claro" do canvas de identidade.

## Princípios

1. **O agente trabalha, a tela mostra.** A interface é para acompanhar e aprovar, não para operar. O que o agente fez aparece em verde (`accent`); o que precisa de uma pessoa aparece em laranja (`warning`).
2. **Leve, não frio.** Fundo claro (`paper`), cartões brancos com cantos generosos (`radius-lg`, `radius-xl`), pouca linha, nenhum excesso de borda. A referência é o tom do Jota, não um painel corporativo.
3. **Títulos com peso, texto calmo.** Títulos em Geist 700 com tracking apertado; todo o resto em Geist 400–500. Nada de fonte de código: números usam Geist com algarismos tabulares.
4. **Movimento com propósito.** Só três coisas se mexem: o fundo do painel (deriva lenta), o turno remanejado (acende) e as mensagens (entram em sequência). Com "reduzir movimento" ativado, tudo fica parado.

## Voz e conteúdo

- Português do Brasil, direto, de igual para igual com quem gerencia loja. "Faltou alguém? Já está coberto." e não "Otimize sua força de trabalho".
- O agente fala na primeira pessoa no WhatsApp ("Recebi, Joana. Já estou cobrindo seu turno."). Na plataforma, a interface descreve o que aconteceu ("Carlos aceitou o turno · sem hora extra").
- Horários sempre como `14–22h` (meia-risca, sem minutos quando são cheios). Datas como `14 a 20 de dezembro`. Jornada como `42h`.
- Nunca mostre diagnóstico de atestado. O máximo é "atestado · 1 dia · válido".
- Botões dizem a ação: "Aprovar escala", "Cobrir com hora extra", "Testar a demo".

## Cor

| Token | Uso |
|---|---|
| `paper` #F3F4F1 | Fundo de página e turno comum na grade |
| `surface` #FFFFFF | Cartões |
| `ink` #17181A | Texto, botão primário, símbolo |
| `ink-muted` #5F6368 | Texto secundário |
| `accent` #2BD48A | O que o agente remanejou ou resolveu. Fundo, nunca texto |
| `accent-strong` #0B7A4B | Verde como texto ou ícone |
| `warning` #E8890C / `warning-ink` #A35A00 | Exceção: precisa de uma pessoa |
| `danger` #C93838 | Violação de regra |

Regras:
- Texto sobre `accent` é sempre `ink`. Branco sobre o verde não passa em contraste.
- Uma tela tem, no máximo, um elemento grande em `accent`. Ele marca a ação do agente, não decora.
- `warning` e `danger` são estados, nunca cor de marca.

## Tipografia

Uma família só: **Geist** (Vercel, licença aberta OFL), carregada pelo Google Fonts ou pelo pacote `geist` no Next.

- `display` 72px/700, `heading-1` 48px/700, `heading-2` 32px/600, `title` 18px/700: tracking negativo.
- `lead` 18px, `body` 15px, `message` 13px: peso 400.
- `label`, `cell`, `eyebrow`: 12–13px, peso 500.
- `wordmark`: "remane" em minúsculas, 500, tracking -0.06em. Não use o wordmark como título.
- Em qualquer número que se alinha (horários, horas, custos): `font-variant-numeric: tabular-nums`.

## Forma e espaço

- Cantos: célula de turno `radius-sm` (10px), balão `radius-md` (16px), cartão `radius-lg` (24px), painel `radius-xl` (32px), botões e chips em pílula (`radius-full`).
- Espaço em múltiplos de 4px: `space-2` entre linhas da grade, `space-6` dentro de cartões, `space-24` entre seções da landing.
- Sombras só em cartões que flutuam sobre o painel em degradê (`shadow-float`). O turno remanejado leva `shadow-accent`.

## O painel vivo

O fundo do hero e das seções de destaque é um degradê de três manchas radiais (duas em `accent` com transparência, uma branca) sobre `#E9ECE6`, que se move devagar (14s, ida e volta). Os cartões brancos flutuam por cima com `shadow-float`. É a assinatura visual da marca: aparece uma vez por página.

## Movimento

| O quê | Como |
|---|---|
| Painel em degradê | `background-position` em 14s, `ease-in-out`, alternado, infinito |
| Turno remanejado | entra com escala .86 → 1.04 → 1 em 400ms, depois fica parado |
| Bloco do símbolo | desliza 6px para cima e para a direita, 4s em loop (só no logo animado) |
| Mensagens | sobem 10px com fade em 500ms, uma depois da outra (~0,9s de intervalo) |
| Hover de botão | 160ms, `cubic-bezier(0.2, 0.8, 0.2, 1)` |

Sempre dentro de `@media (prefers-reduced-motion: no-preference)`.

## Logo

O símbolo é a grade da semana com um bloco sendo remanejado: oito quadrados em `ink` e um em `accent`, deslocado para fora do lugar. Arquivos em Assets › Logos. Ao lado do símbolo, o nome "remane" no estilo `wordmark`. Espaço livre mínimo em volta: a largura de um quadrado.

