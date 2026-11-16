// Banco de perguntas: carregamento, validação e sorteio sem repetição.
// Este arquivo não mexe na tela e não depende do navegador (exceto o fetch em loadQuestions).

export const QUESTION_TYPES = Object.freeze({
  MULTIPLE_CHOICE: "multiple_choice",
  MAP: "map",
  FLAG: "flag"
});

export const DIFFICULTIES = Object.freeze(["easy", "medium", "hard"]);

// Categorias previstas no planejamento (países, capitais, continentes, fronteiras,
// oceanos, localização, cultura e geografia física).
export const CATEGORIES = Object.freeze([
  "countries", "capitals", "continents", "borders",
  "oceans", "location", "culture", "physical", "flags"
]);

// Composição de cada partida: 3 de múltipla escolha + 3 no mapa + 4 de bandeiras.
export const MATCH_COMPOSITION = Object.freeze({
  [QUESTION_TYPES.MULTIPLE_CHOICE]: 3,
  [QUESTION_TYPES.MAP]: 3,
  [QUESTION_TYPES.FLAG]: 4
});

export const MIN_OPTIONS = 2;
export const MAX_OPTIONS = 6;

// Erro específico do banco (tem um "code" para a interface saber o que aconteceu).
export class QuestionBankError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "QuestionBankError";
    this.code = code;
    this.details = details;
  }
}

const isNonEmptyString = value => typeof value === "string" && value.trim() !== "";

// Deixa o texto "comparável": sem acentos, sem maiúsculas, sem pontuação.
// Usado para descobrir perguntas duplicadas.
export function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

// Embaralha uma cópia da lista (algoritmo Fisher-Yates).
export function shuffle(list, random = Math.random) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// Devolve uma lista de problemas. Lista vazia = pergunta válida.
export function validateQuestion(question) {
  if (question === null || typeof question !== "object" || Array.isArray(question)) {
    return ["a pergunta precisa ser um objeto"];
  }
  const problems = [];

  if (!isNonEmptyString(question.id)) problems.push("id ausente ou vazio");
  if (!Object.values(QUESTION_TYPES).includes(question.type)) {
    problems.push(`tipo inválido: ${String(question.type)}`);
  }
  if (!DIFFICULTIES.includes(question.difficulty)) {
    problems.push(`dificuldade inválida: ${String(question.difficulty)}`);
  }
  if (!CATEGORIES.includes(question.category)) {
    problems.push(`categoria inválida: ${String(question.category)}`);
  }
  if (!isNonEmptyString(question.text)) problems.push("enunciado ausente ou vazio");
  if (question.explanation !== undefined && typeof question.explanation !== "string") {
    problems.push("a explicação, quando existe, precisa ser texto");
  }

  if (question.type === QUESTION_TYPES.MULTIPLE_CHOICE) {
    const options = question.options;
    if (!Array.isArray(options) || options.length < MIN_OPTIONS || options.length > MAX_OPTIONS) {
      problems.push(`as alternativas precisam ser uma lista de ${MIN_OPTIONS} a ${MAX_OPTIONS} itens`);
    } else {
      if (!options.every(isNonEmptyString)) problems.push("há alternativa vazia ou que não é texto");
      else if (new Set(options.map(normalizeText)).size !== options.length) {
        problems.push("há alternativas repetidas");
      }
      if (!Number.isInteger(question.correctIndex)
        || question.correctIndex < 0 || question.correctIndex >= options.length) {
        problems.push("correctIndex precisa apontar para uma alternativa existente");
      }
    }
  }

  if (question.type === QUESTION_TYPES.FLAG) {
    if (!/^[a-z]{2}$/.test(question.flagCode ?? "")) {
      problems.push("flagCode precisa ser um código ISO de duas letras minúsculas");
    }
    if (!isNonEmptyString(question.targetId)) problems.push("targetId ausente ou vazio");
    if (!isNonEmptyString(question.targetName)) problems.push("targetName ausente ou vazio");
    if (!Array.isArray(question.options) || question.options.length !== 4
      || !question.options.every(isNonEmptyString)) {
      problems.push("a questão de bandeira precisa ter quatro países nas alternativas");
    } else if (!Number.isInteger(question.correctIndex)
      || question.correctIndex < 0 || question.correctIndex >= question.options.length) {
      problems.push("correctIndex inválido para a questão de bandeira");
    }
  }

  if (question.type === QUESTION_TYPES.MAP) {
    if (!isNonEmptyString(question.targetId)) {
      problems.push("targetId (identificador do país no GeoJSON) ausente ou vazio");
    }
    // targetName é opcional: nome do país para mostrar no feedback.
    if (question.targetName !== undefined && !isNonEmptyString(question.targetName)) {
      problems.push("targetName, quando existe, precisa ser um texto não vazio");
    }
  }
  return problems;
}

function countBy(list, key) {
  return list.reduce((acc, item) => {
    acc[item[key]] = (acc[item[key]] ?? 0) + 1;
    return acc;
  }, {});
}

// Valida o banco inteiro. Perguntas com problema NÃO derrubam o jogo:
// ficam de fora (em "rejected") e o relatório diz o motivo.
export function validateBank(raw) {
  const list = Array.isArray(raw) ? raw : raw?.questions;
  if (!Array.isArray(list)) {
    throw new QuestionBankError(
      "INVALID_BANK_FORMAT",
      "O banco precisa ser uma lista de perguntas ou um objeto com a chave \"questions\"."
    );
  }

  const questions = [];
  const rejected = [];
  const seenIds = new Set();
  const seenTexts = new Map();

  list.forEach((question, index) => {
    const problems = validateQuestion(question);
    let textKey = null;
    if (problems.length === 0) {
      if (seenIds.has(question.id)) problems.push(`id duplicado: ${question.id}`);
      textKey = `${question.type}|${normalizeText(question.text)}`;
      if (seenTexts.has(textKey)) {
        problems.push(`enunciado duplicado (igual ao da pergunta ${seenTexts.get(textKey)})`);
      }
    }
    if (problems.length > 0) {
      rejected.push({ index, id: question?.id ?? null, problems });
      return;
    }
    seenIds.add(question.id);
    seenTexts.set(textKey, question.id);
    questions.push(question);
  });

  return {
    questions,
    rejected,
    stats: {
      total: list.length,
      valid: questions.length,
      rejected: rejected.length,
      byType: countBy(questions, "type"),
      byDifficulty: countBy(questions, "difficulty"),
      byCategory: countBy(questions, "category")
    }
  };
}

// Remove perguntas de mapa cujo "targetId" não existe no GeoJSON (seriam impossíveis de acertar).
// validIds é um Set com os identificadores dos países (properties.id do GeoJSON).
export function filterMapQuestions(questions, validIds) {
  const kept = [];
  const removed = [];
  for (const question of questions) {
    if (question.type === QUESTION_TYPES.MAP && !validIds.has(question.targetId)) {
      removed.push({ id: question.id, targetId: question.targetId });
    } else {
      kept.push(question);
    }
  }
  return { questions: kept, removed };
}

// Lê data/questions.json e devolve a lista bruta de perguntas.
// Aceita tanto uma lista pura quanto { "questions": [...] } (formato atual do arquivo).
export async function loadQuestions(url = "./data/questions.json") {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Não foi possível carregar questions.json.");
  const data = await response.json();
  const list = Array.isArray(data) ? data : data?.questions;
  if (!Array.isArray(list)) {
    throw new QuestionBankError(
      "INVALID_BANK_FORMAT",
      "O banco de perguntas precisa ser uma lista JSON ou conter a chave \"questions\"."
    );
  }
  return list;
}

// Carrega E valida. É a função que o jogo deve usar.
export async function loadQuestionBank(url) {
  const bank = validateBank(await loadQuestions(url));
  if (bank.rejected.length > 0) {
    console.warn(`GeoMaster: ${bank.rejected.length} pergunta(s) inválida(s) ignorada(s).`, bank.rejected);
  }
  return bank;
}

// Escolhe "n" perguntas misturando as dificuldades (ex.: 2 fáceis, 2 médias, 1 difícil).
function pickBalanced(list, n, random) {
  if (n <= 0) return [];
  const buckets = DIFFICULTIES.map(level => shuffle(list.filter(q => q.difficulty === level), random))
    .filter(bucket => bucket.length > 0);
  const order = shuffle(buckets, random);
  const picked = [];
  while (picked.length < n && order.some(bucket => bucket.length > 0)) {
    for (const bucket of order) {
      if (picked.length >= n) break;
      if (bucket.length > 0) picked.push(bucket.shift());
    }
  }
  return picked;
}

// Guarda os ids já usados. Prefere localStorage; se não existir, usa a memória.
function createDefaultStorage() {
  try {
    const storage = globalThis.localStorage;
    const probe = "geomaster.probe";
    storage.setItem(probe, "1");
    storage.removeItem(probe);
    return storage;
  } catch {
    const memory = new Map();
    return {
      getItem: key => (memory.has(key) ? memory.get(key) : null),
      setItem: (key, value) => memory.set(key, String(value))
    };
  }
}

// Sorteador de partidas: evita repetir perguntas enquanto houver outras disponíveis.
// Quando as de um tipo acabam, o ciclo recomeça (embaralha de novo).
export function createQuestionSelector(questions, options = {}) {
  const {
    random = Math.random,
    storage = createDefaultStorage(),
    storageKey = "geomaster.usedQuestions",
    composition = MATCH_COMPOSITION
  } = options;

  const knownIds = new Set(questions.map(q => q.id));
  let used = new Set();
  try {
    const saved = JSON.parse(storage.getItem(storageKey) ?? "[]");
    if (Array.isArray(saved)) used = new Set(saved.filter(id => knownIds.has(id)));
  } catch {
    used = new Set(); // dado salvo corrompido: começa do zero
  }

  const persist = () => {
    try { storage.setItem(storageKey, JSON.stringify([...used])); } catch { /* sem armazenamento: segue sem salvar */ }
  };

  function drawFromType(pool, needed) {
    const fresh = pool.filter(q => !used.has(q.id));
    let picked;
    if (fresh.length >= needed) {
      picked = pickBalanced(fresh, needed, random);
    } else {
      // Banco do tipo esgotado: usa as que sobraram e reinicia o ciclo.
      picked = [...fresh];
      pool.forEach(q => used.delete(q.id));
      const rest = pool.filter(q => !picked.includes(q));
      picked.push(...pickBalanced(rest, needed - picked.length, random));
    }
    picked.forEach(q => used.add(q.id));
    return picked;
  }

  return {
    // Devolve as perguntas de uma partida, em ordem aleatória.
    drawMatch() {
      const pools = Object.entries(composition).map(([type, needed]) => ({
        type, needed, pool: questions.filter(q => q.type === type)
      }));
      // Confere tudo ANTES de sortear, para não deixar o histórico pela metade.
      const missing = pools.filter(({ needed, pool }) => pool.length < needed);
      if (missing.length > 0) {
        throw new QuestionBankError(
          "INSUFFICIENT_QUESTIONS",
          "O banco não tem perguntas suficientes para montar uma partida.",
          { missing: missing.map(({ type, needed, pool }) => ({ type, needed, available: pool.length })) }
        );
      }
      const match = pools.flatMap(({ pool, needed }) => drawFromType(pool, needed));
      persist();
      return shuffle(match, random);
    },
    resetHistory() {
      used = new Set();
      persist();
    },
    getUsage() {
      return { used: used.size, total: questions.length };
    }
  };
}
