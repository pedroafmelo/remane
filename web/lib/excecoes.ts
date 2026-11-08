// Textos puros da fila de exceções e do celular simulado (pt-BR). Só apresentam o que o backend decidiu.

import { shiftLabel, spanHours } from "./format.ts";
import type { ExceptionItem, MyFalta, MyWeek } from "./types-excecoes.ts";

/** Execução do rastro de um cartão do acompanhamento (`track-<case_id>` ou `track-sweep`); `null` nos demais. */
export function trackRunId(item: Pick<ExceptionItem, "source">): string | null {
  const { kind, run_id: runId } = item.source;
  return kind === "track" && typeof runId === "string" && runId.startsWith("track-") ? runId : null;
}

const WEEKDAYS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

/** "2027-01-13" -> "qua 13/01" (sem passar pelo fuso de quem lê). */
export function dayLabel(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]} ${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
}

/** Prazo relativo ao relógio da demo: "vence em 25 min", "vence em 3 h", "vence em 2 dias", "venceu". */
export function dueLabel(deadline: string | null, now: string): string | null {
  if (!deadline) return null;
  const h = spanHours(now, deadline);
  if (h <= 0) return "venceu";
  if (h < 1) return `vence em ${Math.max(1, Math.round(h * 60))} min`;
  if (h < 48) return `vence em ${Math.floor(h)} h`;
  return `vence em ${Math.floor(h / 24)} dias`;
}

/** O que o Pat diz sobre a falta, em primeira pessoa e sem prometer o que depende da gestora. */
export function faltaReply(f: MyFalta): string {
  const turno = `${dayLabel(f.day)}, ${shiftLabel(f.start, f.end)}`;
  switch (f.status) {
    case "pendente":
      return "Já mandei para a sua gestora as opções de quem pode cobrir. Aviso aqui quando ela decidir.";
    case "coberta":
      return `Sua gestora decidiu: ${f.covered_by ?? "um colega"} cobre o seu turno de ${turno}. A escala já foi atualizada.`;
    case "descoberta":
      return `Sua gestora decidiu deixar o turno de ${turno} descoberto. Você não precisa fazer mais nada.`;
    default:
      return `Sua gestora decidiu: ${f.decision ?? "registrado"}.`;
  }
}

export function receiptText(f: MyFalta): string {
  return `Recebi. Já estou procurando quem cubra seu turno de ${dayLabel(f.day)}, ${shiftLabel(f.start, f.end)}. Sua gestora vai decidir.`;
}

/** Dias em que dá para avisar falta: com turno e sem falta já avisada. */
export function faltaDays(week: MyWeek): { day: string; label: string }[] {
  const taken = new Set(week.faltas.map((f) => f.day));
  return week.shifts.filter((s) => !taken.has(s.day)).map((s) => ({ day: s.day, label: `${dayLabel(s.day)} · ${shiftLabel(s.start, s.end)}` }));
}
