import type { ReactNode } from "react";
import { StatusChip } from "../StatusChip";

/** Selo permanente: tudo na demonstração é sintético (regra de integridade do projeto). */
export function SyntheticBadge() {
  return <StatusChip tone="neutral">dados sintéticos</StatusChip>;
}

/** Cartão de seção da plataforma: `rounded-card` branco, título no estilo `title`. */
export function Card({ title, aside, children, id }: { title: string; aside?: ReactNode; children: ReactNode; id?: string }) {
  return (
    <section aria-labelledby={id} className="rounded-card bg-surface p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 id={id} className="text-lg font-bold tracking-[-0.02em]">
          {title}
        </h2>
        {aside && <span className="tabular text-[13px] text-ink-muted">{aside}</span>}
      </div>
      {children}
    </section>
  );
}

/** Aviso de erro ou de estado. `alert` interrompe a leitura; `status` espera a vez. */
export function Notice({ tone = "warning", role = "alert", children }: { tone?: "warning" | "danger"; role?: "alert" | "status"; children: ReactNode }) {
  const cls = tone === "danger" ? "border-[#efc3c3] bg-danger-soft text-danger" : "border-[#f4d6ad] bg-warning-soft text-warning-ink";
  return (
    <div role={role} className={`rounded-bubble border px-4 py-3 text-[15px] font-medium ${cls}`}>
      {children}
    </div>
  );
}

export function Muted({ children }: { children: ReactNode }) {
  return <p className="text-sm text-ink-muted">{children}</p>;
}

/** Tabela de dados no estilo da grade: linhas finas, números tabulares, rola dentro do cartão no celular. */
export function DataTable({ caption, head, children }: { caption: string; head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="tabular w-full min-w-[480px] border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="text-[13px] text-ink-muted">
            {head.map((h, i) => (
              <th key={`${h}-${i}`} scope="col" className="border-b border-line px-2 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export const cellCls = "border-b border-line px-2 py-2.5 align-top";
