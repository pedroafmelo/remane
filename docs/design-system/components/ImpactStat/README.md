# ImpactStat

Um número de resultado na tela de Impacto, com rótulo em cima e contexto embaixo.

- Rótulo diz o que foi medido em linguagem de gestor ("Faltas cobertas sem o gestor").
- Valor em 40px/700 com algarismos tabulares; a unidade fica menor, em `ink-muted`.
- Embaixo, uma barra em `accent` (quando é proporção) ou uma nota de origem ("medido no trace", "premissa do time").
- Os números do preview são exemplos. Na plataforma, eles vêm do trace (Langfuse); o que for estimativa leva a nota "premissa".

```tsx
export function ImpactStat({ label, value, unit, ratio, note }) {
  return (
    <div className="rounded-card bg-surface p-5 flex flex-col gap-2">
      <span className="text-[13px] font-medium text-ink-muted">{label}</span>
      <span className="text-[40px] font-bold tracking-[-0.045em] leading-none tabular">
        {value}{unit && <small className="text-lg font-medium tracking-[-0.02em] text-ink-muted"> {unit}</small>}
      </span>
      {ratio != null && (
        <div className="h-1.5 rounded-full bg-paper overflow-hidden"><div className="h-full rounded-full bg-accent" style={{ width: `${ratio * 100}%` }} /></div>
      )}
      {note && <span className="text-xs text-ink-muted">{note}</span>}
    </div>
  );
}
```
