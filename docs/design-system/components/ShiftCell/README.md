# ShiftCell

Uma célula da grade de escala: o que uma pessoa faz em um dia.

| Estado | Visual | Quando |
|---|---|---|
| `shift` | fundo `paper`, horário em `ink` | turno normal |
| `off` | borda tracejada `line-strong`, "folga" em `ink-subtle` | folga |
| `absence` | listras, texto riscado | atestado, falta, férias |
| `moved` | fundo `accent`, `shadow-accent`, entra com "pop" | turno que o agente remanejou |
| `open` | fundo `warning-soft`, borda `warning` | turno descoberto que virou exceção |

Só um estado `moved` acende por evento. Depois de 24h ele volta a `shift`.

```tsx
const base = "h-[38px] rounded-cell flex items-center justify-center text-xs font-medium tabular";
const variants = {
  shift: "bg-paper text-ink",
  off: "border border-dashed border-line-strong text-ink-subtle",
  absence: "text-ink-subtle line-through bg-[repeating-linear-gradient(135deg,#f7f7f4_0_6px,#e4e5e1_6px_12px)]",
  moved: "bg-accent text-ink shadow-accent motion-safe:animate-pop",
  open: "bg-warning-soft text-warning-ink border border-warning",
};

export function ShiftCell({ state = "shift", children }) {
  return <span className={`${base} ${variants[state]}`}>{children}</span>;
}
```
