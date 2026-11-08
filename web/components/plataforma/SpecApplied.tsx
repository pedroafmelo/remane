import { dateBr } from "@/lib/format";
import type { EmployeePublic, SolveSpec, SpecConstraint } from "@/lib/types";
import { StatusChip } from "../StatusChip";
import { Card } from "./ui";

const WINDOWS = { manha: "manhã", tarde: "tarde", noite: "noite" } as const;

function describe(c: SpecConstraint): { kind: string; hard: boolean; text: string } {
  switch (c.type) {
    case "indisponivel": {
      const span = c.start && c.end ? ` (${c.start.slice(0, 5)} às ${c.end.slice(0, 5)})` : "";
      return { kind: "Indisponível", hard: true, text: `não trabalha em ${dateBr(c.day)}${span}` };
    }
    case "max_horas_semana":
      return { kind: "Limite semanal", hard: true, text: `no máximo ${c.hours} h na semana` };
    case "folga_preferida":
      return { kind: "Folga preferida", hard: false, text: `prefere folgar em ${dateBr(c.day)}` };
    case "janela_preferida":
      return { kind: "Janela preferida", hard: false, text: `prefere trabalhar de ${WINDOWS[c.window]}` };
  }
}

/** O pedido do gestor traduzido pelo Pat em restrições aceitas, cada uma com o trecho do pedido que a justifica. */
export function SpecApplied({ spec, employees }: { spec: SolveSpec; employees: EmployeePublic[] }) {
  if (spec.constraints.length === 0) return null;
  const names = new Map(employees.map((e) => [e.id, e.name]));
  return (
    <Card title="O que o Pat aplicou do seu pedido" id="pedido-aplicado" aside={`${spec.constraints.length} restrição(ões)`}>
      <ul className="flex flex-col gap-3">
        {spec.constraints.map((c, i) => {
          const d = describe(c);
          return (
            <li key={`${i}-${c.type}-${c.employee_id}`} className="flex flex-col gap-1">
              <span className="flex flex-wrap items-center gap-2 text-sm">
                <StatusChip tone={d.hard ? "ok" : "neutral"}>{d.kind}</StatusChip>
                <span className="font-medium">{names.get(c.employee_id) ?? c.employee_id}</span>
                <span className="text-ink-muted">{d.text}</span>
              </span>
              <span className="text-[13px] text-ink-muted">Do seu pedido: “{c.evidence}”</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[13px] text-ink-muted">
        Restrições duras o solver cumpre sempre; as preferências ele tenta cumprir. Lei e convenção não mudam com o pedido.
      </p>
    </Card>
  );
}
