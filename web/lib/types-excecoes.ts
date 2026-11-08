// Contratos de `src/escalista/api/excecoes.py` e `store/exceptions.py` (fila de exceções e celular simulado).

import type { ExceptionCard, Role } from "./types.ts";

export interface Decision {
  option_index: number;
  label: string;
  by: string;
  role: Role;
  at: string;
  outcome: string;
}

export interface ExceptionItem {
  id: string;
  status: "open" | "decided";
  created_at: string;
  card: ExceptionCard;
  source: Record<string, unknown>;
  decision: Decision | null;
}

export interface ExceptionQueue {
  /** relógio da demo, para o "vence em" */
  now: string;
  open: ExceptionItem[];
  decided: ExceptionItem[];
}

export interface MyShift {
  day: string;
  start: string;
  end: string;
}

export type FaltaStatus = "pendente" | "coberta" | "descoberta" | "decidida";

export interface MyFalta {
  exception_id: string;
  day: string;
  start: string;
  end: string;
  status: FaltaStatus;
  covered_by: string | null;
  decision: string | null;
}

export interface MyWeek {
  published: boolean;
  week_start: string | null;
  employee: { id: string; name: string; job: string; store: string } | null;
  shifts: MyShift[];
  faltas: MyFalta[];
  synthetic: boolean;
}
