import { hours, money, pct } from '../format'
import type { Comparison, ScheduleMetrics } from '../types'
import { Section } from './Common'
import { Stat } from './Summary'

/** Antes e depois pela mesma função de custo; as violações depois ficam em destaque (meta 0). */
export function CompareView({ comparison }: { comparison: Comparison }) {
  const { before, after } = comparison
  const rows: [string, (m: ScheduleMetrics) => string][] = [
    ['Custo total', (m) => money(m.total_cost)],
    ['Horas normais', (m) => hours(m.regular_hours)],
    ['Horas extras', (m) => hours(m.overtime_hours)],
    ['Custo das horas extras', (m) => money(m.overtime_cost)],
    ['Cobertura da demanda', (m) => pct(m.coverage_pct)],
    ['Faixas sem cobertura', (m) => String(m.uncovered_slots)],
    ['Violações', (m) => String(m.violations)],
  ]
  return (
    <Section title="Antes e depois">
      <div className="stats">
        <Stat
          label="Violações depois (meta 0)"
          value={String(after.violations)}
          tone={after.violations === 0 ? 'good' : 'bad'}
        />
        <Stat label="Violações antes" value={String(before.violations)} />
        <Stat label="Economia" value={money(comparison.savings)} tone="good" />
        <Stat label="Horas extras evitadas" value={hours(comparison.overtime_hours_avoided)} />
        <Stat label="Violações evitadas" value={String(comparison.violations_avoided)} />
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th></th>
              <th>Antes</th>
              <th>Depois</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, fmt]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{fmt(before)}</td>
                <td>{fmt(after)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">Custo e horas calculados pela mesma função nas duas escalas, sobre dados sintéticos.</p>
    </Section>
  )
}
