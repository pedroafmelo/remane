// Cliente das rotas do relógio de demo e do celular simulado do acompanhamento (C7).

import { request } from "./api.ts";
import type { AdvanceMinutes, AdvanceResult, CaseView, DemoClock, Inbox, PeopleList, ReportBody, ReportInput } from "./types-tracker.ts";

const postJson = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

/** Corpo JSON do aviso. O texto livre fica no celular: o servidor só fica sabendo que houve texto (RN-06). */
export function reportBody(input: ReportInput): ReportBody {
  return { as: input.as, day: input.day, kind: input.kind, has_text: Boolean(input.text?.trim()) };
}

/** Aviso e, se houver, o PDF em seguida, no corpo bruto (como `startRun`). Devolve o caso no estado mais recente. */
async function report(input: ReportInput): Promise<CaseView> {
  const view = await postJson<CaseView>("/api/colaborador/aviso", reportBody(input));
  if (!input.file) return view;
  const params = new URLSearchParams({ as: input.as, file_name: input.file.name });
  return request<CaseView>(`/api/colaborador/caso/${encodeURIComponent(view.case_id)}/anexo?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/pdf" },
    body: input.file,
  });
}

export const trackerApi = {
  clock: () => request<DemoClock>("/api/demo/clock"),
  advance: (minutes: AdvanceMinutes) => postJson<AdvanceResult>("/api/demo/clock/advance", { minutes }),
  reset: () => request<{ now: string }>("/api/demo/reset", { method: "POST" }),
  people: () => request<PeopleList>("/api/colaborador/pessoas"),
  inbox: (as: string) => request<Inbox>(`/api/colaborador/caixa?as=${encodeURIComponent(as)}`),
  report,
  answerOffer: (offerId: string, as: string, accept: boolean) =>
    postJson<CaseView>(`/api/colaborador/oferta/${encodeURIComponent(offerId)}`, { as, accept }),
  answerQuestion: (as: string, caseId: string, coming: boolean) =>
    postJson<CaseView>("/api/colaborador/resposta", { as, case_id: caseId, coming }),
};
