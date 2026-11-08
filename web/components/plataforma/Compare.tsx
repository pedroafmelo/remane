import { savingsCaveat } from "@/lib/compare";
import { hours, money, pct } from "@/lib/format";
import type { Comparison, ScheduleMetrics } from "@/lib/types";
import { ImpactStat } from "../ImpactStat";
import { Card, DataTable, Muted, cellCls } from "./ui";

const ROWS: [string, (m: ScheduleMetrics) => string][] = [
  ["Custo total", (m) => money(m.total_cost)],
  ["Horas normais", (m) => hours(m.regular_hours)],
  ["Horas extras", (m) => hours(m.overtime_hours)],
  ["Custo das horas extras", (m) => money(m.overtime_cost)],
  ["Cobertura da demanda", (m) => pct(m.coverage_pct)],
  ["Faixas sem cobertura", (m) => String(m.uncovered_slots)],
  ["Violações", (m) => String(m.violations)],
];

/** Antes e depois pela mesma função de custo; as violações depois ficam em destaque (meta 0). */
export function ComparePanel({ comparison }: { comparison: Comparison }) {
  const { before, after } = comparison;
  const clean = after.violations === 0;
  return (
    <Card title="Antes e depois" id="antes-depois">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-3">
        <ImpactStat size="sm" label="Violações depois" value={String(after.violations)} tone={clean ? "good" : "bad"} note={clean ? "meta 0 atingida" : "meta 0 não atingida"} />
        <ImpactStat size="sm" label="Violações antes" value={String(before.violations)} />
        <ImpactStat size="sm" label="Economia" value={money(comparison.savings)} tone="good" note={savingsCaveat(comparison) ?? undefined} />
        <ImpactStat size="sm" label="Cobertura depois" value={pct(after.coverage_pct)} note={`antes: ${pct(before.coverage_pct)}`} />
        <ImpactStat size="sm" label="Horas extras evitadas" value={hours(comparison.overtime_hours_avoided)} />
        <ImpactStat size="sm" label="Violações evitadas" value={String(comparison.violations_avoided)} />
      </div>
      <div className="mt-5">
        <DataTable caption="Escala atual e escala proposta lado a lado" head={["", "Antes", "Depois"]}>
          {ROWS.map(([label, fmt]) => (
            <tr key={label}>
              <th scope="row" className={`${cellCls} font-medium`}>
                {label}
              </th>
              <td className={cellCls}>{fmt(before)}</td>
              <td className={cellCls}>{fmt(after)}</td>
            </tr>
          ))}
        </DataTable>
      </div>
      <div className="mt-3">
        <Muted>
          Custo e horas calculados pela mesma função nas duas escalas, sobre dados sintéticos. Leia a economia junto da cobertura: cobrir menos
          custa menos.
        </Muted>
      </div>
    </Card>
  );
}
