// Regras de pontuação, correção de respostas e ranking.
// Este arquivo não mexe na tela: só recebe dados e devolve resultados.
import { QUESTION_TYPES } from "./questions.js";

export const POINTS_BY_DIFFICULTY = Object.freeze({
  easy: 10,
  medium: 20,
  hard: 30
});

// Regras fixas da partida (definidas no planejamento do projeto).
export const MATCH_RULES = Object.freeze({
  minPlayers: 1,
  maxPlayers: 4,
  questionsPerMatch: 10,
  secondsPerQuestion: 30
});

// Os três resultados possíveis de uma pergunta.
export const RESULT = Object.freeze({
  CORRECT: "correct",
  WRONG: "wrong",
  TIMEOUT: "timeout" // tempo esgotado = "não respondida"
});

export function createGameState(overrides = {}) {
  return {
    questionsPerMatch: MATCH_RULES.questionsPerMatch,
    secondsPerQuestion: MATCH_RULES.secondsPerQuestion,
    currentQuestionIndex: 0,
    currentPlayerIndex: 0,
    status: "setup",
    ...overrides
  };
}

export function pointsForDifficulty(difficulty) {
  return POINTS_BY_DIFFICULTY[difficulty] ?? 0;
}

// Placar individual de um jogador.
export function createPlayerStats(name, index) {
  return { index, name, score: 0, correct: 0, wrong: 0, unanswered: 0 };
}

// A resposta tem o formato certo para esse tipo de pergunta?
//   múltipla escolha -> { optionIndex: 0..n-1 }
//   desafio no mapa  -> { countryId: "BRA" }
export function isAnswerValid(question, answer) {
  if (!answer || typeof answer !== "object") return false;
  if (question.type === QUESTION_TYPES.MULTIPLE_CHOICE || question.type === QUESTION_TYPES.FLAG) {
    return Number.isInteger(answer.optionIndex)
      && answer.optionIndex >= 0
      && answer.optionIndex < question.options.length;
  }
  if (question.type === QUESTION_TYPES.MAP) {
    return typeof answer.countryId === "string" && answer.countryId.trim() !== "";
  }
  return false;
}

// Corrige a resposta. Sem resposta (null) significa tempo esgotado.
export function evaluateAnswer(question, answer) {
  if (answer === null || answer === undefined) return RESULT.TIMEOUT;
  if (question.type === QUESTION_TYPES.MULTIPLE_CHOICE || question.type === QUESTION_TYPES.FLAG) {
    return answer.optionIndex === question.correctIndex ? RESULT.CORRECT : RESULT.WRONG;
  }
  // Mapa: o identificador clicado precisa ser exatamente o da pergunta.
  return answer.countryId.trim() === question.targetId ? RESULT.CORRECT : RESULT.WRONG;
}

// Atualiza o placar do jogador e devolve os pontos ganhos.
// Pontos só são concedidos em resposta correta.
export function applyResult(stats, result, difficulty) {
  if (result === RESULT.CORRECT) {
    const points = pointsForDifficulty(difficulty);
    stats.score += points;
    stats.correct += 1;
    return points;
  }
  if (result === RESULT.WRONG) stats.wrong += 1;
  else stats.unanswered += 1;
  return 0;
}

// Monta o ranking: mais pontos primeiro; empate de pontos -> mais acertos.
// Se pontos E acertos forem iguais, os jogadores dividem a mesma posição (empate).
export function buildRanking(statsList) {
  const sorted = [...statsList].sort((a, b) =>
    b.score - a.score || b.correct - a.correct || a.index - b.index);

  let position = 0;
  const ranking = sorted.map((player, i) => {
    const previous = sorted[i - 1];
    const sameAsPrevious = previous
      && previous.score === player.score
      && previous.correct === player.correct;
    if (!sameAsPrevious) position = i + 1;
    return { ...player, position, tied: false };
  });

  // Marca quem está empatado com outra pessoa.
  ranking.forEach(entry => {
    entry.tied = ranking.filter(other => other.position === entry.position).length > 1;
  });
  return ranking;
}
