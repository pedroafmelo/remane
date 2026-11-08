// Espelho dos contratos da API (src/escalista/domain). Decimal chega como string no JSON.

export type Role = 'gerente' | 'dp' | 'colaborador'

export interface Me {
  id: string
  nome: string
  papel: Role
}

export interface ExceptionOption {
  label: string
  cost_usd: string | null
  effect: string | null
}

export interface ExceptionCard {
  code: string
  title: string
  reason: string
  decider: Role | null
  deadline: string | null
  evidence: string[]
  options: ExceptionOption[]
  recommendation: string | null
  if_no_answer: string | null
  trace_id: string | null
}

export interface CsvIssue {
  line: number
  field: string | null
  reason: string
}

export interface ReadSummary {
  file_name: string
  rows: number
  employees: number
  stores: number
  week_start: string | null
  total_hours: string
  issues: CsvIssue[]
  ok: boolean
}

export interface ScheduleMetrics {
  total_cost: string
  regular_hours: string
  overtime_hours: string
  overtime_cost: string
  coverage_pct: number
  uncovered_slots: number
  violations: number
}

export interface Comparison {
  before: ScheduleMetrics
  after: ScheduleMetrics
  savings: string
  overtime_hours_avoided: string
  violations_avoided: number
}

export interface Violation {
  rule_id: string
  kind: string
  employee_id: string | null
  day: string | null
  source: string
  detail: string
}

export interface ViolationReport {
  violations: Violation[]
  total: number
}

export interface JustificationItem {
  text: string
  rule_refs: string[]
}

export interface Justification {
  summary: string
  items: JustificationItem[]
}

export type Phase = 'read' | 'awaiting_confirm' | 'optimized' | 'awaiting_approval' | 'published' | 'failed'

export interface RunState {
  run_id: string
  phase: Phase
  summary: ReadSummary | null
  comparison: Comparison | null
  report: ViolationReport | null
  justification: Justification | null
  version_id: string | null
  exception: ExceptionCard | null
}

export interface Shift {
  employee_id: string
  store_id: string
  start: string
  end: string
}

export interface Schedule {
  week_start: string
  shifts: Shift[]
}

export interface EmployeePublic {
  id: string
  name: string
  store_id: string
  job: string
  hourly_wage: string
  contract_hours: number
  profile: 'padrao' | 'aprendiz' | 'menor'
}

export interface ProposedSchedule {
  schedule: Schedule
  employees: EmployeePublic[]
}

export interface ScheduleVersion {
  id: string
  run_id: string
  schedule: Schedule
  status: 'draft' | 'approved' | 'published'
  input_hash: string
  seed: number
  violations_total: number
  created_at: string
}

export interface PublishedSchedule {
  version: ScheduleVersion | null
  employees: EmployeePublic[]
}

export interface TraceEvent {
  id: string
  run_id: string
  parent_id: string | null
  kind: string
  at: string
  rule_ref: string | null
  message_ref: string | null
  model: string | null
  key_index: number | null
  tokens_in: number | null
  tokens_out: number | null
  cost_usd: string | null
  latency_ms: number | null
  payload: Record<string, unknown>
}
