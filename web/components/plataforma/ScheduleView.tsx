"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { dateBr } from "@/lib/format";
import { buildGrid } from "@/lib/grid";
import type { EmployeePublic, Schedule } from "@/lib/types";
import { ScheduleGrid } from "../ScheduleGrid";
import { StatusChip } from "../StatusChip";
import { Card, Muted } from "./ui";

/** Grade semanal pessoa x dia, uma loja por vez. Só apresenta: nada é calculado aqui. */
export function ScheduleView({ title, schedule, employees, note, id }: { title: string; schedule: Schedule; employees: EmployeePublic[]; note?: string; id: string }) {
  const grid = useMemo(() => buildGrid(schedule, employees), [schedule, employees]);
  const [picked, setPicked] = useState(0);
  const store = grid.stores[Math.min(picked, Math.max(grid.stores.length - 1, 0))];
  const [names, setNames] = useState<Map<string, string>>(new Map());
  useEffect(() => {
    // sem quadro guardado (404 num banco novo) ou com ids que não batem, a loja aparece pelo id
    api.roster().then((r) => setNames(new Map(r.stores.map((s) => [s.id, s.name]))), () => {});
  }, [schedule]);
  const storeName = (id: string) => {
    const name = names.get(id);
    return name && name !== id ? name : `Loja ${id}`; // o CSV padrão grava o id como nome
  };
  return (
    <Card title={title} id={id} aside={`semana de ${dateBr(schedule.week_start)}`}>
      {note && (
        <div className="mb-3">
          <Muted>{note}</Muted>
        </div>
      )}
      {grid.stores.length > 1 && (
        <div role="group" aria-label="Loja" className="mb-3 flex flex-wrap gap-2">
          {grid.stores.map((s, i) => (
            <button
              key={s.storeId}
              type="button"
              aria-pressed={i === picked}
              onClick={() => setPicked(i)}
              className={`h-9 rounded-full border px-3.5 text-[13px] font-medium transition-colors ${
                i === picked ? "border-ink bg-ink text-white" : "border-line-strong bg-surface text-ink hover:border-ink-subtle"
              }`}
            >
              {storeName(s.storeId)}
            </button>
          ))}
        </div>
      )}
      {store ? (
        <ScheduleGrid
          title={storeName(store.storeId)}
          chip={<StatusChip tone="neutral">{store.rows.length} pessoas</StatusChip>}
          days={grid.days}
          rows={store.rows}
          nameCol="176px"
          minWidth={820}
        />
      ) : (
        <Muted>Esta grade não tem turnos.</Muted>
      )}
    </Card>
  );
}
