import type { ReactNode } from 'react'
import { ROLE_LABELS, costUsd, ruleStatusLabel, timeBr } from '../format'
import type { ExceptionCard } from '../types'

export function SyntheticBadge() {
  return <span className="badge badge-synth">dados sintéticos</span>
}

export function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="card">
      <div className="card-head">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export function RuleChip({ id, status }: { id: string; status?: string }) {
  return (
    <code className="chip" title={status ? `status: ${ruleStatusLabel(status)}` : undefined}>
      {id}
      {status ? ` · ${ruleStatusLabel(status)}` : ''}
    </code>
  )
}

/** Cartão de exceção (FT-04): código, título, motivo, quem decide e recomendação. */
export function ExceptionCardView({ card }: { card: ExceptionCard }) {
  return (
    <section className="card exception" role="alert">
      <div className="card-head">
        <h2>
          <span className="badge badge-warn">{card.code}</span> {card.title}
        </h2>
      </div>
      <dl className="facts">
        <dt>Motivo</dt>
        <dd>{card.reason}</dd>
        <dt>Quem decide</dt>
        <dd>{card.decider ? (ROLE_LABELS[card.decider] ?? card.decider) : 'Não definido'}</dd>
        {card.deadline && (
          <>
            <dt>Prazo</dt>
            <dd>{timeBr(card.deadline)}</dd>
          </>
        )}
        {card.recommendation && (
          <>
            <dt>Recomendação</dt>
            <dd>{card.recommendation}</dd>
          </>
        )}
        {card.if_no_answer && (
          <>
            <dt>Se ninguém responder</dt>
            <dd>{card.if_no_answer}</dd>
          </>
        )}
      </dl>
      {card.evidence.length > 0 && (
        <>
          <h3>Evidências</h3>
          <ul>
            {card.evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </>
      )}
      {card.options.length > 0 && (
        <>
          <h3>Opções</h3>
          <ul>
            {card.options.map((o, i) => (
              <li key={i}>
                {o.label}
                {o.effect ? `: ${o.effect}` : ''}
                {o.cost_usd !== null ? ` (${costUsd(o.cost_usd)})` : ''}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
