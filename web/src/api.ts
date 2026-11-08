import type {
  ExceptionCard,
  Me,
  ProposedSchedule,
  PublishedSchedule,
  RunState,
  TraceEvent,
} from './types'

/** Erro HTTP da API, com o corpo já lido. `exception` vem preenchido quando o corpo traz um cartão (RX-13, RH-01). */
export class ApiError extends Error {
  status: number
  exception: ExceptionCard | null

  constructor(status: number, message: string, exception: ExceptionCard | null) {
    super(message)
    this.status = status
    this.exception = exception
  }
}

async function failure(res: Response): Promise<ApiError> {
  let detail = `Erro ${res.status}`
  let exception: ExceptionCard | null = null
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') detail = body.detail
    else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg ?? '').join('; ')
    if (body?.exception) exception = body.exception as ExceptionCard
  } catch {
    // corpo vazio ou não JSON: fica a mensagem padrão
  }
  return new ApiError(res.status, detail, exception)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: 'same-origin', ...init })
  if (!res.ok) throw await failure(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

const post = <T>(path: string) => request<T>(path, { method: 'POST' })

export const api = {
  loginGerente: () => post<Me>('/auth/demo/gerente'),
  me: () => request<Me>('/api/me'),
  logout: () => post<void>('/auth/logout'),
  startRun: (fileName: string, csv: Blob) =>
    request<RunState>(`/api/runs?file_name=${encodeURIComponent(fileName)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'text/csv' },
      body: csv,
    }),
  getRun: (id: string) => request<RunState>(`/api/runs/${id}`),
  confirm: (id: string) => post<RunState>(`/api/runs/${id}/confirm`),
  schedule: (id: string) => request<ProposedSchedule>(`/api/runs/${id}/schedule`),
  approve: (id: string) => post<RunState>(`/api/runs/${id}/approve`),
  trace: (id: string) => request<TraceEvent[]>(`/api/runs/${id}/trace`),
  published: () => request<PublishedSchedule>('/api/schedules/published'),
  demoFile: async (name: string): Promise<Blob> => {
    const res = await fetch(`/api/demo/files/${name}`, { credentials: 'same-origin' })
    if (!res.ok) throw await failure(res)
    return res.blob()
  },
}
