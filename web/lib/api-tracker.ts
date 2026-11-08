// Cliente das rotas do relógio de demo e do celular simulado do acompanhamento (C7).

import { request } from "./api.ts";
import type { AdvanceMinutes, AdvanceResult, CaseView, DemoClock, Inbox, PeopleList, ReportInput } from "./types-tracker.ts";

const postJson = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

/** Corpo multipart do aviso: o texto e o arquivo só entram quando existem. O navegador define o `Content-Type`. */
export function reportForm(input: ReportInput): FormData {
  const form = new FormData();
  form.set("as", input.as);
  form.set("day", input.day);
  form.set("kind", input.kind);
  const text = input.text?.trim();
  if (text) form.set("text", text);
  if (input.file) form.set("file", input.file);
  return form;
}

export const trackerApi = {
  clock: () => request<DemoClock>("/api/demo/clock"),
  advance: (minutes: AdvanceMinutes) => postJson<AdvanceResult>("/api/demo/clock/advance", { minutes }),
  reset: () => request<{ now: string }>("/api/demo/reset", { method: "POST" }),
  people: () => request<PeopleList>("/api/colaborador/pessoas"),
  inbox: (as: string) => request<Inbox>(`/api/colaborador/caixa?as=${encodeURIComponent(as)}`),
  report: (input: ReportInput) => request<CaseView>("/api/colaborador/aviso", { method: "POST", body: reportForm(input) }),
  answerOffer: (offerId: string, as: string, accept: boolean) =>
    postJson<CaseView>(`/api/colaborador/oferta/${encodeURIComponent(offerId)}`, { as, accept }),
  answerQuestion: (as: string, caseId: string, coming: boolean) =>
    postJson<CaseView>("/api/colaborador/resposta", { as, case_id: caseId, coming }),
};
