# Logo

Símbolo da grade com o bloco remanejado, seguido do nome "remane" em minúsculas.

- Versão animada (o bloco desliza 6px para cima e para a direita em loop de 4s) só no topo da landing e na tela de carregamento. Em todo o resto, a versão parada, com o bloco já deslocado.
- Sobre fundo claro: quadrados `ink`. Sobre fundo escuro: quadrados `surface`. O bloco é sempre `accent`.
- Tamanho mínimo do símbolo: 20px de largura.

```tsx
export function Logo({ animated = false, inverse = false }) {
  const cell = inverse ? "fill-surface" : "fill-ink";
  const cells = [[4,4],[24,4],[44,4],[4,24],[24,24],[4,44],[24,44],[44,44]];
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg width="28" height="26" viewBox="0 0 70 64" aria-hidden="true">
        {cells.map(([x, y]) => <rect key={`${x}-${y}`} className={cell} x={x} y={y} width="16" height="16" rx="5" />)}
        <rect
          className={`fill-accent ${animated ? "motion-safe:animate-[slide_4s_ease-in-out_infinite]" : ""}`}
          x={animated ? 44 : 50} y={animated ? 24 : 18} width="16" height="16" rx="5"
        />
      </svg>
      <span className={`text-[22px] font-medium tracking-[-0.06em] ${inverse ? "text-surface" : "text-ink"}`}>remane</span>
    </span>
  );
}
```

Para o loop do bloco, adicione no `globals.css`:
`@keyframes slide { 0%,15%{transform:translate(0,0)} 35%,85%{transform:translate(6px,-6px)} 100%{transform:translate(0,0)} }`
