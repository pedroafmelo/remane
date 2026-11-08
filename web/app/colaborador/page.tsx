"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { asFailure } from "@/lib/api";
import { trackerApi } from "@/lib/api-tracker";
import type { Failure } from "@/lib/errors";
import type { PatEstado } from "@/lib/pat";
import {
  PERSON_STORAGE_KEY,
  attachmentsByCase,
  caseStateLines,
  deadlineLabel,
  inboundText,
  isOpenCase,
  isAttachmentOnly,
  isOpenOffer,
  offerText,
  outboundText,
  personOptionLabel,
  pickPerson,
  questionText,
  reportDays,
} from "@/lib/tracker";
import type { Inbox, PeopleList, ReportInput } from "@/lib/types-tracker";
import { Button } from "@/components/Button";
import { ChatBubble } from "@/components/ChatBubble";
import { Pat } from "@/components/Pat";
import { StatusChip } from "@/components/StatusChip";
import { useClockChange } from "@/components/plataforma/DemoClockBar";
import { ReportForm } from "@/components/plataforma/ReportForm";
import { Shell } from "@/components/plataforma/Shell";
import { SessionGate, useSession } from "@/components/plataforma/session";
import { Notice } from "@/components/plataforma/ui";

const POLL_MS = 3000;

function storedPerson(): string | null {
  try {
    return window.localStorage.getItem(PERSON_STORAGE_KEY);
  } catch {
    return null;
  }
}

function rememberPerson(id: string) {
  try {
    window.localStorage.setItem(PERSON_STORAGE_KEY, id);
  } catch {
    // sem armazenamento (janela privada): a escolha só vale nesta visita
  }
}

type Step = { kind: "menu" } | { kind: "form"; report: ReportInput["kind"] };

/** Celular simulado do colaborador (FT-03): semana, caixa do Pat, avisos com anexo, ofertas e perguntas do agente. */
export default function ColaboradorPage() {
  const [people, setPeople] = useState<PeopleList | null>(null);
  const [personId, setPersonId] = useState<string | null>(null);
  const [inbox, setInbox] = useState<Inbox | null>(null);
  const [now, setNow] = useState<string | null>(null);
  const [problem, setProblem] = useState<Failure | null>(null);
  const [step, setStep] = useState<Step>({ kind: "menu" });
  const [sending, setSending] = useState(false);
  const current = useRef<string | null>(null);

  const loadPeople = useCallback(async () => {
    try {
      const list = await trackerApi.people();
      setPeople(list);
      setPersonId(pickPerson(list, storedPerson()));
    } catch (err) {
      setProblem(asFailure(err));
    }
  }, []);
  const session = useSession("colaborador", loadPeople);

  const loadInbox = useCallback(async () => {
    const id = current.current;
    if (!id) return;
    try {
      const box = await trackerApi.inbox(id);
      if (current.current !== id) return; // a pessoa mudou durante a chamada: descarta a resposta velha
      setInbox(box);
      setNow(box.now);
      setProblem(null);
    } catch (err) {
      if (current.current === id) setProblem(asFailure(err));
    }
  }, []);

  useEffect(() => {
    current.current = personId;
    if (personId) void loadInbox();
  }, [personId, loadInbox]);

  useClockChange(() => void loadInbox());

  useEffect(() => {
    if (!personId || sending) return;
    const timer = setInterval(() => {
      if (!document.hidden) void loadInbox();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [personId, sending, loadInbox]);

  function choosePerson(id: string) {
    rememberPerson(id);
    setInbox(null);
    setStep({ kind: "menu" });
    setPersonId(id);
  }

  async function act(fn: () => Promise<unknown>) {
    setSending(true);
    setProblem(null);
    try {
      await fn();
      await loadInbox();
    } catch (err) {
      const failure = asFailure(err);
      if (failure.kind === "auth") session.toLogin();
      else setProblem(failure);
    } finally {
      setSending(false);
    }
  }

  const report = (kind: ReportInput["kind"], day: string, text: string, file: File | null) => {
    if (!personId) return;
    setStep({ kind: "menu" });
    return act(() => trackerApi.report({ as: personId, day, kind, text, file }));
  };
  const answerOffer = (offerId: string, accept: boolean) => personId && act(() => trackerApi.answerOffer(offerId, personId, accept));
  const answerQuestion = (caseId: string, coming: boolean) => personId && act(() => trackerApi.answerQuestion(personId, caseId, coming));

  if (!session.me) return <SessionGate session={session} />;

  const cases = inbox?.cases ?? [];
  const openOffers = inbox?.offers.filter(isOpenOffer) ?? [];
  const questions = inbox?.questions ?? [];
  const lastCase = cases.at(-1);
  const estado: PatEstado = sending
    ? "digitando"
    : openOffers.length > 0 || questions.length > 0
      ? "excecao"
      : cases.some(isOpenCase)
        ? "trabalhando"
        : lastCase?.status === "coberto" || lastCase?.status === "decidido"
          ? "resolveu"
          : "parado";
  const days = inbox ? reportDays(inbox.shifts) : [];
  const allMessages = inbox?.messages ?? [];
  const attachments = attachmentsByCase(allMessages);
  const messages = allMessages.filter((m) => !isAttachmentOnly(m)).sort((a, b) => a.at.localeCompare(b.at));
  const caseById = new Map(cases.map((c) => [c.case_id, c]));
  const firstName = inbox?.employee.name.split(" ")[0];

  return (
    <Shell who={session.who} onLogout={session.logout} clock="colaborador">
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Sua escala</h1>
      <div className="mx-auto w-full max-w-[380px]">
        <div className="mb-2 flex items-center justify-center gap-2">
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-ink-muted">celular simulado</p>
          <StatusChip tone="neutral">SINTÉTICO</StatusChip>
        </div>
        {people && (
          <div className="mb-3 flex items-center justify-center gap-2 text-sm">
            <label htmlFor="voce-e" className="font-medium">
              Você é:
            </label>
            <select
              id="voce-e"
              value={personId ?? ""}
              onChange={(e) => choosePerson(e.target.value)}
              disabled={sending}
              className="max-w-[240px] rounded-bubble border border-line-strong bg-surface px-3 py-1.5 text-[14px]"
            >
              {people.people.map((p) => (
                <option key={p.id} value={p.id}>
                  {personOptionLabel(p)}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="flex min-h-[640px] flex-col overflow-hidden rounded-[44px] border-[10px] border-ink bg-surface-chat">
          <div className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
            <Pat estado={estado} size={40} />
            <div className="leading-tight">
              <p className="text-[15px] font-semibold">Pat</p>
              <p className="text-xs text-ink-muted">assistente automático do Remane</p>
            </div>
          </div>
          <div className="flex flex-1 flex-col px-3 pt-4" aria-live="polite">
            {!inbox ? (
              problem ? null : (
                <p role="status" className="text-center text-sm text-ink-muted">
                  Carregando…
                </p>
              )
            ) : (
              <>
                <ChatBubble mirrored from="agent">
                  Oi, {firstName}! Sou o Pat, assistente automático. Esta é a sua semana na {inbox.employee.store} ({inbox.employee.job}):
                  <ul className="mt-2 flex flex-col gap-0.5 tabular text-[13.5px]">
                    {days.map((d) => (
                      <li key={d.day}>{d.label}</li>
                    ))}
                    {days.length === 0 && <li>Nenhum turno nesta semana.</li>}
                  </ul>
                </ChatBubble>
                {messages.map((m) =>
                  m.direction === "out" ? (
                    <ChatBubble key={m.id} mirrored from="agent">
                      {outboundText(m)}
                    </ChatBubble>
                  ) : (
                    <ChatBubble key={m.id} mirrored from="person">
                      {inboundText(m, m.case_id ? caseById.get(m.case_id) : undefined, m.case_id ? attachments.get(m.case_id) : null)}
                    </ChatBubble>
                  ),
                )}
                {cases.map((c) => (
                  <ChatBubble key={c.case_id} from="event">
                    <span className="flex flex-col items-center gap-0.5 text-center">
                      {caseStateLines(c).map((line) => (
                        <span key={line}>{line}</span>
                      ))}
                    </span>
                  </ChatBubble>
                ))}
                {questions.map((q) => (
                  <div key={q.case_id} className="pb-2.5">
                    <ChatBubble mirrored from="agent">
                      {questionText(q)}
                    </ChatBubble>
                    <div className="flex flex-wrap justify-start gap-2 pb-1">
                      <Button size="sm" onClick={() => answerQuestion(q.case_id, true)} disabled={sending}>
                        Estou a caminho
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => answerQuestion(q.case_id, false)} disabled={sending}>
                        Não vou
                      </Button>
                    </div>
                  </div>
                ))}
                {openOffers.map((o) => (
                  <div key={o.offer_id} className="pb-2.5">
                    <ChatBubble mirrored from="agent">
                      Um colega precisa de cobertura. {offerText(o)}. Responda {deadlineLabel(o.deadline, now)}.
                    </ChatBubble>
                    <div className="flex flex-wrap justify-start gap-2 pb-1">
                      <Button size="sm" onClick={() => answerOffer(o.offer_id, true)} disabled={sending}>
                        Aceitar
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => answerOffer(o.offer_id, false)} disabled={sending}>
                        Recusar
                      </Button>
                    </div>
                  </div>
                ))}
                {sending && <ChatBubble from="typing" mirrored />}
              </>
            )}
            {problem && <Notice>{problem.message}</Notice>}
          </div>
          {inbox && (
            <div className="flex flex-wrap justify-end gap-2 border-t border-line bg-surface px-3 py-3">
              {step.kind === "menu" ? (
                <>
                  <Button size="sm" variant="secondary" onClick={() => setStep({ kind: "form", report: "falta" })} disabled={sending || days.length === 0}>
                    Vou faltar
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => setStep({ kind: "form", report: "atraso" })} disabled={sending || days.length === 0}>
                    Vou me atrasar
                  </Button>
                </>
              ) : (
                <ReportForm
                  kind={step.report}
                  days={days}
                  busy={sending}
                  onSubmit={(day, text, file) => report(step.report, day, text, file)}
                  onCancel={() => setStep({ kind: "menu" })}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
