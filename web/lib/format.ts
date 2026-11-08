// Formatação pura da plataforma (pt-BR). Nada aqui calcula negócio: só apresenta o que o backend mediu.

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const num2 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const usd = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 6 });

/** Reais a partir de um Decimal em string. */
export function money(value: string | number): string {
  return brl.format(Number(value));
}

export function hours(value: string | number): string {
  return `${num2.format(Number(value))} h`;
}

export function pct(value: number): string {
  return `${num2.format(value)}%`;
}

/** Custo medido em US$: 0 aparece como 0 e nulo como "—" (nunca confundir os dois). */
export function costUsd(value: string | null): string {
  return value === null ? "—" : `US$ ${usd.format(Number(value))}`;
}

export function latency(ms: number | null): string {
  if (ms === null) return "—";
  return ms >= 1000 ? `${num2.format(ms / 1000)} s` : `${ms} ms`;
}

/** "2027-01-11" -> "11/01/2027" (sem passar por Date, para não deslocar o dia por fuso). */
export function dateBr(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

/** "2027-01-11T08:00:00" -> "08:00" */
export function hhmm(iso: string): string {
  return iso.slice(11, 16);
}

export function timeBr(iso: string): string {
  return `${dateBr(iso)} ${iso.slice(11, 19)}`;
}

const RULE_STATUS_LABELS: Record<string, string> = {
  ficticia: "fictícia (demo)",
  conferida: "conferida",
  interpretacao: "interpretação",
  pendente: "pendente",
};

/** Status de regra como está; `ficticia` aparece como "fictícia (demo)". */
export function ruleStatusLabel(status: string): string {
  return RULE_STATUS_LABELS[status] ?? status;
}

export const PHASE_LABELS: Record<string, string> = {
  read: "Lendo o arquivo",
  awaiting_confirm: "Aguardando a confirmação da leitura",
  optimized: "Escala otimizada",
  awaiting_approval: "Aguardando a aprovação do gestor",
  published: "Publicada",
  failed: "Interrompida com exceção",
};

export function phaseLabel(phase: string): string {
  return PHASE_LABELS[phase] ?? phase;
}

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

/** Os sete dias da semana a partir da segunda: `iso` para casar com os turnos, `label` para o cabeçalho. */
export function weekDays(weekStart: string): { iso: string; label: string }[] {
  const [y, m, d] = weekStart.split("-").map(Number);
  return WEEKDAYS.map((label, i) => {
    const iso = new Date(Date.UTC(y, m - 1, d + i)).toISOString().slice(0, 10);
    return { iso, label: `${label} ${iso.slice(8, 10)}/${iso.slice(5, 7)}` };
  });
}

function clock(time: string): string {
  const [h, m] = time.split(":");
  return m === "00" ? String(Number(h)) : `${Number(h)}:${m}`;
}

/** Horário no padrão do design system: "14–22h" (sem minutos quando cheios); "+1" se termina no dia seguinte. */
export function shiftLabel(startIso: string, endIso: string): string {
  const next = endIso.slice(0, 10) !== startIso.slice(0, 10) ? " +1" : "";
  return `${clock(hhmm(startIso))}–${clock(hhmm(endIso))}h${next}`;
}

/** Horas entre dois horários "locais" da API (sem fuso), sem depender do fuso de quem lê. */
export function spanHours(startIso: string, endIso: string): number {
  return (naiveMs(endIso) - naiveMs(startIso)) / 3_600_000;
}

function naiveMs(iso: string): number {
  const [y, mo, d] = iso.slice(0, 10).split("-").map(Number);
  const [h, mi] = iso.slice(11, 16).split(":").map(Number);
  return Date.UTC(y, mo - 1, d, h, mi);
}
