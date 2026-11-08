import { test } from "node:test";
import assert from "node:assert/strict";
import { CHAT_MAX_CHARS, chatCounter, chatInputError, chatSuggestions } from "./chat.ts";
import { inboundText } from "./tracker.ts";
import type { InboxMessage } from "./types-tracker.ts";

test("chatInputError recusa vazio e acima de 300 caracteres, aceita o resto", () => {
  assert.equal(chatInputError("   "), "Escreva uma mensagem.");
  assert.equal(chatInputError("a".repeat(CHAT_MAX_CHARS + 1)), "Até 300 caracteres.");
  assert.equal(chatInputError("a".repeat(CHAT_MAX_CHARS)), null);
  assert.equal(chatInputError("Amanhã não vou conseguir ir"), null);
});

test("chatCounter mostra o que já foi usado do limite", () => {
  assert.equal(chatCounter(""), "0/300");
  assert.equal(chatCounter("oi"), "2/300");
});

test("chatSuggestions prioriza a pergunta do ponto, depois a oferta, depois as padrão", () => {
  assert.deepEqual(chatSuggestions({ openQuestions: 1, openOffers: 1 }), ["Estou a caminho", "Hoje não vou"]);
  assert.deepEqual(chatSuggestions({ openQuestions: 0, openOffers: 1 }), ["Pode ser, aceito", "Não posso"]);
  assert.deepEqual(chatSuggestions({ openQuestions: 0, openOffers: 0 }), [
    "Amanhã não vou conseguir ir",
    "Vou me atrasar 40 min",
    "Qual é a minha escala?",
  ]);
});

test("a mensagem de chat da própria pessoa volta como balão com o texto já sem CID", () => {
  const m: InboxMessage = {
    id: "m1",
    direction: "in",
    template: "chat",
    body: "amanhã não vou, atestado",
    has_text: true,
    attachment_media_type: null,
    at: "2027-01-13T10:00:00",
  } as InboxMessage;
  assert.equal(inboundText(m, undefined), "amanhã não vou, atestado");
});
