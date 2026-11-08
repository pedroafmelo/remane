// Cliente da API FastAPI do mesmo host (rotas reais: `/auth/*` fora do prefixo `/api`; o resto em `/api/*`).

import { networkFailure, readFailureBody, type Failure } from "./errors.ts";
import type { Me, ProposedSchedule, PublishedSchedule, Role, RunState, TraceEvent } from "./types.ts";

/** Erro HTTP da API, já traduzido. `exception` vem preenchido quando o corpo traz um cartão (RX-13, recusa de publicação). */
export class ApiError extends Error {
  failure: Failure;

  constructor(failure: Failure) {
    super(failure.message);
    this.failure = failure;
  }
}

/** Qualquer erro lançado pelo cliente como `Failure`; o que não for `ApiError` é falha de rede. */
export function asFailure(err: unknown): Failure {
  return err instanceof ApiError ? err.failure : networkFailure();
}

async function failureOf(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // corpo vazio ou não JSON: vale a mensagem padrão do status
  }
  return new ApiError(readFailureBody(res.status, body));
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(path, { credentials: "same-origin", ...init });
  } catch {
    throw new ApiError(networkFailure());
  }
  if (!res.ok) throw await failureOf(res);
  return res;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const post = <T>(path: string) => request<T>(path, { method: "POST" });

export const api = {
  loginDemo: (role: Role) => post<Me>(`/auth/demo/${role}`),
  me: () => request<Me>("/api/me"),
  logout: () => post<void>("/auth/logout"),
  startRun: (fileName: string, csv: Blob) =>
    request<RunState>(`/api/runs?file_name=${encodeURIComponent(fileName)}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: csv,
    }),
  confirm: (id: string) => post<RunState>(`/api/runs/${id}/confirm`),
  schedule: (id: string) => request<ProposedSchedule>(`/api/runs/${id}/schedule`),
  approve: (id: string) => post<RunState>(`/api/runs/${id}/approve`),
  trace: (id: string) => request<TraceEvent[]>(`/api/runs/${id}/trace`),
  published: () => request<PublishedSchedule>("/api/schedules/published"),
  demoFile: async (name: string): Promise<Blob> => (await send(`/api/demo/files/${name}`)).blob(),
};
