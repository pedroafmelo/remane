// Textos e escolhas puras do acompanhamento (relógio de demo e celular simulado). Só apresentam o que o backend decidiu.

import { dayLabel } from "./excecoes.ts";
import { hhmm, hourLabel, shiftLabel } from "./format.ts";
import type { CaseStatus, CaseView, InboxMessage, InboxOffer, InboxQuestion, PeopleList, Person, Trigger } from "./types-tracker.ts";

/** Evento de janela que a barra do relógio dispara depois de avançar ou reiniciar; as telas escutam para recarregar. */
export const CLOCK_EVENT = "remane:clock";

export interface ClockChange {
  action: "advance" | "reset";
  now: string;
}

export const PERSON_STORAGE_KEY = "remane:colaborador";

/** "2027-01-13T13:55:00" -> "qua 13/01/2027 · 13:55". */
export function clockText(now: string): string {
  return `${dayLabel(now)}/${now.slice(0, 4)} · ${hhmm(now)}`;
}

const TRIGGER_LABELS: Record<string, string> = {
  no_punch: "sem batida de ponto",
  no_answer: "sem resposta do colaborador",
  offer_expired: "oferta vencida sem resposta",
  overtime_needed: "hora extra necessária",
  overtime_near_limit: "hora extra perto do limite",
  overtime_limit: "limite de hora extra",
  weekly_check: "conferência semanal",
};

export function triggerLabel(kind: string): string {
  return TRIGGER_LABELS[kind] ?? kind;
}

/** Resumo curto depois de avançar o relógio: "1 gatilho: sem batida de ponto", "2 gatilhos: ...", ou nenhum. */
export function triggerSummary(triggers: Trigger[]): string {
  if (triggers.length === 0) return "Nenhum gatilho neste avanço.";
  const counts = new Map<string, number>();
  for (const t of triggers) counts.set(t.kind, (counts.get(t.kind) ?? 0) + 1);
  const parts = [...counts].map(([kind, n]) => (n > 1 ? `${triggerLabel(kind)} (${n}×)` : triggerLabel(kind)));
  return `${triggers.length} ${triggers.length === 1 ? "gatilho" : "gatilhos"}: ${parts.join(", ")}`;
}

/** Pessoa do seletor: a guardada, se ainda existe no quadro; senão a padrão do servidor; senão a primeira. */
export function pickPerson(list: PeopleList, stored: string | null): string | null {
  const ids = new Set(list.people.map((p) => p.id));
  if (stored && ids.has(stored)) return stored;
  if (ids.has(list.default_id)) return list.default_id;
  return list.people[0]?.id ?? null;
}

export function personOptionLabel(p: Person): string {
  return `${p.name} (${p.job}, ${p.store})`;
}

/** "qui 14/01 · 14–22h". */
export function turnLabel(start: string, end: string): string {
  return `${dayLabel(start)} · ${shiftLabel(start, end)}`;
}

/** Texto decimal de horas extras: "0" e "0.00" são "sem hora extra"; "1.5" é "1,5h extra". */
export function overtimeLabel(value: string): string {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "sem hora extra";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(n)}h extra`;
}

/** Prazo da oferta: "até 14:20" no mesmo dia do relógio de demo; "até qui 14/01 14:20" em outro dia. */
export function deadlineLabel(deadline: string, now: string | null): string {
  if (now && deadline.slice(0, 10) === now.slice(0, 10)) return `até ${hhmm(deadline)}`;
  return `até ${dayLabel(deadline)} ${hhmm(deadline)}`;
}

/** Oferta que ainda espera resposta do colaborador. */
export function isOpenOffer(o: InboxOffer): boolean {
  return o.status === "enviada";
}

/** "Você não bateu o ponto às 14h. Você vem hoje?" (o turno em pergunta começa às 14h). */
export function questionText(q: InboxQuestion): string {
  return `Você não bateu o ponto às ${hourLabel(q.start)}. Você vem hoje?`;
}

/** Linha da oferta: "Cobrir qui 14/01 · 14–22h na Loja Centro · sem hora extra". */
export function offerText(o: InboxOffer): string {
  return `Cobrir ${turnLabel(o.start, o.end)} na ${o.store} · ${overtimeLabel(o.overtime_hours)}`;
}

/** O que o Pat diz sobre a comprovação anexada; `null` quando não há anexo a comentar. */
export function attestationLabel(c: CaseView): string | null {
  const r = c.reading;
  if (r) {
    if (r.verdict === "valido") {
      const days = r.days ?? 0;
      const dias = days === 1 ? "1 dia" : `${days} dias`;
      return `atestado lido: válido, ${dias}; abono provisório até o gestor confirmar`;
    }
    return "atestado com pendência; o gestor vai conferir";
  }
  if (c.abono === "provisorio") return "anexo recebido; leitura indisponível; abono provisório";
  return null;
}

const STATUS_LABELS: Record<CaseStatus, string> = {
  aguardando_colaborador: "aguardando a sua resposta",
  oferta_enviada: "procurando quem cubra: oferta enviada a um colega",
  aguardando_gestor: "aguardando a decisão do gestor",
  coberto: "turno coberto",
  descoberto: "turno ficou descoberto; o gestor foi avisado",
  atraso_registrado: "atraso registrado",
  decidido: "decidido pelo gestor",
};

export function caseStatusLabel(status: CaseStatus): string {
  return STATUS_LABELS[status] ?? status;
}

/** Estado do caso para o celular: a situação e, quando houver anexo, o que o Pat leu. */
export function caseStateLines(c: CaseView): string[] {
  const lines = [`${c.kind === "falta" ? "Falta" : "Atraso"} em ${dayLabel(c.day)}: ${caseStatusLabel(c.status)}`];
  const doc = attestationLabel(c);
  if (doc) lines.push(doc);
  return lines;
}

/** Caso ainda sem desfecho: a sondagem de 3 s continua enquanto houver um. */
export function isOpenCase(c: CaseView): boolean {
  return c.status === "aguardando_colaborador" || c.status === "oferta_enviada" || c.status === "aguardando_gestor";
}

const REPLIES: Record<string, string> = {
  oferta_aceita: "Aceito cobrir o turno.",
  oferta_recusada: "Não posso cobrir.",
  resposta_vou: "Estou a caminho.",
  resposta_nao_vou: "Não vou.",
};

/** Anexos enviados por caso (mensagens `in` com `attachment_media_type`). */
export function attachmentsByCase(messages: InboxMessage[]): Map<string, string> {
  const found = new Map<string, string>();
  for (const m of messages) {
    if (m.direction === "in" && m.case_id && m.attachment_media_type) found.set(m.case_id, m.attachment_media_type);
  }
  return found;
}

/** Tipos aceitos no anexo da comprovação (o servidor confere pelos bytes): PDF ou foto. */
export const ATTACHMENT_ACCEPT = "application/pdf,image/png,image/jpeg";
export type AttachmentType = "application/pdf" | "image/png" | "image/jpeg";

/** Tipo do anexo pelo `type` do arquivo e, na falta dele, pela extensão; `null` quando não é PDF, PNG nem JPEG. */
export function attachmentType(file: { type: string; name: string }): AttachmentType | null {
  const declared = file.type.toLowerCase();
  if (declared === "application/pdf" || declared === "image/png" || declared === "image/jpeg") return declared;
  if (declared === "image/jpg") return "image/jpeg";
  const name = file.name.toLowerCase();
  if (name.endsWith(".pdf")) return "application/pdf";
  if (name.endsWith(".png")) return "image/png";
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
  return null;
}

/** Rótulo curto do anexo no balão do aviso: " (anexo PDF)", " (foto)" ou " (anexo)"; vazio sem anexo. */
export function attachmentSuffix(mediaType?: string | null): string {
  if (!mediaType) return "";
  if (mediaType === "application/pdf") return " (anexo PDF)";
  if (mediaType === "image/png" || mediaType === "image/jpeg") return " (foto)";
  return " (anexo)";
}

/** A mensagem do anexo não vira balão próprio: ela aparece no "Você avisou … (anexo PDF)". */
export function isAttachmentOnly(m: InboxMessage): boolean {
  return m.direction === "in" && m.template === "anexo";
}

/** Balão do colaborador a partir de uma mensagem `in`: o texto livre nunca volta, então só se descreve o ato.
 * `attachment`: o tipo do anexo enviado no mesmo caso, se houver. */
export function inboundText(m: InboxMessage, c: CaseView | undefined, attachment?: string | null): string {
  const suffix = attachmentSuffix(attachment);
  if (m.template.startsWith("aviso") && c) {
    return `Você avisou: ${c.kind === "falta" ? "vou faltar" : "vou me atrasar"} ${dayLabel(c.day)}.${suffix}`;
  }
  return REPLIES[m.template] ?? m.body ?? "Você respondeu.";
}

/** Balão do Pat a partir de uma mensagem `out`. */
export function outboundText(m: InboxMessage): string {
  return m.body ?? "Mensagem do Pat.";
}

/** Dias em que dá para avisar: um por turno da semana, com o rótulo do turno. */
export function reportDays(shifts: { day: string; start: string; end: string }[]): { day: string; label: string }[] {
  return shifts.map((s) => ({ day: s.day, label: turnLabel(s.start, s.end) }));
}
