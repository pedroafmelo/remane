import { test } from "node:test";
import assert from "node:assert/strict";
import { PAT_ESTADOS, patPose, patLabel, patDoPasso } from "./pat.ts";

test("todo estado do Pat tem pose e rótulo em português", () => {
  for (const e of PAT_ESTADOS) {
    assert.ok(patPose(e).eyes, e);
    assert.ok(patLabel(e).length > 0, e);
  }
});

test("só o estado de exceção usa o contorno warning", () => {
  for (const e of PAT_ESTADOS) {
    assert.equal(patPose(e).ring, e === "excecao", e);
  }
});

test("só o estado digitando mostra os três pontinhos", () => {
  for (const e of PAT_ESTADOS) {
    assert.equal(patPose(e).dots, e === "digitando", e);
  }
});

test("movimento: só trabalhando desliza e só resolveu faz pop", () => {
  for (const e of PAT_ESTADOS) {
    assert.equal(patPose(e).motion === "slide", e === "trabalhando", e);
    assert.equal(patPose(e).motion === "pop", e === "resolveu", e);
  }
});

test("cada estado tem aparência própria (parado não é igual a trabalhando)", () => {
  const chaves = PAT_ESTADOS.map((e) => {
    const p = patPose(e);
    return `${p.eyes}|${p.dots}|${p.ring}|${p.ghost}`;
  });
  assert.equal(new Set(chaves).size, PAT_ESTADOS.length);
});

test("só trabalhando deixa o contorno tracejado do lugar vazio", () => {
  for (const e of PAT_ESTADOS) assert.equal(patPose(e).ghost, e === "trabalhando", e);
});

test("a história do hero passa por todos os estados da conversa, na ordem do caso", () => {
  const ordem = [0, 1, 2, 3, 4, 5].map(patDoPasso);
  assert.deepEqual(ordem, ["parado", "trabalhando", "digitando", "trabalhando", "resolveu", "resolveu"]);
});

test("passo fora da faixa não quebra", () => {
  assert.equal(patDoPasso(-3), "parado");
  assert.equal(patDoPasso(99), "resolveu");
});

test("trabalhando é o único com olhar concentrado", () => {
  for (const e of PAT_ESTADOS) assert.equal(patPose(e).eyes === "concentrado", e === "trabalhando", e);
});
