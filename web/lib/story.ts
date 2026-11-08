import type { ShiftKind } from "../components/ShiftCell.tsx";

// Progresso da rolagem (0–1) em que cada passo da história do hero acontece.
export const STORY_THRESHOLDS = [0.08, 0.24, 0.4, 0.58, 0.76];
export const STORY_LAST_STEP = STORY_THRESHOLDS.length;

export function stepFromProgress(p: number, thresholds = STORY_THRESHOLDS): number {
  return thresholds.filter((t) => p >= t).length;
}

export const STORY_CAPTIONS = [
  "Role para ver uma falta sendo resolvida",
  "07:02 · Patrick avisa a falta pelo WhatsApp",
  "A escala marca o atestado e o turno das 14h fica descoberto",
  "O agente confirma o atestado e procura quem pode cobrir",
  "Carlos aceita ir para as 14h, sem hora extra",
  "Turno coberto. A gestora só recebe o aviso.",
];

export const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

type Cell = { kind: ShiftKind; label: string; alert?: boolean };
const s = (label: string): Cell => ({ kind: "shift", label });
const off: Cell = { kind: "off", label: "folga" };

// Grade da Loja Boa Viagem no passo `step` da história (quarta = índice 2).
export function storyRows(step: number) {
  const patrickWed: Cell = step >= 2 ? { kind: "sick", label: "atestado", alert: step < 4 } : s("14–22h");
  const carlosWed: Cell = step >= 4 ? { kind: "moved", label: "14–22h" } : s("7–15h");
  return [
    { name: "Ana", cells: [s("7–15h"), s("7–15h"), off, s("7–15h"), s("7–15h"), s("7–15h"), off] },
    { name: "Bruno", cells: [s("14–22h"), s("14–22h"), s("14–22h"), off, s("14–22h"), s("14–22h"), off] },
    { name: "Carlos", cells: [s("7–15h"), off, carlosWed, s("7–15h"), s("7–15h"), off, s("7–15h")] },
    { name: "Patrick", cells: [s("14–22h"), s("14–22h"), patrickWed, off, s("14–22h"), s("14–22h"), off] },
    { name: "Diego", cells: [off, s("14–22h"), s("7–15h"), s("14–22h"), s("14–22h"), off, s("7–15h")] },
  ];
}
