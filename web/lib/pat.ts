/** Estados do Pat, o agente do Remane. O mascote é o rosto do logo (óculos e bigode); o olhar muda por estado. */
export const PAT_ESTADOS = ["parado", "trabalhando", "digitando", "resolveu", "excecao"] as const;
export type PatEstado = (typeof PAT_ESTADOS)[number];

export type PatPose = {
  /** olhos: abertos olhando em frente, concentrado (olhos estreitos, sobrancelhas franzidas, olhando para o lado do movimento), para baixo, para cima, ou fechados em arco (feliz) */
  eyes: "frente" | "concentrado" | "baixo" | "cima" | "feliz";
  /** contorno tracejado no lugar de onde o Pat saiu (ele desliza para remanejar) */
  ghost: boolean;
  /** três pontinhos de "digitando" */
  dots: boolean;
  /** contorno warning: precisa de uma pessoa */
  ring: boolean;
  /** movimento: slide (sai do lugar), pop (turno remanejado), blink (pisca parado) */
  motion: "blink" | "slide" | "pop" | "none";
};

const POSES: Record<PatEstado, PatPose> = {
  parado: { eyes: "frente", dots: false, ring: false, ghost: false, motion: "blink" },
  trabalhando: { eyes: "concentrado", dots: false, ring: false, ghost: true, motion: "slide" },
  digitando: { eyes: "baixo", dots: true, ring: false, ghost: false, motion: "none" },
  resolveu: { eyes: "feliz", dots: false, ring: false, ghost: false, motion: "pop" },
  excecao: { eyes: "cima", dots: false, ring: true, ghost: false, motion: "none" },
};

const LABELS: Record<PatEstado, string> = {
  parado: "Pat, o agente do Remane",
  trabalhando: "Pat está trabalhando",
  digitando: "Pat está digitando",
  resolveu: "Pat resolveu",
  excecao: "Pat precisa de uma pessoa",
};

export const patPose = (e: PatEstado): PatPose => POSES[e];
export const patLabel = (e: PatEstado): string => LABELS[e];

/** Estado do Pat em cada passo (0 a 5) da história do hero: o caso do Pedro. */
const POR_PASSO: PatEstado[] = ["parado", "trabalhando", "digitando", "trabalhando", "resolveu", "resolveu"];
export const patDoPasso = (passo: number): PatEstado => POR_PASSO[Math.min(Math.max(passo, 0), POR_PASSO.length - 1)];
