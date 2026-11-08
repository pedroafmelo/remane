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
