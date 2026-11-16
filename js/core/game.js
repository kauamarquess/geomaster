// Motor do jogo: turnos, perguntas, cronômetro, correção, pontuação e ranking.
//
// Este arquivo NÃO desenha nada na tela. Ele guarda o "estado da partida" e
// avisa a interface por meio de eventos (Etapa 4 vai conectar os dois lados).
//
// Fluxo de uma partida:
//   const game = createGame({ players: ["Ana", "Bia"], questions });
//   game.on("turnStart", ...);  game.on("feedback", ...);  game.on("end", ...);
//   game.start();                    -> começa a pergunta 1
//   game.submitAnswer({ optionIndex: 2 })   // ou { countryId: "BRA" }
//   game.nextTurn();                 -> próxima pergunta (ou fim da partida)
import { getPlayers } from "./players.js";
import { QUESTION_TYPES, validateQuestion } from "./questions.js";
import {
  MATCH_RULES, RESULT, createGameState, createPlayerStats, pointsForDifficulty,
  isAnswerValid, evaluateAnswer, applyResult, buildRanking
} from "./scoring.js";
import { createQuestionTimer } from "./timer.js";

export const GAME_STATUS = Object.freeze({
  SETUP: "setup",
  AWAITING_ANSWER: "awaiting_answer", // pergunta na tela, cronômetro rodando
  FEEDBACK: "feedback",               // resposta registrada, mostrando o resultado
  FINISHED: "finished",
  ABORTED: "aborted"
});

export class GameError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "GameError";
    this.code = code;
    this.details = details;
  }
}

// Versão da pergunta que a interface pode ver ANTES de responder:
// não inclui a resposta certa (correctIndex / targetId).
function toPublicQuestion(question) {
  const view = {
    id: question.id,
    type: question.type,
    difficulty: question.difficulty,
    category: question.category,
    text: question.text,
    points: pointsForDifficulty(question.difficulty)
  };
  if (question.type === QUESTION_TYPES.MULTIPLE_CHOICE || question.type === QUESTION_TYPES.FLAG) {
    view.options = [...question.options];
  }
  if (question.type === QUESTION_TYPES.FLAG) view.flagCode = question.flagCode;
  return view;
}

function describeCorrectAnswer(question) {
  if (question.type === QUESTION_TYPES.MULTIPLE_CHOICE || question.type === QUESTION_TYPES.FLAG) {
    return { optionIndex: question.correctIndex, text: question.options[question.correctIndex] };
  }
  const answer = { countryId: question.targetId };
  if (question.targetName) answer.name = question.targetName; // nome do país, se existir
  return answer;
}

export function createGame(options = {}) {
  const {
    players: playerNames,
    questions,
    secondsPerQuestion = MATCH_RULES.secondsPerQuestion,
    scheduler // opcional: usado só nos testes para controlar o relógio
  } = options;

  // ---------- Validações iniciais ----------
  if (!Array.isArray(playerNames) || !playerNames.every(name => typeof name === "string")) {
    throw new GameError("INVALID_PLAYERS", "A lista de jogadores precisa conter nomes (texto).");
  }
  if (playerNames.length < MATCH_RULES.minPlayers || playerNames.length > MATCH_RULES.maxPlayers) {
    throw new GameError("INVALID_PLAYERS",
      `A partida precisa de ${MATCH_RULES.minPlayers} a ${MATCH_RULES.maxPlayers} jogadores.`);
  }
  const checkedPlayers = getPlayers(playerNames);
  if (!checkedPlayers.valid) {
    throw new GameError("INVALID_PLAYERS",
      checkedPlayers.duplicate ? "Há nomes de jogadores repetidos." : "Há nomes de jogadores vazios.");
  }
  if (!Array.isArray(questions) || questions.length === 0) {
    throw new GameError("INVALID_QUESTIONS", "A partida precisa de ao menos uma pergunta.");
  }
  const questionProblems = questions
    .map((question, index) => ({ index, id: question?.id ?? null, problems: validateQuestion(question) }))
    .filter(item => item.problems.length > 0);
  if (questionProblems.length > 0) {
    throw new GameError("INVALID_QUESTIONS", "Há perguntas inválidas na partida.", { questionProblems });
  }
  if (new Set(questions.map(q => q.id)).size !== questions.length) {
    throw new GameError("INVALID_QUESTIONS", "Há perguntas repetidas na mesma partida.");
  }
  if (!Number.isFinite(secondsPerQuestion) || secondsPerQuestion <= 0) {
    throw new GameError("INVALID_SETTINGS", "O tempo por pergunta precisa ser maior que zero.");
  }

  // ---------- Estado interno ----------
  const state = createGameState({
    questionsPerMatch: questions.length,
    secondsPerQuestion
  });
  const playerStats = checkedPlayers.list.map((name, index) => createPlayerStats(name, index));
  const history = [];
  const listeners = new Map();
  let timer = null;
  let currentFeedback = null;

  // ---------- Eventos ----------
  function on(eventName, handler) {
    if (!listeners.has(eventName)) listeners.set(eventName, new Set());
    listeners.get(eventName).add(handler);
    return () => listeners.get(eventName)?.delete(handler); // devolve a função de "descadastrar"
  }

  function emit(eventName, payload) {
    (listeners.get(eventName) ?? []).forEach(handler => {
      try { handler(payload); } catch (error) { console.error(`Erro no evento "${eventName}":`, error); }
    });
  }

  // ---------- Consultas (a interface só lê cópias) ----------
  const currentQuestion = () => questions[state.currentQuestionIndex];

  function getCurrentTurn() {
    if (state.status !== GAME_STATUS.AWAITING_ANSWER && state.status !== GAME_STATUS.FEEDBACK) return null;
    const player = playerStats[state.currentPlayerIndex];
    return {
      questionNumber: state.currentQuestionIndex + 1,
      totalQuestions: questions.length,
      player: { index: player.index, name: player.name, score: player.score },
      question: toPublicQuestion(currentQuestion()),
      secondsPerQuestion,
      remainingSeconds: timer ? timer.getRemaining() : secondsPerQuestion
    };
  }

  function getScoreboard() {
    return playerStats.map(stats => ({
      ...stats,
      isCurrent: state.status !== GAME_STATUS.FINISHED && stats.index === state.currentPlayerIndex
    }));
  }

  const getRanking = () => buildRanking(playerStats);

  function getResults() {
    const ranking = getRanking();
    return {
      finished: state.status === GAME_STATUS.FINISHED,
      ranking,
      winners: ranking.filter(entry => entry.position === 1),
      history: history.map(entry => ({ ...entry })),
      totalQuestions: questions.length
    };
  }

  // ---------- Fluxo da partida ----------
  function beginTurn(index) {
    state.currentQuestionIndex = index;
    state.currentPlayerIndex = index % playerStats.length; // turnos alternados automáticos
    state.status = GAME_STATUS.AWAITING_ANSWER;
    currentFeedback = null;

    // Cada turno ganha um cronômetro novo (volta aos 30 segundos).
    timer = createQuestionTimer(
      secondsPerQuestion,
      () => resolveTurn(null),                       // tempo acabou
      remaining => emit("tick", { remaining }),
      scheduler
    );
    emit("turnStart", getCurrentTurn());
    timer.start();
  }

  // Fecha o turno atual. answer === null significa tempo esgotado.
  function resolveTurn(answer) {
    if (state.status !== GAME_STATUS.AWAITING_ANSWER) return currentFeedback; // já resolvido
    timer.stop();

    const question = currentQuestion();
    const stats = playerStats[state.currentPlayerIndex];
    const result = evaluateAnswer(question, answer);
    const pointsEarned = applyResult(stats, result, question.difficulty);
    const isLastQuestion = state.currentQuestionIndex === questions.length - 1;

    currentFeedback = {
      questionNumber: state.currentQuestionIndex + 1,
      totalQuestions: questions.length,
      playerIndex: stats.index,
      playerName: stats.name,
      questionId: question.id,
      result,
      isCorrect: result === RESULT.CORRECT,
      pointsEarned,
      totalScore: stats.score,
      correctAnswer: describeCorrectAnswer(question),
      explanation: question.explanation ?? null,
      timeSpentMs: Math.round(timer.getElapsedMs()),
      isLastQuestion
    };
    history.push({
      questionNumber: currentFeedback.questionNumber,
      questionId: question.id,
      playerIndex: stats.index,
      playerName: stats.name,
      type: question.type,
      difficulty: question.difficulty,
      category: question.category,
      answer: answer === null ? null : { ...answer },
      result,
      pointsEarned,
      timeSpentMs: currentFeedback.timeSpentMs
    });

    state.status = GAME_STATUS.FEEDBACK;
    emit("feedback", currentFeedback);
    return currentFeedback;
  }

  function start() {
    if (state.status !== GAME_STATUS.SETUP) {
      throw new GameError("INVALID_STATE", "A partida já foi iniciada.");
    }
    beginTurn(0);
  }

  // Registra a resposta do jogador atual.
  // Retorna { ok: true, feedback } ou { ok: false, reason } sem consumir o turno
  // quando a resposta é inválida.
  function submitAnswer(answer) {
    if (state.status === GAME_STATUS.FEEDBACK) return { ok: false, reason: "already_answered" };
    if (state.status !== GAME_STATUS.AWAITING_ANSWER) return { ok: false, reason: "not_awaiting_answer" };

    // Mesmo que o cronômetro ainda não tenha "disparado", o tempo manda:
    // depois de zero não se aceita resposta.
    if (timer.isExpired()) {
      return { ok: false, reason: "time_expired", feedback: resolveTurn(null) };
    }
    if (!isAnswerValid(currentQuestion(), answer)) return { ok: false, reason: "invalid_answer" };
    return { ok: true, feedback: resolveTurn(answer) };
  }

  // Avança para a próxima pergunta ou encerra a partida automaticamente.
  function nextTurn() {
    if (state.status !== GAME_STATUS.FEEDBACK) {
      throw new GameError("INVALID_STATE", "Só é possível avançar depois de a pergunta ser respondida.");
    }
    if (currentFeedback.isLastQuestion) {
      state.status = GAME_STATUS.FINISHED;
      const results = getResults();
      emit("end", results);
      return { finished: true, results };
    }
    beginTurn(state.currentQuestionIndex + 1);
    return { finished: false, turn: getCurrentTurn() };
  }

  // Interrompe a partida (ex.: jogador volta ao início no meio do jogo).
  function destroy() {
    timer?.stop();
    if (state.status !== GAME_STATUS.FINISHED) state.status = GAME_STATUS.ABORTED;
    listeners.clear();
  }

  return {
    on,
    start,
    submitAnswer,
    nextTurn,
    destroy,
    getCurrentTurn,
    getScoreboard,
    getRanking,
    getResults,
    getHistory: () => history.map(entry => ({ ...entry })),
    getState: () => ({ ...state, totalPlayers: playerStats.length })
  };
}
