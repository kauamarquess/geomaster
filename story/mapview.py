"""Desenho do mapa do Modo História: carrega data/map.json e pinta continentes, países e fases."""
import json

import pygame

from mapgeo import bbox, point_in_ring, ring_area


class Country:
    """Um país já decodificado: anéis em (lon, lat), caixas, posição das 10 fases e centro."""

    def __init__(self, cid, raw, q):
        self.id = cid
        k = 1.0 / q
        self.rings = [[(r[i] * k, r[i + 1] * k) for i in range(0, len(r), 2)] for r in raw["r"]]
        self.boxes = [bbox(r) for r in self.rings]
        self.area = sum(ring_area(r) for r in self.rings)
        self.focus = raw["f"]
        self.holes = [[(r[i] * k, r[i + 1] * k) for i in range(0, len(r), 2)] for r in raw.get("h", [])]
        self.nodes = [tuple(n) for n in raw["n"]]
        self.center = tuple(raw["c"])
        self.box = list(raw["box"])  # caixa da vista do país (já com a forma ampliada, se for ilha minúscula)
        self.wrap = bool(raw.get("w"))
        bl = raw.get("bl")
        self.blob = [(bl[i], bl[i + 1]) for i in range(0, len(bl), 2)] if bl else None
        # tamanho real (em graus) do desenho, para decidir se no mapa ele vira um "pino"
        real = [self.boxes[i] for i in self.focus]
        lons = [v for b in real for v in (b[0], b[2])]
        if min(lons) < -90 and max(lons) > 90:  # cruza a linha de data (Fiji...): empurra o lado oeste para +360
            lons = [v + 360 if v < 0 else v for v in lons]
        self.real_size = (max(lons) - min(lons), max(b[3] for b in real) - min(b[1] for b in real))

    def shape_rings(self):
        """Anéis do país na tela de fases: a mancha de ilha, se existir, senão o desenho de verdade."""
        return [self.blob] if self.blob else self.rings


class MapData:
    def __init__(self, raw):
        q = raw["q"]
        self.countries = {cid: Country(cid, c, q) for cid, c in raw["countries"].items()}
        self.regions = raw["regions"]
        self.world_box = raw["world"]["box"]
        # grandes primeiro, pequenos por cima. A Antártida fica de fora: o desenho dela atravessa a linha de data
        # e, nas vistas do Pacífico, viraria uma faixa quebrada.
        self.by_area = sorted((c for c in self.countries if c != "ATA"), key=lambda c: -self.countries[c].area)


def load_map(path):
    with open(path, encoding="utf-8") as file:
        return MapData(json.load(file))


class Terrain:
    """Mapa pintado uma vez numa Surface, com os desenhos já projetados para acertar cliques."""

    def __init__(self, data, view, size, ocean):
        self.data, self.view = data, view
        self.surface = pygame.Surface(size)
        self.surface.fill(ocean)
        self.surface.set_clip(pygame.Rect(view.rect))  # nada é pintado fora da área do mapa
        self.shapes = {}  # id -> [(pontos na tela, caixa na tela)]

    def paint(self, cid, fill, border=None, rings=None):
        country, view = self.data.countries[cid], self.view
        rings = country.rings if rings is None else rings
        boxes = country.boxes if len(rings) == len(country.boxes) and rings is country.rings else [bbox(r) for r in rings]
        out = self.shapes.setdefault(cid, [])
        for ring, ring_box in zip(rings, boxes):
            if not view.visible(ring_box):
                continue
            pts = view.project_ring(ring)
            x0, y0, x1, y1 = bbox(pts)
            if x1 - x0 < 1.5 and y1 - y0 < 1.5:  # ilhota: um pixel, para não sumir do mapa
                self.surface.set_at((int((x0 + x1) / 2), int((y0 + y1) / 2)), fill)
            else:
                pygame.draw.polygon(self.surface, fill, pts)
                if border and min(x1 - x0, y1 - y0) >= 8:  # em formas estreitas a borda comeria a cor do país
                    pygame.draw.polygon(self.surface, border, pts, 1)
            out.append((pts, (x0, y0, x1, y1)))

    def paint_all(self, fills, default=None, border=None, skip=()):
        """Pinta os países por tamanho (grandes primeiro). `fills`: id -> cor; os que faltam usam `default`."""
        for cid in self.data.by_area:
            if cid in skip:
                continue
            color = fills.get(cid, default)
            if color is not None:
                self.paint(cid, color, border)

    def paint_holes(self, cid, color):
        """Buracos (Lesoto dentro da África do Sul...) são repintados com a cor de fundo dos vizinhos."""
        for hole in self.data.countries[cid].holes:
            if self.view.visible(bbox(hole)):
                pts = self.view.project_ring(hole)
                if len(pts) >= 3:
                    pygame.draw.polygon(self.surface, color, pts)

    def hit(self, pos, ids):
        """Qual país (entre `ids`) está sob o ponto da tela; os pequenos têm prioridade."""
        order = sorted((c for c in ids if c in self.shapes), key=lambda c: self.data.countries[c].area)
        for cid in order:
            for pts, (x0, y0, x1, y1) in self.shapes[cid]:
                if x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1 and point_in_ring(pos, pts):
                    return cid
        return None

    def outline(self, target, cid, color):
        for pts, _ in self.shapes.get(cid, ()):
            if len(pts) >= 3:
                pygame.draw.polygon(target, color, pts, 1)

    def screen_size(self, cid):
        """Largura e altura (em pixels) do país nesta vista."""
        w, h = self.data.countries[cid].real_size
        return w * self.view.k * self.view.scale, h * self.view.scale

    def center(self, cid):
        x, y = self.view.project(*self.data.countries[cid].center)
        return int(round(x)), int(round(y))


def draw_pin(target, pos, fill, outline=(10, 14, 26), radius=2):
    pygame.draw.circle(target, outline, pos, radius + 1)
    pygame.draw.circle(target, fill, pos, radius)
