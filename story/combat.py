"""Regras do combate do Modo História. Não usa pygame, então dá para testar sem abrir janela."""
import json
import random
from pathlib import Path

HERO_HP = 100
QUESTION_SECONDS = 30
DIFFICULTY_MULTIPLIER = {"easy": 1.0, "medium": 1.5, "hard": 2.0}


def progress(world, country_id, stage):
    """0 = primeira fase do primeiro país, perto de 1 = última fase do último país."""
    order = [c for region in world["order"] for c in region["countries"]]
    return (order.index(country_id) * 10 + stage - 1) / (len(order) * 10)


def difficulty_weights(p, stage=1):
    """A dificuldade sobe dentro de cada país e continua crescendo ao avançar pelo mundo."""
    local_progress = max(0.0, min(1.0, (int(stage) - 1) / 9))
    world_progress = max(0.0, min(1.0, float(p)))
    t = max(local_progress, world_progress)
    return {
        "easy": max(0.08, 1.05 - 1.15 * t),
        "medium": max(0.15, 0.25 + 1.0 * (1 - abs(2 * t - 1))),
        "hard": max(0.08, 0.08 + 1.15 * t),
    }


def monster_stats(stage, boss=False):
    hp, attack = 30 + 6 * (stage - 1), 8 + stage
    return (round(hp * 2.5), 15) if boss else (hp, attack)


def power_value(power):
    """Valor do poder já com o nível: +50% por nível acima do 1 (esquiva e redução de dano têm teto de 60%)."""
    value = power.get("value", 0) * (1 + 0.5 * (power.get("level", 1) - 1))
    return min(value, 0.6) if power["effect"] in ("dodge_chance", "damage_reduction") else value


def power_uses(power):
    """Usos por combate: +1 a cada 2 níveis."""
    return power.get("usesPerBattle", 0) + (power.get("level", 1) - 1) // 2


def hit_damage(difficulty, seconds_left, streak, total=QUESTION_SECONDS):
    """Dano base pela dificuldade, +até 50% por rapidez e +10% por acerto seguido (máx. 50%)."""
    speed = 0.5 * max(seconds_left, 0) / total
    return round(10 * DIFFICULTY_MULTIPLIER[difficulty] * (1 + speed + min(0.5, 0.1 * streak)))


class QuestionBank:
    """Perguntas de múltipla escolha, sorteadas do país, da região ou do mundo."""

    def __init__(self, questions, question_country, world, rng=None):
        self.rng = rng or random.Random()
        self.questions = [q for q in questions if q["type"] == "multiple_choice"]
        self.country_of = question_country
        self.region_of = {c: r["id"] for r in world["order"] for c in r["countries"]}
        self.by_id = {q["id"]: q for q in self.questions}

    def pick(self, country_id, p, used, stage=1):
        free = [q for q in self.questions if q["id"] not in used]
        mine = [q for q in free if self.country_of.get(q["id"]) == country_id]
        region = [q for q in free if self.region_of.get(self.country_of.get(q["id"])) == self.region_of.get(country_id)]
        # Prioriza conteúdo do país atual; recorre à região e ao mundo quando necessário.
        roll = self.rng.random()
        pools = [mine, region, free] if roll < 0.78 else [region, free] if roll < 0.95 else [free]
        pool = next((candidates for candidates in pools if candidates), None)
        if not pool:
            return None

        # Distribui os assuntos ao longo do combate. Folclore continua no jogo,
        # mas deixa de dominar a sequência quando há perguntas de outros temas.
        category_counts = {}
        for question_id in used:
            previous = self.by_id.get(question_id)
            if previous:
                category = previous.get("category", "general")
                category_counts[category] = category_counts.get(category, 0) + 1
        grouped = {}
        for question in pool:
            grouped.setdefault(question.get("category", "general"), []).append(question)
        least_seen = min(category_counts.get(category, 0) for category in grouped)
        balanced_categories = [category for category in grouped if category_counts.get(category, 0) == least_seen]
        category = self.rng.choice(balanced_categories)
        balanced_pool = grouped[category]

        weights = difficulty_weights(p, stage)
        return self.rng.choices(balanced_pool, weights=[weights[q["difficulty"]] for q in balanced_pool])[0]


class Battle:
    """Um combate: estados 'asking' → 'feedback' → (volta a 'asking') até 'won' ou 'lost'.
    `powers` são os poderes equipados (dicionários de powers.json com a chave extra "id")."""

    def __init__(self, bank, world, country_id, stage, monster, boss=False, powers=None, rng=None):
        self.bank, self.country_id, self.stage, self.monster, self.boss = bank, country_id, stage, monster, boss
        self.p = progress(world, country_id, stage)
        self.rng = rng or random.Random()
        self.powers = [dict(power) for power in (powers or [])]
        passive = {pw["effect"]: power_value(pw) for pw in self.powers if pw["type"] == "passive"}
        self.question_seconds = QUESTION_SECONDS + passive.get("extra_seconds", 0)
        self.hero_max = HERO_HP + round(passive.get("max_hp", 0))
        self.damage_multiplier = 1 + passive.get("damage_bonus", 0)
        self.damage_reduction = passive.get("damage_reduction", 0)
        self.dodge_chance = passive.get("dodge_chance", 0)
        self.first_hit_bonus = passive.get("first_hit_bonus", 0)
        self.monster_max, base_attack = monster_stats(stage, boss)
        self.monster_attack = max(1, round(base_attack * (1 - self.damage_reduction)))
        self.monster_hp, self.hero_hp = self.monster_max, self.hero_max
        self.streak = int(passive.get("starting_streak", 0))
        self.uses = {pw["id"]: power_uses(pw) for pw in self.powers if pw["type"] == "active"}
        self.double_armed, self.freeze_left, self.hits = False, 0.0, 0
        self.used, self.question, self.last, self.eliminated = set(), None, None, set()
        self.state = "asking"
        self.next_question()

    def next_question(self):
        self.question = self.bank.pick(self.country_id, self.p, self.used, self.stage)
        self.used.add(self.question["id"])
        self.time_left, self.state, self.last, self.eliminated = self.question_seconds, "asking", None, set()

    def tick(self, dt):
        if self.state != "asking":
            return
        if self.freeze_left > 0:  # Tempo Congelado: o relógio espera
            self.freeze_left -= dt
            return
        self.time_left -= dt
        if self.time_left <= 0:
            self.answer(None)  # acabou o tempo = errou

    def answer(self, index):
        if self.state != "asking" or index in self.eliminated:
            return None
        q = self.question
        if index == q["correctIndex"]:
            damage = hit_damage(q["difficulty"], self.time_left, self.streak, self.question_seconds) * self.damage_multiplier
            if self.hits == 0:
                damage *= 1 + self.first_hit_bonus
            if self.double_armed:
                damage, self.double_armed = damage * 2, False
            damage = round(damage)
            self.monster_hp = max(0, self.monster_hp - damage)
            self.streak += 1
            self.hits += 1
            self.last = {"result": "hit", "damage": damage, "chosen": index}
        else:
            dodged = self.rng.random() < self.dodge_chance
            damage = 0 if dodged else self.monster_attack
            before, self.hero_hp = self.hero_hp, max(0, self.hero_hp - damage)
            self.streak = 0
            self.last = {"result": "timeout" if index is None else "miss", "damage": damage, "lost": before - self.hero_hp,
                         "chosen": index, "dodged": dodged}
        self.state = "won" if self.monster_hp == 0 else "lost" if self.hero_hp == 0 else "feedback"
        return self.last

    def can_use(self, power_id):
        power = next((x for x in self.powers if x["id"] == power_id and x["type"] == "active"), None)
        if not power or self.uses.get(power_id, 0) <= 0 or self.state in ("won",):
            return False
        effect, state = power["effect"], self.state
        missed = bool(self.last) and self.last["result"] in ("miss", "timeout") and not self.last.get("dodged")
        if effect in ("eliminate_two_options", "eliminate_one_option"):
            return state == "asking" and len(self._wrong_left()) > 0
        if effect == "freeze_timer":
            return state == "asking" and self.freeze_left <= 0
        if effect == "double_damage":
            return state in ("asking", "feedback") and not self.double_armed
        if effect == "heal":
            return state in ("asking", "feedback") and self.hero_hp < self.hero_max
        if effect == "retry_question":
            return state in ("feedback", "lost") and missed
        return False

    def _wrong_left(self):
        return [i for i in range(len(self.question["options"])) if i != self.question["correctIndex"] and i not in self.eliminated]

    def use_power(self, power_id):
        """Usa um poder ativo. Devolve True se funcionou."""
        if not self.can_use(power_id):
            return False
        power = next(x for x in self.powers if x["id"] == power_id)
        effect = power["effect"]
        if effect in ("eliminate_two_options", "eliminate_one_option"):
            wrong = self._wrong_left()
            self.eliminated.update(self.rng.sample(wrong, min(2 if effect == "eliminate_two_options" else 1, len(wrong))))
        elif effect == "freeze_timer":
            self.freeze_left = power_value(power) or 10
        elif effect == "double_damage":
            self.double_armed = True
        elif effect == "heal":
            self.hero_hp = min(self.hero_max, self.hero_hp + round(power_value(power) or 25))
        elif effect == "retry_question":  # desfaz o dano do erro e permite tentar de novo
            self.hero_hp = min(self.hero_max, self.hero_hp + self.last["lost"])  # devolve só a vida realmente perdida
            if self.last["chosen"] is not None:
                self.eliminated.add(self.last["chosen"])
            self.state, self.last, self.time_left = "asking", None, self.question_seconds
        self.uses[power_id] -= 1
        return True


def load_bank(base, world, rng=None):
    """Procura o banco na pasta do jogo web (../data) e, se não achar, em story/data."""
    for folder in (base.parent / "data", base / "data"):
        if (folder / "questions.json").exists() and (folder / "question-countries.json").exists():
            raw = json.loads((folder / "questions.json").read_text(encoding="utf-8"))
            countries = json.loads((folder / "question-countries.json").read_text(encoding="utf-8"))
            return QuestionBank(raw["questions"] if isinstance(raw, dict) else raw, countries, world, rng)
    raise FileNotFoundError("questions.json e question-countries.json não encontrados")
