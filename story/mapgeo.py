"""Geometria do mapa do Modo História. Não usa pygame, então dá para testar em qualquer lugar.

Coordenadas: longitude/latitude em graus. A projeção é a "equiretangular corrigida": o eixo x é
multiplicado pelo cosseno da latitude central da vista, o que evita países achatados perto dos polos.
"""
import math


class View:
    """Enquadra uma caixa (lon0, lat0, lon1, lat1) dentro de um retângulo da tela, sem deformar.

    `wrap=True` empurra o lado oeste (longitudes negativas) para +360, usado perto da linha de data (Oceania, Fiji...).
    """

    def __init__(self, box, rect, wrap=False, pad=0):
        lon0, lat0, lon1, lat1 = box
        x, y, w, h = rect
        w, h = max(1, w - 2 * pad), max(1, h - 2 * pad)
        self.box, self.rect, self.wrap = tuple(box), tuple(rect), wrap
        self.k = max(0.25, math.cos(math.radians((lat0 + lat1) / 2)))
        span_x, span_y = max(1e-6, (lon1 - lon0) * self.k), max(1e-6, lat1 - lat0)
        self.scale = min(w / span_x, h / span_y)  # pixels por grau
        self.ox = x + pad + (w - span_x * self.scale) / 2
        self.oy = y + pad + (h - span_y * self.scale) / 2
        self.lon0, self.lat1 = lon0, lat1

    def project(self, lon, lat):
        if self.wrap and lon < 0:
            lon += 360
        return (self.ox + (lon - self.lon0) * self.k * self.scale, self.oy + (self.lat1 - lat) * self.scale)

    def project_ring(self, ring):
        """Um contorno inteiro. Na vista com linha de data, só desloca o contorno que está todo no lado oeste
        (assim a Argélia, que tem pontos de lon negativa e positiva, não vira uma faixa esticada)."""
        if self.wrap and max(lon for lon, _ in ring) < 0:
            return [self.project(lon + 360, lat) for lon, lat in ring]
        return [self.project(lon, lat) for lon, lat in ring]

    def visible(self, ring_box):
        """Teste rápido (em graus) de uma caixa (minlon, minlat, maxlon, maxlat) contra a área desenhável."""
        x, y, w, h = self.rect
        lon_lo = self.lon0 + (x - self.ox) / (self.k * self.scale)
        lon_hi = self.lon0 + (x + w - self.ox) / (self.k * self.scale)
        lat_hi = self.lat1 - (y - self.oy) / self.scale
        lat_lo = self.lat1 - (y + h - self.oy) / self.scale
        a, b, c, d = ring_box
        if self.wrap and c < 0:
            a, c = a + 360, c + 360
        return not (c < lon_lo or a > lon_hi or d < lat_lo or b > lat_hi)


def bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def ring_area(points):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def point_in_ring(point, ring):
    """Regra par-ímpar. `ring` é uma lista de (x, y)."""
    x, y = point
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def clip_ring(points, rect):
    """Sutherland–Hodgman: recorta o polígono para caber no retângulo (x, y, largura, altura)."""
    x0, y0, x1, y1 = rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]
    edges = (
        (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
        (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1)),
    )
    out = points
    for inside, cut in edges:
        if not out:
            break
        source, out = out, []
        previous = source[-1]
        for current in source:
            if inside(current):
                if not inside(previous):
                    out.append(cut(previous, current))
                out.append(current)
            elif inside(previous):
                out.append(cut(previous, current))
            previous = current
    return out


def pick_direction(current, positions, dx, dy):
    """Índice do vizinho mais natural ao andar na direção (dx, dy) da tela. Devolve `current` se não há ninguém."""
    cx, cy = positions[current]
    best, best_score = current, None
    for i, (x, y) in enumerate(positions):
        if i == current:
            continue
        along = (x - cx) * dx + (y - cy) * dy
        if along <= 0.5:
            continue
        across = abs((x - cx) * dy - (y - cy) * dx)
        score = along + 2.2 * across
        if best_score is None or score < best_score:
            best, best_score = i, score
    return best
