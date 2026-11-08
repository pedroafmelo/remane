import { test } from "node:test";
import assert from "node:assert/strict";
import { countsLine, evalsCommand, isReport, modelRows, NOT_MEASURED, rn04Metrics, suiteRows } from "./evals.ts";
import type { EvalsReport } from "./types-insights.ts";

const plain = (s: string) => s.replace(/\u00a0/g, " ");

const report = (over: Partial<EvalsReport> = {}): EvalsReport => ({
  status: "ok",
  modo: "sem_modelo",
  contagem: { cenarios: 30, sem_modelo: 20, com_modelo: 10, executados: 21, passaram: 21, falharam: 0, nao_executados: 9, com_modelo_executados: 1 },
  suites: {
    e1: { cenarios: 11, passaram: 11, falharam: 0, nao_executados: 0 },
    e3: { cenarios: 6, passaram: 0, falharam: 0, nao_executados: 6 },
  },
  rn04: {
    violacoes_nao_detectadas: { plantadas: 14, detectadas: 14, nao_detectadas: 0, falsos_positivos: 0 },
    cobertura: { escala_demo_pct: 97.5, casos_cobertos: null },
    custo_contra_planilha: { antes_brl: "1000.00", depois_brl: "900.00", fonte: "compute_metrics, dados sintéticos" },
    acerto_atestado: { campos_certos: null, campos: null, n_atestados: 0, status: "não medido" },
  },
  modelo: { chamadas: 0, cost_usd: null, latencia_ms_p50: null, latencia_ms_max: null },
  ...over,
});

test("isReport separa o relatório do estado vazio", () => {
  assert.equal(isReport(report()), true);
  assert.equal(isReport({ status: "sem_relatorio" }), false);
});

test("countsLine diz N cenários, M com modelo, K executados", () => {
  assert.equal(countsLine(report()), "30 cenários · 10 com modelo (1 executados) · 21 executados");
  assert.equal(countsLine(report({ contagem: {} })), "— cenários · — com modelo · — executados");
});

test("evalsCommand usa o do relatório ou o padrão do modo", () => {
  assert.equal(evalsCommand(report({ comando: "x y" })), "x y");
  assert.equal(evalsCommand(report()), "uv run python -m escalista.evals --suite all --snapshot data/evals");
  assert.match(evalsCommand(report({ modo: "com_modelo" })), /--with-model/);
});

test("suiteRows mantém não executado à parte dos aprovados", () => {
  const rows = suiteRows(report());
  assert.deepEqual(rows.map((r) => r.key), ["e1", "e3"]);
  const e3 = rows[1];
  assert.equal(e3.passaram, 0);
  assert.equal(e3.naoExecutados, 6);
  assert.equal(e3.cenarios, 6);
});

test("suiteRows conta pelos cenários quando falta o placar da suíte", () => {
  const rows = suiteRows(
    report({
      suites: { e4: {} },
      cenarios: [
        { id: "E4-01", suite: "e4", status: "passou" },
        { id: "E4-02", suite: "e4", status: "não executado" },
        { id: "E4-03", suite: "e4", status: "falhou" },
      ],
    }),
  );
  assert.deepEqual(rows[0], { key: "e4", title: "E4 · injeção de texto", cenarios: 3, passaram: 1, falharam: 1, naoExecutados: 1 });
});

test("suiteRows sem placar nem cenários deixa nulo, não zero", () => {
  const [row] = suiteRows(report({ suites: { e2: {} }, cenarios: [] }));
  assert.equal(row.passaram, null);
});

test("as quatro métricas do RN-04 saem na ordem, com não medido onde falta valor", () => {
  const [violations, coverage, cost, attestation] = rn04Metrics(report());
  assert.equal(violations.value, "0");
  assert.equal(violations.tone, "good");
  assert.match(violations.note, /14 plantadas/);
  assert.equal(plain(coverage.value), "97,5%");
  assert.match(coverage.note, /casos cobertos: não medido/);
  assert.equal(plain(cost.value), "R$ 1.000,00 → R$ 900,00");
  assert.equal(attestation.value, NOT_MEASURED);
  assert.equal(attestation.measured, false);
});

test("violações não detectadas acima de zero ficam em tom ruim", () => {
  const r = report();
  r.rn04!.violacoes_nao_detectadas!.nao_detectadas = 2;
  assert.equal(rn04Metrics(r)[0].tone, "bad");
});

test("sem bloco rn04 tudo é não medido", () => {
  const metrics = rn04Metrics(report({ rn04: null }));
  assert.equal(metrics.length, 4);
  assert.ok(metrics.every((m) => m.value === NOT_MEASURED && !m.measured));
});

test("acerto do atestado medido mostra campos e n", () => {
  const r = report();
  r.rn04!.acerto_atestado = { campos_certos: 30, campos: 40, n_atestados: 5, status: "medido" };
  const m = rn04Metrics(r)[3];
  assert.equal(m.value, "30/40 campos");
  assert.match(plain(m.note), /75% · 5 atestado/);
});

test("modelo sem rodada é não medido; com rodada mostra o medido (zero continua zero)", () => {
  assert.ok(modelRows(report()).every((r) => r.value === NOT_MEASURED));
  const rows = modelRows(report({ modelo: { chamadas: 4, cost_usd: "0", latencia_ms_p50: 850, latencia_ms_max: 2100 } }));
  assert.deepEqual(rows.map((r) => plain(r.value)), ["4", "US$ 0", "850 ms", "2,1 s"]);
});
