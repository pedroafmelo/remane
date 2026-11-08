# ScheduleGrid

A escala da semana de uma loja: uma linha por pessoa, uma coluna por dia, feita de ShiftCell.

- Cabeçalho: nome da loja e período no estilo `title`, e um StatusChip com o resumo das regras.
- Coluna de nomes com 70px; os sete dias dividem o resto (`grid-cols-[70px_repeat(7,minmax(0,1fr))]`).
- No celular, a grade rola na horizontal dentro do cartão; a página nunca rola de lado.
- Recebe os dados da escala do backend; a grade não calcula nada.

```tsx
type Cell = { label: string; state: "shift" | "off" | "absence" | "moved" | "open" };
type Row = { name: string; cells: Cell[] };
const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

export function ScheduleGrid({ title, summary, rows }: { title: string; summary: string; rows: Row[] }) {
  const cols = "grid grid-cols-[70px_repeat(7,minmax(0,1fr))] gap-1.5 items-center";
  return (
    <div className="rounded-card bg-surface p-5 shadow-float flex flex-col gap-2 overflow-x-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-1.5">
        <span className="text-lg font-bold tracking-[-0.02em]">{title}</span>
        <StatusChip>{summary}</StatusChip>
      </div>
      <div className={`${cols} text-xs font-medium text-ink-muted min-w-[560px]`}>
        <span />{DAYS.map((d) => <span key={d}>{d}</span>)}
      </div>
      {rows.map((r) => (
        <div key={r.name} className={`${cols} min-w-[560px]`}>
          <span className="text-sm font-medium">{r.name}</span>
          {r.cells.map((c, i) => <ShiftCell key={i} state={c.state}>{c.label}</ShiftCell>)}
        </div>
      ))}
    </div>
  );
}
```
