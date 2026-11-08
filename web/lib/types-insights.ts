// Espelho de src/escalista/api/insights.py e simulation.py. Decimal chega como string no JSON.

import type { ExceptionCard, ScheduleMetrics } from "./types.ts";

export interface RuleView {
  id: string
  title: string
  limit: string
  status: string
  source: string
  engine: boolean
  escalates: boolean
  provisional: boolean
  note: string | null
}

export interface RuleGroup {
  layer: "lei" | "convencao" | "politica"
  title: string
  rules: RuleView[]
}

export interface RulesView {
  reference_date: string
  groups: RuleGroup[]
}

export interface RegimeResult {
  regime: "44h" | "42h"
  label: string
  reference_date: string
  limits: string[]
  status: string
  solve_ms: number
  metrics: ScheduleMetrics
  uncovered_person_hours: number
  violations_under_ec141: number
  hiring: ExceptionCard | null
}

export interface VigenciaSimulation {
  simulated: true
  week_start: string
  cached: boolean
  before: RegimeResult
  after: RegimeResult
  cost_of_ec141: string
  coverage_change_pct: number
  notes: string[]
}

export interface RunImpact {
  run_id: string
  phase: string
  started_at: string | null
  published_at: string | null
  cost_before: string | null
  cost_after: string | null
  savings: string | null
  overtime_hours_avoided: string | null
  violations_avoided: number | null
  coverage_after: number | null
  agent_cost_usd: string
  agent_latency_ms: number
  events: number
}

export interface Impact {
  current: RunImpact | null
  runs_total: number
  runs_published: number
  agent_cost_usd_total: string
  agent_latency_ms_avg: number | null
  runs: RunImpact[]
  provenance: Record<"comparison" | "agent" | "scope", string>
}

// Retrato do relatório de evals (src/escalista/api/evals_view.py). Tolerante: tudo que não foi medido vem `null` ou ausente.
export interface EvalsCounts {
  cenarios?: number | null
  sem_modelo?: number | null
  com_modelo?: number | null
  executados?: number | null
  passaram?: number | null
  falharam?: number | null
  nao_executados?: number | null
  com_modelo_executados?: number | null
}

export interface EvalsSuiteTally {
  cenarios?: number | null
  passaram?: number | null
  falharam?: number | null
  nao_executados?: number | null
}

export interface EvalsScenario {
  id: string
  suite?: string
  status?: "passou" | "falhou" | "não executado" | string
  usa_modelo?: boolean
  motivo?: string | null
}

export interface EvalsRn04 {
  violacoes_nao_detectadas?: {
    plantadas?: number | null
    detectadas?: number | null
    nao_detectadas?: number | null
    falsos_positivos?: number | null
  } | null
  cobertura?: { escala_demo_pct?: number | null; casos_cobertos?: number | null } | null
  custo_contra_planilha?: { antes_brl?: string | number | null; depois_brl?: string | number | null; fonte?: string | null } | null
  acerto_atestado?: {
    campos_certos?: number | null
    campos?: number | null
    n_atestados?: number | null
    status?: "medido" | "não medido" | string | null
  } | null
}

export interface EvalsModelUse {
  chamadas?: number | null
  cost_usd?: string | number | null
  latencia_ms_p50?: number | null
  latencia_ms_max?: number | null
  teto_usd?: number | string | null
}

export interface EvalsReport {
  status: "ok"
  suite?: string | null
  gerado_em?: string | null
  git_sha?: string | null
  modo?: "sem_modelo" | "com_modelo" | string | null
  dados?: string | null
  comando?: string | null
  privacidade?: string | null
  contagem: EvalsCounts
  rn04?: EvalsRn04 | null
  modelo?: EvalsModelUse | null
  suites?: Record<string, EvalsSuiteTally> | null
  cenarios?: EvalsScenario[] | null
}

export interface EvalsMissing {
  status: "sem_relatorio"
}

export type EvalsResponse = EvalsReport | EvalsMissing
