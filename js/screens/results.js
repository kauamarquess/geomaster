// Tela de resultados: classificação final com acertos, erros e não respondidas.
const $ = id => document.getElementById(id);

function plural(count, singular, pluralForm) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

// ["Ana"] -> "Ana" | ["Ana","Bia"] -> "Ana e Bia" | 3+ -> "Ana, Bia e Caio"
function joinNames(names) {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} e ${names[names.length - 1]}`;
}

export function renderResults(results) {
  const { ranking, winners } = results;
  const title = $("results-title");
  const subtitle = $("results-subtitle");

  if (ranking.length === 1) {
    title.textContent = "Partida concluída!";
    subtitle.textContent = `${ranking[0].name} fez ${plural(ranking[0].score, "ponto", "pontos")}.`;
  } else if (winners.length === 1) {
    title.textContent = `${winners[0].name} venceu!`;
    subtitle.textContent = `Com ${plural(winners[0].score, "ponto", "pontos")} e ${plural(winners[0].correct, "acerto", "acertos")}.`;
  } else {
    title.textContent = "Empate!";
    subtitle.textContent = `${joinNames(winners.map(w => w.name))} dividem o primeiro lugar.`;
  }

  $("ranking").replaceChildren(...ranking.map((player, index) => {
    const row = document.createElement("article");
    row.className = `rank-row${player.position === 1 && ranking.length > 1 ? " first" : ""}`;
    row.style.animationDelay = `${index * 90}ms`;

    const position = document.createElement("div");
    position.className = "rank-position";
    position.textContent = `${player.position}º`;

    const info = document.createElement("div");
    const name = document.createElement("div");
    name.className = "rank-name";
    name.textContent = player.name;
    if (player.tied) {
      const badge = document.createElement("span");
      badge.className = "tie-badge";
      badge.textContent = "Empate";
      name.append(badge);
    }
    const stats = document.createElement("div");
    stats.className = "rank-stats";
    [
      `✓ ${plural(player.correct, "acerto", "acertos")}`,
      `✕ ${plural(player.wrong, "erro", "erros")}`,
      `◷ ${plural(player.unanswered, "não respondida", "não respondidas")}`
    ].forEach(text => {
      const item = document.createElement("span");
      item.textContent = text;
      stats.append(item);
    });
    info.append(name, stats);

    const score = document.createElement("div");
    score.className = "rank-score";
    const value = document.createElement("strong");
    value.textContent = String(player.score);
    const label = document.createElement("span");
    label.textContent = "PONTOS";
    score.append(value, label);

    row.append(position, info, score);
    return row;
  }));
}
