import { dateBr, hours } from '../format'
import type { ReadSummary } from '../types'
import { Section } from './Common'

/** Resumo da leitura (RF-23): o gerente confere antes de confirmar. */
export function SummaryView({
  summary,
  canConfirm,
  busy,
  onConfirm,
}: {
  summary: ReadSummary
  canConfirm: boolean
  busy: boolean
  onConfirm: () => void
}) {
  return (
    <Section title="Resumo da leitura" aside={<span className="muted">{summary.file_name}</span>}>
      <div className="stats">
        <Stat label="Linhas" value={String(summary.rows)} />
        <Stat label="Pessoas" value={String(summary.employees)} />
        <Stat label="Lojas" value={String(summary.stores)} />
        <Stat label="Semana (segunda)" value={summary.week_start ? dateBr(summary.week_start) : '—'} />
        <Stat label="Horas totais" value={hours(summary.total_hours)} />
      </div>
      {summary.issues.length > 0 ? (
        <>
          <h3>Problemas encontrados ({summary.issues.length})</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Linha</th>
                <th>Campo</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              {summary.issues.map((issue, i) => (
                <tr key={i}>
                  <td>{issue.line}</td>
                  <td>{issue.field ?? '—'}</td>
                  <td>{issue.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="ok">Nenhum problema encontrado na leitura.</p>
      )}
      {canConfirm && summary.ok && (
        <div className="actions">
          <button className="btn btn-primary" onClick={onConfirm} disabled={busy}>
            {busy ? 'Otimizando…' : 'Confirmar'}
          </button>
          <span className="muted">Confirma que a leitura está certa e libera a otimização.</span>
        </div>
      )}
    </Section>
  )
}

export function Stat({ label, value, tone }: { label: string; value: string; tone?: 'good' | 'bad' }) {
  return (
    <div className={`stat${tone ? ` stat-${tone}` : ''}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
