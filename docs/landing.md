# Landing Remane: handoff de design

> Handoff original da landing, mantido como referência de marca, tokens, copy e movimento. **Onde diverge do repositório, vale a
> [DEC-035](decisoes.md):** a landing fica em `web/` com export estático servido pelo FastAPI (não Vercel), e o botão "Testar a demo"
> leva a `/entrar` (não `/app`). **A copy e a seção "Fim da 6x1" abaixo foram substituídas pela [DEC-036](decisoes.md)**; o texto em vigor está no código. Código: `web/app/page.tsx` e `web/components/`. **Toda menção a WhatsApp abaixo está
> superada pela [DEC-069](decisoes.md)** (2026-11-08 11:31): o canal é um chat dentro do app; não há botão nem QR do WhatsApp.


Leia este arquivo inteiro antes de começar.

## Contexto
Remane é um digital worker que monta a escala de trabalho de lojas dentro da CLT, da convenção coletiva e da EC 141 (fim da escala 6x1), e cobre faltas conversando com a equipe pelo WhatsApp. Projeto do hackathon Converge Challenge powered by Tako (submissão: domingo 8/11, 13h).

- Design System (tokens, componentes com JSX + Tailwind, logos em SVG): https://claude.ai/artifact/8Bg2WxFALVjNyQ34zZU3Jf
- Canvas de identidade (referência visual: board "Rodada 2 · Claro"): https://claude.ai/artifact/7PJDjV9qDYG43zqtQSAvHC
- Se conseguir ler os links, leia primeiro o README.md e o desenvolvimento.md do Design System. Se não conseguir, use os tokens abaixo, que são os mesmos.

## Stack e estrutura
- Next.js (App Router) + TypeScript + Tailwind v4, deploy na Vercel (remane.vercel.app). Sem domínio próprio por enquanto.
- Landing em `/`. A plataforma vai morar em `/app` no mesmo projeto: o botão "Testar a demo" aponta para `/app` (pode ser uma página placeholder por enquanto).
- Fonte: pacote `geist` (`GeistSans.variable` no `<html>`). Uma família só; nada de fonte mono.
- Componentes em `components/` com os nomes do Design System: Logo, Button, StatusChip, ShiftCell, ScheduleGrid, ChatBubble, ImpactStat.
- Comece o repositório do zero hoje (o hackathon pode pedir o histórico de commits).

## Tokens (app/globals.css)
```css
@import "tailwindcss";

@theme {
  --font-sans: var(--font-geist-sans), "Helvetica Neue", Arial, sans-serif;
  --color-paper: #f3f4f1;
  --color-surface: #ffffff;
  --color-surface-chat: #f7f7f4;
  --color-line: #e4e5e1;
  --color-line-strong: #d5d7d1;
  --color-ink: #17181a;
  --color-ink-muted: #5f6368;
  --color-ink-subtle: #686c73;
  --color-accent: #2bd48a;
  --color-accent-soft: #2bd48a2e;
  --color-accent-strong: #0b7a4b;
  --color-warning: #e8890c;
  --color-warning-ink: #a35a00;
  --color-warning-soft: #fdf1e2;
  --color-danger: #c93838;
  --color-danger-soft: #fbeaea;
  --radius-cell: 10px;
  --radius-bubble: 16px;
  --radius-card: 24px;
  --radius-panel: 32px;
  --shadow-float: 0 30px 60px -30px rgba(23, 24, 26, 0.35);
  --shadow-accent: 0 8px 20px -8px #2bd48a;
  --animate-drift: drift 14s ease-in-out infinite alternate;
  --animate-pop: pop 400ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  --animate-rise: rise 500ms ease-out both;
  @keyframes drift { 0% { background-position: 0% 0%, 100% 0%, 50% 100%; } 100% { background-position: 30% 20%, 70% 30%, 40% 70%; } }
  @keyframes pop { 0% { transform: scale(0.86); opacity: 0.35; } 70% { transform: scale(1.04); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
  @keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
  @keyframes slide { 0%, 15% { transform: translate(0, 0); } 35%, 85% { transform: translate(6px, -6px); } 100% { transform: translate(0, 0); } }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}

.panel-live {
  background:
    radial-gradient(60% 70% at 15% 20%, #2bd48a88 0%, transparent 60%),
    radial-gradient(50% 60% at 85% 15%, #2bd48a55 0%, transparent 65%),
    radial-gradient(70% 70% at 60% 95%, #ffffff 0%, transparent 60%),
    #e9ece6;
  background-size: 140% 140%;
}
.tabular { font-variant-numeric: tabular-nums; }
```

## Regras visuais
- Fundo `paper`, cartões `surface` com `rounded-card` (24px), seções/painéis com `rounded-panel` (32px), botões e chips em pílula.
- Títulos em Geist 700 com tracking negativo (hero: 72px, -0.055em, line-height 0.98; seções: 48px, -0.045em). Texto em Geist 400. Rótulos 12–13px peso 500. Números com `tabular`.
- `accent` (verde-menta) só marca o que o agente fez (turno remanejado, mensagens do agente). Texto sobre accent é sempre `ink`. Nunca use accent como fundo de botão nem como cor de texto (para verde em texto: `accent-strong`).
- O painel vivo (`panel-live animate-drift`) aparece uma vez por página: no hero.
- Movimento só onde tem propósito: painel em deriva, turno remanejado com `animate-pop`, mensagens com `animate-rise` em sequência (~0,9s entre elas), bloco do logo deslizando (`slide`, 4s) só no logo do topo.
- Responsivo até 375px: a grade de escala rola na horizontal dentro do próprio cartão; a página nunca rola de lado. Foco visível em tudo que é clicável.
- Nada de emoji, nada de degradê roxo-azul, nada de cartão com borda colorida na lateral.

## Movimento (decidido com o Pedro em 7/11, sobrepõe "Regras visuais" onde conflitar)
- **Hero com história na rolagem:** abaixo dos botões, o painel vivo fica fixo (sticky) enquanto a rolagem (~260vh) conduz o caso da Joana em 6 passos: (0) escala "tudo conforme" → (1) chega a mensagem da Joana → (2) célula dela vira "atestado" com contorno `warning`, chip vira "1 turno descoberto · qua 14h" (warning) e o agente aparece "digitando" → (3) agente responde → (4) Carlos passa de 7–15h para 14–22h com `animate-pop` em accent + evento "Carlos aceitou o turno · sem hora extra" → (5) "Pronto, turno coberto…" e chip volta a "tudo conforme". Legenda com bolinhas de progresso abaixo do painel. Rolar para cima desfaz.
- **Links e botões de âncora não atravessam a história:** salto instantâneo até perto do destino e rolagem suave só no trecho final, para não parecer um corte seco.
- **Fim da 6x1:** seção estática (linha do tempo + três fatos), sem animação de rolagem.
- **Como funciona:** 4 passos fixos à esquerda; o visual da direita troca conforme o passo ativo (regras → grade → chat → exceção). No celular vira lista simples.
- **Demais seções:** entram uma vez com subir-e-aparecer.
- **Reduced motion:** tudo parado, já no estado final da história.
- Protótipo de referência (descartável) validado com o Pedro antes de construir.

## Logo
Símbolo SVG (viewBox "0 0 70 64"): quadrados 16x16 com rx 5 em ink nas posições (4,4) (24,4) (44,4) (4,24) (24,24) (4,44) (24,44) (44,44); o nono em accent em (50,18) (deslocado). Na versão animada, o accent começa em (44,24) com um contorno tracejado line-strong no lugar vazio, e desliza com `slide`. Ao lado: "remane" em minúsculas, Geist 500, tracking -0.06em. Favicon: fundo ink com cantos arredondados e o símbolo em branco + accent.

## Seções da landing (copy pronta, pode ajustar)
1. **Nav**: Logo animado · links "Como funciona", "Fim da 6x1", "WhatsApp" (âncoras) · botão "Testar a demo" (ink, pílula) → `/app`.
2. **Hero** (centralizado, como o jota.ai):
   - Pílula: "EC 141 promulgada · 42h a partir de 15 de dezembro"
   - H1: "Sua escala se remaneja sozinha."
   - Lead: "Um agente que monta a escala dentro da lei e cobre faltas pelo WhatsApp antes de o gestor abrir o celular."
   - Botões: "Testar a demo" (primário) e "Falar com o agente no WhatsApp" (secundário, link wa.me, número em variável de ambiente `NEXT_PUBLIC_WHATSAPP_NUMBER`).
   - Abaixo, o painel vivo com dois cartões flutuando (shadow-float): ScheduleGrid "Loja Boa Viagem · 14 a 20 de dezembro" com chip "42h · 2 folgas · tudo conforme" (linhas: Ana, Bruno, Carlos, Joana, Diego; na quarta, Joana = atestado, Carlos = 14–22h remanejado) e uma conversa de WhatsApp: Joana "Bom dia, não vou conseguir ir hoje. Mandei o atestado." (anexo "atestado.jpg · 1 dia") → agente "Recebi, Joana. Atestado ok, melhoras. Já estou cobrindo seu turno das 14h." → evento "Carlos aceitou o turno · sem hora extra" → agente "Pronto, turno coberto. A gestora já foi avisada."
3. **O problema**: título "Hoje, a escala vive numa planilha e as faltas, no WhatsApp do gerente." Três cartões: "Hora extra cara" / "Turno descoberto no pico" / "Passivo trabalhista" (uma frase cada).
4. **Fim da 6x1** (id `fim-da-6x1`): título "A lei mudou. A escala de todo mundo vai ter que mudar." Linha do tempo real (é uma sequência, então numeração faz sentido): 16/10/2026 EC 141 promulgada → ~15/12/2026 jornada máxima de 42h e 2 folgas por semana → ~dez/2027 jornada máxima de 40h. Três fatos: "≈ 15 milhões de pessoas trabalham hoje em 6x1 (MTE)", "salário não pode cair, então a hora fica cerca de 10% mais cara", "2 folgas semanais, uma preferencialmente no domingo". Nota pequena: "Datas e números conforme o texto da EC 141; confira o texto oficial."
5. **Como funciona** (id `como-funciona`), 4 passos em ordem:
   1. "Lê as regras": lei + convenção coletiva viram regras com a origem de cada uma; o DP confere uma vez.
   2. "Monta a escala": um otimizador cobre a demanda ao menor custo, sem violar regra; o gestor aprova.
   3. "Resolve o dia a dia": falta, atraso, atestado e troca chegam pelo WhatsApp; o agente encontra quem pode cobrir e confirma.
   4. "Chama você só quando precisa": o que custa dinheiro ou foge da regra vira exceção, com opções e custo.
6. **WhatsApp** (id `whatsapp`): "Teste agora: mande uma mensagem como se fosse a Joana." QR code (lib `qrcode.react`) para `https://wa.me/${NEXT_PUBLIC_WHATSAPP_NUMBER}?text=Bom%20dia%2C%20n%C3%A3o%20vou%20conseguir%20ir%20hoje`. Se a variável não existir, mostre o botão "Testar a demo" no lugar do QR.
7. **Para quem**: "Redes de varejo, food service e farmácia com 5 a 200 lojas que fazem escala em planilha."
8. **CTA final**: "Sua próxima falta já pode chegar resolvida." + botão "Testar a demo".
9. **Rodapé**: logo, "Feito no Converge Challenge powered by Tako · Recife, 2026", "Demo com dados sintéticos."

## Não fazer
- Não inventar números de resultado (clientes, % de economia, depoimentos). Nada de logos de empresas reais.
- Não usar imagem de pessoas.
- Não colocar preço como fato; se houver seção de preço, marcar "em validação".

## Pronto quando
- `npm run build` sem erros, Lighthouse sem erro de contraste, funciona em 375px e em 1440px.
- Publicado na Vercel com o botão "Testar a demo" levando para `/app`.
