import { test } from "node:test";
import assert from "node:assert/strict";
import { dayLabel, dueLabel, faltaDays, faltaReply, receiptText, trackRunId } from "./excecoes.ts";
import type { MyFalta, MyWeek } from "./types-excecoes.ts";

const falta: MyFalta = {
  exception_id: "exc-1",
  day: "2027-01-13",
  start: "2027-01-13T14:00:00",
  end: "2027-01-13T22:00:00",
  status: "pendente",
  covered_by: null,
  decision: null,
};

test("trackRunId só devolve o rastro de cartões do acompanhamento", () => {
  assert.equal(trackRunId({ source: { kind: "track", case_id: "c1", run_id: "track-c1" } }), "track-c1");
  assert.equal(trackRunId({ source: { kind: "track", case_id: null, run_id: "track-sweep" } }), "track-sweep");
  assert.equal(trackRunId({ source: { kind: "regras" } }), null);
  assert.equal(trackRunId({ source: { kind: "falta", run_id: "run-1" } }), null);
});

test("dayLabel usa o dia da semana em português", () => {
  assert.equal(dayLabel("2027-01-13"), "qua 13/01");
  assert.equal(dayLabel("2027-01-17"), "dom 17/01");
});

test("dueLabel é relativo ao relógio da demo", () => {
  const now = "2027-01-13T10:00:00";
  assert.equal(dueLabel(null, now), null);
  assert.equal(dueLabel("2027-01-13T10:25:00", now), "vence em 25 min");
  assert.equal(dueLabel("2027-01-13T13:30:00", now), "vence em 3 h");
  assert.equal(dueLabel("2027-01-15T10:00:00", now), "vence em 2 dias");
  assert.equal(dueLabel("2027-01-13T09:00:00", now), "venceu");
});

test("o Pat confirma o recebimento e não promete a cobertura", () => {
  assert.equal(receiptText(falta), "Recebi. Já estou procurando quem cubra seu turno de qua 13/01, 14–22h. Sua gestora vai decidir.");
  assert.match(faltaReply(falta), /gestora/);
  assert.match(faltaReply({ ...falta, status: "coberta", covered_by: "Paulo" }), /Paulo cobre/);
  assert.match(faltaReply({ ...falta, status: "descoberta" }), /descoberto/);
});

test("faltaDays tira os dias com falta já avisada", () => {
  const week: MyWeek = {
    published: true,
    week_start: "2027-01-11",
    employee: null,
    shifts: [
      { day: "2027-01-11", start: "2027-01-11T08:00:00", end: "2027-01-11T16:00:00" },
      { day: "2027-01-13", start: "2027-01-13T14:00:00", end: "2027-01-13T22:00:00" },
    ],
    faltas: [falta],
    synthetic: true,
  };
  assert.deepEqual(faltaDays(week), [{ day: "2027-01-11", label: "seg 11/01 · 8–16h" }]);
});
