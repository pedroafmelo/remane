import type { Justification } from '../types'
import { RuleChip, Section } from './Common'

/** Justificativa com as regras citadas. Quem chama só renderiza isto sem `exception` na execução. */
export function JustificationView({ justification }: { justification: Justification }) {
  return (
    <Section title="Justificativa">
      <p>{justification.summary}</p>
      <ul className="justify">
        {justification.items.map((item, i) => (
          <li key={i}>
            {item.text}{' '}
            {item.rule_refs.map((r) => (
              <RuleChip key={r} id={r} />
            ))}
          </li>
        ))}
      </ul>
    </Section>
  )
}
