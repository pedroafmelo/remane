# StatusChip

Pílula pequena que diz o estado de uma escala, de um evento ou de uma regra.

- `neutral`: resumo informativo ("42h · 2 folgas · tudo conforme").
- `ok`: o agente resolveu sozinho. Ponto em `accent-strong`.
- `warning`: precisa de uma pessoa. Sempre leva a uma exceção.
- `danger`: uma regra foi violada. Raro: o agente não publica escala com violação.

O estado é dito em texto, nunca só pela cor.

```tsx
const tones = {
  neutral: "bg-paper text-ink",
  ok: "bg-accent-soft text-ink",
  warning: "bg-warning-soft text-warning-ink",
  danger: "bg-danger-soft text-danger",
};
const dots = { ok: "bg-accent-strong", warning: "bg-warning", danger: "bg-danger" };

export function StatusChip({ tone = "neutral", children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-[7px] text-xs font-medium ${tones[tone]}`}>
      {tone !== "neutral" && <span className={`size-[7px] rounded-full ${dots[tone]}`} />}
      {children}
    </span>
  );
}
```
