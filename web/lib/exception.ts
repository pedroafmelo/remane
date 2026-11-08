import { costUsd, timeBr } from "./format.ts";
import { roleLabel } from "./roles.ts";
import type { ExceptionCard } from "./types.ts";

export interface ExceptionView {
  chip: string;
  time: string | null;
  title: string;
  reason: string;
  evidence: string[];
  options: { label: string; value: string | null }[];
  decider: string;
  recommendation: string | null;
  ifNoAnswer: string | null;
}

/** Cartão de exceção do backend no formato do componente. Os valores vêm prontos; aqui só se formata. */
export function toExceptionView(card: ExceptionCard): ExceptionView {
  return {
    chip: `${card.code} · precisa de você`,
    time: card.deadline ? `prazo ${timeBr(card.deadline)}` : null,
    title: card.title,
    reason: card.reason,
    evidence: card.evidence,
    options: card.options.map((o) => ({
      label: o.label,
      value: [o.effect, o.cost_usd !== null ? costUsd(o.cost_usd) : null].filter((v) => v !== null && v !== "").join(" · ") || null,
    })),
    decider: card.decider ? roleLabel(card.decider) : "Não definido",
    recommendation: card.recommendation,
    ifNoAnswer: card.if_no_answer,
  };
}
