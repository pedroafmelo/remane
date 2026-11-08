const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const num1 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })
const usd = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 6 })

/** Reais a partir de um Decimal em string. */
export function money(value: string | number): string {
  return brl.format(Number(value))
}

export function hours(value: string | number): string {
  return `${num1.format(Number(value))} h`
}

export function pct(value: number): string {
  return `${num1.format(value)}%`
}

/** Custo medido em US$: 0 aparece como 0 e nulo como "—" (nunca confundir os dois). */
export function costUsd(value: string | null): string {
  return value === null ? '—' : `US$ ${usd.format(Number(value))}`
}

export function latency(ms: number | null): string {
  if (ms === null) return '—'
  return ms >= 1000 ? `${num1.format(ms / 1000)} s` : `${ms} ms`
}

/** "2027-01-11" -> "11/01/2027" (sem passar por Date, para não deslocar o dia por fuso). */
export function dateBr(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split('-')
  return `${d}/${m}/${y}`
}

/** "2027-01-11T08:00:00" -> "08:00" */
export function hhmm(iso: string): string {
  return iso.slice(11, 16)
}

export function timeBr(iso: string): string {
  return `${dateBr(iso)} ${iso.slice(11, 19)}`
}

const STATUS_LABELS: Record<string, string> = {
  ficticia: 'fictícia (demo)',
  conferida: 'conferida',
  interpretacao: 'interpretação',
  pendente: 'pendente',
}

/** Status de regra como está; `ficticia` aparece como "fictícia (demo)". */
export function ruleStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

export const ROLE_LABELS: Record<string, string> = {
  gerente: 'Gerente',
  dp: 'DP (departamento pessoal)',
  colaborador: 'Colaborador',
}

export const PHASE_LABELS: Record<string, string> = {
  read: 'Lendo o arquivo',
  awaiting_confirm: 'Aguardando a confirmação da leitura',
  optimized: 'Escala otimizada',
  awaiting_approval: 'Aguardando a aprovação do gerente',
  published: 'Publicada',
  failed: 'Interrompida com exceção',
}

const WEEKDAYS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

export function weekDays(weekStart: string): { iso: string; label: string }[] {
  const [y, m, d] = weekStart.split('-').map(Number)
  return WEEKDAYS.map((label, i) => {
    const dt = new Date(Date.UTC(y, m - 1, d + i))
    const iso = dt.toISOString().slice(0, 10)
    return { iso, label: `${label} ${iso.slice(8, 10)}/${iso.slice(5, 7)}` }
  })
}
