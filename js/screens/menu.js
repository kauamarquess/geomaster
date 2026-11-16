// Menu pós-partida: jogar novamente, nova partida ou encerrar.
const $ = id => document.getElementById(id);

export function bindPostGameMenu({ onReplay, onNewMatch, onEnd }) {
  const replay = $("replay-button");
  replay.addEventListener("click", async () => {
    replay.disabled = true; // evita cliques repetidos enquanto a nova partida é preparada
    try { await onReplay(); } finally { replay.disabled = false; }
  });
  $("new-match-button").addEventListener("click", () => onNewMatch());
  $("end-button").addEventListener("click", () => onEnd());
}

// Mostra (ou limpa) uma mensagem de erro abaixo dos botões.
export function showMenuMessage(text = "") {
  const message = $("menu-message");
  message.textContent = text;
  message.hidden = text === "";
}
