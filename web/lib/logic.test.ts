import { test } from "node:test";
import assert from "node:assert/strict";
import { stepFromProgress, STORY_LAST_STEP } from "./story.ts";
import { glideStart } from "./glide.ts";

test("stepFromProgress fica entre 0 e o último passo", () => {
  assert.equal(stepFromProgress(-1), 0);
  assert.equal(stepFromProgress(0), 0);
  assert.equal(stepFromProgress(0.5), 3);
  assert.equal(stepFromProgress(2), STORY_LAST_STEP);
  assert.equal(STORY_LAST_STEP, 5);
});

test("glideStart salta para perto do destino e só desliza o trecho final", () => {
  assert.equal(glideStart(0, 5000, 600), 4400);
  assert.equal(glideStart(5000, 0, 600), 600);
  assert.equal(glideStart(100, 400, 600), 100);
});
