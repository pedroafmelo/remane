"use client";

import { useState } from "react";
import { asFailure } from "@/lib/api";
import { trackerApi } from "@/lib/api-tracker";
import { ASSISTANT_SUGGESTIONS } from "@/lib/chat";
import type { Failure } from "@/lib/errors";
import { ChatBubble } from "../ChatBubble";
import { StatusChip } from "../StatusChip";
import { ChatComposer } from "./ChatComposer";
import { Shell } from "./Shell";
import { SessionGate, useSession } from "./session";
import { Card, Muted, Notice } from "./ui";

type Turn = { id: number; from: "person" | "agent"; text: string };

/** Assistente do gestor (FT-08, C7b N2): pergunta em texto livre, resposta só de leitura e montada por modelo de texto. */
export function AssistenteArea() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Failure | null>(null);
  const session = useSession("gestor");

  async function ask(text: string): Promise<boolean> {
    setBusy(true);
    setProblem(null);
    try {
      const reply = await trackerApi.ask(text);
      setTurns((t) => [...t, { id: t.length, from: "person", text }, { id: t.length + 1, from: "agent", text: reply.body }]);
      return true;
    } catch (err) {
      const failure = asFailure(err);
      if (failure.kind === "auth") session.toLogin();
      else setProblem(failure);
      return false;
    } finally {
      setBusy(false);
    }
  }

  if (!session.me) return <SessionGate session={session} />;
  return (
    <Shell who={session.who} area="assistente" onLogout={session.logout}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Assistente</h1>
      <Muted>
        Pergunte sobre a escala publicada, as exceções abertas, a hora extra da semana, uma regra ou o último caso. O assistente só lê: não
        muda escala, não aprova nada e não responde sobre saúde. Sobre lei, cita o cartão de regras com a fonte; não é parecer jurídico.
      </Muted>
      <Card title="Conversa" aside={<StatusChip tone="neutral">SINTÉTICO</StatusChip>}>
        <div className="flex flex-col gap-1 rounded-bubble bg-surface-chat px-3 py-4" aria-live="polite">
          {turns.length === 0 && (
            <ChatBubble mirrored from="agent">
              Oi! Sou o Pat. Posso consultar a escala, as exceções, a hora extra, as regras e o último caso.
            </ChatBubble>
          )}
          {turns.map((t) => (
            <ChatBubble key={t.id} mirrored from={t.from}>
              <span className="whitespace-pre-line">{t.text}</span>
            </ChatBubble>
          ))}
          {busy && <ChatBubble from="typing" mirrored />}
        </div>
        {problem && <Notice>{problem.message}</Notice>}
        <div className="mt-3">
          <ChatComposer suggestions={ASSISTANT_SUGGESTIONS} busy={busy} placeholder="Pergunte ao Pat" onSend={ask} />
        </div>
      </Card>
    </Shell>
  );
}
