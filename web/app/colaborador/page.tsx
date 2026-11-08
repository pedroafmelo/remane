"use client";

import { useCallback, useEffect, useState } from "react";
import { asFailure } from "@/lib/api";
import { excecoesApi } from "@/lib/api-excecoes";
import type { Failure } from "@/lib/errors";
import { dayLabel, faltaDays, faltaReply, receiptText } from "@/lib/excecoes";
import { shiftLabel } from "@/lib/format";
import type { PatEstado } from "@/lib/pat";
import type { MyWeek } from "@/lib/types-excecoes";
import { Button } from "@/components/Button";
import { ChatBubble } from "@/components/ChatBubble";
import { Pat } from "@/components/Pat";
import { Shell } from "@/components/plataforma/Shell";
import { SessionGate, useSession } from "@/components/plataforma/session";
import { Notice } from "@/components/plataforma/ui";

const POLL_MS = 3000;

/** Celular simulado do colaborador (FT-03 mínimo): a semana publicada e o aviso de falta ao Pat. */
export default function ColaboradorPage() {
  const [week, setWeek] = useState<MyWeek | null>(null);
  const [problem, setProblem] = useState<Failure | null>(null);
  const [step, setStep] = useState<"menu" | "dias">("menu");
  const [sending, setSending] = useState<string | null>(null); // dia sendo avisado

  const load = useCallback(async () => {
    try {
      setWeek(await excecoesApi.myWeek());
    } catch (err) {
      setProblem(asFailure(err));
    }
  }, []);
  const session = useSession("colaborador", load);

  const pending = week?.faltas.some((f) => f.status === "pendente") ?? false;
  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [pending, load]);

  async function report(day: string) {
    setSending(day);
    setStep("menu");
    setProblem(null);
    try {
      setWeek(await excecoesApi.reportFalta(day));
    } catch (err) {
      const failure = asFailure(err);
      if (failure.kind === "auth") session.toLogin();
      else setProblem(failure);
    } finally {
      setSending(null);
    }
  }

  if (!session.me) return <SessionGate session={session} />;
  const last = week?.faltas.at(-1);
  const estado: PatEstado = sending
    ? "digitando"
    : last?.status === "pendente"
      ? "excecao"
      : last?.status === "coberta"
        ? "resolveu"
        : "parado";
  const days = week ? faltaDays(week) : [];
  const firstName = week?.employee?.name.split(" ")[0];

  return (
    <Shell who={session.who} onLogout={session.logout}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Sua escala</h1>
      <div className="mx-auto w-full max-w-[380px]">
        <p className="mb-2 text-center text-xs font-medium uppercase tracking-[0.08em] text-ink-muted">celular simulado</p>
        <div className="flex min-h-[640px] flex-col overflow-hidden rounded-[44px] border-[10px] border-ink bg-surface-chat">
          <div className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
            <Pat estado={estado} size={40} />
            <div className="leading-tight">
              <p className="text-[15px] font-semibold">Pat</p>
              <p className="text-xs text-ink-muted">assistente automático do Remane</p>
            </div>
          </div>
          <div className="flex flex-1 flex-col px-3 pt-4" aria-live="polite">
            {!week ? (
              <p role="status" className="text-center text-sm text-ink-muted">
                Carregando…
              </p>
            ) : !week.published || !week.employee ? (
              <>
                <ChatBubble mirrored from="agent">
                  A escala desta semana ainda não foi publicada. Quando a gestora publicar, ela aparece aqui.
                </ChatBubble>
                <ChatBubble from="event">Na demo: entre como gestor, envie a escala de exemplo e aprove.</ChatBubble>
              </>
            ) : (
              <>
                <ChatBubble mirrored from="agent">
                  Oi, {firstName}! Sou o Pat, assistente automático. Esta é a sua semana na {week.employee.store} ({week.employee.job}):
                  <ul className="mt-2 flex flex-col gap-0.5 tabular text-[13.5px]">
                    {week.shifts.map((s) => (
                      <li key={s.start}>
                        {dayLabel(s.day)} · {shiftLabel(s.start, s.end)}
                      </li>
                    ))}
                    {week.shifts.length === 0 && <li>Nenhum turno nesta semana.</li>}
                  </ul>
                </ChatBubble>
                {week.faltas.map((f) => (
                  <div key={f.exception_id}>
                    <ChatBubble mirrored from="person">Vou faltar {dayLabel(f.day)}.</ChatBubble>
                    <ChatBubble mirrored from="agent">{receiptText(f)}</ChatBubble>
                    {f.status === "pendente" ? (
                      <ChatBubble from="event">aguardando a decisão da gestora</ChatBubble>
                    ) : (
                      <ChatBubble mirrored from="agent">{faltaReply(f)}</ChatBubble>
                    )}
                  </div>
                ))}
                {sending && (
                  <>
                    <ChatBubble mirrored from="person">Vou faltar {dayLabel(sending)}.</ChatBubble>
                    <ChatBubble from="typing" />
                  </>
                )}
                {problem && <Notice>{problem.message}</Notice>}
              </>
            )}
          </div>
          {week?.published && week.employee && (
            <div className="flex flex-wrap justify-end gap-2 border-t border-line bg-surface px-3 py-3">
              {step === "menu" ? (
                <Button size="sm" variant="secondary" onClick={() => setStep("dias")} disabled={!!sending || days.length === 0}>
                  Avisar falta
                </Button>
              ) : (
                <>
                  <p className="w-full text-xs text-ink-muted">Qual dia?</p>
                  {days.map((d) => (
                    <Button key={d.day} size="sm" variant="secondary" onClick={() => report(d.day)}>
                      {d.label}
                    </Button>
                  ))}
                  <Button size="sm" variant="secondary" onClick={() => setStep("menu")}>
                    Voltar
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
