// Contratos das rotas do acompanhamento (relógio de demo e celular simulado, camada C7).
// Datas ISO sem fuso, no horário de Brasília. Os valores decimais chegam como texto.

export interface DemoClock {
  now: string;
  base: string;
  simulated: true;
}

export type AdvanceMinutes = 15 | 1440 | 10080;

export interface Trigger {
  /** `no_punch`, `no_answer`, `offer_expired`, `overtime_needed`, ...; um tipo novo aparece com o próprio nome */
  kind: string;
  employee_id: string;
  ref: string;
}

export interface AdvanceResult {
  now: string;
  triggers: Trigger[];
  events: number;
}

export interface Person {
  id: string;
  name: string;
  job: string;
  store: string;
}

export interface PeopleList {
  people: Person[];
  default_id: string;
}

export interface InboxMessage {
  id: string;
  direction: "in" | "out";
  template: string;
  /** mensagens `out` e o chat da própria pessoa (já sem CID); o texto do aviso por formulário nunca vai ao servidor */
  body: string | null;
  /** o colaborador escreveu algo (o texto em si não sai do celular) */
  has_text: boolean;
  /** tipo do anexo enviado nesta mensagem de entrada (`application/pdf`), ou `null` */
  attachment_media_type: string | null;
  at: string;
  case_id: string | null;
}

export type OfferStatus = "enviada" | "aceita" | "recusada" | "vencida";

export interface InboxOffer {
  offer_id: string;
  case_id: string;
  start: string;
  end: string;
  store: string;
  status: OfferStatus;
  deadline: string;
  /** horas extras da oferta, em texto decimal ("0" = sem hora extra) */
  overtime_hours: string;
  added_cost: string;
}

export interface InboxQuestion {
  case_id: string;
  start: string;
  end: string;
}

export type CaseStatus =
  | "aguardando_colaborador"
  | "oferta_enviada"
  | "aguardando_gestor"
  | "coberto"
  | "descoberto"
  | "atraso_registrado"
  | "decidido";

export type ReadingVerdict = "valido" | "inconsistente" | "ilegivel";

export interface AtestadoReading {
  legible: boolean;
  issued_on: string | null;
  start_on: string | null;
  days: number | null;
  patient_matches: boolean | null;
  has_crm: boolean | null;
  verdict: ReadingVerdict;
  reasons: string[];
}

export interface CaseOffer {
  offer_id: string;
  candidate_id: string;
  rank: number;
  status: string;
  deadline: string;
}

export interface CaseView {
  case_id: string;
  status: CaseStatus;
  kind: "falta" | "atraso";
  employee_id: string;
  day: string;
  abono: "provisorio" | "nenhum";
  reading: AtestadoReading | null;
  offers: CaseOffer[];
  exception_ids: string[];
}

export interface Inbox {
  /** relógio de demo no instante da leitura da caixa */
  now: string;
  employee: Person;
  week_start: string;
  shifts: { day: string; start: string; end: string }[];
  messages: InboxMessage[];
  offers: InboxOffer[];
  questions: InboxQuestion[];
  cases: CaseView[];
  synthetic: boolean;
}

export interface ReportInput {
  as: string;
  day: string;
  kind: "falta" | "atraso";
  /** fica no celular: só vira `has_text` no corpo do aviso */
  text?: string;
  file?: File | null;
}

/** Resposta do `POST /api/colaborador/mensagem` (C7b): texto de modelo do servidor e sugestões fixas. */
export interface ChatReply {
  template: string;
  body: string;
  case_id: string | null;
  suggestions: string[];
}

/** Resposta do `POST /api/assistente/mensagem` (C7b N2): somente leitura, texto de modelo do servidor. */
export interface AssistantReply {
  template: string;
  body: string;
  tool: string | null;
  suggestions: string[];
  synthetic: true;
}

/** Corpo do `POST /api/colaborador/aviso`. */
export interface ReportBody {
  as: string;
  day: string;
  kind: "falta" | "atraso";
  has_text: boolean;
}
