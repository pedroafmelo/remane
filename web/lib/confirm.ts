// Lógica pura da tela de resumo (C6): monta o `ConfirmInput`, "ajustar para caber", bloqueios e rótulos.
// Nada aqui mede negócio: a capacidade e o mapeamento vêm do backend.

import type { ColumnMapping, ColumnRef, ConfirmInput, IdentityCard, MappingSource, ReadSummary, RunState } from "./types.ts";

export const COVERAGE_MIN = 50;
export const COVERAGE_MAX = 120;
export const COVERAGE_DEFAULT = 100;
export const NOTE_MAX = 500;

/** O que o gestor digitou, ainda como texto de formulário. */
export interface ConfirmForm {
  coverage: Record<string, number>; // por loja; ausente = padrão
  wage: string; // "33,50" ou "33.5"; vazio = não informado
  plannedWeek: string; // "2027-01-11"; vazio = a do arquivo
  note: string;
  identity: Record<string, boolean>; // card_id -> mesma pessoa?
}

export const emptyForm = (): ConfirmForm => ({ coverage: {}, wage: "", plannedWeek: "", note: "", identity: {} });

export function clampCoverage(value: number): number {
  if (!Number.isFinite(value)) return COVERAGE_DEFAULT;
  return Math.min(COVERAGE_MAX, Math.max(COVERAGE_MIN, Math.round(value)));
}

/** "Ajustar para caber": põe `max_fitting_pct` (dentro de 50 a 120) em todas as lojas. */
export function fitAll(storeIds: string[], maxFittingPct: number): Record<string, number> {
  const pct = clampCoverage(maxFittingPct);
  return Object.fromEntries(storeIds.map((id) => [id, pct]));
}

/** `max_fitting_pct` abaixo do piso de 50% não cabe nem no mínimo que a tela aceita: o gestor precisa saber. */
export const fitsBelowFloor = (maxFittingPct: number) => maxFittingPct < COVERAGE_MIN;

/** Salário-hora em reais, aceitando vírgula. `null` = vazio; `NaN` = inválido (zero, negativo ou texto). */
export function parseWage(text: string): number | null {
  const t = text.trim().replace(/^R\$\s*/, "");
  if (t === "") return null;
  if (!/^\d+([.,]\d{1,2})?$/.test(t)) return Number.NaN;
  const n = Number(t.replace(",", "."));
  return n > 0 ? n : Number.NaN;
}

/** Segunda-feira? (`iso` "AAAA-MM-DD", sem passar por fuso). */
export function isMonday(iso: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return false;
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCMonth() === m - 1 && date.getUTCDate() === d && date.getUTCDay() === 1;
}

/** Cartões de homônimo sem resposta: sem resposta, a leitura não confirma (plano, seção 7). */
export function pendingHomonyms(cards: IdentityCard[], answers: Record<string, boolean>): IdentityCard[] {
  return cards.filter((c) => c.kind === "homonimo" && answers[c.id] === undefined);
}

/** Arquivo em grade só com dia da semana (sem data) e sem semana na leitura: a semana planejada é obrigatória. */
export function weekRequired(summary: ReadSummary, mode: RunState["mode"]): boolean {
  return mode === "upload" && summary.week_start === null && summary.planned_week_start === null;
}

export interface Blocker {
  id: string;
  text: string;
}

/** Motivos que travam o botão de confirmar, com a explicação que a tela mostra. */
export function blockers(summary: ReadSummary, mode: RunState["mode"], form: ConfirmForm): Blocker[] {
  const out: Blocker[] = [];
  const pending = pendingHomonyms(summary.identity, form.identity);
  if (pending.length > 0) {
    out.push({
      id: "homonimo",
      text: `Responda ${pending.length === 1 ? "o cartão de homônimo" : `os ${pending.length} cartões de homônimo`} acima: sem a resposta, o Pat não sabe se são pessoas diferentes e a leitura não confirma.`,
    });
  }
  const wage = parseWage(form.wage);
  if (Number.isNaN(wage)) out.push({ id: "salario", text: "O salário-hora precisa ser um valor em reais maior que zero (ex.: 18,50), ou ficar em branco." });
  if (mode === "upload") {
    if (form.plannedWeek !== "" && !isMonday(form.plannedWeek)) out.push({ id: "semana", text: "A semana planejada precisa ser uma segunda-feira." });
    else if (form.plannedWeek === "" && weekRequired(summary, mode)) {
      out.push({ id: "semana", text: "O arquivo não diz a data da semana (só o dia da semana): escolha a segunda-feira da semana a planejar." });
    }
  }
  if (form.note.length > NOTE_MAX) out.push({ id: "texto", text: `O texto passa de ${NOTE_MAX} caracteres.` });
  return out;
}

/** O `ConfirmInput` do formulário: só o que foge do padrão, para o rastro registrar o que o gestor mudou. */
export function buildConfirmInput(form: ConfirmForm, mode: RunState["mode"], storeIds?: string[]): ConfirmInput {
  const known = storeIds ? new Set(storeIds) : null;
  const coverage_pct: Record<string, number> = {};
  for (const [id, value] of Object.entries(form.coverage)) {
    if (known && !known.has(id)) continue;
    const pct = clampCoverage(value);
    if (pct !== COVERAGE_DEFAULT) coverage_pct[id] = pct;
  }
  const input: ConfirmInput = {
    coverage_pct,
    note: form.note.trim(),
    identity: Object.entries(form.identity).map(([card_id, same]) => ({ card_id, same })),
  };
  const wage = parseWage(form.wage);
  if (wage !== null && !Number.isNaN(wage)) input.hourly_wage_default = wage.toFixed(2);
  if (mode === "upload" && form.plannedWeek !== "" && isMonday(form.plannedWeek)) input.planned_week_start = form.plannedWeek;
  return input;
}

/** A semana planejada difere da do arquivo? (só no modo upload, com as duas conhecidas) */
export function weekWasShifted(summary: ReadSummary, plannedWeek: string): boolean {
  return plannedWeek !== "" && summary.week_start !== null && plannedWeek !== summary.week_start;
}

export function mappingSourceLabel(source: MappingSource): string {
  switch (source) {
    case "modelo":
      return "lido pelo agente";
    case "heuristica":
      return "lido sem o modelo, confira";
    case "csv_dec039":
      return "formato padrão";
    case "plataforma":
      return "a partir da última escala publicada";
  }
}

export const FORMAT_LABELS: Record<ReadSummary["format"], string> = {
  csv: "CSV",
  xlsx: "XLSX",
  pdf: "PDF",
  continuidade: "continuidade (sem arquivo)",
};

const colText = (c: ColumnRef) => `coluna ${c.index + 1} · "${c.header}"`;

const WEEKDAY_NAMES = { seg: "segunda", ter: "terça", qua: "quarta", qui: "quinta", sex: "sexta", sab: "sábado", dom: "domingo" } as const;

const hhmm = (t: string | null) => (t ? t.slice(0, 5) : "?");

/** Linhas "coluna → campo" do mapeamento. Só entram os campos que o mapeamento usa. */
export function mappingRows(m: ColumnMapping): { field: string; column: string }[] {
  const rows: { field: string; column: string }[] = [];
  const add = (field: string, ref: ColumnRef | null) => {
    if (ref) rows.push({ field, column: colText(ref) });
  };
  add("Pessoa", m.person);
  add("Matrícula", m.person_code);
  add("Loja", m.store);
  if (m.layout === "long") {
    add("Data", m.date);
    add("Início", m.start);
    add("Fim", m.end);
    add("Turno", m.shift);
  } else if (m.day_columns.length > 0) {
    const days = m.day_columns.map((d) => d.weekday ? WEEKDAY_NAMES[d.weekday] : d.day ?? colText(d.col)).join(", ");
    rows.push({ field: "Dias da grade", column: `${m.day_columns.length} colunas (${days})` });
  }
  add("Salário-hora", m.wage);
  add("Observações", m.notes);
  if (m.shift_codes.length > 0) {
    const codes = m.shift_codes.map((c) => (c.off ? `${c.code} = folga` : `${c.code} = ${hhmm(c.start)} às ${hhmm(c.end)}`)).join("; ");
    rows.push({ field: "Códigos de turno", column: codes });
  }
  return rows;
}

export const IDENTITY_KIND_LABELS: Record<IdentityCard["kind"], string> = {
  homonimo: "Possível homônimo",
  grafia_parecida: "Grafia parecida",
  sem_par_no_quadro: "Pessoa nova?",
};

/** Lojas oferecidas no seletor de cobertura: as do resumo, senão as do quadro guardado. */
export function storeOptions(summary: ReadSummary, roster: { id: string; name: string }[] | null): { id: string; name: string }[] {
  const names = new Map((roster ?? []).map((s) => [s.id, s.name]));
  if (summary.store_ids && summary.store_ids.length > 0) return summary.store_ids.map((id) => ({ id, name: names.get(id) ?? id }));
  return roster ?? [];
}
