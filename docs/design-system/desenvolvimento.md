# Usando no Next + Tailwind

Tudo aqui sai dos tokens deste sistema. Copie para o projeto e use as classes do Tailwind com os nomes da marca (`bg-paper`, `text-ink`, `bg-accent`, `rounded-card`...).

## 1. Fonte (Geist)

```bash
npm i geist
```

```tsx
// app/layout.tsx
import { GeistSans } from "geist/font/sans";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={GeistSans.variable}>
      <body className="bg-paper text-ink font-sans antialiased">{children}</body>
    </html>
  );
}
```

## 2. Tailwind v4 (globals.css)

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

  --text-display: 72px;
  --text-display--line-height: 0.98;
  --text-display--letter-spacing: -0.055em;
  --text-display--font-weight: 700;

  --animate-drift: drift 14s ease-in-out infinite alternate;
  --animate-pop: pop 400ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  --animate-rise: rise 500ms ease-out both;

  @keyframes drift {
    0% { background-position: 0% 0%, 100% 0%, 50% 100%; }
    100% { background-position: 30% 20%, 70% 30%, 40% 70%; }
  }
  @keyframes pop {
    0% { transform: scale(0.86); opacity: 0.35; }
    70% { transform: scale(1.04); opacity: 1; }
    100% { transform: scale(1); opacity: 1; }
  }
  @keyframes rise {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: none; }
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}

/* O painel vivo: use em um elemento por página */
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

Usando:

```tsx
<h1 className="text-display font-bold">Sua escala se remaneja sozinha.</h1>
<section className="panel-live animate-drift rounded-panel p-9">...</section>
<span className="rounded-cell bg-accent text-ink shadow-accent animate-pop">14–22h</span>
```

## 3. Tailwind v3 (se o projeto ainda usar)

```js
// tailwind.config.js
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["var(--font-geist-sans)", "Helvetica Neue", "Arial", "sans-serif"] },
      colors: {
        paper: "#f3f4f1", surface: "#ffffff", "surface-chat": "#f7f7f4",
        line: "#e4e5e1", "line-strong": "#d5d7d1",
        ink: "#17181a", "ink-muted": "#5f6368", "ink-subtle": "#686c73",
        accent: "#2bd48a", "accent-soft": "#2bd48a2e", "accent-strong": "#0b7a4b",
        warning: "#e8890c", "warning-ink": "#a35a00", "warning-soft": "#fdf1e2",
        danger: "#c93838", "danger-soft": "#fbeaea",
      },
      borderRadius: { cell: "10px", bubble: "16px", card: "24px", panel: "32px" },
      boxShadow: { float: "0 30px 60px -30px rgba(23,24,26,0.35)", accent: "0 8px 20px -8px #2bd48a" },
    },
  },
};
```

## 4. Componentes

Cada componente na aba Components tem um preview e um trecho em JSX + Tailwind pronto para colar. Os nomes batem com as telas da plataforma:

| Componente | Onde aparece |
|---|---|
| Logo | Topo da landing e da plataforma, avatar do WhatsApp |
| Button | Todas as telas |
| StatusChip | Escala, Exceções, Impacto |
| ShiftCell | Escala |
| ScheduleGrid | Escala, hero da landing |
| ExceptionCard | Exceções |
| ChatBubble | Celular simulado, hero da landing |
| ImpactStat | Impacto |
