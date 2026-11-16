export function addPlayer(players) {
  if (players.length >= 4) return players;
  return [...players, `Jogador ${players.length + 1}`];
}

export function removePlayer(players, index) {
  if (players.length <= 1) return players;
  return players.filter((_, current) => current !== index);
}

export function getPlayers(players) {
  const list = players.map(name => name.trim());
  const valid = list.every(Boolean);
  const normalized = list.map(name => name.toLocaleLowerCase("pt-BR"));
  const unique = new Set(normalized).size === normalized.length;
  return { valid: valid && unique, list, duplicate: !unique };
}

export function updatePlayerCount(counter, addButton, count) {
  counter.textContent = `${count} / 4`;
  addButton.disabled = count >= 4;
  addButton.textContent = count >= 4 ? "Limite de 4 jogadores atingido" : "＋ Adicionar jogador";
}