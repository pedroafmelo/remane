// Cobertura ao lado do custo (plano da C6, seção 9): "economia" com cobertura menor engana se a tela não disser.

import type { Comparison } from "./types.ts";

/** Texto de apoio da economia: avisa quando a escala nova cobre menos que a antiga. `null` = nada a avisar. */
export function savingsCaveat(c: Comparison): string | null {
  const diff = c.before.coverage_pct - c.after.coverage_pct;
  if (diff <= 0) return null;
  return `com a cobertura ${diff.toFixed(1).replace(".", ",")} ponto(s) menor`;
}
