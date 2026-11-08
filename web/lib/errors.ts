// Tradução dos erros da API em mensagens para quem usa a tela. Pura: quem faz fetch é api.ts.

import type { ExceptionCard } from "./types.ts";

export const NETWORK_MESSAGE = "Não foi possível falar com o servidor. Confira a conexão e tente de novo.";

export type FailureKind = "network" | "auth" | "forbidden" | "missing" | "conflict" | "rejected" | "server" | "other";

export interface Failure {
  status: number;
  kind: FailureKind;
  message: string;
  exception: ExceptionCard | null;
}

/** Falha sem resposta HTTP (servidor fora do ar, rede caída). */
export function networkFailure(): Failure {
  return { status: 0, kind: "network", message: NETWORK_MESSAGE, exception: null };
}

export function kindOf(status: number): FailureKind {
  if (status === 401) return "auth";
  if (status === 403) return "forbidden";
  if (status === 404) return "missing";
  if (status === 409) return "conflict";
  if (status === 413 || status === 422) return "rejected";
  if (status >= 500) return "server";
  return "other";
}

/** Mensagem sobre o corpo de erro da API (`{detail}` texto ou lista de validação, e `{exception}` com o cartão). */
export function readFailureBody(status: number, body: unknown): Failure {
  const kind = kindOf(status);
  const record = (typeof body === "object" && body !== null ? body : {}) as Record<string, unknown>;
  let detail: string | null = null;
  if (typeof record.detail === "string" && record.detail !== "") detail = record.detail;
  else if (Array.isArray(record.detail)) {
    const parts = record.detail
      .map((d) => (typeof d === "object" && d !== null && typeof (d as { msg?: unknown }).msg === "string" ? (d as { msg: string }).msg : ""))
      .filter((m) => m !== "");
    if (parts.length > 0) detail = parts.join("; ");
  }
  const exception = record.exception && typeof record.exception === "object" ? (record.exception as ExceptionCard) : null;

  let message: string;
  if (kind === "auth") message = "Sua sessão expirou ou não existe. Entre de novo.";
  else if (kind === "server") message = "O servidor falhou ao processar o pedido. Tente de novo em instantes.";
  // 403 do guarda de papel tem texto técnico; o 403 de publicação recusada traz a razão e o cartão.
  else if (kind === "forbidden" && exception === null) message = "O seu papel não tem acesso a esta ação.";
  else message = detail ?? `Erro ${status}.`;
  return { status, kind, message, exception };
}

/** Mensagem do botão de entrada: 404 quer dizer que o login de demonstração está desligado no servidor. */
export function loginMessage(failure: Failure): string {
  if (failure.kind === "missing") return "A entrada de demonstração está desligada neste ambiente.";
  return failure.message;
}
