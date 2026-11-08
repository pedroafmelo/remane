import type { ReactNode } from "react";
import { StatusChip } from "./StatusChip";

export type ExceptionOption = { label: string; value?: string | null };

type Props = {
  chip: string;
  time?: string | null;
  title: string;
  /** O que aconteceu e o que o agente já tentou, em uma ou duas frases. */
  reason: string;
  options?: ExceptionOption[];
  evidence?: string[];
  /** Quem decide, recomendação e o que acontece sem resposta: linhas de apoio, na ordem. */
  facts?: { label: string; value: string }[];
  /** Botões das opções (só quando existe ato humano para a exceção). */
  actions?: ReactNode;
};

/** Um caso que o agente não resolveu dentro das regras. Os valores vêm do backend; a interface não calcula custo. */
export function ExceptionCard({ chip, time, title, reason, options = [], evidence = [], facts = [], actions }: Props) {
  return (
    <article role="alert" className="flex flex-col gap-3.5 rounded-card bg-surface p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusChip tone="warning">{chip}</StatusChip>
        {time && <span className="tabular text-xs font-medium text-ink-muted">{time}</span>}
      </div>
      <h3 className="text-lg font-bold tracking-[-0.02em]">{title}</h3>
      <p className="text-[15px] leading-relaxed text-ink-muted">{reason}</p>
      {options.length > 0 && (
        <ul className="flex flex-col gap-2" aria-label="Opções">
          {options.map((o, i) => (
            <li key={`${o.label}-${i}`} className="flex items-center justify-between gap-3 rounded-bubble bg-paper px-3.5 py-3 text-sm">
              <span>{o.label}</span>
              {o.value && <span className="tabular whitespace-nowrap font-medium">{o.value}</span>}
            </li>
          ))}
        </ul>
      )}
      {evidence.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-ink-muted" aria-label="Evidências">
          {evidence.map((e, i) => (
            <li key={`${e}-${i}`}>{e}</li>
          ))}
        </ul>
      )}
      {facts.length > 0 && (
        <dl className="grid gap-x-4 gap-y-1 border-t border-line pt-3 text-xs font-medium text-ink-muted sm:grid-cols-[max-content_1fr]">
          {facts.map((f) => (
            <div key={f.label} className="contents">
              <dt>{f.label}</dt>
              <dd className="font-normal text-ink">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </article>
  );
}
