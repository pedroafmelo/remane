import { test } from "node:test";
import assert from "node:assert/strict";
import { blockers, buildConfirmInput, clampCoverage, emptyForm, fitAll, fitsBelowFloor, isMonday, mappingRows, mappingSourceLabel, parseWage, pendingHomonyms, storeOptions, weekWasShifted } from "./confirm.ts";
import { contentTypeFor } from "./files.ts";
import { savingsCaveat } from "./compare.ts";
import type { ColumnMapping, Comparison, IdentityCard, ReadSummary } from "./types.ts";

const card = (id: string, kind: IdentityCard["kind"]): IdentityCard => ({ id, kind, names: ["Ana Souza", "Ana de Souza"], rows: [], suggestion: "mesma", reason: "grafia parecida" });

const summary = (over: Partial<ReadSummary> = {}): ReadSummary => ({
  file_name: "escala.xlsx",
  rows: 10,
  employees: 3,
  stores: 2,
  week_start: "2026-11-09",
  total_hours: "100",
  issues: [],
  ok: true,
  format: "xlsx",
  mapping: null,
  mapping_source: "modelo",
  assumptions: [],
  identity: [],
  capacity: { demand_person_hours: "2776", capacity_person_hours: "2400", fits: false, max_fitting_pct: 86 },
  planned_week_start: null,
  ...over,
});

test("ajustar para caber põe max_fitting_pct em todas as lojas, dentro de 50 a 120", () => {
  assert.deepEqual(fitAll(["L1", "L2"], 86), { L1: 86, L2: 86 });
  assert.deepEqual(fitAll(["L1"], 30), { L1: 50 });
  assert.deepEqual(fitAll(["L1"], 400), { L1: 120 });
  assert.deepEqual(fitAll([], 86), {});
  assert.equal(fitsBelowFloor(30), true);
  assert.equal(fitsBelowFloor(86), false);
});

test("clampCoverage arredonda, limita e trata valor inválido como 100", () => {
  assert.equal(clampCoverage(85.6), 86);
  assert.equal(clampCoverage(10), 50);
  assert.equal(clampCoverage(Number.NaN), 100);
});

test("parseWage aceita vírgula e recusa zero, negativo e texto", () => {
  assert.equal(parseWage(""), null);
  assert.equal(parseWage("  "), null);
  assert.equal(parseWage("18,50"), 18.5);
  assert.equal(parseWage("R$ 18.5"), 18.5);
  assert.ok(Number.isNaN(parseWage("0")));
  assert.ok(Number.isNaN(parseWage("-3")));
  assert.ok(Number.isNaN(parseWage("abc")));
  assert.ok(Number.isNaN(parseWage("1,234")));
});

test("isMonday confere o dia da semana sem fuso e recusa data impossível", () => {
  assert.equal(isMonday("2027-01-11"), true);
  assert.equal(isMonday("2027-01-12"), false);
  assert.equal(isMonday("2027-02-30"), false);
  assert.equal(isMonday(""), false);
});

test("homônimo sem resposta é pendente; os outros cartões não bloqueiam", () => {
  const cards = [card("a", "homonimo"), card("b", "grafia_parecida"), card("c", "sem_par_no_quadro"), card("d", "homonimo")];
  assert.deepEqual(pendingHomonyms(cards, {}).map((c) => c.id), ["a", "d"]);
  assert.deepEqual(pendingHomonyms(cards, { a: false }).map((c) => c.id), ["d"]);
  assert.deepEqual(pendingHomonyms(cards, { a: false, d: true }), []);
});

test("blockers: homônimo pendente trava o confirmar e explica", () => {
  const s = summary({ identity: [card("a", "homonimo")] });
  const stops = blockers(s, "upload", emptyForm());
  assert.equal(stops.length, 1);
  assert.equal(stops[0].id, "homonimo");
  assert.match(stops[0].text, /homônimo/);
  const form = { ...emptyForm(), identity: { a: false } };
  assert.deepEqual(blockers(s, "upload", form), []);
});

test("blockers: salário, semana e texto inválidos travam; semana obrigatória sem data no arquivo", () => {
  const s = summary();
  assert.deepEqual(blockers(s, "upload", { ...emptyForm(), wage: "0" }).map((b) => b.id), ["salario"]);
  assert.deepEqual(blockers(s, "upload", { ...emptyForm(), plannedWeek: "2027-01-12" }).map((b) => b.id), ["semana"]);
  assert.deepEqual(blockers(s, "upload", { ...emptyForm(), note: "x".repeat(501) }).map((b) => b.id), ["texto"]);
  const gradeSemData = summary({ week_start: null });
  assert.deepEqual(blockers(gradeSemData, "upload", emptyForm()).map((b) => b.id), ["semana"]);
  assert.deepEqual(blockers(gradeSemData, "upload", { ...emptyForm(), plannedWeek: "2027-01-11" }), []);
  // na continuidade a semana vem da plataforma
  assert.deepEqual(blockers(gradeSemData, "continuidade", emptyForm()), []);
});

test("buildConfirmInput envia só o que foge do padrão", () => {
  const input = buildConfirmInput(emptyForm(), "upload", ["L1"]);
  assert.deepEqual(input, { coverage_pct: {}, note: "", identity: [] });
});

test("buildConfirmInput monta cobertura, salário, semana, texto e identidade", () => {
  const form = {
    coverage: { L1: 86, L2: 100, L9: 70 },
    wage: "18,5",
    plannedWeek: "2027-01-11",
    note: "  a Ana está de férias na quarta  ",
    identity: { a: false, b: true },
  };
  const input = buildConfirmInput(form, "upload", ["L1", "L2"]);
  assert.deepEqual(input, {
    coverage_pct: { L1: 86 }, // L2 é o padrão; L9 não é loja do resumo
    hourly_wage_default: "18.50",
    planned_week_start: "2027-01-11",
    note: "a Ana está de férias na quarta",
    identity: [
      { card_id: "a", same: false },
      { card_id: "b", same: true },
    ],
  });
});

test("na continuidade a semana planejada não vai no ConfirmInput", () => {
  const input = buildConfirmInput({ ...emptyForm(), plannedWeek: "2027-01-11" }, "continuidade", []);
  assert.equal("planned_week_start" in input, false);
});

test("nenhum campo sex em ConfirmInput nem nos rótulos de mapeamento (RN-13)", () => {
  const input = buildConfirmInput(emptyForm(), "upload", []);
  assert.equal(JSON.stringify(input).includes("sex"), false);
});

test("rótulos da fonte do mapeamento", () => {
  assert.equal(mappingSourceLabel("modelo"), "lido pelo agente");
  assert.equal(mappingSourceLabel("heuristica"), "lido sem o modelo, confira");
  assert.equal(mappingSourceLabel("csv_dec039"), "formato padrão");
  assert.equal(mappingSourceLabel("plataforma"), "a partir da última escala publicada");
});

test("weekWasShifted compara a semana do arquivo com a escolhida", () => {
  const s = summary();
  assert.equal(weekWasShifted(s, ""), false);
  assert.equal(weekWasShifted(s, "2026-11-09"), false);
  assert.equal(weekWasShifted(s, "2027-01-11"), true);
  assert.equal(weekWasShifted(summary({ week_start: null }), "2027-01-11"), false);
});

const ref = (index: number, header: string) => ({ index, header });

test("mappingRows lista coluna → campo para o layout em lista", () => {
  const m: ColumnMapping = {
    table: 0, header_row: 0, layout: "long", person: ref(0, "Colaborador"), person_code: ref(1, "Mat."), store: ref(2, "Unidade"),
    date: ref(3, "Dia"), start: ref(4, "Entrada"), end: ref(5, "Saída"), shift: null, day_columns: [], date_order: "dmy", shift_codes: [], wage: null, notes: null,
  };
  const rows = mappingRows(m);
  assert.deepEqual(rows.map((r) => r.field), ["Pessoa", "Matrícula", "Loja", "Data", "Início", "Fim"]);
  assert.equal(rows[0].column, 'coluna 1 · "Colaborador"');
});

test("mappingRows resume dias da grade e códigos de turno", () => {
  const m: ColumnMapping = {
    table: 0, header_row: 0, layout: "grid", person: ref(0, "Nome"), person_code: null, store: null, date: null, start: null, end: null, shift: null,
    day_columns: [
      { col: ref(1, "Seg"), day: null, weekday: "seg" },
      { col: ref(2, "Ter"), day: null, weekday: "ter" },
    ],
    date_order: "dmy",
    shift_codes: [
      { code: "M", start: "07:00:00", end: "15:00:00", off: false, evidence: "M = 07:00 às 15:00" },
      { code: "F", start: null, end: null, off: true, evidence: null },
    ],
    wage: null, notes: null,
  };
  const rows = mappingRows(m);
  assert.equal(rows.find((r) => r.field === "Dias da grade")?.column, "2 colunas (segunda, terça)");
  assert.equal(rows.find((r) => r.field === "Códigos de turno")?.column, "M = 07:00 às 15:00; F = folga");
});

test("storeOptions prefere a lista do resumo e usa o quadro como reserva", () => {
  const roster = [{ id: "L1", name: "Centro" }];
  assert.deepEqual(storeOptions(summary({ store_ids: ["L1", "L2"] }), roster), [
    { id: "L1", name: "Centro" },
    { id: "L2", name: "L2" },
  ]);
  assert.deepEqual(storeOptions(summary(), roster), roster);
  assert.deepEqual(storeOptions(summary(), null), []);
});

test("contentTypeFor segue a extensão", () => {
  assert.equal(contentTypeFor("escala.CSV"), "text/csv");
  assert.equal(contentTypeFor("a.xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  assert.equal(contentTypeFor("a.pdf"), "application/pdf");
  assert.equal(contentTypeFor("sem-extensao"), "application/octet-stream");
});

test("savingsCaveat avisa só quando a cobertura cai", () => {
  const base = { savings: "1", overtime_hours_avoided: "0", violations_avoided: 0 };
  const m = (c: number) => ({ total_cost: "1", regular_hours: "1", overtime_hours: "0", overtime_cost: "0", coverage_pct: c, uncovered_slots: 0, violations: 0 });
  const down: Comparison = { ...base, before: m(100), after: m(86) };
  const up: Comparison = { ...base, before: m(90), after: m(95) };
  assert.match(savingsCaveat(down) ?? "", /14,0 ponto/);
  assert.equal(savingsCaveat(up), null);
});
