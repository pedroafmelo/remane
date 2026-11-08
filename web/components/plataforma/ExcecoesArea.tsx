"use client";

import { useCallback, useState } from "react";
import { api, asFailure } from "@/lib/api";
import { excecoesApi } from "@/lib/api-excecoes";
import type { Failure } from "@/lib/errors";
import { toExceptionView } from "@/lib/exception";
import { dueLabel, trackRunId } from "@/lib/excecoes";
import { timeBr } from "@/lib/format";
import { roleLabel } from "@/lib/roles";
import type { TraceEvent } from "@/lib/types";
import type { ExceptionItem, ExceptionQueue } from "@/lib/types-excecoes";
import { Button } from "../Button";
import { ExceptionCard } from "../ExceptionCard";
import { Pat } from "../Pat";
import { useClockChange } from "./DemoClockBar";
import { Shell } from "./Shell";
import { SessionGate, useSession } from "./session";
import { TracePanel } from "./Trace";
import { Card, Muted, Notice } from "./ui";

type Choice = { id: string; index: number };
type CaseTrace = { runId: string; title: string; events: TraceEvent[] };

/** Fila de exceções do gestor (FT-04): abertas com as opções e o custo, a escolha confirmada, depois o histórico. */
export function ExcecoesArea() {
  const [queue, setQueue] = useState<ExceptionQueue | null>(null);
  const [problem, setProblem] = useState<Failure | null>(null);
  const [choice, setChoice] = useState<Choice | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [caseTrace, setCaseTrace] = useState<CaseTrace | null>(null);

  // auditoria do caso (passo 6 do roteiro): o mesmo rastro das execuções, lido de `track-<case_id>`
  async function showTrace(item: ExceptionItem) {
    const runId = trackRunId(item);
    if (!runId) return;
    setProblem(null);
    try {
      setCaseTrace({ runId, title: item.card.title, events: await api.trace(runId) });
      requestAnimationFrame(() => document.getElementById("rastro-caso")?.scrollIntoView({ behavior: "smooth" }));
    } catch (err) {
      const failure = asFailure(err);
      if (failure.kind === "auth") session.toLogin();
      else setProblem(failure);
    }
  }

  const load = useCallback(async () => {
    try {
      setQueue(await excecoesApi.queue());
    } catch (err) {
      setProblem(asFailure(err));
    }
  }, []);
  const session = useSession("gestor", load);
  // o relógio avançou ou a demo reiniciou: os cartões novos (cobertura, ponto) chegam sem recarregar a página
  useClockChange(() => {
    setDone(null);
    void load();
  });

  async function decide(c: Choice) {
    setBusy(true);
    setProblem(null);
    try {
      const item = await excecoesApi.decide(c.id, c.index);
      setDone(item.decision ? `${item.card.title}: ${item.decision.outcome}` : null);
      setChoice(null);
      await load();
    } catch (err) {
      const failure = asFailure(err);
      if (failure.kind === "auth") session.toLogin();
      else setProblem(failure);
    } finally {
      setBusy(false);
    }
  }

  if (!session.me) return <SessionGate session={session} />;
  const open = queue?.open ?? [];
  return (
    <Shell who={session.who} area="excecoes" badges={{ excecoes: open.length }} onLogout={session.logout} busy={busy}>
      <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.035em]">Exceções</h1>
      <Muted>O que o Pat não resolveu dentro das regras. Cada cartão traz o contexto, as opções com o custo e a recomendação; quem decide é você.</Muted>
      {problem && <Notice>{problem.message}</Notice>}
      {done && (
        <p role="status" className="rounded-bubble bg-accent-soft px-4 py-3 text-[15px] font-medium">
          {done}
        </p>
      )}
      {!queue ? (
        <p role="status" className="text-ink-muted">
          Carregando a fila…
        </p>
      ) : open.length === 0 ? (
        <Card title="Fila" id="fila">
          <div className="flex items-center gap-4">
            <Pat estado="resolveu" size={48} />
            <p className="text-[15px] text-ink-muted">Nenhuma exceção aberta.</p>
          </div>
        </Card>
      ) : (
        open.map((item) => (
          <OpenItem
            key={item.id}
            item={item}
            now={queue.now}
            choice={choice}
            busy={busy}
            onChoose={setChoice}
            onConfirm={decide}
            onTrace={showTrace}
          />
        ))
      )}
      {queue && queue.decided.length > 0 && (
        <Card title="Decididas" id="decididas" aside={`${queue.decided.length}`}>
          <ul className="flex flex-col divide-y divide-line">
            {queue.decided.map((item) => (
              <li key={item.id} className="flex flex-col gap-1 py-3 text-sm">
                <span className="font-semibold">
                  {item.card.code} · {item.card.title}
                </span>
                {item.decision && (
                  <>
                    <span>Escolha: {item.decision.label}</span>
                    <span className="text-ink-muted">
                      {roleLabel(item.decision.role)} ({item.decision.by}) em {timeBr(item.decision.at)} · {item.decision.outcome}
                    </span>
                  </>
                )}
                {trackRunId(item) && (
                  <span>
                    <Button size="sm" variant="secondary" onClick={() => void showTrace(item)}>
                      Ver rastro do caso
                    </Button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {caseTrace && (
        <>
          <TracePanel events={caseTrace.events} title={`Rastro do caso · ${caseTrace.title}`} id="rastro-caso" simulated />
          <Muted>Execução {caseTrace.runId}. Horas em tempo simulado (relógio de demo); custo e tokens são os medidos no rastro.</Muted>
        </>
      )}
    </Shell>
  );
}

function OpenItem({
  item,
  now,
  choice,
  busy,
  onChoose,
  onConfirm,
  onTrace,
}: {
  item: ExceptionItem;
  now: string;
  choice: Choice | null;
  busy: boolean;
  onChoose: (c: Choice | null) => void;
  onConfirm: (c: Choice) => void;
  onTrace: (item: ExceptionItem) => void;
}) {
  const v = toExceptionView(item.card);
  const chosen = choice?.id === item.id ? choice : null;
  const facts = [
    { label: "Quem decide", value: v.decider },
    ...(v.recommendation ? [{ label: "Recomendação do Pat", value: v.recommendation }] : []),
    ...(v.ifNoAnswer ? [{ label: "Se ninguém responder", value: v.ifNoAnswer }] : []),
  ];
  const traceButton = trackRunId(item) ? (
    <Button size="sm" variant="secondary" onClick={() => onTrace(item)} disabled={busy}>
      Ver rastro do caso
    </Button>
  ) : null;
  const decision = chosen ? (
    <div className="flex w-full flex-col gap-2 rounded-bubble border border-line-strong p-3.5">
      <p className="text-sm">
        Você escolheu: <strong>{v.options[chosen.index].label}</strong>. Confirmar?
      </p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => onConfirm(chosen)} disabled={busy} aria-busy={busy}>
          {busy ? "Registrando…" : "Confirmar decisão"}
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onChoose(null)} disabled={busy}>
          Voltar
        </Button>
      </div>
    </div>
  ) : (
    <ul className="flex w-full flex-col gap-2" aria-label="Opções">
      {v.options.map((o, i) => (
        <li key={`${o.label}-${i}`}>
          <button
            type="button"
            disabled={busy}
            onClick={() => onChoose({ id: item.id, index: i })}
            className="flex w-full items-center justify-between gap-3 rounded-bubble border border-transparent bg-paper px-3.5 py-3 text-left text-sm transition-colors hover:border-ink-subtle disabled:opacity-50"
          >
            <span className="font-medium">{o.label}</span>
            {o.value && <span className="text-[13px] text-ink-muted">{o.value}</span>}
          </button>
        </li>
      ))}
    </ul>
  );
  const actions = (
    <div className="flex w-full flex-col gap-2">
      {decision}
      {traceButton && <div>{traceButton}</div>}
    </div>
  );
  return (
    <ExceptionCard
      chip={v.chip}
      time={dueLabel(item.card.deadline, now)}
      title={v.title}
      reason={v.reason}
      evidence={v.evidence}
      facts={facts}
      actions={actions}
    />
  );
}
