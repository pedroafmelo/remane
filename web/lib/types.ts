// Espelho dos contratos da API (src/escalista/domain). Decimal chega como string no JSON.

export type Role = 'gestor' | 'colaborador'

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

export type Weekday = 'seg' | 'ter' | 'qua' | 'qui' | 'sex' | 'sab' | 'dom'

/** Coluna apontada pelo mapeamento: índice (a partir de 0) e texto literal do cabeçalho. */
export interface ColumnRef {
  index: number
  header: string
}

export interface ShiftCode {
  code: string
  start: string | null // "07:00:00"
  end: string | null
  off: boolean
  evidence: string | null
}

export interface DayColumn {
  col: ColumnRef
  day: string | null
  weekday: Weekday | null
}

export interface ColumnMapping {
  table: number
  header_row: number
  layout: 'long' | 'grid'
  person: ColumnRef
  person_code: ColumnRef | null
  store: ColumnRef | null
  date: ColumnRef | null
  start: ColumnRef | null
  end: ColumnRef | null
  shift: ColumnRef | null
  day_columns: DayColumn[]
  date_order: 'dmy' | 'ymd' | 'mdy'
  shift_codes: ShiftCode[]
  wage: ColumnRef | null
  notes: ColumnRef | null
}

export interface CellRef {
  table: number
  row: number
  col: number
}

export interface IdentityCard {
  id: string
  kind: 'homonimo' | 'grafia_parecida' | 'sem_par_no_quadro'
  names: string[]
  rows: CellRef[]
  suggestion: 'mesma' | 'distintas'
  reason: string
}

export interface CapacityCheck {
  demand_person_hours: string
  capacity_person_hours: string
  fits: boolean
  max_fitting_pct: number
}

export interface CsvIssue {
  line: number
  field: string | null
  reason: string
  table?: string | null
  col?: number | null
}

export type MappingSource = 'modelo' | 'heuristica' | 'csv_dec039' | 'plataforma'

export interface ReadSummary {
  file_name: string
  rows: number
  employees: number
  stores: number
  week_start: string | null
  total_hours: string
  issues: CsvIssue[]
  ok: boolean
  format: 'csv' | 'xlsx' | 'pdf' | 'continuidade'
  mapping: ColumnMapping | null
  mapping_source: MappingSource
  assumptions: string[]
  identity: IdentityCard[]
  capacity: CapacityCheck | null
  planned_week_start: string | null
  /**
   * Ids das lojas lidas, para o seletor de cobertura-alvo. PEDIDO ao backend: o contrato da C6 ainda não traz a lista
   * (só `stores`, a contagem); sem ela a tela cai no quadro guardado (`GET /api/roster`) e, sem os dois, não mostra o
   * seletor.
   */
  store_ids?: string[]
}

export interface IdentityAnswer {
  card_id: string
  same: boolean
}

/** O que o gestor confirma ou corrige depois da leitura (`POST /api/runs/{id}/confirm`). */
export interface ConfirmInput {
  coverage_pct: Record<string, number>
  hourly_wage_default?: string
  planned_week_start?: string
  note: string
  identity: IdentityAnswer[]
}

export interface Store {
  id: string
  name: string
  opens: string
  closes: string
}

/** `GET /api/roster`: só as lojas importam para a tela. */
export interface Roster {
  version: number
  stores: Store[]
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
  mode: 'upload' | 'continuidade'
  week_start: string | null
  /** Avisos que não bloqueiam (RX-02, RX-12 da leitura e da formulação). `exception` é o que bloqueia. */
  notices: ExceptionCard[]
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
