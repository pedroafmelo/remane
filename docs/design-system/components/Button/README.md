# Button

Botão em pílula; o texto diz exatamente a ação.

- **Primário** (`ink`): uma ação principal por tela ("Aprovar escala", "Testar a demo").
- **Secundário** (`surface` com borda `line-strong`): ações de apoio.
- **Exceção** (`warning-soft` com texto `warning-ink`): só dentro de um cartão de exceção, para a opção que custa dinheiro.
- Nunca use `accent` como fundo de botão: o verde é reservado para o que o agente já fez.

```tsx
const styles = {
  primary: "bg-ink text-surface",
  secondary: "bg-surface text-ink border border-line-strong",
  warning: "bg-warning-soft text-warning-ink border border-warning",
};

export function Button({ variant = "primary", size = "md", ...props }) {
  const pad = size === "sm" ? "px-3.5 py-2 text-[13px]" : "px-5 py-3 text-[15px]";
  return (
    <button
      className={`rounded-full font-medium transition-transform duration-150 hover:-translate-y-px focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-ink ${pad} ${styles[variant]}`}
      {...props}
    />
  );
}
```
