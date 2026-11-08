# ChatBubble

Uma mensagem da conversa entre o agente e alguém da equipe, usada no celular simulado e no hero.

- `in`: mensagem do colaborador. Fundo `surface`, canto de baixo à esquerda reto.
- `out`: mensagem do agente. Fundo `accent-soft`, canto de baixo à direita reto.
- `system`: evento no meio da conversa ("Carlos aceitou o turno · sem hora extra"). Pílula centralizada.
- Anexo (atestado): rótulo com nome do arquivo e dias, nunca o diagnóstico.
- As mensagens entram com `animate-rise`, uma depois da outra (atraso de ~0,9s), só na demo e no hero. No app real, sem atraso.

O avatar do agente é o `remane-avatar-whatsapp.svg` (Assets › Logos).

```tsx
const shapes = {
  in: "self-start bg-surface rounded-[16px_16px_16px_4px]",
  out: "self-end bg-accent-soft rounded-[16px_16px_4px_16px]",
};

export function ChatBubble({ from = "in", attachment, delay = 0, children }) {
  if (from === "system") {
    return <div className="self-center rounded-full bg-surface px-3 py-1.5 text-xs text-ink-muted motion-safe:animate-rise" style={{ animationDelay: `${delay}s` }}>{children}</div>;
  }
  return (
    <div className={`max-w-[80%] px-3 py-2.5 text-[13px] leading-snug motion-safe:animate-rise ${shapes[from]}`} style={{ animationDelay: `${delay}s` }}>
      {children}
      {attachment && <span className="mt-1.5 block rounded-lg bg-paper px-2 py-1.5 text-xs text-ink-muted">{attachment}</span>}
    </div>
  );
}
```
