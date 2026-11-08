# ExceptionCard

Um caso que o agente não conseguiu resolver dentro das regras, já com as opções e o custo de cada uma.

Estrutura, sempre nesta ordem:
1. StatusChip `warning` "precisa de você" e a hora do evento.
2. Título: o que está em jogo, em uma linha ("Turno de sábado, 14–22h, sem cobertura").
3. O que o agente já tentou, na primeira pessoa, em uma ou duas frases.
4. Opções, cada uma com o custo à direita (dinheiro, horas ou impacto na cobertura).
5. A regra que impediu o agente de resolver, com a origem (lei ou cláusula) e a versão das regras.
6. Botões: a opção que custa dinheiro usa o Button `warning`; as outras, `secondary`.

Os valores das opções vêm do backend; a interface não calcula custo.

```tsx
export function ExceptionCard({ time, title, tried, options, rule, onPick }) {
  return (
    <article className="rounded-card bg-surface p-6 flex flex-col gap-3.5 max-w-[560px]">
      <div className="flex items-center justify-between">
        <StatusChip tone="warning">precisa de você</StatusChip>
        <span className="text-xs font-medium text-ink-muted tabular">{time}</span>
      </div>
      <h3 className="text-lg font-bold tracking-[-0.02em]">{title}</h3>
      <p className="text-[15px] leading-relaxed text-ink-muted">{tried}</p>
      <ul className="flex flex-col gap-2">
        {options.map((o) => (
          <li key={o.id} className="flex items-center justify-between gap-3 rounded-bubble bg-paper px-3.5 py-3 text-sm">
            <span>{o.label}</span><span className="font-medium tabular whitespace-nowrap">{o.cost}</span>
          </li>
        ))}
      </ul>
      <p className="border-t border-line pt-3 text-xs font-medium text-ink-muted">{rule}</p>
      <div className="flex flex-wrap gap-2">
        {options.filter((o) => o.action).map((o) => (
          <Button key={o.id} size="sm" variant={o.costsMoney ? "warning" : "secondary"} onClick={() => onPick(o.id)}>{o.action}</Button>
        ))}
      </div>
    </article>
  );
}
```
