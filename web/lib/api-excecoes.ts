// Cliente das rotas de exceções (gestor) e do celular simulado (colaborador).

import { request } from "./api.ts";
import type { ExceptionItem, ExceptionQueue, MyWeek } from "./types-excecoes.ts";

const postJson = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const excecoesApi = {
  queue: () => request<ExceptionQueue>("/api/exceptions"),
  decide: (id: string, optionIndex: number) => postJson<ExceptionItem>(`/api/exceptions/${encodeURIComponent(id)}/decide`, { option_index: optionIndex }),
  myWeek: () => request<MyWeek>("/api/colaborador/escala"),
  reportFalta: (day: string) => postJson<MyWeek>("/api/colaborador/falta", { day }),
};
