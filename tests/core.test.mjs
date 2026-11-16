import assert from "node:assert/strict";
import { validateQuestions, selectMatchQuestions } from "../js/core/questions.js";
import { createGameState, recordAnswer, advanceTurn, getRanking } from "../js/core/scoring.js";
import { readFile } from "node:fs/promises";

const payload = JSON.parse(await readFile(new URL("../data/questions.json", import.meta.url), "utf8"));
const questions = payload.questions;

const world = JSON.parse(await readFile(new URL("../data/geojson/countries.geojson", import.meta.url), "utf8"));
assert.equal(world.type, "FeatureCollection");
assert.ok(world.features.length >= 170, "O mapa deve conter a maior parte dos países do mundo.");
const mapCodes = new Set(world.features.map(feature => feature.properties?.iso_a3));
for (const code of ["BRA", "FRA", "JPN", "ZAF", "KAZ"]) {
  assert.ok(mapCodes.has(code), `O mapa precisa conter o país ${code}.`);
}
assert.ok(world.features.every(feature => feature.geometry?.type && feature.geometry?.coordinates), "Cada país precisa ter geometria GeoJSON.");

assert.equal(validateQuestions(questions).valid, true);
assert.equal(questions.length, 10);
const selected = selectMatchQuestions(questions, { rng: () => 0.42 });
assert.equal(selected.length, 10);
assert.equal(selected.filter(q => q.type === "multiple_choice").length, 5);
assert.equal(selected.filter(q => q.type === "map").length, 5);
assert.equal(new Set(selected.map(q => q.id)).size, 10);

const state = createGameState(["Ana", "Bia"], selected);
const first = state.questions[0];
const result = recordAnswer(state, first.correctAnswer);
assert.equal(result.correct, true);
assert.equal(result.points, first.difficulty === "easy" ? 10 : first.difficulty === "medium" ? 20 : 30);
assert.throws(() => recordAnswer(state, first.correctAnswer));
advanceTurn(state);
assert.equal(state.currentPlayerIndex, 1);

const wrongQuestion = state.questions[1];
const wrong = recordAnswer(state, "__resposta_incorreta__");
assert.equal(wrong.correct, false);
assert.equal(wrong.points, 0);
advanceTurn(state);

// Completa as perguntas restantes, validando rotação e finalização.
while (state.status === "playing") {
  if (!state.currentResult) recordAnswer(state, null, { timedOut: true });
  advanceTurn(state);
}
assert.equal(state.status, "finished");
assert.equal(state.players.reduce((sum, p) => sum + p.correct + p.incorrect + p.unanswered, 0), 10);
assert.equal(getRanking(state).length, 2);
assert.equal(state.players.reduce((sum, p) => sum + p.unanswered, 0), 8);

assert.throws(() => selectMatchQuestions(questions.slice(0, 8)), /Banco insuficiente/);
console.log("OK: testes do motor do GeoMaster concluídos.");
