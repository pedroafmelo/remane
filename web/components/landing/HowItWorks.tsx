"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ScheduleGrid } from "../ScheduleGrid";
import { StatusChip } from "../StatusChip";
import { ChatBubble } from "../ChatBubble";
import { Pat } from "../Pat";
import type { PatEstado } from "@/lib/pat";
import { DAYS, storyRows } from "@/lib/story";

// Pat em cada passo: lê as regras, espera a aprovação, conversa e chama uma pessoa.
const PAT_NO_PASSO: PatEstado[] = ["trabalhando", "parado", "resolveu", "excecao"];
const PatTag = ({ i }: { i: number }) => <Pat key={PAT_NO_PASSO[i]} estado={PAT_NO_PASSO[i]} size={40} />;

const RULES = [
  ["Máximo de 42h por semana", "EC 141"],
  ["2 folgas por semana, uma preferencialmente no domingo", "EC 141"],
  ["11h de descanso entre um turno e outro", "CLT, art. 66"],
  ["1h de intervalo em turno acima de 6h", "CLT, art. 71"],
];

const visuals: ReactNode[] = [
  <div key="regras" className="rounded-card bg-surface p-5 shadow-float">
    <div className="mb-3 flex items-center gap-2.5">
      <PatTag i={0} />
      <p className="text-[13px] font-medium text-ink-subtle">Pat lendo as regras da Loja Boa Viagem</p>
    </div>
    <ul className="divide-y divide-line">
      {RULES.map(([rule, source]) => (
        <li key={rule} className="flex items-center justify-between gap-4 py-3 text-[15px]">
          <span>{rule}</span>
          <span className="whitespace-nowrap rounded-full bg-surface-chat px-2.5 py-1 text-xs font-medium text-ink-muted">{source}</span>
        </li>
      ))}
    </ul>
    <p className="mt-3 text-[13px] font-medium text-accent-strong">Conferido pelo DP</p>
  </div>,
  <ScheduleGrid
    key="grade"
    title="Semana de 14 a 20 de dezembro"
    chip={<span className="inline-flex items-center gap-2"><PatTag i={1} /><StatusChip>Aguardando aprovação da gestora</StatusChip></span>}
    days={DAYS}
    rows={storyRows(0).slice(0, 4)}
  />,
  <div key="chat" className="flex flex-col rounded-card bg-surface-chat p-5 pb-2.5 shadow-float">
    <div className="mb-3 flex items-center gap-2.5 text-[13px] font-medium text-ink-subtle"><PatTag i={2} /> Pat resolveu o atraso</div>
    <ChatBubble from="person">Vou atrasar uns 30 min, o ônibus quebrou.</ChatBubble>
    <ChatBubble from="agent">Tranquilo, Diego. Já avisei a loja e a Ana segura o caixa até você chegar.</ChatBubble>
    <ChatBubble from="event">Ana confirmou · atraso registrado</ChatBubble>
  </div>,
  <div key="excecao" className="rounded-card bg-surface p-5 shadow-float">
    <div className="flex items-center gap-2.5">
      <PatTag i={3} />
      <StatusChip tone="warning">Precisa de você</StatusChip>
    </div>
    <p className="mt-4 text-[17px] font-medium leading-snug">Sábado, 14h: ninguém disponível sem hora extra.</p>
    <ul className="mt-4 flex flex-col gap-2 text-[15px]">
      <li className="tabular flex justify-between gap-4 rounded-cell bg-surface-chat px-3.5 py-3"><span>Bruno faz 2h extras</span><span className="text-ink-muted">R$ 58</span></li>
      <li className="tabular flex justify-between gap-4 rounded-cell bg-surface-chat px-3.5 py-3"><span>Trocar a folga do Diego</span><span className="text-ink-muted">R$ 0 · pede o aceite dele</span></li>
    </ul>
  </div>,
];

const STEPS = [
  ["Lê as regras", "Lei e convenção coletiva viram regras, cada uma com a sua origem. O DP confere uma vez."],
  ["Monta a escala ótima", "Um otimizador cobre a demanda ao menor custo, sem violar nenhuma regra. O gestor aprova."],
  ["Acompanha o dia a dia", "Falta, atraso, atestado e troca chegam pelo WhatsApp. O agente encontra quem pode cobrir e confirma."],
  ["Chama você só quando precisa", "O que custa dinheiro ou foge da regra vira exceção, com as opções e o custo de cada uma."],
];

export function HowItWorks() {
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(Number((e.target as HTMLElement).dataset.i))),
      { rootMargin: "-45% 0px -45% 0px" },
    );
    refs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div className="mt-12 grid [overflow-anchor:none] grid-cols-[minmax(0,1fr)] gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:gap-16">
      <ol className="flex flex-col gap-12 lg:gap-0">
        {STEPS.map(([title, text], i) => (
          <li
            key={title}
            data-i={i}
            ref={(el) => { refs.current[i] = el; }}
            className={`transition-opacity duration-300 lg:flex lg:min-h-[60vh] lg:flex-col lg:justify-center ${active === i ? "" : "lg:opacity-35"}`}
          >
            <span className="tabular text-[13px] font-medium text-ink-subtle">0{i + 1}</span>
            <h3 className="mt-2 text-[28px] font-bold leading-tight tracking-[-0.04em]">{title}</h3>
            <p className="mt-3 max-w-md text-[17px] leading-relaxed text-ink-muted">{text}</p>
            <div className="mt-6 lg:hidden">{visuals[i]}</div>
          </li>
        ))}
      </ol>
      <div className="hidden lg:block">
        <div className="sticky top-[calc(50vh-180px)]">
          <div key={active} className="animate-rise">{visuals[active]}</div>
        </div>
      </div>
    </div>
  );
}
