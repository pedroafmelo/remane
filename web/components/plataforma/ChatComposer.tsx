"use client";

import { useId, useState } from "react";
import { CHAT_MAX_CHARS, chatCounter, chatInputError } from "@/lib/chat";
import { Button } from "../Button";

type Props = {
  suggestions: string[];
  busy: boolean;
  placeholder: string;
  onSend: (text: string) => Promise<boolean>;
};

/** Campo de texto livre com contador de 300 e sugestões que só preenchem o campo (C7b). Enter envia. */
export function ChatComposer({ suggestions, busy, placeholder, onSend }: Props) {
  const id = useId();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const problem = chatInputError(text);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    if (await onSend(text.trim())) setText("");
  }

  return (
    <div className="flex w-full flex-col gap-2">
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5" aria-label="Sugestões">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setText(s);
                setError(null);
              }}
              disabled={busy}
              className="rounded-full border border-line-strong bg-surface px-3 py-1 text-[13px] hover:bg-surface-chat disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <label htmlFor={id} className="sr-only">
          Mensagem
        </label>
        <textarea
          id={id}
          value={text}
          rows={2}
          maxLength={CHAT_MAX_CHARS}
          placeholder={placeholder}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          className="min-h-[44px] flex-1 resize-none rounded-bubble border border-line-strong bg-surface px-3 py-2 text-[14px] focus-visible:outline-2"
        />
        <Button size="sm" type="submit" disabled={busy}>
          Enviar
        </Button>
      </form>
      <div className="flex justify-between text-xs text-ink-muted">
        <span role={error ? "alert" : undefined} className={error ? "text-danger" : undefined}>
          {error ?? "Não envie diagnóstico nem CID: o atestado basta."}
        </span>
        <span className="tabular">{chatCounter(text)}</span>
      </div>
    </div>
  );
}
