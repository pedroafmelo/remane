import { costUsd, latency, timeBr } from '../format'
import type { TraceEvent } from '../types'
import { RuleChip, Section } from './Common'

/** Status de regra só aparece se o evento o trouxer no payload (a API não o inventa). */
function ruleStatus(e: TraceEvent): string | undefined {
  const v = e.payload['rule_status']
  return typeof v === 'string' ? v : undefined
}

export function TraceView({ events }: { events: TraceEvent[] }) {
  const total = events.reduce((acc, e) => acc + (e.cost_usd === null ? 0 : Number(e.cost_usd)), 0)
  return (
    <Section title="Rastro da execução" aside={<span className="muted">custo medido: {costUsd(String(total))}</span>}>
      {events.length === 0 ? (
        <p className="muted">Nenhum evento ainda.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Hora</th>
                <th>Regra</th>
                <th>Modelo</th>
                <th>Custo</th>
                <th>Latência</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td>
                    <code>{e.kind}</code>
                  </td>
                  <td>{timeBr(e.at)}</td>
                  <td>{e.rule_ref ? <RuleChip id={e.rule_ref} status={ruleStatus(e)} /> : '—'}</td>
                  <td>{e.model ?? '—'}</td>
                  <td>{costUsd(e.cost_usd)}</td>
                  <td>{latency(e.latency_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  )
}
