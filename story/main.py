"""GeoMaster — Modo História (Etapa 2: base do jogo).
Rodar no PC:  python story/main.py   (precisa de: pip install pygame)
O laço principal é assíncrono de propósito: é o formato que o pygbag exige para rodar no navegador."""
import asyncio
import json
import math
import os
import sys
import textwrap
import time
from pathlib import Path

import pygame

from combat import Battle, load_bank
from mapgeo import View, pick_direction
from mapview import Terrain, draw_pin, load_map
from progress import Progress
from sprites import hex_to_rgb, monster_sprite
import traveler
import webstore

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
        self._map = None
        self._terrains = {}
        self.scene = MenuScene(self)
        self.running = True

    @property
    def map(self):
        """Formas dos países e posição das fases (data/map.json); só é lido na primeira vez que o mapa aparece."""
        if self._map is None:
            self._map = load_map(BASE / "data/map.json")
        return self._map

    def terrain(self, key, build):
        """Mapas já pintados ficam guardados (poucos): voltar a um continente não repinta o mundo todo."""
        if key not in self._terrains:
            if len(self._terrains) >= 14:
                self._terrains.pop(next(iter(self._terrains)))
            self._terrains[key] = build()
        return self._terrains[key]

    def text(self, message, x, y, color=INK, size=14, center=False):
        image = self.fonts[size].render(message, False, color)  # False = sem suavização (visual pixelado)
        self.screen.blit(image, (x - image.get_width() // 2 if center else x, y))

    def save(self):
        """Grava no arquivo e, no navegador, também no localStorage. Só avisa se nenhum dos dois funcionou."""
        text = self.progress.dumps()
        in_file, in_browser = self.progress.save(self.save_path, text), webstore.write(text)
        self.save_failed = not (in_file or in_browser)

    def delete_save(self):
        """Apaga o save. No navegador deixa um save VAZIO e mais novo que o antigo, para que uma cópia que o navegador
        não conseguiu remover não "ressuscite". Devolve True se, depois disso, não resta progresso nenhum."""
        newest = max(int(time.time()), self.load_progress().saved_at + 1)
        Progress.delete(self.save_path)
        webstore.write(Progress(self.order).dumps(newest))
        self.progress = Progress(self.order)
        self.save_failed = False
        return not self.load_progress().has_progress()

    def load_progress(self):
        """Lê o save do arquivo e o do navegador (se houver) e fica com o mais recente."""
        found = [Progress.load(self.save_path, self.order)]
        text = webstore.read()
        if text:
            found.append(Progress.loads(text, self.order))
        return Progress.newest(*found)

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
    OPTIONS = ["Nova aventura", "Continuar", "Apagar save", "Sair"]
    NEEDS_SAVE = (1, 2)  # Continuar e Apagar só fazem sentido com um save

    def __init__(self, game):
        super().__init__(game)
        self.index = 0
        self.saved = game.load_progress()
        self.has_save = self.saved.has_progress()
        self.confirm = None  # None, "new" (Nova aventura sobre um save) ou "delete" (Apagar save)
        self.message, self.message_color, self.t = "", GOLD, 0.0

    def update(self, dt):
        self.t += dt

    def rect(self, i):
        return pygame.Rect(80, 82 + i * 21, 160, 19)

    def choose(self, i):
        g = self.game
        if i == 0:
            if self.has_save and self.confirm != "new":
                self.confirm = "new"
                return
            g.progress = Progress(g.order)
            g.scene = GlobeScene(g)
        elif i == 1 and self.has_save:
            g.progress = self.saved
            g.scene = GlobeScene(g)
        elif i == 2 and self.has_save:
            if self.confirm != "delete":
                self.confirm = "delete"
                return
            self.confirm = None
            if g.delete_save():
                self.saved, self.has_save = g.progress, False
                self.message, self.message_color = "Save apagado.", GOLD
            else:
                self.message, self.message_color = "Não foi possível apagar o save.", RED
        elif i == 3:
            g.running = False

    def handle(self, event):
        if self.confirm:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose(0 if self.confirm == "new" else 2)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.confirm = None
            return
        self.message = ""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.choose(self.index)
        elif event.type == pygame.MOUSEMOTION:
            self.index = next((i for i in range(len(self.OPTIONS)) if self.rect(i).collidepoint(event.pos)), self.index)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.rect(self.index).collidepoint(event.pos):
            self.choose(self.index)

    def draw(self):
        g = self.game
        for y in range(0, H, 6):  # faixas escuras no fundo
            pygame.draw.rect(g.screen, (14, 36, 62), (0, y, W, 3))
        g.text("GEOMASTER", W // 2, 24, GOLD, 28, center=True)
        g.text("MODO HISTÓRIA", W // 2, 52, INK, 18, center=True)
        sprite = traveler.idle(self.t, 3)  # o viajante, em tamanho grande, ao lado das opções
        g.screen.blit(sprite, (254, 100))
        for i, label in enumerate(self.OPTIONS):
            selected = i == self.index
            if selected:
                pygame.draw.rect(g.screen, DARK, self.rect(i))
            disabled = i in self.NEEDS_SAVE and not self.has_save
            color = (110, 125, 150) if disabled else (GOLD if selected else INK)
            extra = " (sem save)" if disabled else f" ({self.saved.completed_count()}/{len(g.order)})" if i == 1 else ""
            g.text(("> " if selected else "  ") + label + extra, 90, self.rect(i).y + 4, color)
        if self.confirm:
            pygame.draw.rect(g.screen, PAPER, (30, 66, 260, 62))
            pygame.draw.rect(g.screen, RED, (30, 66, 260, 62), 2)
            if self.confirm == "delete":
                g.text("Apagar o save de vez?", W // 2, 74, INK, 14, center=True)
                g.text(f"Você perde {self.saved.completed_count()}/{len(g.order)} países e os poderes.", W // 2, 90, (150, 165, 190), 14, center=True)
            else:
                g.text("Apagar o progresso salvo?", W // 2, 80, INK, 14, center=True)
            g.text("Enter = sim   Esc = não", W // 2, 108, GOLD, 14, center=True)
        else:
            g.text(self.message or "Setas + Enter, ou mouse", W // 2, H - 14, self.message_color if self.message else (110, 125, 150), center=True)


def mix(a, b, t):
    """Mistura duas cores: t=0 devolve `a`, t=1 devolve `b`."""
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


REGION_COLORS = {
    "south_america": (96, 168, 104), "central_america": (72, 176, 170), "north_america": (96, 128, 208),
    "europe": (160, 120, 208), "africa": (214, 156, 76), "asia": (208, 96, 96), "oceania": (84, 194, 224),
}
LOCKED, SOON, CONTEXT, BORDER = (58, 80, 116), (90, 112, 150), (26, 42, 66), (10, 14, 26)
MAP_RECT = (0, 20, W, 120)  # área do mapa-múndi e dos continentes (o resto da tela é texto)
STAGE_RECT = (0, 26, 204, 128)  # área do país com as 10 fases (o painel da fase fica à direita)
PANEL = pygame.Rect(208, 26, 108, 130)


def draw_traveler_marker(target, pos, t):
    """O viajante em miniatura em pé sobre `pos`, respirando (sobe e desce 1 pixel)."""
    sprite = traveler.mini()
    target.blit(sprite, (pos[0] - sprite.get_width() // 2, pos[1] - sprite.get_height() - int(t * 2) % 2))


class GlobeScene(Scene):
    """Mapa-múndi: cada continente é uma região da jornada. Enter entra no continente."""

    def __init__(self, game, focus=None):
        super().__init__(game)
        self.regions = game.world["order"]
        focus = focus or game.progress.current_country()
        self.region = next(i for i, r in enumerate(self.regions) if focus in r["countries"])
        self.country_region = {c: i for i, r in enumerate(self.regions) for c in r["countries"]}
        self.message, self.t, self.outlines = "", 0.0, {}
        data = game.map
        fills = {}
        for cid, i in self.country_region.items():
            base = REGION_COLORS[self.regions[i]["id"]]
            if not self.unlocked(i):
                fills[cid] = mix(base, PAPER, 0.5)
            elif game.progress.is_complete(cid):
                fills[cid] = mix(base, INK, 0.3)  # território já conquistado fica mais claro
            else:
                fills[cid] = mix(base, PAPER, 0.12)

        def build():
            terrain = Terrain(data, View(data.world_box, MAP_RECT), (W, H), PAPER)
            terrain.paint_all(fills, default=CONTEXT)
            return terrain

        self.terrain = game.terrain(("globe", tuple(fills.items())), build)
        view = self.terrain.view
        self.nav = [view.project(*data.regions[r["id"]]["nav"]) for r in self.regions]
        self.here = self.terrain.center(game.progress.current_country())

    def unlocked(self, i):
        return self.game.progress.is_unlocked(self.regions[i]["countries"][0])

    def move(self, step):
        self.region, self.message = (self.region + step) % len(self.regions), ""

    def open_region(self):
        g, countries = self.game, self.regions[self.region]["countries"]
        focus = next((c for c in countries if not g.progress.is_complete(c)), countries[0])
        g.scene = WorldMapScene(g, focus)

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            arrows = {pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
                      pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}
            if event.key in arrows:
                self.region, self.message = pick_direction(self.region, self.nav, *arrows[event.key]), ""
            elif event.key in (pygame.K_e, pygame.K_TAB, pygame.K_PAGEDOWN):
                self.move(1)
            elif event.key in (pygame.K_q, pygame.K_PAGEUP):
                self.move(-1)
            elif event.key == pygame.K_p:
                self.game.scene = PowersScene(self.game, self)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.open_region()
            elif event.key == pygame.K_ESCAPE:
                self.game.scene = MenuScene(self.game)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            cid = self.terrain.hit(event.pos, self.country_region)
            if cid is not None:
                was_selected, self.region = self.region == self.country_region[cid], self.country_region[cid]
                self.message = ""
                if was_selected:
                    self.open_region()

    def update(self, dt):
        self.t += dt

    def outline(self):
        if self.region not in self.outlines:
            layer = pygame.Surface((W, H), pygame.SRCALPHA)
            for cid in self.regions[self.region]["countries"]:
                self.terrain.outline(layer, cid, INK)
            self.outlines[self.region] = layer
        return self.outlines[self.region]

    def draw(self):
        g, region = self.game, self.regions[self.region]
        g.screen.blit(self.terrain.surface, (0, 0))
        g.screen.blit(self.outline(), (0, 0))
        draw_traveler_marker(g.screen, self.here, self.t)  # o viajante, no país onde a aventura está
        g.text("MAPA-MÚNDI", 8, 4, GOLD, 18)
        g.text(f"{g.progress.completed_count()}/{len(g.order)} países · poderes: {len(g.progress.powers)}", W - 8 - g.fonts[14].size(f"{g.progress.completed_count()}/{len(g.order)} países · poderes: {len(g.progress.powers)}")[0], 7, GREEN)
        done = g.progress.completed_count(region["countries"])
        g.text(region["name"], 8, 144, REGION_COLORS[region["id"]], 18)
        state = "Concluído" if done == len(region["countries"]) else f"{done}/{len(region['countries'])} países" if self.unlocked(self.region) else "Bloqueado: conclua o continente anterior"
        g.text(state, 8, 157, (150, 165, 190))
        footer = "Não foi possível salvar o progresso!" if g.save_failed else self.message or "Setas continente · Enter entra · P poderes · Esc menu"
        g.text(footer, W // 2, 168, RED if g.save_failed else (110, 125, 150), center=True)


class WorldMapScene(Scene):
    """Um continente em destaque: cada país é uma região do mapa, na ordem da jornada (cores = progresso)."""

    def __init__(self, game, focus=None, region=None):
        super().__init__(game)
        if region is None:
            focus = focus or game.progress.current_country()
            region = next(i for i, r in enumerate(game.world["order"]) if focus in r["countries"])
        self.region, self.message, self.t = region, "", 0.0
        self.index = self.countries().index(focus) if focus in self.countries() else 0
        self.build()

    def countries(self):
        return self.game.world["order"][self.region]["countries"]

    def build(self):
        g, ids = self.game, self.countries()
        spec = g.map.regions[g.world["order"][self.region]["id"]]
        fills = {c: self.fill(c) for c in ids}

        def paint():
            terrain = Terrain(g.map, View(spec["box"], MAP_RECT, wrap=spec["wrap"]), (W, H), PAPER)
            terrain.paint_all({}, default=CONTEXT, skip=set(ids))  # vizinhança escura
            terrain.paint_all(fills, border=BORDER)
            for c in ids:
                if max(terrain.screen_size(c)) < 5:  # país minúsculo vira um "pino"
                    draw_pin(terrain.surface, terrain.center(c), mix(fills[c], INK, 0.25))
            return terrain

        self.terrain = g.terrain(("region", self.region, tuple(fills.values())), paint)
        self.centers = [self.terrain.center(c) for c in ids]
        self.tiny = [i for i, c in enumerate(ids) if max(self.terrain.screen_size(c)) < 5]
        self.here = self.terrain.center(g.progress.current_country()) if g.progress.current_country() in ids else None

    def fill(self, cid):
        g = self.game
        if g.progress.is_complete(cid):
            return GREEN
        if g.progress.is_unlocked(cid):
            return mix(GOLD, PAPER, 0.1) if g.has_data(cid) else SOON
        return LOCKED

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
        self.build()

    def pick(self, pos):
        ids = self.countries()
        cid = self.terrain.hit(pos, ids)
        if cid is not None:
            return ids.index(cid)
        near = [(math.hypot(x - pos[0], y - pos[1]), i) for i, (x, y) in enumerate(self.centers)]
        near = [n for n in near if n[0] <= 6]
        return min(near)[1] if near else None

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            arrows = {pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
                      pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}
            if event.key in arrows:
                self.index, self.message = pick_direction(self.index, self.centers, *arrows[event.key]), ""
            elif event.key == pygame.K_TAB:  # próximo país na ordem da jornada (Shift volta)
                step = -1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 1
                self.index, self.message = (self.index + step) % len(self.countries()), ""
            elif event.key == pygame.K_p:
                self.game.scene = PowersScene(self.game, self)
            elif event.key in (pygame.K_q, pygame.K_PAGEUP):
                self.switch_region(-1)
            elif event.key in (pygame.K_e, pygame.K_PAGEDOWN):
                self.switch_region(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.open_selected()
            elif event.key == pygame.K_ESCAPE:
                self.game.scene = GlobeScene(self.game, self.countries()[0])
        elif event.type == pygame.MOUSEBUTTONDOWN:
            i = self.pick(event.pos)
            if i is not None:
                was_selected, self.index, self.message = self.index == i, i, ""
                if was_selected:
                    self.open_selected()

    def update(self, dt):
        self.t += dt

    def status(self, cid):
        g = self.game
        if g.progress.is_complete(cid):
            return "Concluído (10/10)"
        if not g.progress.is_unlocked(cid):
            return "Bloqueado"
        return f"Fases: {g.progress.stages_done(cid)}/10" + ("" if g.has_data(cid) else " · em breve")

    def draw(self):
        g, region = self.game, self.game.world["order"][self.region]
        ids = self.countries()
        g.screen.blit(self.terrain.surface, (0, 0))
        cid = ids[self.index]
        self.terrain.outline(g.screen, cid, INK)
        x, y = self.centers[self.index]
        if self.index in self.tiny:
            pygame.draw.circle(g.screen, INK, (x, y), 5, 1)
        if self.here is not None:  # o viajante, no país onde a aventura está
            draw_traveler_marker(g.screen, self.here, self.t)
        done = g.progress.completed_count(region["countries"])
        g.text(region["name"].upper(), 8, 4, GOLD, 18)
        info = f"{done}/{len(ids)} países · poderes: {len(g.progress.powers)}"
        g.text(info, W - 8 - g.fonts[14].size(info)[0], 7, GREEN)
        g.text(g.names[cid], 8, 144, INK, 18)
        g.text(self.status(cid), 8, 157, (150, 165, 190))
        footer = "Não foi possível salvar o progresso!" if g.save_failed else self.message or "Setas países · Enter entra · Q/E continente · Esc volta"
        g.text(footer, W // 2, 168, RED if g.save_failed or self.message else (110, 125, 150), center=True)


class WorldScene(Scene):
    """O país em tela cheia: as 10 fases ficam DENTRO do desenho do país, ligadas por um caminho."""

    def __init__(self, game, country_id="BRA"):
        super().__init__(game)
        self.region_name = next(r["name"] for r in game.world["order"] if country_id in r["countries"])
        self.country = load_json(f"data/countries/{country_id}.json")
        self.country_name = game.names[country_id]
        self.index = min(game.progress.stages_done(country_id), 9)  # já aponta para a próxima fase a vencer
        self.message, self.t = "", 0.0
        self.build()

    def build(self):
        g, cid = self.game, self.country["id"]
        shape = g.map.countries[cid]
        palette = [hex_to_rgb(c) for c in self.country["theme"]["palette"]]
        wide = not shape.blob and max(shape.box[2] - shape.box[0], shape.box[3] - shape.box[1]) >= 2

        def paint():
            terrain = Terrain(g.map, View(shape.box, STAGE_RECT, wrap=shape.wrap, pad=12), (W, H), PAPER)
            if wide:  # os vizinhos aparecem apagados; ilhas minúsculas ficam sozinhas no mar
                terrain.paint_all({}, default=CONTEXT, skip={cid})
            terrain.paint(cid, mix(palette[1], PAPER, 0.2), border=mix(palette[3], INK, 0.25), rings=shape.shape_rings())
            if wide:
                terrain.paint_holes(cid, CONTEXT)
            return terrain

        self.terrain = g.terrain(("country", cid), paint)
        self.ampliada = bool(shape.blob)
        self.points = [tuple(int(round(v)) for v in self.terrain.view.project(lon, lat)) for lon, lat in shape.nodes]
        gaps = [math.dist(a, b) for i, a in enumerate(self.points) for b in self.points[i + 1:]]
        self.radius = int(max(3, min(6, min(gaps) / 2 - 1))) if gaps else 5

    def activate(self):
        stages, cid = self.country["stages"], self.country["id"]
        if self.index > self.game.progress.stages_done(cid):
            self.message = "Vença a fase anterior primeiro."
        else:
            stage = stages[self.index]
            self.game.scene = CombatScene(self.game, Battle(
                self.game.bank, self.game.world, cid, stage["stage"], stage["monster"], stage.get("boss", False), powers=self.game.equipped_powers()), stage, self.country["theme"]["palette"])

    def handle(self, event):
        count = len(self.country["stages"])
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.game.scene = PowersScene(self.game, self)
            elif event.key == pygame.K_ESCAPE:
                self.game.scene = WorldMapScene(self.game, self.country["id"])
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.index, self.message = (self.index + 1) % count, ""
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.index, self.message = (self.index - 1) % count, ""
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.index, self.message = pick_direction(self.index, self.points, 0, -1), ""
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index, self.message = pick_direction(self.index, self.points, 0, 1), ""
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            near = [(math.dist(p, event.pos), i) for i, p in enumerate(self.points)]
            near = [n for n in near if n[0] <= self.radius + 4]
            if near:
                i = min(near)[1]
                was_selected, self.index, self.message = self.index == i, i, ""
                if was_selected:
                    self.activate()

    def update(self, dt):
        self.t += dt

    def dashed(self, a, b, color):
        length = math.dist(a, b)
        steps = int(length // 4)
        for n in range(steps):
            if n % 2 == 0:
                s, e = n / steps, (n + 1) / steps
                pygame.draw.line(self.game.screen, color, (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s),
                                 (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e))

    def draw(self):
        g, cid = self.game, self.country["id"]
        g.screen.blit(self.terrain.surface, (0, 0))
        g.text(self.country_name, 8, 4, GOLD, 18)
        g.text(self.region_name, W - 8 - g.fonts[14].size(self.region_name)[0], 7, GREEN)
        if self.ampliada:
            g.text("ilha ampliada", 8, 142, (110, 125, 150))
        done = g.progress.stages_done(cid)
        stages = self.country["stages"]
        for i in range(len(stages) - 1):  # o caminho: verde onde o jogador já passou
            self.dashed(self.points[i], self.points[i + 1], (110, 230, 150) if i + 1 <= done else (150, 165, 190))
        for i, stage in enumerate(stages):
            boss, won = stage.get("boss", False), (cid, stage["stage"]) in g.progress.cleared
            r = self.radius + (2 if boss else 0)
            x, y = self.points[i]
            fill = (90, 220, 140) if won else RED if boss else GOLD if i == done else (86, 104, 140)
            if i == done and int(self.t * 3) % 2 == 0:
                pygame.draw.circle(g.screen, GOLD, (x, y), r + 3, 1)  # pisca na próxima fase a vencer
            pygame.draw.circle(g.screen, BORDER, (x, y), r + 1)
            pygame.draw.circle(g.screen, fill, (x, y), r)
            if r >= 5:
                g.text("B" if boss else str(stage["stage"]), x, y - 4, PAPER if fill != (86, 104, 140) else INK, 14, center=True)
            if i == self.index:
                pygame.draw.circle(g.screen, INK, (x, y), r + 3, 1)
        here = self.points[min(done, len(stages) - 1)]  # o viajante espera na próxima fase a vencer
        sprite = traveler.idle(self.t)
        g.screen.blit(sprite, (here[0] - sprite.get_width() // 2, here[1] - sprite.get_height() - self.radius + 3))
        stage = stages[self.index]
        monster, boss = stage["monster"], stage.get("boss", False)
        pygame.draw.rect(g.screen, (16, 36, 62), PANEL)
        pygame.draw.rect(g.screen, DARK, PANEL, 1)
        y = PANEL.y + 4
        g.text(f"Fase {stage['stage']}/10", PANEL.x + 5, y, (150, 165, 190))
        if boss:
            g.text("CHEFÃO", PANEL.right - 5 - g.fonts[14].size("CHEFÃO")[0], y, RED)
        y += 12
        size = 18 if len(g.wrap(monster["name"], PANEL.w - 10, 18)) <= 2 else 14  # nome comprido: letra menor
        for line in g.wrap(monster["name"], PANEL.w - 10, size):
            g.text(line, PANEL.x + 5, y + 2, GOLD, size)
            y += 13 if size == 18 else 11
        y += 6
        lines, room = g.wrap(monster["legend"], PANEL.w - 10), (PANEL.bottom - y - 2) // 11
        if len(lines) > room:  # não deveria acontecer com as lendas atuais; corta com reticências em vez de vazar
            lines = lines[:room]
            lines[-1] = g.fit(lines[-1] + "...", PANEL.w - 10)
        for line in lines:
            g.text(line, PANEL.x + 5, y, INK)
            y += 11
        g.text(self.message or "Enter luta · setas escolhem · P poderes · Esc volta", W // 2, H - 12, (110, 125, 150), center=True)


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
        self.battle, self.stage, self.note, self.t = battle, stage, "", 0.0
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
        self.t += dt
        self.battle.tick(dt)

    def hero_face(self):
        """A expressão do viajante acompanha a luta: respira, comemora o acerto, sente o golpe, cai na derrota."""
        b = self.battle
        if b.state == "lost":
            return "down"
        if b.state == "won" or (b.state == "feedback" and b.last["result"] == "hit"):
            return "happy"
        if b.state == "feedback":
            return "hurt"
        return "idle1" if int(self.t * 2) % 2 else "idle0"

    def bar(self, x, y, w, value, maximum, color):
        pygame.draw.rect(self.game.screen, DARK, (x, y, w, 6))
        pygame.draw.rect(self.game.screen, color, (x, y, round(w * value / maximum), 6))

    def draw(self):
        g, b = self.game, self.battle
        g.text(g.fit(b.monster["name"] + (" (BOSS)" if b.boss else ""), 150), 8, 1, GOLD)
        g.screen.blit(traveler.portrait(self.hero_face()), (162, 0))
        g.text("Você", 182, 1)
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
