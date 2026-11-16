// Tela da partida: pergunta, alternativas, cronômetro, placar e feedback.
// Este arquivo só DESENHA. Quem decide as regras é o motor (js/core/game.js);
// quem liga um ao outro é js/match-controller.js.
//
// Importante: nomes de jogadores são digitados pelo usuário, por isso sempre
// usamos textContent (e nunca innerHTML) para exibi-los com segurança.
import { QUESTION_TYPES } from "../core/questions.js";
import { clearCountryCard, countryIdFor, initCountryInfo, showCountryCard } from "../country-info.js";

const DIFFICULTY_LABELS = { easy: "Fácil", medium: "Média", hard: "Difícil" };
const CATEGORY_LABELS = {
  countries: "Países", capitals: "Capitais", continents: "Continentes", borders: "Fronteiras",
  oceans: "Oceanos", location: "Localização", culture: "Cultura", physical: "Geografia física"
};
const OPTION_LETTERS = "ABCDEF";
const $ = id => document.getElementById(id);

// Marcador usado só se nenhum mapa for fornecido (o mapa de verdade está em js/map/world-map.js).
// Um "mapRenderer" é qualquer objeto com render(container, question, onSelect)
// e, opcionalmente, showResult(container, feedback, chosenAnswer).
function createPlaceholderMapRenderer() {
  return {
    render(container) {
      const box = document.createElement("div");
      box.className = "map-placeholder";
      const text = document.createElement("p");
      text.className = "map-placeholder-text";
      text.textContent = "O mapa não está disponível nesta tela.";
      box.append(text);
      container.replaceChildren(box);
    }
  };
}

export function createQuizScreen({ onAnswer, onNext, onQuit, mapRenderer = createPlaceholderMapRenderer() }) {
  const ui = {
    counter: $("quiz-counter"), progressBar: $("quiz-progress-bar"),
    timer: $("quiz-timer"), timerValue: $("timer-value"),
    timerBar: $("timer-bar"), timerFill: $("timer-bar-fill"),
    scoreboard: $("scoreboard"),
    turnPlayer: $("turn-player"), difficulty: $("question-difficulty"),
    category: $("question-category"), points: $("question-points"),
    card: $("question-card"), text: $("question-text"), options: $("options"), map: $("map-challenge"),
    flag: $("flag-challenge"),
    feedback: $("feedback-card"), feedbackIcon: $("feedback-icon"),
    feedbackTitle: $("feedback-title"), feedbackPoints: $("feedback-points"),
    feedbackAnswer: $("feedback-answer"), feedbackExplanation: $("feedback-explanation"),
    feedbackTotal: $("feedback-total"), next: $("next-turn"), countryCard: $("country-card")
  };
  let currentQuestion = null;
  initCountryInfo(); // pré-carrega os dados dos países

  ui.next.addEventListener("click", () => onNext());
  $("quit-match").addEventListener("click", () => onQuit());

  function renderScoreboard(scoreboard) {
    ui.scoreboard.replaceChildren(...scoreboard.map(player => {
      const chip = document.createElement("div");
      chip.className = `score-chip${player.isCurrent ? " current" : ""}`;
      const name = document.createElement("span");
      name.className = "score-name";
      name.textContent = player.name;
      const score = document.createElement("span");
      score.className = "score-value";
      score.textContent = `${player.score} pts`;
      chip.append(name, score);
      return chip;
    }));
  }

  function renderTurn(turn, scoreboard) {
    const { question } = turn;
    currentQuestion = question;

    ui.counter.textContent = `Pergunta ${turn.questionNumber} de ${turn.totalQuestions}`;
    ui.progressBar.style.width = `${(turn.questionNumber / turn.totalQuestions) * 100}%`;
    ui.turnPlayer.textContent = `Vez de ${turn.player.name}`;
    ui.difficulty.textContent = DIFFICULTY_LABELS[question.difficulty] ?? question.difficulty;
    ui.difficulty.className = `tag ${question.difficulty}`;
    ui.category.textContent = CATEGORY_LABELS[question.category] ?? question.category;
    ui.points.textContent = `${question.points} pts`;
    ui.text.textContent = question.text;
    renderScoreboard(scoreboard);

    // Cronômetro volta ao início, sem animação, para o novo turno.
    ui.timerFill.style.transition = "none";
    ui.timerFill.style.width = "100%";
    void ui.timerFill.offsetWidth; // força o navegador a aplicar o reset antes de reativar a animação
    ui.timerFill.style.transition = "";
    ui.timerValue.textContent = String(turn.secondsPerQuestion);
    ui.timer.classList.remove("warn", "danger");
    ui.timerBar.classList.remove("warn", "danger");

    ui.feedback.hidden = true;
    clearCountryCard(ui.countryCard);
    ui.card.classList.toggle("has-map", question.type === QUESTION_TYPES.MAP); // compacta o cartão para o mapa caber na tela
    ui.flag.hidden = question.type !== QUESTION_TYPES.FLAG;
    if (question.type === QUESTION_TYPES.FLAG) {
      const image = document.createElement("img");
      image.className = "flag-image";
      image.src = `https://flagcdn.com/w640/${question.flagCode}.png`;
      image.alt = "Bandeira do país — identifique o país";
      image.loading = "eager";
      image.onerror = () => { image.alt = "Não foi possível carregar a bandeira. Verifique a conexão."; };
      ui.flag.replaceChildren(image);
    } else {
      ui.flag.replaceChildren();
    }

    if (question.type === QUESTION_TYPES.MULTIPLE_CHOICE || question.type === QUESTION_TYPES.FLAG) {
      ui.map.hidden = true;
      ui.options.hidden = false;
      ui.options.replaceChildren(...question.options.map((optionText, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "option";
        const letter = document.createElement("span");
        letter.className = "option-letter";
        letter.textContent = OPTION_LETTERS[index];
        const label = document.createElement("span");
        label.textContent = optionText;
        button.append(letter, label);
        button.addEventListener("click", () => {
          // Trava as alternativas na hora, para não haver clique duplo.
          ui.options.querySelectorAll(".option").forEach(option => { option.disabled = true; });
          onAnswer({ optionIndex: index });
        });
        return button;
      }));
    } else {
      ui.options.hidden = true;
      ui.options.replaceChildren();
      ui.map.hidden = false;
      mapRenderer.render(ui.map, question, answer => onAnswer(answer));
    }
  }

  // Chamado a cada segundo pelo motor.
  function renderTick(remaining, total) {
    ui.timerValue.textContent = String(Math.max(0, remaining));
    // A barra anda até o valor do PRÓXIMO segundo, assim ela chega a zero junto com o relógio.
    ui.timerFill.style.width = `${(Math.max(0, remaining - 1) / total) * 100}%`;
    const warn = remaining <= 10 && remaining > 5;
    const danger = remaining <= 5;
    ui.timer.classList.toggle("warn", warn);
    ui.timer.classList.toggle("danger", danger);
    ui.timerBar.classList.toggle("warn", warn);
    ui.timerBar.classList.toggle("danger", danger);
  }

  function renderFeedback(feedback, { chosenAnswer, nextLabel, scoreboard }) {
    const isMultipleChoice = currentQuestion?.type === QUESTION_TYPES.MULTIPLE_CHOICE
      || currentQuestion?.type === QUESTION_TYPES.FLAG;
    const view = {
      correct: { css: "ok", icon: "✓", title: "Acertou!" },
      wrong: { css: "bad", icon: "✕", title: "Errou" },
      timeout: { css: "timeout", icon: "◷", title: "Tempo esgotado" }
    }[feedback.result];

    ui.feedback.className = `feedback-card ${view.css}`;
    ui.feedbackIcon.textContent = view.icon;
    ui.feedbackTitle.textContent = view.title;
    ui.feedbackPoints.textContent = feedback.pointsEarned > 0
      ? `+${feedback.pointsEarned} pontos` : "0 pontos";

    const correct = feedback.correctAnswer;
    const correctText = isMultipleChoice ? correct.text : (correct.name ?? correct.countryId);
    ui.feedbackAnswer.textContent = feedback.isCorrect
      ? `Resposta correta: ${correctText}`
      : `A resposta correta era: ${correctText}`;

    ui.feedbackExplanation.hidden = !feedback.explanation;
    ui.feedbackExplanation.textContent = feedback.explanation ?? "";
    ui.feedbackTotal.textContent = `${feedback.playerName} tem agora ${feedback.totalScore} pontos.`;
    ui.next.firstChild.textContent = `${nextLabel} `;

    // Marca as alternativas: certa em verde, escolhida errada em vermelho.
    if (isMultipleChoice) {
      [...ui.options.children].forEach((button, index) => {
        button.disabled = true;
        if (index === correct.optionIndex) button.classList.add("correct");
        else if (chosenAnswer && index === chosenAnswer.optionIndex) button.classList.add("wrong");
        else button.classList.add("dim");
      });
    } else {
      mapRenderer.showResult?.(ui.map, feedback, chosenAnswer);
    }

    renderScoreboard(scoreboard);
    ui.feedback.hidden = false;
    showCountryCard(ui.countryCard, countryIdFor(currentQuestion));
    ui.next.focus({ preventScroll: true });
    ui.feedback.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return { renderTurn, renderTick, renderFeedback, renderScoreboard };
}
