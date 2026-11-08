import type { ReactNode } from "react";
import { ShiftCell, type ShiftCellProps } from "./ShiftCell";

type Row = { name: string; sub?: string; cells: ShiftCellProps[] };

type GridProps = {
  title: string;
  chip?: ReactNode;
  days: string[];
  rows: Row[];
  /** Largura da coluna de nomes (padrão 64px, que serve para primeiros nomes). */
  nameCol?: string;
  /** Largura mínima da grade antes de rolar na horizontal (padrão 560px). */
  minWidth?: number;
};

export function ScheduleGrid({ title, chip, days, rows, nameCol = "64px", minWidth = 560 }: GridProps) {
  return (
    <div className="min-w-0 rounded-card bg-surface p-4 shadow-float sm:p-5.5">
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-bold tracking-[-0.03em] sm:text-lg">{title}</h3>
        {chip}
      </div>
      {/* a grade rola dentro do cartão; a página nunca rola de lado */}
      <div className="overflow-x-auto">
        <div className="grid gap-1 sm:gap-1.5" style={{ minWidth, gridTemplateColumns: `${nameCol} repeat(7, 1fr)` }}>
          <span />
          {days.map((d) => (
            <span key={d} className="px-1 text-[13px] font-medium text-ink-subtle">{d}</span>
          ))}
          {rows.map((r) => (
            <div key={r.name} className="contents">
              <span className="self-center pr-1 text-[15px] font-medium sm:text-base">
                {r.name}
                {r.sub && <span className="tabular block text-xs font-normal text-ink-muted">{r.sub}</span>}
              </span>
              {r.cells.map((c, i) => (
                <ShiftCell key={`${r.name}-${i}-${c.kind}`} {...c} />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
