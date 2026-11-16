// Controlador da partida: a "ponte" entre o motor (js/core) e as telas (js/screens).
//
//   motor  --eventos-->  controlador  --desenha-->  telas
//   telas  --cliques-->  controlador  --chama---->  motor
//
// Assim o motor não sabe nada sobre HTML e as telas não sabem nada sobre regras.
import { showScreen } from "./utils/helpers.js";
import {
  QuestionBankError, createQuestionSelector, filterMapQuestions, loadQuestionBank
} from "./core/questions.js";
import { MapDataError, createMapChallengeRenderer, loadCountries } from "./map/world-map.js";
import { GAME_STATUS, createGame } from "./core/game.js";
import { createQuizScreen } from "./screens/quiz.js";
import { renderResults } from "./screens/results.js";
import { bindPostGameMenu, showMenuMessage } from "./screens/menu.js";

// Modo de teste: abra o jogo com ?dev=1 no endereço para usar o banco provisório
// (data/questions.dev.json) para testar os três tipos de questão.
export const DEV_MODE = new URLSearchParams(window.location.search).get("dev") === "1";
const BANK_URL = DEV_MODE ? "./data/questions.dev.json" : "./data/questions.json";
const STORAGE_KEY = DEV_MODE ? "geomaster.usedQuestions.dev" : "geomaster.usedQuestions";

let selector = null;       // sorteador (guarda quais perguntas já saíram)
let game = null;           // motor da partida atual
let matchPlayers = [];     // nomes, para "Jogar novamente"
let starting = false;      // evita iniciar duas partidas ao mesmo tempo

const quiz = createQuizScreen({
  onAnswer: answer => { game?.submitAnswer(answer); },
  onNext: () => { game?.nextTurn(); },
  onQuit: () => { if (leaveMatch()) showScreen("home-screen"); },
  mapRenderer: createMapChallengeRenderer()
});

bindPostGameMenu({
  onReplay: async () => {
    showMenuMessage("");
    const result = await startMatch(matchPlayers);
    if (!result.ok) showMenuMessage(result.message);
  },
  onNewMatch: () => {
    showMenuMessage("");
    showScreen("setup-screen"); // os nomes já digitados continuam preenchidos
  },
  onEnd: () => {
    showMenuMessage("");
    showScreen("home-screen");
  }
});

// Transforma erros técnicos em mensagens que o jogador entende.
function friendlyMessage(error) {
  if (error instanceof QuestionBankError && error.code === "INSUFFICIENT_QUESTIONS") {
    return "O banco de perguntas ainda não tem perguntas suficientes para uma partida "
      + "(são necessárias 3 de múltipla escolha, 3 de mapa e 4 de bandeiras). Confira se o banco atualizado foi copiado por completo. "
      + "Para testar agora, abra o jogo com ?dev=1 no final do endereço (exemplo: http://127.0.0.1:5500/?dev=1).";
  }
  if (error instanceof MapDataError) {
    return `${error.message} Confira se o arquivo data/geojson/countries.geojson existe e recarregue com Ctrl+F5.`;
  }
  if (error instanceof QuestionBankError) return `Problema no banco de perguntas: ${error.message}`;
  if (error instanceof TypeError || /carregar/i.test(error?.message ?? "")) {
    return "Não foi possível carregar as perguntas. Abra o jogo por um servidor local (Live Server) e tente de novo.";
  }
  return `Não foi possível iniciar a partida: ${error?.message ?? error}`;
}

function nextButtonLabel(feedback, scoreboard) {
  if (feedback.isLastQuestion) return "Ver resultado final";
  if (scoreboard.length === 1) return "Próxima pergunta";
  const next = scoreboard[(feedback.playerIndex + 1) % scoreboard.length];
  return `Passar para ${next.name}`;
}

function connectGame(newGame) {
  newGame.on("turnStart", turn => quiz.renderTurn(turn, newGame.getScoreboard()));
  newGame.on("tick", ({ remaining }) => quiz.renderTick(remaining, newGame.getState().secondsPerQuestion));
  newGame.on("feedback", feedback => {
    const scoreboard = newGame.getScoreboard();
    const lastEntry = newGame.getHistory().at(-1);
    quiz.renderFeedback(feedback, {
      chosenAnswer: lastEntry?.answer ?? null,
      nextLabel: nextButtonLabel(feedback, scoreboard),
      scoreboard
    });
  });
  newGame.on("end", results => {
    renderResults(results);
    showScreen("results-screen");
  });
}

// Inicia uma partida com os nomes informados.
// Devolve { ok: true } ou { ok: false, message } para a tela mostrar o problema.
export async function startMatch(playerNames) {
  if (starting) return { ok: false, message: "Aguarde: a partida já está sendo preparada." };
  starting = true;
  try {
    if (!selector) {
      // Banco de perguntas e dados do mapa carregam juntos.
      const [bank, countries] = await Promise.all([loadQuestionBank(BANK_URL), loadCountries()]);
      // Pergunta de mapa com país inexistente no GeoJSON seria impossível de acertar: fica de fora.
      const { questions: playable, removed } = filterMapQuestions(bank.questions, countries.ids);
      if (removed.length > 0) {
        console.warn(`GeoMaster: ${removed.length} pergunta(s) de mapa ignorada(s) por apontar para país inexistente no GeoJSON.`, removed);
      }
      selector = createQuestionSelector(playable, { storageKey: STORAGE_KEY });
    }
    const questions = selector.drawMatch();
    const newGame = createGame({ players: playerNames, questions });

    game?.destroy(); // encerra a partida anterior, se houver
    game = newGame;
    matchPlayers = [...playerNames];
    connectGame(game);

    showScreen("quiz-screen");
    game.start();
    return { ok: true };
  } catch (error) {
    console.error("Falha ao iniciar a partida:", error);
    return { ok: false, message: friendlyMessage(error) };
  } finally {
    starting = false;
  }
}

export function isMatchInProgress() {
  const status = game?.getState().status;
  return status === GAME_STATUS.AWAITING_ANSWER || status === GAME_STATUS.FEEDBACK;
}

// Pede confirmação antes de abandonar uma partida em andamento.
// Devolve true se pode sair (e já encerra a partida), false se o jogador desistiu de sair.
export function leaveMatch() {
  if (!isMatchInProgress()) return true;
  if (!window.confirm("Sair da partida? O progresso desta partida será perdido.")) return false;
  game.destroy();
  return true;
}

// Aviso do navegador se a aba for fechada no meio da partida.
window.addEventListener("beforeunload", event => {
  if (isMatchInProgress()) {
    event.preventDefault();
    event.returnValue = "";
  }
});
