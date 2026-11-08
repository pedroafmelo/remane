import { test } from "node:test";
import assert from "node:assert/strict";
import {
  attestationLabel,
  caseStateLines,
  clockText,
  deadlineLabel,
  inboundText,
  isOpenCase,
  offerText,
  overtimeLabel,
  pickPerson,
  questionText,
  triggerSummary,
  turnLabel,
} from "./tracker.ts";
import { reportForm } from "./api-tracker.ts";
import type { CaseView, InboxMessage, InboxOffer } from "./types-tracker.ts";

const base: CaseView = {
  case_id: "c1",
  status: "aguardando_gestor",
  kind: "falta",
  employee_id: "e1",
  day: "2027-01-14",
  abono: "nenhum",
  reading: null,
  offers: [],
  exception_ids: [],
};

const reading = { legible: true, issued_on: "2027-01-13", start_on: "2027-01-14", days: 2, patient_matches: true, has_crm: true, verdict: "valido" as const, reasons: [] };

test("clockText mostra dia, data e hora do tempo simulado", () => {
  assert.equal(clockText("2027-01-13T13:55:00"), "qua 13/01/2027 · 13:55");
});

test("triggerSummary resume os gatilhos do avanço", () => {
  assert.equal(triggerSummary([]), "Nenhum gatilho neste avanço.");
  assert.equal(triggerSummary([{ kind: "no_punch", employee_id: "e1", ref: "r" }]), "1 gatilho: sem batida de ponto");
  assert.equal(
    triggerSummary([
      { kind: "no_punch", employee_id: "e1", ref: "a" },
      { kind: "no_punch", employee_id: "e2", ref: "b" },
      { kind: "no_answer", employee_id: "e3", ref: "c" },
    ]),
    "3 gatilhos: sem batida de ponto (2×), sem resposta do colaborador",
  );
  assert.equal(triggerSummary([{ kind: "novo_tipo", employee_id: "e1", ref: "r" }]), "1 gatilho: novo_tipo");
});

test("pickPerson prefere a guardada, depois a padrão, depois a primeira", () => {
  const list = {
    people: [
      { id: "a", name: "Ana", job: "caixa", store: "Loja 1" },
      { id: "b", name: "Bia", job: "caixa", store: "Loja 1" },
    ],
    default_id: "b",
  };
  assert.equal(pickPerson(list, "a"), "a");
  assert.equal(pickPerson(list, "zzz"), "b");
  assert.equal(pickPerson(list, null), "b");
  assert.equal(pickPerson({ ...list, default_id: "x" }, null), "a");
  assert.equal(pickPerson({ people: [], default_id: "x" }, "a"), null);
});

test("turnLabel e overtimeLabel seguem o padrão do design system", () => {
  assert.equal(turnLabel("2027-01-14T14:00:00", "2027-01-14T22:00:00"), "qui 14/01 · 14–22h");
  assert.equal(overtimeLabel("0"), "sem hora extra");
  assert.equal(overtimeLabel("0.00"), "sem hora extra");
  assert.equal(overtimeLabel("1.5"), "1,5h extra");
  assert.equal(overtimeLabel("2"), "2h extra");
});

test("deadlineLabel omite o dia quando é o do relógio", () => {
  assert.equal(deadlineLabel("2027-01-13T14:20:00", "2027-01-13T14:00:00"), "até 14:20");
  assert.equal(deadlineLabel("2027-01-14T09:00:00", "2027-01-13T14:00:00"), "até qui 14/01 09:00");
  assert.equal(deadlineLabel("2027-01-14T09:00:00", null), "até qui 14/01 09:00");
});

test("a oferta e a pergunta do agente dizem o turno e a hora", () => {
  const offer: InboxOffer = {
    offer_id: "o1",
    case_id: "c1",
    start: "2027-01-14T14:00:00",
    end: "2027-01-14T22:00:00",
    store: "Loja Centro",
    status: "enviada",
    deadline: "2027-01-13T14:20:00",
    overtime_hours: "0",
    added_cost: "0",
  };
  assert.equal(offerText(offer), "Cobrir qui 14/01 · 14–22h na Loja Centro · sem hora extra");
  assert.equal(questionText({ case_id: "c2", start: "2027-01-13T14:00:00", end: "2027-01-13T22:00:00" }), "Você não bateu o ponto às 14h. Você vem hoje?");
  assert.equal(questionText({ case_id: "c2", start: "2027-01-13T14:30:00", end: "2027-01-13T22:00:00" }), "Você não bateu o ponto às 14:30. Você vem hoje?");
});

test("attestationLabel depende da leitura e do abono", () => {
  assert.equal(attestationLabel({ ...base, abono: "provisorio", reading }), "atestado lido: válido, 2 dias; abono provisório até o gestor confirmar");
  assert.equal(attestationLabel({ ...base, abono: "provisorio", reading: { ...reading, days: 1 } }), "atestado lido: válido, 1 dia; abono provisório até o gestor confirmar");
  assert.equal(attestationLabel({ ...base, reading: { ...reading, verdict: "inconsistente" } }), "atestado com pendência; o gestor vai conferir");
  assert.equal(attestationLabel({ ...base, reading: { ...reading, legible: false, verdict: "ilegivel" } }), "atestado com pendência; o gestor vai conferir");
  assert.equal(attestationLabel({ ...base, abono: "provisorio" }), "anexo recebido; leitura indisponível; abono provisório");
  assert.equal(attestationLabel(base), null);
});

test("caseStateLines junta a situação e a leitura do anexo", () => {
  assert.deepEqual(caseStateLines({ ...base, status: "coberto" }), ["Falta em qui 14/01: turno coberto"]);
  assert.deepEqual(caseStateLines({ ...base, kind: "atraso", status: "atraso_registrado", abono: "provisorio" }), [
    "Atraso em qui 14/01: atraso registrado",
    "anexo recebido; leitura indisponível; abono provisório",
  ]);
});

test("isOpenCase mantém a sondagem enquanto não há desfecho", () => {
  assert.equal(isOpenCase(base), true);
  assert.equal(isOpenCase({ ...base, status: "coberto" }), false);
  assert.equal(isOpenCase({ ...base, status: "decidido" }), false);
});

test("inboundText descreve o aviso sem repetir o texto livre", () => {
  const msg: InboxMessage = { id: "m1", direction: "in", template: "aviso_falta", body: null, at: "2027-01-13T13:56:00", case_id: "c1" };
  assert.equal(inboundText(msg, base), "Você avisou: vou faltar qui 14/01.");
  assert.equal(inboundText(msg, { ...base, abono: "provisorio" }), "Você avisou: vou faltar qui 14/01. (anexo PDF)");
  assert.equal(inboundText(msg, { ...base, kind: "atraso" }), "Você avisou: vou me atrasar qui 14/01.");
  assert.equal(inboundText({ ...msg, template: "resposta" }, base), "Você respondeu.");
});

test("reportForm só envia texto e arquivo quando existem", () => {
  const bare = reportForm({ as: "e1", day: "2027-01-14", kind: "falta", text: "  " });
  assert.equal(bare.get("as"), "e1");
  assert.equal(bare.get("kind"), "falta");
  assert.equal(bare.has("text"), false);
  assert.equal(bare.has("file"), false);
  const file = new File(["%PDF"], "at.pdf", { type: "application/pdf" });
  const full = reportForm({ as: "e1", day: "2027-01-14", kind: "atraso", text: " cheguei tarde ", file });
  assert.equal(full.get("text"), "cheguei tarde");
  assert.equal((full.get("file") as File).name, "at.pdf");
});

test("o cartão de um código novo do acompanhamento vira o formato do componente sem supor falta", async () => {
  const { toExceptionView } = await import("./exception.ts");
  for (const code of ["COBERTURA", "RX-05", "RX-06", "RX-08", "RX-09"]) {
    const view = toExceptionView({
      code,
      title: "Cobertura: Bia aceitou",
      reason: "Bia aceitou cobrir o turno.",
      decider: "gestor",
      deadline: null,
      evidence: ["3 candidatos avaliados"],
      options: [{ label: "Validar a cobertura", effect: null, cost_usd: null }],
      recommendation: null,
      if_no_answer: null,
      trace_id: null,
    });
    assert.equal(view.chip, `${code} · precisa de você`);
    assert.equal(view.time, null);
    assert.deepEqual(view.options, [{ label: "Validar a cobertura", value: null }]);
  }
});
