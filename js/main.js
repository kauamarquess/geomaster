import { showScreen } from "./utils/helpers.js";
import { addPlayer, getPlayers, removePlayer, updatePlayerCount } from "./core/players.js";

// Avisa o index.html que o main.js carregou (veja o verificador no final do index.html).
window.__geomasterReady = true;

const DEV_MODE = new URLSearchParams(window.location.search).get("dev") === "1";
let controller = null; // js/match-controller.js, carregado no final deste arquivo
let startupProblem = null; // texto explicando por que a partida não pode começar

// Mostra uma faixa vermelha no topo da página com o problema e o que fazer.
function showProblemBanner(message) {
  let banner = document.getElementById("startup-problem");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "startup-problem";
    banner.setAttribute("role", "alert");
    banner.style.cssText = "background:#fff1f1;color:#9b1c1c;border-bottom:2px solid #f5b5b5;padding:14px 20px;"
      + "font:600 13px/1.6 Inter,system-ui,sans-serif;text-align:center";
    document.body.prepend(banner);
  }
  banner.textContent = message;
}

const playerList = document.querySelector("#player-list");
const addButton = document.querySelector("#add-player");
const counter = document.querySelector("#player-counter");
const DEFAULT_HINT = "Você pode jogar sozinho ou chamar até três amigos.";
let players = ["Jogador 1"];

// No modo de teste (?dev=1) aparece um selo na barra superior.
const devBadge = document.querySelector("#dev-badge");
if (devBadge) devBadge.hidden = !DEV_MODE;

function renderPlayers() {
  playerList.innerHTML = "";
  players.forEach((name, index) => {
    const field = document.createElement("label");
    field.className = "player-field";
    const number = document.createElement("span");
    number.className = "player-number";
    number.textContent = String(index + 1);
    const input = document.createElement("input");
    input.className = "player-input";
    input.maxLength = 18;
    input.placeholder = `Nome do jogador ${index + 1}`;
    input.value = name;
    input.setAttribute("aria-label", `Nome do jogador ${index + 1}`);
    input.addEventListener("input", () => { players[index] = input.value; });
    field.append(number, input);
    if (players.length > 1) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-player";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remover jogador ${index + 1}`);
      remove.addEventListener("click", () => { players = removePlayer(players, index); renderPlayers(); });
      field.append(remove);
    } else {
      const status = document.createElement("span");
      status.className = "player-status";
      status.textContent = "●";
      field.append(status);
    }
    playerList.append(field);
  });
  updatePlayerCount(counter, addButton, players.length);
}

document.querySelector("#start-button").addEventListener("click", () => showScreen("setup-screen"));
document.querySelector("#story-button").addEventListener("click", () => { window.location.href = "story/web/index.html"; });
document.querySelector("#how-button").addEventListener("click", () => showScreen("how-screen"));
// Voltar ao início: se houver partida em andamento, pede confirmação antes.
document.querySelectorAll("[data-home]").forEach(button => button.addEventListener("click", event => {
  event.preventDefault();
  if (!controller || controller.leaveMatch()) showScreen("home-screen");
}));
document.querySelectorAll("[data-start]").forEach(button => button.addEventListener("click", () => showScreen("setup-screen")));
addButton.addEventListener("click", () => { players = addPlayer(players); renderPlayers(); });

const beginButton = document.querySelector("#begin-button");
const setupHint = document.querySelector("#setup-hint");

function showSetupHint(text, isError) {
  setupHint.textContent = text;
  setupHint.style.color = isError ? "#dc4b4b" : "";
}

beginButton.addEventListener("click", async () => {
  const names = getPlayers(players);
  if (!names.valid) {
    const hasEmpty = names.list.some(name => name === "");
    showSetupHint(hasEmpty
      ? "Preencha todos os nomes antes de continuar."
      : "Cada jogador precisa ter um nome diferente.", true);
    return;
  }
  sessionStorage.setItem("geomaster.players", JSON.stringify(names.list));

  if (!controller) {
    showSetupHint(startupProblem ?? "O jogo ainda está carregando. Tente novamente em instantes.", true);
    return;
  }
  beginButton.disabled = true;
  showSetupHint("Preparando a partida…", false);
  const result = await controller.startMatch(names.list);
  beginButton.disabled = false;
  showSetupHint(result.ok ? DEFAULT_HINT : result.message, !result.ok);
});

renderPlayers();

// Carrega a parte da partida por último. Se algo estiver errado (arquivo faltando ou
// desatualizado), os botões de navegação continuam funcionando e o problema aparece na tela.
const REQUIRED_ELEMENT_IDS = [
  "quiz-screen", "results-screen", "quit-match", "quiz-counter", "quiz-progress-bar", "quiz-timer",
  "timer-value", "timer-bar", "timer-bar-fill", "scoreboard", "turn-player", "question-difficulty",
  "question-category", "question-points", "question-text", "options", "map-challenge", "feedback-card",
  "feedback-icon", "feedback-title", "feedback-points", "feedback-answer", "feedback-explanation",
  "feedback-total", "next-turn", "results-title", "results-subtitle", "ranking",
  "replay-button", "new-match-button", "end-button", "menu-message"
];

try {
  const missing = REQUIRED_ELEMENT_IDS.filter(id => !document.getElementById(id));
  if (missing.length > 0) {
    throw new Error(`o index.html está desatualizado (faltam: ${missing.slice(0, 3).join(", ")}…)`);
  }
  if (!window.L) throw new Error("o Leaflet não foi carregado (pasta assets/vendor/leaflet)");
  controller = await import("./match-controller.js");
} catch (error) {
  console.error("GeoMaster: falha ao carregar a partida.", error);
  startupProblem = `Não foi possível carregar a partida: ${error.message}. `
    + "Confira se TODOS os arquivos do ZIP da Etapa 4 foram copiados (principalmente index.html e a pasta js) "
    + "e recarregue a página com Ctrl+F5.";
  showProblemBanner(startupProblem);
}
