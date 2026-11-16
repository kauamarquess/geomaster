"""GeoMaster — Modo História (Etapa 2: base do jogo).
Rodar no PC:  python story/main.py   (precisa de: pip install pygame)
O laço principal é assíncrono de propósito: é o formato que o pygbag exige para rodar no navegador."""
import asyncio
import json
import os
import sys
import textwrap
from pathlib import Path

import pygame

from combat import Battle, load_bank
from progress import Progress
from sprites import monster_sprite

BASE = Path(__file__).resolve().parent
W, H = 320, 180  # tela interna pequena; o pygame amplia com pixels nítidos
INK, PAPER, GOLD, GREEN, DARK, RED = (240, 244, 255), (11, 29, 51), (242, 201, 76), (60, 170, 110), (24, 56, 92), (220, 80, 80)


def load_json(relative):
    return json.loads((BASE / relative).read_text(encoding="utf-8"))


def default_save_path():
    """No PC o save fica ao lado do jogo. No navegador (pygbag) vai para a pasta persistente /data."""
    if sys.platform == "emscripten":
        os.makedirs("/data/data/geomaster", exist_ok=True)
        return "/data/data/geomaster/save.json"
    return str(BASE / "save.json")


class Game:
    """Guarda a tela, a fonte e a cena atual. Cada tela do jogo é uma Scene."""

    def __init__(self, screen, save_path=None):
        self.screen = screen
        self.save_path = str(save_path or default_save_path())
        self.fonts = {size: pygame.font.Font(None, size) for size in (14, 18, 28)}
        self.world = load_json("data/world-order.json")
        self.powers_data = load_json("data/powers.json")
        self.bank = load_bank(BASE, self.world)
        self.names = load_json("data/country-names.json")
        self.order = [c for region in self.world["order"] for c in region["countries"]]
        self.progress = Progress(self.order)
        self.save_failed = False
        self.scene = MenuScene(self)
        self.running = True

    def text(self, message, x, y, color=INK, size=14, center=False):
        image = self.fonts[size].render(message, False, color)  # False = sem suavização (visual pixelado)
        self.screen.blit(image, (x - image.get_width() // 2 if center else x, y))

    def save(self):
        self.save_failed = not self.progress.save(self.save_path)

    def equipped_powers(self):
        """Poderes equipados, já no formato que o combate espera."""
        return [{**self.powers_data[p], "id": p, "level": self.progress.level(p)} for p in self.progress.equipped if p in self.powers_data]

    def has_data(self, country_id):
        return (BASE / "data/countries" / f"{country_id}.json").exists()

    def fit(self, message, width, size=14):
        """Corta o texto com '..' para caber na largura."""
        font = self.fonts[size]
        while font.size(message)[0] > width and len(message) > 3:
            message = message[:-3].rstrip() + ".."
        return message

    def wrap(self, message, width, size=14):
        font, lines, line = self.fonts[size], [], ""
        for word in message.split():
            if line and font.size(f"{line} {word}")[0] > width:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        return lines + [line] if line else lines

    def frame(self, events, dt=0.0):
        self.scene.update(dt)
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            else:
                self.scene.handle(event)
        self.screen.fill(PAPER)
        self.scene.draw()
        return self.running


class Scene:
    def __init__(self, game):
        self.game = game

    def handle(self, event): ...
    def update(self, dt): ...
    def draw(self): ...


class MenuScene(Scene):
    OPTIONS = ["Nova aventura", "Continuar", "Sair"]

    def __init__(self, game):
        super().__init__(game)
        self.index = 0
        self.has_save = Progress.load(game.save_path, game.order).has_progress()
        self.confirm = False  # pergunta antes de apagar um save existente

    def rect(self, i):
        return pygame.Rect(80, 88 + i * 24, 160, 20)

    def choose(self, i):
        g = self.game
        if i == 0:
            if self.has_save and not self.confirm:
                self.confirm = True
                return
            g.progress = Progress(g.order)
            g.scene = WorldMapScene(g)
        elif i == 1 and self.has_save:
            g.progress = Progress.load(g.save_path, g.order)
            g.scene = WorldMapScene(g)
        elif i == 2:
            g.running = False

    def handle(self, event):
        if self.confirm:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose(0)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.confirm = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose(self.index)
        elif event.type == pygame.MOUSEMOTION:
            self.index = next((i for i in range(3) if self.rect(i).collidepoint(event.pos)), self.index)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.rect(self.index).collidepoint(event.pos):
            self.choose(self.index)

    def draw(self):
        g = self.game
        for y in range(0, H, 6):  # faixas escuras no fundo
            pygame.draw.rect(g.screen, (14, 36, 62), (0, y, W, 3))
        g.text("GEOMASTER", W // 2, 28, GOLD, 28, center=True)
        g.text("MODO HISTÓRIA", W // 2, 56, INK, 18, center=True)
        for i, label in enumerate(self.OPTIONS):
            selected = i == self.index
            if selected:
                pygame.draw.rect(g.screen, DARK, self.rect(i))
            disabled = i == 1 and not self.has_save
            color = (110, 125, 150) if disabled else (GOLD if selected else INK)
            g.text(("> " if selected else "  ") + label + (" (sem save)" if disabled else ""), 90, self.rect(i).y + 4, color)
        if self.confirm:
            pygame.draw.rect(g.screen, PAPER, (30, 70, 260, 50))
            pygame.draw.rect(g.screen, RED, (30, 70, 260, 50), 2)
            g.text("Apagar o progresso salvo?", W // 2, 80, INK, 14, center=True)
            g.text("Enter = sim   Esc = não", W // 2, 98, GOLD, 14, center=True)
        else:
            g.text("Setas + Enter, ou mouse", W // 2, H - 14, (110, 125, 150), center=True)


class WorldScene(Scene):
    """As 10 fases de um país, lidas de data/countries/<ID>.json."""

    def __init__(self, game, country_id="BRA"):
        super().__init__(game)
        self.region_name = next(r["name"] for r in game.world["order"] if country_id in r["countries"])
        self.country = load_json(f"data/countries/{country_id}.json")
        self.country_name = game.names[country_id]
        self.index = min(game.progress.stages_done(country_id), 9)  # já aponta para a próxima fase a vencer
        self.message = ""

    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return
        stages = self.country["stages"]
        if event.key == pygame.K_p:
            self.game.scene = PowersScene(self.game, self)
        elif event.key == pygame.K_ESCAPE:
            self.game.scene = WorldMapScene(self.game, self.country["id"])
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.index = (self.index + 1) % len(stages)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.index = (self.index - 1) % len(stages)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            cid = self.country["id"]
            done = self.game.progress.stages_done(cid)
            if self.index > done:
                self.message = "Vença a fase anterior primeiro."
            else:
                stage = stages[self.index]
                self.game.scene = CombatScene(self.game, Battle(
                    self.game.bank, self.game.world, cid, stage["stage"], stage["monster"], stage.get("boss", False), powers=self.game.equipped_powers()), stage, self.country["theme"]["palette"])

    def draw(self):
        g = self.game
        g.text(self.region_name.upper(), W // 2, 12, GREEN, 14, center=True)
        g.text(self.country_name, W // 2, 28, GOLD, 28, center=True)
        for i, stage in enumerate(self.country["stages"]):
            box = pygame.Rect(20 + (i % 5) * 58, 62 + (i // 5) * 32, 50, 26)
            boss = stage.get("boss", False)
            won = (self.country["id"], stage["stage"]) in g.progress.cleared
            pygame.draw.rect(g.screen, GREEN if won else RED if boss else DARK, box)
            if i == self.index:
                pygame.draw.rect(g.screen, GOLD, box, 2)
            g.text("BOSS" if boss else str(stage["stage"]), box.centerx, box.y + 8, INK, 14, center=True)
        monster = self.country["stages"][self.index]["monster"]
        g.text(monster["name"], 20, 124, GOLD, 18)
        for line, text in enumerate(textwrap.wrap(monster["legend"], 46)[:2]):  # quebra a lenda em até 2 linhas
            g.text(text, 20, 142 + line * 12, INK, 14)
        g.text(self.message or "Enter luta · P poderes · Esc volta", W // 2, H - 12, (110, 125, 150), center=True)


class WorldMapScene(Scene):
    """Mapa-múndi: uma região por vez, com um quadrado por país na ordem da jornada."""
    COLS = 8
    LOCKED, SOON = (30, 45, 70), (60, 80, 110)

    def __init__(self, game, focus=None):
        super().__init__(game)
        focus = focus or game.progress.current_country()
        self.region = next(i for i, r in enumerate(game.world["order"]) if focus in r["countries"])
        self.index = self.countries().index(focus)
        self.message = ""

    def countries(self):
        return self.game.world["order"][self.region]["countries"]

    def node(self, i):
        return pygame.Rect(8 + (i % self.COLS) * 38, 36 + (i // self.COLS) * 15, 34, 13)

    def open_selected(self):
        g, cid = self.game, self.countries()[self.index]
        if not g.progress.is_unlocked(cid):
            self.message = "Bloqueado: conclua o país anterior."
        elif not g.has_data(cid):
            self.message = "Esse país chega nas próximas etapas."
        else:
            g.scene = WorldScene(g, cid)

    def switch_region(self, step):
        self.region = (self.region + step) % len(self.game.world["order"])
        self.index, self.message = 0, ""

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            last = len(self.countries()) - 1
            moves = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -self.COLS, pygame.K_DOWN: self.COLS}
            if event.key in moves:
                self.index, self.message = min(max(self.index + moves[event.key], 0), last), ""
            elif event.key == pygame.K_p:
                self.game.scene = PowersScene(self.game, self)
            elif event.key in (pygame.K_q, pygame.K_PAGEUP):
                self.switch_region(-1)
            elif event.key in (pygame.K_e, pygame.K_PAGEDOWN, pygame.K_TAB):
                self.switch_region(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.open_selected()
            elif event.key == pygame.K_ESCAPE:
                self.game.scene = MenuScene(self.game)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for i in range(len(self.countries())):
                if self.node(i).collidepoint(event.pos):
                    was_selected, self.index = self.index == i, i
                    if was_selected:
                        self.open_selected()

    def status(self, cid):
        g = self.game
        if g.progress.is_complete(cid):
            return "Concluído (10/10)"
        if not g.progress.is_unlocked(cid):
            return "Bloqueado"
        return f"Fases: {g.progress.stages_done(cid)}/10" + ("" if g.has_data(cid) else " · em breve")

    def draw(self):
        g, region = self.game, self.game.world["order"][self.region]
        done = g.progress.completed_count(region["countries"])
        g.text(region["name"].upper(), 8, 4, GOLD, 18)
        g.text(f"{done}/{len(region['countries'])} países · poderes: {len(g.progress.powers)}", 8, 22, GREEN)
        for i, cid in enumerate(self.countries()):
            box, fill, ink = self.node(i), self.LOCKED, (110, 125, 150)
            if g.progress.is_complete(cid):
                fill, ink = GREEN, PAPER
            elif g.progress.is_unlocked(cid):
                fill, ink = (GOLD, PAPER) if g.has_data(cid) else (self.SOON, INK)
            pygame.draw.rect(g.screen, fill, box)
            if i == self.index:
                pygame.draw.rect(g.screen, INK, box, 1)
            g.text(cid, box.centerx, box.y + 2, ink, 14, center=True)
        cid = self.countries()[self.index]
        g.text(g.names[cid], 8, 142, INK, 18)
        g.text(self.status(cid), 8, 155, (150, 165, 190))
        footer = "Não foi possível salvar o progresso!" if g.save_failed else self.message or "Q/E região · Enter entra · P poderes"
        g.text(footer, W // 2, 168, RED if g.save_failed or self.message else (110, 125, 150), center=True)


class PowersScene(Scene):
    """Escolha dos poderes levados para os combates (até 3). Enter equipa ou tira."""

    def __init__(self, game, back):
        super().__init__(game)
        self.back, self.index, self.message = back, 0, ""

    def handle(self, event):
        owned = self.game.progress.powers
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.save()
            self.game.scene = self.back
        elif owned and event.key in (pygame.K_UP, pygame.K_w):
            self.index = (self.index - 1) % len(owned)
        elif owned and event.key in (pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + 1) % len(owned)
        elif owned and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if not self.game.progress.toggle_equipped(owned[self.index]):
                self.message = "Só 3 poderes por vez: tire um antes."
            else:
                self.message = ""

    def draw(self):
        g, owned = self.game, self.game.progress.powers
        g.text("PODERES", W // 2, 4, GOLD, 18, center=True)
        g.text(f"Equipados: {len(g.progress.equipped)}/3", W // 2, 22, GREEN, center=True)
        if not owned:
            g.text("Vença um boss para ganhar poderes.", W // 2, 80, INK, center=True)
        first = max(0, min(self.index - 4, len(owned) - 8))
        for row, pid in enumerate(owned[first:first + 8]):
            i, power = first + row, g.powers_data[pid]
            box = pygame.Rect(20, 38 + row * 13, 280, 12)
            if i == self.index:
                pygame.draw.rect(g.screen, DARK, box)
            mark = "[x]" if pid in g.progress.equipped else "[ ]"
            kind = "passivo" if power["type"] == "passive" else "ativo"
            g.text(g.fit(f"{mark} {power['name']} ({kind}) nv.{g.progress.level(pid)}", 270), box.x + 4, box.y + 1, GOLD if i == self.index else INK)
        if owned:
            for line, text in enumerate(g.wrap(g.powers_data[owned[self.index]]["description"], 290)[:2]):
                g.text(text, 12, 146 + line * 11, (150, 165, 190))
        g.text(self.message or "Enter equipa/tira · Esc volta", W // 2, 168, RED if self.message else (110, 125, 150), center=True)


class CombatScene(Scene):
    """Combate por turnos: responda antes de o tempo acabar. Acertou = dano no monstro; errou = dano em você.
    Poderes ativos: teclas A, S e D (ou clique nos quadros embaixo)."""
    SLOT_KEYS = (pygame.K_a, pygame.K_s, pygame.K_d)
    SLOT_LETTERS = "ASD"

    def __init__(self, game, battle, stage, palette=None):
        super().__init__(game)
        self.battle, self.stage, self.note = battle, stage, ""
        self.palette = tuple(palette or ("#101c30", "#2a4a78", "#f2c94c", "#5f8fd0"))
        self.first_time = (battle.country_id, battle.stage) not in game.progress.cleared  # só a 1ª vitória dá poder

    def rect(self, i):
        return pygame.Rect(8, 70 + i * 17, 304, 15)

    def slot_rect(self, i):
        return pygame.Rect(8 + i * 102, 164, 98, 14)

    def answer(self, index):
        self.note = ""
        self.battle.answer(index)

    def use(self, slot):
        b = self.battle
        if slot < len(b.powers) and b.powers[slot]["type"] == "active":
            power = b.powers[slot]
            if b.use_power(power["id"]):
                self.note = f"{power['name']}!"
            else:
                self.note = "Esse poder não pode ser usado agora."

    def advance(self):
        b = self.battle
        if b.state == "feedback":
            self.note = ""
            b.next_question()
        elif b.state in ("won", "lost"):
            if b.state == "won":
                self.game.progress.clear(b.country_id, b.stage)
                power = self.stage.get("rewardPower")
                if power and self.first_time:
                    self.game.progress.add_power(power)
                self.game.save()
                if b.stage == 10:  # país concluído: volta ao mapa-múndi
                    self.game.scene = WorldMapScene(self.game, b.country_id)
                    return
            self.game.scene = WorldScene(self.game, b.country_id)

    def handle(self, event):
        b = self.battle
        if event.type == pygame.KEYDOWN:
            if b.state == "asking" and pygame.K_1 <= event.key <= pygame.K_4:
                self.answer(event.key - pygame.K_1)
            elif event.key in self.SLOT_KEYS:
                self.use(self.SLOT_KEYS.index(event.key))
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.advance()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            slot = next((i for i in range(3) if self.slot_rect(i).collidepoint(event.pos)), None)
            if slot is not None:
                self.use(slot)
            elif b.state == "asking":
                for i in range(4):
                    if self.rect(i).collidepoint(event.pos):
                        self.answer(i)
            else:
                self.advance()

    def update(self, dt):
        self.battle.tick(dt)

    def bar(self, x, y, w, value, maximum, color):
        pygame.draw.rect(self.game.screen, DARK, (x, y, w, 6))
        pygame.draw.rect(self.game.screen, color, (x, y, round(w * value / maximum), 6))

    def draw(self):
        g, b = self.game, self.battle
        g.text(g.fit(b.monster["name"] + (" (BOSS)" if b.boss else ""), 150), 8, 1, GOLD)
        g.text("Você", 162, 1)
        self.bar(8, 13, 150, b.monster_hp, b.monster_max, RED)
        self.bar(162, 13, 150, b.hero_hp, b.hero_max, GREEN)
        ratio = max(b.time_left, 0) / b.question_seconds
        frozen = b.freeze_left > 0
        pygame.draw.rect(g.screen, (90, 200, 240) if frozen else GOLD if ratio > 0.25 else RED, (8, 24, round(304 * ratio), 3))
        sprite = monster_sprite(b.monster["id"], b.country_id, self.palette, b.boss)
        g.screen.blit(sprite, (W - 8 - sprite.get_width(), 29))
        for i, line in enumerate(g.wrap(b.question["text"], 252)[:3]):
            g.text(line, 8, 32 + i * 11)
        correct = b.question["correctIndex"]
        for i, option in enumerate(b.question["options"]):
            box, out = self.rect(i), i in b.eliminated
            color = DARK
            if b.state != "asking":
                color = GREEN if i == correct else RED if i == b.last["chosen"] else DARK
            pygame.draw.rect(g.screen, (20, 36, 58) if out else color, box)
            g.text(g.fit(f"{i + 1}) {option}", 296), box.x + 4, box.y + 2, (80, 95, 120) if out else INK)
        self.draw_footer()
        self.draw_slots()

    def draw_slots(self):
        g, b = self.game, self.battle
        for i, power in enumerate(b.powers[:3]):
            box = self.slot_rect(i)
            if power["type"] == "passive":
                pygame.draw.rect(g.screen, (20, 50, 44), box)
                label, color = f"+ {power['name']}", GREEN
            else:
                ready = b.can_use(power["id"])
                color = GOLD if ready else (110, 125, 150)
                pygame.draw.rect(g.screen, DARK, box)
                label = f"{self.SLOT_LETTERS[i]}:{power['name']} x{b.uses[power['id']]}"
                if power["effect"] == "double_damage" and b.double_armed:
                    label, color = f"{self.SLOT_LETTERS[i]}:{power['name']} PRONTO", GREEN
            g.text(g.fit(label, 92), box.x + 3, box.y + 2, color)

    def draw_footer(self):
        g, b = self.game, self.battle
        if b.state == "asking":
            g.text(self.note or "1-4 responde · A S D usam poderes", 8, 141, GOLD if self.note else (110, 125, 150))
            return
        if b.state == "won":
            reward = self.stage.get("rewardPower") if self.first_time else None
            text = "VITÓRIA!"
            if reward:
                level = g.progress.level(reward) + 1 if reward in g.progress.powers else 1
                text += f" {g.powers_data[reward]['name']}" + (f" subiu para o nível {level}!" if level > 1 else " conquistado!")
            g.text(g.fit(text, 296), 8, 141, GOLD)
        elif b.state == "lost":
            g.text("DERROTA... você caiu." + (" (A/S/D: poder)" if self.note == "" and any(b.can_use(p["id"]) for p in b.powers) else ""), 8, 141, RED)
        elif b.last["result"] == "hit":
            g.text(f"Acertou! -{b.last['damage']} no monstro", 8, 141, GREEN)
        elif b.last.get("dodged"):
            g.text("Esquivou! Nenhum dano.", 8, 141, GREEN)
        else:
            why = "Tempo esgotado!" if b.last["result"] == "timeout" else "Errou!"
            g.text(f"{why} -{b.last['damage']} de vida", 8, 141, RED)
        g.text(g.fit(self.note or b.question.get("explanation", ""), 304), 8, 151, GOLD if self.note else (150, 165, 190))
        g.text("Enter continua", 232, 141, (110, 125, 150))


async def main():
    pygame.init()
    try:
        screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)  # SCALED amplia sem borrar
    except pygame.error:
        screen = pygame.display.set_mode((W * 3, H * 3))
    pygame.display.set_caption("GeoMaster — Modo História")
    game, clock = Game(screen), pygame.time.Clock()
    dt = 0.0
    while game.frame(pygame.event.get(), dt):
        pygame.display.flip()
        dt = clock.tick(60) / 1000
        await asyncio.sleep(0)  # devolve o controle ao navegador (obrigatório no pygbag)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
