import { test } from "node:test";
import assert from "node:assert/strict";
import { costUsd, dateBr, hours, latency, money, pct, phaseLabel, ruleStatusLabel, shiftLabel, spanHours, timeBr, weekDays } from "./format.ts";
import { loginMessage, networkFailure, readFailureBody } from "./errors.ts";
import { toExceptionView } from "./exception.ts";
import { buildGrid } from "./grid.ts";
import { canOperateSchedule, roleLabel } from "./roles.ts";
import type { EmployeePublic, ExceptionCard, Schedule } from "./types.ts";

const plain = (s: string) => s.replace(/ /g, " ");

test("money, hours e pct seguem o pt-BR", () => {
  assert.equal(plain(money("1234.5")), "R$ 1.234,50");
  assert.equal(plain(hours("42")), "42 h");
  assert.equal(plain(hours("7.333")), "7,33 h");
  assert.equal(pct(96.5), "96,5%");
});

test("costUsd distingue zero de nulo", () => {
  assert.equal(plain(costUsd("0")), "US$ 0");
  assert.equal(costUsd(null), "—");
  assert.equal(plain(costUsd("0.000123")), "US$ 0,000123");
});

test("latency usa ms abaixo de 1 s e s acima", () => {
  assert.equal(latency(null), "—");
  assert.equal(latency(850), "850 ms");
  assert.equal(plain(latency(1500)), "1,5 s");
});

test("datas não deslocam o dia por fuso", () => {
  assert.equal(dateBr("2027-01-11"), "11/01/2027");
  assert.equal(timeBr("2027-01-11T08:05:09"), "11/01/2027 08:05:09");
});

test("weekDays começa na segunda e cruza o fim do mês", () => {
  const days = weekDays("2027-01-27");
  assert.equal(days[0].label, "Seg 27/01");
  assert.equal(days[6].iso, "2027-02-02");
});

test("shiftLabel segue o padrão do design system", () => {
  assert.equal(shiftLabel("2027-01-11T14:00:00", "2027-01-11T22:00:00"), "14–22h");
  assert.equal(shiftLabel("2027-01-11T12:40:00", "2027-01-11T20:00:00"), "12:40–20h");
  assert.equal(shiftLabel("2027-01-11T22:00:00", "2027-01-12T06:00:00"), "22–6h +1");
});

test("spanHours soma o intervalo sem depender do fuso", () => {
  assert.equal(spanHours("2027-01-11T12:40:00", "2027-01-11T20:00:00"), 7 + 1 / 3);
  assert.equal(spanHours("2027-01-11T22:00:00", "2027-01-12T06:00:00"), 8);
});

test("rótulos de status, fase e papel", () => {
  assert.equal(ruleStatusLabel("ficticia"), "fictícia (demo)");
  assert.equal(ruleStatusLabel("outro"), "outro");
  assert.equal(phaseLabel("published"), "Publicada");
  assert.equal(phaseLabel("nova"), "nova");
  assert.equal(roleLabel("gestor"), "Gestor");
  assert.equal(canOperateSchedule("gestor"), true);
  assert.equal(canOperateSchedule("colaborador"), false);
});

test("erro 401 pede nova entrada e 403 do guarda de papel vira mensagem clara", () => {
  const auth = readFailureBody(401, { detail: "sessão ausente ou inválida" });
  assert.equal(auth.kind, "auth");
  assert.match(auth.message, /Entre de novo/);
  const forbidden = readFailureBody(403, { detail: "papel sem acesso a esta rota" });
  assert.equal(forbidden.kind, "forbidden");
  assert.match(forbidden.message, /papel não tem acesso/);
});

test("403 de publicação recusada mantém a razão e o cartão", () => {
  const card = { code: "RH-01", title: "t" } as ExceptionCard;
  const refused = readFailureBody(403, { detail: "sem aprovação registrada", exception: card });
  assert.equal(refused.message, "sem aprovação registrada");
  assert.equal(refused.exception, card);
});

test("413 e 422 trazem o motivo e o cartão RX-13; validação do FastAPI junta as mensagens", () => {
  const card = { code: "RX-13" } as ExceptionCard;
  const big = readFailureBody(413, { detail: "O arquivo passa de 1 MB.", exception: card });
  assert.equal(big.kind, "rejected");
  assert.equal(big.exception, card);
  const validation = readFailureBody(422, { detail: [{ msg: "campo obrigatório" }, { msg: "tamanho mínimo 1" }] });
  assert.equal(validation.message, "campo obrigatório; tamanho mínimo 1");
});

test("corpo ilegível cai na mensagem do status; 5xx esconde detalhe técnico", () => {
  assert.equal(readFailureBody(409, null).message, "Erro 409.");
  assert.match(readFailureBody(500, { detail: "Traceback..." }).message, /servidor falhou/);
});

test("mensagem de entrada: 404 é demo desligada e rede caída é dita", () => {
  assert.match(loginMessage(readFailureBody(404, null)), /desligada/);
  assert.match(loginMessage(networkFailure()), /falar com o servidor/);
});

test("cartão de exceção vira o formato do componente", () => {
  const card: ExceptionCard = {
    code: "RX-12",
    title: "Sem solução dentro das regras",
    reason: "Não há combinação válida.",
    decider: "gestor",
    deadline: "2027-01-11T10:00:00",
    evidence: ["loja L1"],
    options: [
      { label: "Cobrir com hora extra", cost_usd: null, effect: "+2 h extras" },
      { label: "Deixar descoberto", cost_usd: null, effect: null },
    ],
    recommendation: "Cobrir",
    if_no_answer: null,
    trace_id: null,
  };
  const view = toExceptionView(card);
  assert.equal(view.chip, "RX-12 · precisa de você");
  assert.equal(view.time, "prazo 11/01/2027 10:00:00");
  assert.equal(view.decider, "Gestor");
  assert.deepEqual(view.options, [
    { label: "Cobrir com hora extra", value: "+2 h extras" },
    { label: "Deixar descoberto", value: null },
  ]);
});

test("buildGrid separa por loja, marca folgas e não carrega sexo", () => {
  const schedule: Schedule = {
    week_start: "2027-01-11",
    shifts: [
      { employee_id: "P1", store_id: "L1", start: "2027-01-11T08:00:00", end: "2027-01-11T16:00:00" },
      { employee_id: "P1", store_id: "L1", start: "2027-01-12T12:40:00", end: "2027-01-12T20:00:00" },
      { employee_id: "P9", store_id: "L2", start: "2027-01-11T09:00:00", end: "2027-01-11T17:00:00" },
    ],
  };
  const employees: EmployeePublic[] = [
    { id: "P1", name: "Ana", store_id: "L1", job: "Caixa", hourly_wage: "12", contract_hours: 44, profile: "padrao" },
  ];
  const grid = buildGrid(schedule, employees);
  assert.deepEqual(grid.stores.map((s) => s.storeId), ["L1", "L2"]);
  const ana = grid.stores[0].rows[0];
  assert.equal(ana.cells[0].label, "8–16h");
  assert.equal(ana.cells[1].label, "12:40–20h");
  assert.equal(ana.cells[2].kind, "off");
  assert.equal(plain(ana.sub), "Caixa · 15,3 h");
  assert.equal(grid.stores[1].rows[0].name, "P9");
  assert.ok(!JSON.stringify(grid).includes("sex"));
});
