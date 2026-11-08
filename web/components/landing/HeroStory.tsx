"use client";
import { useEffect, useRef, useState } from "react";
import { ScheduleGrid } from "../ScheduleGrid";
import { StatusChip } from "../StatusChip";
import { ChatBubble } from "../ChatBubble";
import { Pat } from "../Pat";
import { patDoPasso, patLabel } from "@/lib/pat";
import { DAYS, STORY_CAPTIONS, STORY_LAST_STEP, stepFromProgress, storyRows } from "@/lib/story";
import { useReducedMotion } from "./useReducedMotion";

// O painel fica preso na tela enquanto a rolagem conduz o caso do Pedro.
export function HeroStory() {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const [scrollStep, setScrollStep] = useState(0);
  const step = reduced ? STORY_LAST_STEP : scrollStep;

  useEffect(() => {
    if (reduced) return;
    const update = () => {
      const el = ref.current;
      if (!el) return;
      const total = el.offsetHeight - innerHeight;
      setScrollStep(stepFromProgress(total > 0 ? -el.getBoundingClientRect().top / total : 1));
    };
    update();
    addEventListener("scroll", update, { passive: true });
    addEventListener("resize", update);
    return () => {
      removeEventListener("scroll", update);
      removeEventListener("resize", update);
    };
  }, [reduced]);

  const estadoPat = patDoPasso(step);
  const warn = step >= 2 && step < 4;

  return (
    <div ref={ref} className={`px-4 sm:px-6 lg:px-10 ${reduced ? "" : "h-[180vh]"}`}>
      <div
        className={`panel-live flex animate-drift flex-col items-center justify-start gap-3 overflow-hidden rounded-panel p-3.5 sm:p-6 lg:justify-center lg:gap-6 ${
          reduced ? "" : "sticky top-[72px] h-[calc(100svh-84px)] max-h-[780px]"
        }`}
      >
        <div className="flex w-full max-w-[1180px] flex-col gap-3 lg:flex-row lg:items-start lg:justify-center lg:gap-7">
          <div className="min-w-0 lg:max-w-[760px] lg:flex-1">
            <ScheduleGrid
              title="Loja Boa Viagem · 14 a 20 de dezembro"
              chip={
                <StatusChip tone={warn ? "warning" : "ok"}>
                  {warn ? "1 turno descoberto · qua 14h" : "Montada pelo Remane · menor custo · dentro da regra"}
                </StatusChip>
              }
              days={DAYS}
              rows={storyRows(step)}
            />
          </div>

          <div className="overflow-hidden rounded-card bg-surface-chat shadow-float lg:w-[400px] lg:flex-none">
            <div className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3 sm:px-5 sm:py-4">
              <span className="-m-1 grid size-12 flex-none place-items-center">
                <Pat key={estadoPat} estado={estadoPat} size={48} />
              </span>
              <div className="leading-tight">
                <b className="block font-medium">Pat</b>
                <span className="text-[13px] text-ink-muted">agente do Remane · Loja Boa Viagem</span>
              </div>
            </div>
            <div className="flex h-[172px] flex-col justify-end gap-2.5 overflow-hidden px-4 py-3 sm:h-[330px] sm:py-4.5" aria-live="polite">
              <span className="sr-only">{patLabel(estadoPat)}</span>
              {step >= 1 && (
                <ChatBubble from="person" attachment="atestado.jpg · 1 dia">
                  Bom dia, não vou conseguir ir hoje. Mandei o atestado.
                </ChatBubble>
              )}
              {step === 2 && <ChatBubble from="typing" />}
              {step >= 3 && <ChatBubble from="agent">Recebi, Pedro. Atestado ok, melhoras. Já estou cobrindo seu turno das 14h.</ChatBubble>}
              {step >= 4 && <ChatBubble from="event">Carlos aceitou o turno · sem hora extra</ChatBubble>}
              {step >= 5 && <ChatBubble from="agent">Pronto, turno coberto. A gestora já foi avisada.</ChatBubble>}
            </div>
          </div>
        </div>

        {!reduced && (
          <div className="flex max-w-full items-center gap-3.5 rounded-full bg-surface py-2.5 pl-3 pr-4.5 shadow-[0_10px_30px_-18px_rgba(23,24,26,0.4)]" aria-hidden="true">
            <span className="flex flex-none gap-1.5">
              {STORY_CAPTIONS.map((c, i) => (
                <span
                  key={c}
                  className={`h-1.5 rounded-full transition-all duration-300 ${i <= step ? "bg-ink" : "bg-line-strong"} ${i === step ? "w-4.5" : "w-1.5"}`}
                />
              ))}
            </span>
            <span key={step} className="animate-rise text-[13px] font-medium sm:text-sm">
              {STORY_CAPTIONS[step]}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
