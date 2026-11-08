// Apresentação do retrato dos evals (pt-BR). Só formata o que o backend mediu: ausente ou nulo vira "não medido",
// nunca zero, e `não executado` nunca entra na conta dos aprovados.

import { costUsd, latency, money, pct } from "./format.ts";
import type { EvalsReport, EvalsResponse, EvalsScenario, EvalsSuiteTally } from "./types-insights.ts";

export const NOT_MEASURED = "não medido";
const SUITE_ORDER = ["e1", "e2", "e3", "e4"];
const SUITE_TITLES: Record<string, string> = {
  e1: "E1 · solver e verificador",
  e2: "E2 · leitura de escalas",
  e3: "E3 · acompanhamento",
  e4: "E4 · injeção de texto",
};

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const present = (v: unknown): v is string | number => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));

export const isReport = (r: EvalsResponse): r is EvalsReport => r.status === "ok";

/** O comando que gera este retrato: o que o relatório trouxe ou, na falta, o padrão do modo. */
export function evalsCommand(r: EvalsReport): string {
  if (r.comando) return r.comando;
  return `uv run python -m escalista.evals --suite all${r.modo === "com_modelo" ? " --with-model" : ""} --snapshot data/evals`;
}

/** "N cenários · M com modelo · K executados" (com quantos dos M rodaram com modelo, quando o relatório diz). */
export function countsLine(r: EvalsReport): string {
  const c = r.contagem;
  const parts = [`${c.cenarios ?? "—"} cenários`];
  const withModel = c.com_modelo ?? null;
  const ran = c.com_modelo_executados ?? null;
  parts.push(withModel === null ? "— com modelo" : `${withModel} com modelo${ran === null ? "" : ` (${ran} executados)`}`);
  parts.push(`${c.executados ?? "—"} executados`);
  return parts.join(" · ");
}

export interface SuiteRow {
  key: string;
  title: string;
  cenarios: number | null;
  passaram: number | null;
  falharam: number | null;
  naoExecutados: number | null;
}

function tallyFromScenarios(list: EvalsScenario[], suite: string): EvalsSuiteTally {
  const mine = list.filter((s) => s.suite === suite);
  return {
    cenarios: mine.length,
    passaram: mine.filter((s) => s.status === "passou").length,
    falharam: mine.filter((s) => s.status === "falhou").length,
    nao_executados: mine.filter((s) => s.status === "não executado").length,
  };
}

/** Uma linha por suíte (E1 a E4 primeiro, depois as outras). Faltando o placar da suíte, conta pelos cenários. */
export function suiteRows(r: EvalsReport): SuiteRow[] {
  const suites = r.suites ?? {};
  const list = r.cenarios ?? [];
  const keys = [...SUITE_ORDER.filter((k) => k in suites || list.some((s) => s.suite === k)), ...Object.keys(suites).filter((k) => !SUITE_ORDER.includes(k))];
  return keys.map((key) => {
    const given = suites[key] ?? {};
    const fallback = tallyFromScenarios(list, key);
    const pick = (k: keyof EvalsSuiteTally) => num(given[k]) ?? (list.length ? num(fallback[k]) : null);
    return {
      key,
      title: SUITE_TITLES[key] ?? key.toUpperCase(),
      cenarios: pick("cenarios"),
      passaram: pick("passaram"),
      falharam: pick("falharam"),
      naoExecutados: pick("nao_executados"),
    };
  });
}

export interface Metric {
  label: string;
  value: string;
  note: string;
  measured: boolean;
  /** `bad` quando a meta é zero e o número não é; `good` quando é zero. Sem valor medido, sem tom. */
  tone?: "good" | "bad";
}

const unmeasured = (label: string, note: string): Metric => ({ label, value: NOT_MEASURED, note, measured: false });

/** As quatro métricas do RN-04, na ordem do requisito. */
export function rn04Metrics(r: EvalsReport): Metric[] {
  const rn = r.rn04 ?? {};
  const v = rn.violacoes_nao_detectadas;
  const missed = num(v?.nao_detectadas);
  const planted = num(v?.plantadas);
  const fp = num(v?.falsos_positivos);
  const violations: Metric =
    missed === null
      ? unmeasured("Violações não detectadas", "meta 0")
      : {
          label: "Violações não detectadas",
          value: String(missed),
          note: `de ${planted ?? "—"} plantadas · falsos positivos ${fp ?? "não medido"} · meta 0`,
          measured: true,
          tone: missed === 0 && (fp ?? 0) === 0 ? "good" : "bad",
        };

  const cov = rn.cobertura;
  const demoPct = num(cov?.escala_demo_pct);
  const cases = num(cov?.casos_cobertos);
  const coverage: Metric =
    demoPct === null && cases === null
      ? unmeasured("Cobertura", "escala da demo e casos cobertos")
      : {
          label: "Cobertura",
          value: demoPct === null ? NOT_MEASURED : pct(demoPct),
          note: `escala da demo · casos cobertos: ${cases === null ? NOT_MEASURED : pct(cases)}`,
          measured: demoPct !== null,
        };

  const cost = rn.custo_contra_planilha;
  const costMetric: Metric =
    present(cost?.antes_brl) && present(cost?.depois_brl)
      ? {
          label: "Custo contra a planilha",
          value: `${money(cost.antes_brl)} → ${money(cost.depois_brl)}`,
          note: cost.fonte ?? "função de custo do código, dados sintéticos",
          measured: true,
        }
      : unmeasured("Custo contra a planilha", "função de custo do código, dados sintéticos");

  const att = rn.acerto_atestado;
  const right = num(att?.campos_certos);
  const fields = num(att?.campos);
  const n = num(att?.n_atestados);
  const attestation: Metric =
    att?.status === "não medido" || right === null || fields === null || fields === 0
      ? unmeasured("Acerto na leitura do atestado", "exige a rodada com modelo")
      : {
          label: "Acerto na leitura do atestado",
          value: `${right}/${fields} campos`,
          note: `${pct(Math.round((right / fields) * 1000) / 10)} · ${n ?? "—"} atestado(s) lidos com modelo`,
          measured: true,
        };

  return [violations, coverage, costMetric, attestation];
}

export interface ModelRow {
  label: string;
  value: string;
  measured: boolean;
}

/** Custo e latência do modelo: os do rastro da rodada com modelo, ou "não medido". */
export function modelRows(r: EvalsReport): ModelRow[] {
  const m = r.modelo ?? {};
  const cost = m.cost_usd;
  const p50 = num(m.latencia_ms_p50);
  const max = num(m.latencia_ms_max);
  const calls = num(m.chamadas);
  const row = (label: string, value: string | null): ModelRow => ({ label, value: value ?? NOT_MEASURED, measured: value !== null });
  return [
    row("Chamadas ao modelo", calls === null || calls === 0 ? null : String(calls)),
    row("Custo medido", present(cost) ? costUsd(String(cost)) : null),
    row("Latência p50", p50 === null ? null : latency(p50)),
    row("Latência máxima", max === null ? null : latency(max)),
  ];
}
