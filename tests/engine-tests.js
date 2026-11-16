// Testes automáticos do motor do jogo (Etapa 3).
// Rodam no Node (tests/run-node.mjs) e no navegador (tests/index.html).
import {
  CATEGORIES, DIFFICULTIES, QUESTION_TYPES, QuestionBankError,
  createQuestionSelector, filterMapQuestions, loadQuestionBank, validateBank, validateQuestion
} from "../js/core/questions.js";
import {
  MapDataError, TINY_AREA_DEGREES, interiorPoint, largestPolygonBox, loadCountries, resetCountriesCache, validateCountries
} from "../js/map/world-map.js";
import { RESULT, buildRanking } from "../js/core/scoring.js";
import { createQuestionTimer } from "../js/core/timer.js";
import { GAME_STATUS, GameError, createGame } from "../js/core/game.js";

// ---------- Ferramentas de teste ----------
const tests = [];
const test = (name, fn) => tests.push({ name, fn });

function assert(condition, message = "condição falsa") {
  if (!condition) throw new Error(message);
}
function equal(actual, expected, message = "") {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${message} esperado ${e}, recebido ${a}`.trim());
}
function throwsWithCode(fn, code) {
  try { fn(); } catch (error) {
    equal(error.code, code, "código do erro:");
    return;
  }
  throw new Error(`esperava um erro com código ${code}, mas nada foi lançado`);
}

// Sorteio previsível (mesma sequência sempre) para os testes não "falharem às vezes".
function seededRandom(seed = 12345) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Relógio falso: permite "passar 30 segundos" instantaneamente.
function createFakeScheduler() {
  let time = 0;
  let nextId = 1;
  const timers = new Map();
  return {
    now: () => time,
    setInterval(fn, ms) { const id = nextId++; timers.set(id, { fn, ms, next: time + ms }); return id; },
    clearInterval(id) { timers.delete(id); },
    // Avança o relógio disparando os temporizadores no caminho.
    advance(ms) {
      const target = time + ms;
      for (;;) {
        let due = null;
        for (const t of timers.values()) if (t.next <= target && (!due || t.next < due.next)) due = t;
        if (!due) break;
        time = due.next; due.next += due.ms; due.fn();
      }
      time = target;
    },
    // Avança o relógio SEM disparar temporizadores (simula navegador travado).
    jump(ms) { time += ms; }
  };
}

function makeBank({ mc = 20, map = 20 } = {}) {
  const list = [];
  for (let i = 0; i < mc; i += 1) {
    list.push({
      id: `mc-${i + 1}`, type: QUESTION_TYPES.MULTIPLE_CHOICE,
      difficulty: DIFFICULTIES[i % 3], category: CATEGORIES[i % CATEGORIES.length],
      text: `Pergunta de teste número ${i + 1}?`,
      options: ["A", "B", "C", "D"].map(letter => `${letter}${i}`),
      correctIndex: i % 4, explanation: `Explicação ${i + 1}.`
    });
  }
  for (let i = 0; i < map; i += 1) {
    list.push({
      id: `map-${i + 1}`, type: QUESTION_TYPES.MAP,
      difficulty: DIFFICULTIES[i % 3], category: CATEGORIES[i % CATEGORIES.length],
      text: `Localize o país de teste ${i + 1}.`, targetId: `T${i + 1}`
    });
  }
  return list;
}

const memoryStorage = () => {
  const data = new Map();
  return { getItem: k => (data.has(k) ? data.get(k) : null), setItem: (k, v) => data.set(k, String(v)) };
};

const correctAnswerFor = question => (question.type === QUESTION_TYPES.MULTIPLE_CHOICE
  ? { optionIndex: question.correctIndex } : { countryId: question.targetId });
const wrongAnswerFor = question => (question.type === QUESTION_TYPES.MULTIPLE_CHOICE
  ? { optionIndex: (question.correctIndex + 1) % question.options.length } : { countryId: "ERRADO" });

// Joga uma partida inteira. policy(question, number) devolve "correct" | "wrong" | "timeout".
function playMatch({ names, questions, policy = () => "correct" }) {
  const scheduler = createFakeScheduler();
  const game = createGame({ players: names, questions, scheduler });
  game.start();
  for (;;) {
    const turn = game.getCurrentTurn();
    const question = questions.find(q => q.id === turn.question.id);
    const action = policy(question, turn.questionNumber);
    if (action === "timeout") scheduler.advance(30000);
    else {
      const answer = action === "correct" ? correctAnswerFor(question) : wrongAnswerFor(question);
      assert(game.submitAnswer(answer).ok, "resposta deveria ser aceita");
    }
    if (game.nextTurn().finished) break;
  }
  return game;
}

// Lê um arquivo JSON do projeto, tanto no Node quanto no navegador.
async function readJson(relativePath) {
  const url = new URL(relativePath, import.meta.url);
  if (typeof process !== "undefined" && process.versions?.node) {
    const { readFile } = await import("node:fs/promises");
    return JSON.parse(await readFile(url, "utf8"));
  }
  return (await fetch(url)).json();
}

// ---------- Validação das perguntas ----------
test("pergunta válida de múltipla escolha e de mapa passam na validação", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const [map] = makeBank({ mc: 0, map: 1 });
  equal(validateQuestion(mc), []);
  equal(validateQuestion(map), []);
});

test("perguntas inválidas são reprovadas com o motivo", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const [map] = makeBank({ mc: 0, map: 1 });
  assert(validateQuestion({ ...mc, id: "" }).length > 0, "id vazio");
  assert(validateQuestion({ ...mc, type: "quiz" }).length > 0, "tipo");
  assert(validateQuestion({ ...mc, difficulty: "impossible" }).length > 0, "dificuldade");
  assert(validateQuestion({ ...mc, category: "esportes" }).length > 0, "categoria");
  assert(validateQuestion({ ...mc, text: "  " }).length > 0, "enunciado");
  assert(validateQuestion({ ...mc, correctIndex: 4 }).length > 0, "correctIndex fora");
  assert(validateQuestion({ ...mc, correctIndex: "1" }).length > 0, "correctIndex texto");
  assert(validateQuestion({ ...mc, options: ["Sim", "sim", "Não", "Talvez"] }).length > 0, "alternativas repetidas");
  assert(validateQuestion({ ...mc, options: ["Só uma"] }).length > 0, "poucas alternativas");
  assert(validateQuestion({ ...map, targetId: "" }).length > 0, "targetId vazio");
  assert(validateQuestion(null).length > 0, "nulo");
});

test("validateBank separa válidas, inválidas e duplicadas", () => {
  const bank = makeBank({ mc: 3, map: 2 });
  const withProblems = [
    ...bank,
    { ...bank[0] },                                              // id duplicado
    { ...bank[1], id: "outro-id", text: "PERGUNTA de teste número 2" }, // mesmo enunciado (sem acento/pontuação)
    { ...bank[2], id: "ruim", correctIndex: 99 }                 // inválida
  ];
  const result = validateBank(withProblems);
  equal(result.questions.length, 5);
  equal(result.rejected.length, 3);
  equal(result.stats.total, 8);
  equal(result.stats.byType, { multiple_choice: 3, map: 2 });
  throwsWithCode(() => validateBank("texto"), "INVALID_BANK_FORMAT");
  equal(validateBank({ questions: bank }).questions.length, 5);
});

test("loadQuestionBank lê tanto { questions: [...] } quanto lista pura", async () => {
  const original = globalThis.fetch;
  try {
    const bank = makeBank({ mc: 2, map: 2 });
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ version: 1, questions: bank }) });
    equal((await loadQuestionBank()).questions.length, 4);
    globalThis.fetch = async () => ({ ok: true, json: async () => bank });
    equal((await loadQuestionBank()).questions.length, 4);
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ version: 1, questions: [] }) });
    equal((await loadQuestionBank()).questions.length, 0, "banco vazio atual");
    globalThis.fetch = async () => ({ ok: false });
    let failed = false;
    try { await loadQuestionBank(); } catch { failed = true; }
    assert(failed, "deveria falhar quando o arquivo não carrega");
  } finally { globalThis.fetch = original; }
});

// ---------- Sorteio ----------
test("uma partida sorteia 5 de múltipla escolha + 5 de mapa, sem repetir", () => {
  const selector = createQuestionSelector(makeBank(), { random: seededRandom(1), storage: memoryStorage() });
  const match = selector.drawMatch();
  equal(match.length, 10);
  equal(match.filter(q => q.type === "multiple_choice").length, 5);
  equal(match.filter(q => q.type === "map").length, 5);
  equal(new Set(match.map(q => q.id)).size, 10, "ids únicos:");
  assert(new Set(match.map(q => q.difficulty)).size > 1, "dificuldade deveria ser mista");
});

test("a ordem das perguntas é aleatória (tipos misturados)", () => {
  const orders = new Set();
  for (let seed = 1; seed <= 10; seed += 1) {
    const selector = createQuestionSelector(makeBank(), { random: seededRandom(seed), storage: memoryStorage() });
    const order = selector.drawMatch().map(q => (q.type === "map" ? "M" : "C")).join("");
    assert(order.includes("M") && order.includes("C"), "os dois tipos devem aparecer");
    orders.add(order);
  }
  assert(orders.size > 1, "a ordem deveria variar entre partidas");
});

test("não repete perguntas entre partidas enquanto houver outras; depois recomeça o ciclo", () => {
  const selector = createQuestionSelector(makeBank({ mc: 15, map: 15 }), {
    random: seededRandom(3), storage: memoryStorage()
  });
  const seen = new Set();
  for (let i = 0; i < 3; i += 1) {
    selector.drawMatch().forEach(q => { assert(!seen.has(q.id), `repetiu ${q.id} antes de esgotar`); seen.add(q.id); });
  }
  equal(seen.size, 30, "3 partidas usam o banco inteiro:");
  const fourth = selector.drawMatch(); // banco esgotado: embaralha de novo
  equal(fourth.length, 10);
  equal(new Set(fourth.map(q => q.id)).size, 10, "sem repetição dentro da partida:");
});

test("ciclo reinicia no meio de uma partida sem duplicar perguntas", () => {
  const selector = createQuestionSelector(makeBank({ mc: 7, map: 7 }), {
    random: seededRandom(5), storage: memoryStorage()
  });
  selector.drawMatch(); // usa 5+5; sobram 2+2
  const second = selector.drawMatch(); // precisa de 5+5: usa 2+2 e recomeça
  equal(new Set(second.map(q => q.id)).size, 10);
});

test("histórico de perguntas usadas é lembrado entre sessões (armazenamento)", () => {
  const storage = memoryStorage();
  const bank = makeBank({ mc: 10, map: 10 });
  const first = createQuestionSelector(bank, { random: seededRandom(9), storage }).drawMatch();
  const second = createQuestionSelector(bank, { random: seededRandom(9), storage }).drawMatch();
  const ids = new Set(first.map(q => q.id));
  assert(second.every(q => !ids.has(q.id)), "a 2ª partida repetiu perguntas da 1ª");
});

test("banco insuficiente gera erro claro (e não estraga o histórico)", () => {
  const selector = createQuestionSelector(makeBank({ mc: 4, map: 20 }), { storage: memoryStorage() });
  try { selector.drawMatch(); throw new Error("não lançou"); } catch (error) {
    assert(error instanceof QuestionBankError, "tipo do erro");
    equal(error.code, "INSUFFICIENT_QUESTIONS");
    equal(error.details.missing, [{ type: "multiple_choice", needed: 5, available: 4 }]);
  }
  equal(selector.getUsage().used, 0, "nada foi marcado como usado");
  throwsWithCode(() => createQuestionSelector([], { storage: memoryStorage() }).drawMatch(), "INSUFFICIENT_QUESTIONS");
});

// ---------- Ranking ----------
test("ranking: mais pontos vence; empate de pontos desempata por acertos", () => {
  const ranking = buildRanking([
    { index: 0, name: "Ana", score: 30, correct: 1, wrong: 0, unanswered: 0 },
    { index: 1, name: "Bia", score: 30, correct: 2, wrong: 0, unanswered: 0 },
    { index: 2, name: "Caio", score: 50, correct: 2, wrong: 0, unanswered: 0 }
  ]);
  equal(ranking.map(p => p.name), ["Caio", "Bia", "Ana"]);
  equal(ranking.map(p => p.position), [1, 2, 3]);
  assert(ranking.every(p => !p.tied), "ninguém empatado");
});

test("ranking: pontos e acertos iguais = empate com mesma posição", () => {
  const ranking = buildRanking([
    { index: 0, name: "Ana", score: 40, correct: 2, wrong: 0, unanswered: 0 },
    { index: 1, name: "Bia", score: 40, correct: 2, wrong: 0, unanswered: 0 },
    { index: 2, name: "Caio", score: 10, correct: 1, wrong: 0, unanswered: 0 }
  ]);
  equal(ranking.map(p => p.position), [1, 1, 3]);
  equal(ranking.map(p => p.tied), [true, true, false]);
});

// ---------- Cronômetro ----------
test("cronômetro conta de 30 até 0 e avisa o fim uma única vez", () => {
  const scheduler = createFakeScheduler();
  const ticks = []; let expirations = 0;
  const timer = createQuestionTimer(30, () => { expirations += 1; }, s => ticks.push(s), scheduler);
  timer.start();
  equal(ticks[0], 30, "valor inicial:");
  scheduler.advance(10000);
  equal(timer.getRemaining(), 20);
  scheduler.advance(20000);
  equal(timer.getRemaining(), 0);
  equal(expirations, 1, "avisos de fim:");
  scheduler.advance(5000);
  equal(expirations, 1, "não avisa de novo:");
  equal(ticks[ticks.length - 1], 0);
  equal(ticks.length, 31, "um aviso por segundo (30..0):");
  assert(timer.isExpired());
});

test("cronômetro parado não dispara o fim", () => {
  const scheduler = createFakeScheduler();
  let expirations = 0;
  const timer = createQuestionTimer(30, () => { expirations += 1; }, () => {}, scheduler);
  timer.start();
  scheduler.advance(12000);
  timer.stop();
  scheduler.advance(60000);
  equal(expirations, 0);
  equal(timer.getRemaining(), 18);
  equal(Math.round(timer.getElapsedMs()), 12000);
});

// ---------- Partida ----------
test("jogadores inválidos são recusados", () => {
  const questions = makeBank({ mc: 5, map: 5 });
  throwsWithCode(() => createGame({ players: [], questions }), "INVALID_PLAYERS");
  throwsWithCode(() => createGame({ players: ["A", "B", "C", "D", "E"], questions }), "INVALID_PLAYERS");
  throwsWithCode(() => createGame({ players: ["Ana", "  "], questions }), "INVALID_PLAYERS");
  throwsWithCode(() => createGame({ players: ["Ana", " ana "], questions }), "INVALID_PLAYERS");
  throwsWithCode(() => createGame({ players: "Ana", questions }), "INVALID_PLAYERS");
});

test("perguntas inválidas ou repetidas na partida são recusadas", () => {
  const good = makeBank({ mc: 2, map: 0 });
  throwsWithCode(() => createGame({ players: ["Ana"], questions: [] }), "INVALID_QUESTIONS");
  throwsWithCode(() => createGame({ players: ["Ana"], questions: [{ ...good[0], correctIndex: 9 }] }), "INVALID_QUESTIONS");
  throwsWithCode(() => createGame({ players: ["Ana"], questions: [good[0], good[0]] }), "INVALID_QUESTIONS");
});

test("1, 2, 3 e 4 jogadores: turnos alternados e partida de 10 perguntas", () => {
  const expected = { 1: [10], 2: [5, 5], 3: [4, 3, 3], 4: [3, 3, 2, 2] };
  for (const count of [1, 2, 3, 4]) {
    const names = ["Ana", "Bia", "Caio", "Duda"].slice(0, count);
    const selector = createQuestionSelector(makeBank(), { random: seededRandom(count), storage: memoryStorage() });
    const game = playMatch({ names, questions: selector.drawMatch() });
    const history = game.getHistory();
    equal(history.length, 10, `${count} jogador(es): perguntas:`);
    equal(names.map(n => history.filter(h => h.playerName === n).length), expected[count], `${count} jogador(es): turnos:`);
    history.forEach((h, i) => equal(h.playerName, names[i % count], `${count} jogador(es): ordem do turno ${i + 1}:`));
    equal(game.getState().status, GAME_STATUS.FINISHED);
  }
});

test("pontuação: fácil 10, média 20, difícil 30; erro e tempo esgotado valem 0", () => {
  const [easy, medium, hard] = [0, 1, 2].map(i => makeBank({ mc: 3, map: 0 })[i]);
  const game = playMatch({ names: ["Ana"], questions: [easy, medium, hard] });
  equal(game.getRanking()[0].score, 60);
  equal(game.getHistory().map(h => h.pointsEarned), [10, 20, 30]);

  const mixed = playMatch({
    names: ["Ana"], questions: [easy, medium, hard],
    policy: (q, n) => (n === 1 ? "correct" : n === 2 ? "wrong" : "timeout")
  });
  const me = mixed.getRanking()[0];
  equal([me.score, me.correct, me.wrong, me.unanswered], [10, 1, 1, 1]);
  equal(mixed.getHistory().map(h => h.result), [RESULT.CORRECT, RESULT.WRONG, RESULT.TIMEOUT]);
});

test("desafio no mapa: acerta só com o identificador exato", () => {
  const [map] = makeBank({ mc: 0, map: 1 });
  const scheduler = createFakeScheduler();
  const game = createGame({ players: ["Ana"], questions: [map], scheduler });
  game.start();
  equal(game.submitAnswer({ countryId: "T2" }).feedback.result, RESULT.WRONG);
  const game2 = createGame({ players: ["Ana"], questions: [map], scheduler });
  game2.start();
  const answer = game2.submitAnswer({ countryId: "T1" });
  equal(answer.feedback.result, RESULT.CORRECT);
  equal(answer.feedback.correctAnswer, { countryId: "T1" });
});

test("targetName é opcional, validado e aparece no feedback do mapa", () => {
  const [map] = makeBank({ mc: 0, map: 1 });
  assert(validateQuestion({ ...map, targetName: "" }).length > 0, "targetName vazio");
  assert(validateQuestion({ ...map, targetName: 5 }).length > 0, "targetName não texto");
  equal(validateQuestion({ ...map, targetName: "Brasil" }), []);
  const game = createGame({ players: ["Ana"], questions: [{ ...map, targetName: "Brasil" }], scheduler: createFakeScheduler() });
  game.start();
  equal(game.submitAnswer({ countryId: "T1" }).feedback.correctAnswer, { countryId: "T1", name: "Brasil" });
});

test("feedback traz resposta certa, explicação, pontos e jogador", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const game = createGame({ players: ["Ana"], questions: [mc], scheduler: createFakeScheduler() });
  game.start();
  const { feedback } = game.submitAnswer({ optionIndex: 3 }); // correta é a 0
  equal(feedback.isCorrect, false);
  equal(feedback.pointsEarned, 0);
  equal(feedback.correctAnswer, { optionIndex: 0, text: "A0" });
  equal(feedback.explanation, "Explicação 1.");
  equal(feedback.playerName, "Ana");
  equal(feedback.isLastQuestion, true);
});

test("a interface não recebe a resposta certa antes de responder", () => {
  const questions = makeBank({ mc: 1, map: 1 });
  for (const q of questions) {
    const game = createGame({ players: ["Ana"], questions: [q], scheduler: createFakeScheduler() });
    game.start();
    const text = JSON.stringify(game.getCurrentTurn());
    assert(!text.includes("correctIndex") && !text.includes("targetId"), "vazou a resposta");
    assert(!text.includes("Explicação"), "vazou a explicação");
  }
});

test("tempo esgotado: registra 'não respondida' e bloqueia resposta tardia", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const scheduler = createFakeScheduler();
  const game = createGame({ players: ["Ana"], questions: [mc], scheduler });
  const events = [];
  game.on("feedback", f => events.push(f.result));
  game.start();
  scheduler.advance(29000);
  equal(game.getCurrentTurn().remainingSeconds, 1);
  scheduler.advance(1000);
  equal(events, [RESULT.TIMEOUT]);
  equal(game.getRanking()[0].unanswered, 1);
  const late = game.submitAnswer({ optionIndex: 0 });
  equal([late.ok, late.reason], [false, "already_answered"]);
  equal(game.getRanking()[0].score, 0, "resposta tardia não pontua:");
});

test("tempo esgotado também vale se o navegador atrasou o aviso do cronômetro", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const scheduler = createFakeScheduler();
  const game = createGame({ players: ["Ana"], questions: [mc], scheduler });
  game.start();
  scheduler.jump(31000); // passou o tempo, mas o cronômetro ainda não "disparou"
  const late = game.submitAnswer({ optionIndex: 0 });
  equal([late.ok, late.reason], [false, "time_expired"]);
  equal(late.feedback.result, RESULT.TIMEOUT);
  equal(game.getRanking()[0].score, 0);
});

test("resposta no último instante (antes de zerar) ainda vale", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const scheduler = createFakeScheduler();
  const game = createGame({ players: ["Ana"], questions: [mc], scheduler });
  game.start();
  scheduler.advance(29900);
  assert(game.submitAnswer({ optionIndex: 0 }).ok, "deveria aceitar aos 29,9 s");
});

test("resposta inválida não consome o turno; resposta dupla é recusada", () => {
  const [mc] = makeBank({ mc: 1, map: 0 });
  const game = createGame({ players: ["Ana"], questions: [mc], scheduler: createFakeScheduler() });
  game.start();
  for (const bad of [null, undefined, {}, { optionIndex: 9 }, { optionIndex: "1" }, { countryId: "BRA" }]) {
    equal(game.submitAnswer(bad).reason, "invalid_answer");
  }
  equal(game.getState().status, GAME_STATUS.AWAITING_ANSWER);
  assert(game.submitAnswer({ optionIndex: 0 }).ok);
  equal(game.submitAnswer({ optionIndex: 0 }).reason, "already_answered");
  equal(game.getRanking()[0].correct, 1, "contou só uma vez:");
});

test("cronômetro reinicia a cada turno e a partida termina sozinha", () => {
  const questions = makeBank({ mc: 2, map: 0 });
  const scheduler = createFakeScheduler();
  const game = createGame({ players: ["Ana", "Bia"], questions, scheduler });
  const log = [];
  ["turnStart", "feedback", "end"].forEach(name => game.on(name, () => log.push(name)));
  game.start();
  scheduler.advance(20000);
  game.submitAnswer({ optionIndex: 0 });
  const next = game.nextTurn();
  equal(next.finished, false);
  equal(game.getCurrentTurn().remainingSeconds, 30, "cronômetro do turno 2:");
  equal(game.getCurrentTurn().player.name, "Bia");
  scheduler.advance(30000); // tempo esgota no turno 2
  const end = game.nextTurn();
  equal(end.finished, true);
  equal(log, ["turnStart", "feedback", "turnStart", "feedback", "end"]);
  scheduler.advance(60000);
  equal(log.length, 5, "nada acontece depois do fim:");
  throwsWithCode(() => game.nextTurn(), "INVALID_STATE");
});

test("não é possível avançar sem responder nem iniciar duas vezes", () => {
  const game = createGame({ players: ["Ana"], questions: makeBank({ mc: 2, map: 0 }), scheduler: createFakeScheduler() });
  throwsWithCode(() => game.nextTurn(), "INVALID_STATE");
  game.start();
  throwsWithCode(() => game.nextTurn(), "INVALID_STATE");
  throwsWithCode(() => game.start(), "INVALID_STATE");
});

test("resultado final: ranking, desempate, empate total e vencedores", () => {
  const questions = makeBank({ mc: 3, map: 0 }); // fácil, média, difícil (10/20/30)
  // Ana: q1 (10) + q3 (30) = 40 com 2 acertos. Bia: q2 (20) = 20 com 1 acerto.
  const game = playMatch({ names: ["Ana", "Bia"], questions, policy: (q, n) => (n === 2 ? "correct" : "correct") });
  const results = game.getResults();
  equal(results.finished, true);
  equal(results.ranking.map(p => [p.name, p.score, p.correct, p.position]), [["Ana", 40, 2, 1], ["Bia", 20, 1, 2]]);
  equal(results.winners.map(w => w.name), ["Ana"]);

  // Empate total: ambos erram tudo.
  const tie = playMatch({ names: ["Ana", "Bia"], questions: questions.slice(0, 2), policy: () => "wrong" });
  const tieResults = tie.getResults();
  equal(tieResults.ranking.map(p => p.position), [1, 1]);
  equal(tieResults.winners.length, 2);
  equal(tieResults.ranking.map(p => p.wrong), [1, 1]);
});

test("contadores batem: acertos + erros + não respondidas = perguntas respondidas", () => {
  const selector = createQuestionSelector(makeBank(), { random: seededRandom(21), storage: memoryStorage() });
  const questions = selector.drawMatch();
  const game = playMatch({
    names: ["Ana", "Bia", "Caio"], questions,
    policy: (q, n) => ["correct", "wrong", "timeout"][n % 3]
  });
  const total = game.getRanking().reduce((sum, p) => sum + p.correct + p.wrong + p.unanswered, 0);
  equal(total, 10);
  const scoreFromHistory = game.getHistory().reduce((sum, h) => sum + h.pointsEarned, 0);
  equal(game.getRanking().reduce((sum, p) => sum + p.score, 0), scoreFromHistory);
});

test("placar durante a partida indica o jogador da vez", () => {
  const game = createGame({ players: ["Ana", "Bia"], questions: makeBank({ mc: 2, map: 0 }), scheduler: createFakeScheduler() });
  game.start();
  equal(game.getScoreboard().map(p => p.isCurrent), [true, false]);
  game.submitAnswer({ optionIndex: 0 });
  game.nextTurn();
  equal(game.getScoreboard().map(p => p.isCurrent), [false, true]);
  assert(game.getScoreboard()[0].score === 10, "placar atualizado");
});

test("destroy interrompe o cronômetro e a partida", () => {
  const scheduler = createFakeScheduler();
  const game = createGame({ players: ["Ana"], questions: makeBank({ mc: 2, map: 0 }), scheduler });
  let feedbacks = 0;
  game.on("feedback", () => { feedbacks += 1; });
  game.start();
  game.destroy();
  scheduler.advance(60000);
  equal(feedbacks, 0);
  equal(game.getState().status, GAME_STATUS.ABORTED);
  equal(game.submitAnswer({ optionIndex: 0 }).reason, "not_awaiting_answer");
});

test("erro dentro de um ouvinte de evento não derruba o motor", () => {
  const game = createGame({ players: ["Ana"], questions: makeBank({ mc: 1, map: 0 }), scheduler: createFakeScheduler() });
  const originalError = console.error;
  console.error = () => {};
  try {
    game.on("feedback", () => { throw new Error("falha na interface"); });
    game.start();
    assert(game.submitAnswer({ optionIndex: 0 }).ok);
  } finally { console.error = originalError; }
});

test("GameError é exportado e identificável", () => {
  try { createGame({}); } catch (error) { assert(error instanceof GameError); return; }
  throw new Error("deveria lançar");
});


// ---------- Dados do mapa (Etapa 5) ----------
test("GeoJSON: identificadores válidos, únicos e geometrias corretas", async () => {
  const geojson = await readJson("../data/geojson/countries.geojson");
  const { countries, problems } = validateCountries(geojson);
  equal(problems, [], "problemas:");
  assert(countries.size >= 240, `países e territórios: ${countries.size}`);
  assert([...countries.values()].every(c => c.name && c.name !== c.id), "todo país tem nome em português");
});

test("GeoJSON: países essenciais presentes, e a Austrália aparece só uma vez", async () => {
  const geojson = await readJson("../data/geojson/countries.geojson");
  const ids = geojson.features.map(f => f.properties.id);
  for (const code of ["BRA", "USA", "FRA", "NOR", "SSD", "VAT", "MLT", "SGP", "KOS", "PSE", "TWN", "ESH", "GRL", "ATA"]) {
    assert(ids.includes(code), `falta ${code}`);
  }
  equal(ids.filter(id => id === "AUS").length, 1, "ocorrências de AUS:");
  equal(ids.filter(id => id === "FRA").length, 1, "ocorrências de FRA:");
});

test("GeoJSON: ao menos 50 países minúsculos recebem ponto clicável", async () => {
  const geojson = await readJson("../data/geojson/countries.geojson");
  const tiny = geojson.features.filter(f => largestPolygonBox(f.geometry).area < TINY_AREA_DEGREES);
  assert(tiny.length >= 50 && tiny.length < 120, `minúsculos: ${tiny.length}`);
  assert(tiny.some(f => f.properties.id === "VAT") && !tiny.some(f => f.properties.id === "BRA"));
});

test("banco de teste: todo targetId existe no GeoJSON e o nome confere", async () => {
  const geojson = await readJson("../data/geojson/countries.geojson");
  const { countries } = validateCountries(geojson);
  const bank = validateBank(await readJson("../data/questions.dev.json"));
  equal(bank.rejected, [], "perguntas rejeitadas:");
  const mapQuestions = bank.questions.filter(q => q.type === QUESTION_TYPES.MAP);
  assert(mapQuestions.length >= 5, "há perguntas de mapa");
  for (const q of mapQuestions) {
    assert(countries.has(q.targetId), `${q.id}: ${q.targetId} não existe no GeoJSON`);
    equal(q.targetName, countries.get(q.targetId).name, `${q.id}: nome diferente do GeoJSON —`);
  }
});

test("interiorPoint cai dentro do país em todos os registros (inclusive Chile e África do Sul)", async () => {
  const geojson = await readJson("../data/geojson/countries.geojson");
  const inRing = (x, y, ring) => {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  };
  const outside = [];
  for (const feature of geojson.features) {
    const { lat, lng } = interiorPoint(feature.geometry);
    const polygons = feature.geometry.type === "MultiPolygon" ? feature.geometry.coordinates : [feature.geometry.coordinates];
    const inside = polygons.some(([outer, ...holes]) => inRing(lng, lat, outer) && !holes.some(h => inRing(lng, lat, h)));
    if (!inside) outside.push(feature.properties.id);
  }
  equal(outside, [], "países com ponto fora:");
  // Teste de forma: um "L" deitado tem o centro da caixa fora da figura.
  const L = { type: "Polygon", coordinates: [[[0, 0], [10, 0], [10, 1], [1, 1], [1, 10], [0, 10], [0, 0]]] };
  const p = interiorPoint(L);
  assert(inRing(p.lng, p.lat, L.coordinates[0]), "ponto dentro do L");
});

test("filterMapQuestions remove só perguntas de mapa com país inexistente", () => {
  const bank = makeBank({ mc: 2, map: 3 }); // alvos T1, T2, T3
  const { questions, removed } = filterMapQuestions(bank, new Set(["T1", "T3"]));
  equal(removed, [{ id: "map-2", targetId: "T2" }]);
  equal(questions.length, 4);
  assert(questions.some(q => q.type === QUESTION_TYPES.MULTIPLE_CHOICE && q.id === "mc-2"), "múltipla escolha preservada");
});

test("largestPolygonBox escolhe o maior pedaço (ex.: continente e ilhas distantes)", () => {
  const box = largestPolygonBox({
    type: "MultiPolygon",
    coordinates: [
      [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
      [[[50, 50], [51, 50], [51, 51], [50, 51], [50, 50]]]
    ]
  });
  equal([box.west, box.south, box.east, box.north], [0, 0, 10, 10]);
  equal(largestPolygonBox({ type: "Polygon", coordinates: [[[1, 1], [3, 1], [3, 2], [1, 2], [1, 1]]] }).area, 2);
});

test("loadCountries: erros de carregamento viram MapDataError e permitem tentar de novo", async () => {
  const original = globalThis.fetch;
  try {
    resetCountriesCache();
    globalThis.fetch = async () => ({ ok: false });
    let failed = null;
    try { await loadCountries("x"); } catch (error) { failed = error; }
    assert(failed instanceof MapDataError, "404 vira MapDataError");

    globalThis.fetch = async () => ({ ok: true, json: async () => ({ type: "FeatureCollection", features: [
      { type: "Feature", properties: { id: "AAA", name: "A" }, geometry: { type: "Polygon", coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] } },
      { type: "Feature", properties: { id: "AAA", name: "B" }, geometry: { type: "Polygon", coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] } }
    ] }) });
    resetCountriesCache();
    failed = null;
    try { await loadCountries("x"); } catch (error) { failed = error; }
    assert(failed instanceof MapDataError && /repetido/.test(failed.message), "identificador repetido é recusado");

    // Depois de um erro, uma nova tentativa com dados bons funciona.
    globalThis.fetch = async () => ({ ok: true, json: async () => readJson("../data/geojson/countries.geojson") });
    resetCountriesCache();
    const data = await loadCountries("x");
    assert(data.ids.has("BRA") && data.countries.get("BRA").name === "Brasil");
  } finally { globalThis.fetch = original; resetCountriesCache(); }
});

test("validateCountries recusa arquivo vazio ou fora do formato", () => {
  assert(validateCountries(null).problems.length > 0);
  assert(validateCountries({ type: "FeatureCollection", features: [] }).problems.length > 0);
  assert(validateCountries({ type: "FeatureCollection", features: [{ type: "Feature", properties: { id: "br" }, geometry: null }] }).problems.length >= 2);
});

// ---------- Execução ----------
export async function runAllTests() {
  const results = [];
  for (const { name, fn } of tests) {
    try { await fn(); results.push({ name, ok: true }); }
    catch (error) { results.push({ name, ok: false, error: error.message }); }
  }
  return {
    results,
    passed: results.filter(r => r.ok).length,
    failed: results.filter(r => !r.ok).length
  };
}
