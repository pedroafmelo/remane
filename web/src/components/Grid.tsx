import { dateBr, hhmm, weekDays } from '../format'
import type { EmployeePublic, Schedule, Shift } from '../types'
import { Section } from './Common'

function cell(shifts: Shift[]): string[] {
  return shifts.map((s) => `${hhmm(s.start)}–${hhmm(s.end)}${s.end.slice(0, 10) !== s.start.slice(0, 10) ? ' (+1)' : ''}`)
}

function spanHours(shifts: Shift[]): number {
  return shifts.reduce((acc, s) => acc + (Date.parse(s.end) - Date.parse(s.start)) / 3_600_000, 0)
}

/** Grade semanal: pessoa × dia, com os horários dos turnos. */
export function GridView({
  title,
  schedule,
  employees,
  note,
}: {
  title: string
  schedule: Schedule
  employees: EmployeePublic[]
  note?: string
}) {
  const days = weekDays(schedule.week_start)
  const byPerson = new Map<string, Shift[]>()
  for (const s of schedule.shifts) byPerson.set(s.employee_id, [...(byPerson.get(s.employee_id) ?? []), s])
  const known = new Set(employees.map((e) => e.id))
  const rows = [
    ...employees.map((e) => ({ id: e.id, name: e.name, sub: `${e.id} · ${e.store_id}` })),
    ...[...byPerson.keys()].filter((id) => !known.has(id)).map((id) => ({ id, name: id, sub: '' })),
  ]
  return (
    <Section title={title} aside={<span className="muted">semana de {dateBr(schedule.week_start)}</span>}>
      {note && <p className="muted">{note}</p>}
      <div className="table-wrap">
        <table className="table grid">
          <thead>
            <tr>
              <th>Pessoa</th>
              {days.map((d) => (
                <th key={d.iso}>{d.label}</th>
              ))}
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const mine = byPerson.get(r.id) ?? []
              return (
                <tr key={r.id}>
                  <th scope="row">
                    {r.name}
                    {r.sub && <div className="muted small">{r.sub}</div>}
                  </th>
                  {days.map((d) => {
                    const todays = mine.filter((s) => s.start.slice(0, 10) === d.iso)
                    return (
                      <td key={d.iso} className={todays.length ? '' : 'off'}>
                        {todays.length ? cell(todays).map((t) => <div key={t}>{t}</div>) : 'folga'}
                      </td>
                    )
                  })}
                  <td>{spanHours(mine).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Section>
  )
}
