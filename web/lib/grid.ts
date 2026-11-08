import { shiftLabel, spanHours, weekDays } from "./format.ts";
import type { EmployeePublic, Schedule, Shift } from "./types.ts";

export interface GridCell {
  kind: "shift" | "off";
  label: string;
}

export interface GridRow {
  name: string;
  sub: string;
  cells: GridCell[];
}

export interface StoreGrid {
  storeId: string;
  rows: GridRow[];
}

export interface Grid {
  days: string[];
  stores: StoreGrid[];
}

function fmtHours(h: number): string {
  return `${h.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} h`;
}

/** Pessoa x dia por loja, a partir da grade e das pessoas (sem `sex`). Turnos de quem não está na lista ficam na loja do turno. */
export function buildGrid(schedule: Schedule, employees: EmployeePublic[]): Grid {
  const week = weekDays(schedule.week_start);
  const byPerson = new Map<string, Shift[]>();
  for (const s of schedule.shifts) byPerson.set(s.employee_id, [...(byPerson.get(s.employee_id) ?? []), s]);

  const people = employees.map((e) => ({ id: e.id, name: e.name, store: e.store_id, job: e.job }));
  const known = new Set(employees.map((e) => e.id));
  for (const [id, shifts] of byPerson) {
    if (!known.has(id)) people.push({ id, name: id, store: shifts[0].store_id, job: "" });
  }

  const stores = new Map<string, GridRow[]>();
  for (const p of people) {
    const mine = byPerson.get(p.id) ?? [];
    const total = mine.reduce((acc, s) => acc + spanHours(s.start, s.end), 0);
    const row: GridRow = {
      name: p.name,
      sub: [p.job, fmtHours(total)].filter((v) => v !== "").join(" · "),
      cells: week.map((d) => {
        const today = mine.filter((s) => s.start.slice(0, 10) === d.iso);
        return today.length
          ? { kind: "shift", label: today.map((s) => shiftLabel(s.start, s.end)).join(" + ") }
          : { kind: "off", label: "folga" };
      }),
    };
    stores.set(p.store, [...(stores.get(p.store) ?? []), row]);
  }
  return {
    days: week.map((d) => d.label),
    stores: [...stores.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([storeId, rows]) => ({ storeId, rows })),
  };
}
