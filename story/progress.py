"""Progresso do jogador no Modo História: fases vencidas, poderes ganhos e salvamento em arquivo."""
import json
import os

STAGES_PER_COUNTRY = 10
MAX_EQUIPPED = 3
MAX_LEVEL = 5
SAVE_VERSION = 1


class Progress:
    def __init__(self, order):
        self.order = list(order)  # todos os países, na ordem do mundo
        self.cleared = set()      # {(país, fase)}
        self.powers = []
        self.levels = {}  # nível de cada poder: receber o mesmo poder de novo o fortalece
        self.equipped = []  # até MAX_EQUIPPED poderes levados para os combates

    def stages_done(self, country_id):
        """Quantas fases seguidas, a partir da 1, já foram vencidas."""
        n = 0
        while n < STAGES_PER_COUNTRY and (country_id, n + 1) in self.cleared:
            n += 1
        return n

    def is_complete(self, country_id):
        return self.stages_done(country_id) == STAGES_PER_COUNTRY

    def is_unlocked(self, country_id):
        i = self.order.index(country_id)
        return i == 0 or self.is_complete(self.order[i - 1])

    def current_country(self):
        return next((c for c in self.order if not self.is_complete(c)), self.order[-1])

    def completed_count(self, countries=None):
        return sum(self.is_complete(c) for c in (countries or self.order))

    def has_progress(self):
        return bool(self.cleared)

    def clear(self, country_id, stage):
        self.cleared.add((country_id, stage))

    def level(self, power_id):
        return self.levels.get(power_id, 1)

    def add_power(self, power_id):
        """Guarda o poder (e o equipa se houver vaga). Se já era seu, ele sobe de nível. Devolve o nível."""
        if power_id in self.powers:
            self.levels[power_id] = min(MAX_LEVEL, self.level(power_id) + 1)
        else:
            self.powers.append(power_id)
            self.levels[power_id] = 1
            if len(self.equipped) < MAX_EQUIPPED:
                self.equipped.append(power_id)
        return self.level(power_id)

    def toggle_equipped(self, power_id):
        """Equipa ou desequipa. Devolve False se não há vaga ou o poder não foi conquistado."""
        if power_id in self.equipped:
            self.equipped.remove(power_id)
            return True
        if power_id in self.powers and len(self.equipped) < MAX_EQUIPPED:
            self.equipped.append(power_id)
            return True
        return False

    def save(self, path):
        """Grava em arquivo. Devolve False (sem derrubar o jogo) se não for possível gravar."""
        data = {"version": SAVE_VERSION, "cleared": sorted(self.cleared), "powers": self.powers, "equipped": self.equipped, "levels": self.levels}
        try:
            tmp = f"{path}.tmp"
            with open(tmp, "w", encoding="utf-8") as file:
                json.dump(data, file)
            os.replace(tmp, path)  # troca atômica: um corte de energia não corrompe o save
            return True
        except OSError:
            return False

    @classmethod
    def load(cls, path, order):
        """Lê o save. Se o arquivo não existir ou estiver danificado, começa do zero."""
        progress = cls(order)
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
            known = set(order)
            progress.cleared = {(c, int(s)) for c, s in data["cleared"] if c in known and 1 <= int(s) <= STAGES_PER_COUNTRY}
            progress.powers = [p for p in data["powers"] if isinstance(p, str)]
            progress.levels = {p: min(MAX_LEVEL, max(1, int(n))) for p, n in data.get("levels", {}).items() if p in progress.powers}
            saved = data.get("equipped", progress.powers)  # saves antigos não tinham "equipped"
            progress.equipped = [p for p in saved if p in progress.powers][:MAX_EQUIPPED]
        except (OSError, ValueError, KeyError, TypeError):
            return cls(order)
        return progress

    @staticmethod
    def exists(path):
        return os.path.exists(path)
