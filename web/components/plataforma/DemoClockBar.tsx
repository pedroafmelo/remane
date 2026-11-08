"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { asFailure } from "@/lib/api";
import { trackerApi } from "@/lib/api-tracker";
import { CLOCK_EVENT, clockText, triggerSummary, type ClockChange } from "@/lib/tracker";
import type { AdvanceMinutes } from "@/lib/types-tracker";
import { Button } from "../Button";

export const RESET_WARNING = "Isso publica a semana sintética com folga e apaga os casos do acompanhamento. Continuar?";

const STEPS: { minutes: AdvanceMinutes; label: string }[] = [
  { minutes: 15, label: "+15 min" },
  { minutes: 1440, label: "+1 dia" },
  { minutes: 10080, label: "+1 semana" },
];

/** Telas que mostram dados do acompanhamento recarregam quando o relógio avança ou a demo reinicia. */
export function useClockChange(onChange: (change: ClockChange) => void) {
  const ref = useRef(onChange);
  useEffect(() => {
    ref.current = onChange;
  });
  useEffect(() => {
    const handler = (e: Event) => ref.current((e as CustomEvent<ClockChange>).detail);
    window.addEventListener(CLOCK_EVENT, handler);
    return () => window.removeEventListener(CLOCK_EVENT, handler);
  }, []);
}

/**
 * Barra do relógio de demo: a hora é simulada e sempre aparece rotulada. Cada avanço roda o varredor no servidor e
 * devolve os gatilhos; "Reiniciar demo" (só do gestor) pede confirmação antes de apagar os casos.
 */
export function DemoClockBar({ canReset }: { canReset: boolean }) {
  const [now, setNow] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const announce = useCallback((change: ClockChange) => {
    window.dispatchEvent(new CustomEvent<ClockChange>(CLOCK_EVENT, { detail: change }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    trackerApi
      .clock()
      .then((c) => {
        if (!cancelled) setNow(c.now);
      })
      .catch((err) => {
        if (!cancelled) setProblem(asFailure(err).message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // outra barra (outra aba da mesma tela) ou um reinício muda a hora: acompanha sem nova chamada
  useClockChange((c) => setNow(c.now));

  async function advance(minutes: AdvanceMinutes) {
    setBusy(true);
    setProblem(null);
    setConfirming(false);
    try {
      const result = await trackerApi.advance(minutes);
      setNow(result.now);
      setSummary(triggerSummary(result.triggers));
      announce({ action: "advance", now: result.now });
    } catch (err) {
      setProblem(asFailure(err).message);
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    setBusy(true);
    setProblem(null);
    setConfirming(false);
    try {
      const result = await trackerApi.reset();
      setNow(result.now);
      setSummary("Demo reiniciada: semana sintética com folga publicada e casos apagados.");
      announce({ action: "reset", now: result.now });
    } catch (err) {
      setProblem(asFailure(err).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-b border-line bg-paper">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
        <p className="tabular text-[13px]" aria-label="Relógio da demonstração">
          <span className="font-semibold">{now ? clockText(now) : "…"}</span>{" "}
          <span className="text-xs font-medium uppercase tracking-[0.08em] text-ink-muted">tempo simulado</span>
        </p>
        <span className="flex-1" />
        <div className="flex flex-wrap items-center gap-2">
          {STEPS.map((s) => (
            <Button key={s.minutes} size="sm" variant="secondary" onClick={() => advance(s.minutes)} disabled={busy || now === null}>
              {s.label}
            </Button>
          ))}
          {canReset && !confirming && (
            <Button size="sm" variant="secondary" onClick={() => setConfirming(true)} disabled={busy}>
              Reiniciar demo
            </Button>
          )}
        </div>
        {confirming && (
          <div role="alertdialog" aria-label="Confirmar reinício da demo" className="flex w-full flex-wrap items-center gap-2 rounded-bubble border border-line-strong bg-surface px-3.5 py-2.5">
            <p className="flex-1 text-sm">{RESET_WARNING}</p>
            <Button size="sm" onClick={reset} disabled={busy} aria-busy={busy}>
              Continuar
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setConfirming(false)} disabled={busy}>
              Cancelar
            </Button>
          </div>
        )}
        {(summary || problem) && (
          <p role={problem ? "alert" : "status"} className={`w-full text-[13px] ${problem ? "font-medium text-warning-ink" : "text-ink-muted"}`}>
            {problem ?? summary}
          </p>
        )}
      </div>
    </div>
  );
}
