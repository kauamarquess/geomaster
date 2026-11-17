"""Gera story/data/map.json: as formas dos países e a posição das 10 fases dentro de cada país.

Uso (na pasta principal do projeto):
    python story/tools/build_map_data.py

Fonte: data/geojson/countries.geojson (o mesmo mapa do site). O arquivo gerado já vem no projeto;
só rode de novo se trocar o GeoJSON ou quiser mudar as regras abaixo.

Regras:
  * "foco" de um país = a maior ilha/polígono + os que têm pelo menos 15% do tamanho dela
    (assim a Indonésia e o Japão mostram o arquivipélago, e a Rússia/EUA não esticam até a linha de data).
  * países cujo desenho é só um ponto minúsculo (Vaticano, Mônaco...) ganham uma "mancha" de ilha ampliada.
  * as 10 fases ficam DENTRO do país, bem espalhadas, ligadas por um caminho; a fase 10 (chefão) fica no
    ponto mais interno do país.
"""
import json
import math
import zlib
from pathlib import Path

STORY = Path(__file__).resolve().parent.parent
ROOT = STORY.parent
GEO = ROOT / "data/geojson/countries.geojson"
WORLD = STORY / "data/world-order.json"
OUT = STORY / "data/map.json"

STAGES = 10
Q = 100  # as coordenadas guardadas são inteiros em centésimos de grau

WORLD_BOX = [-180, -58, 180, 84]
# caixa de cada continente: lon0, lat0, lon1, lat1 (o jogo ainda mostra a vizinhança em volta, mais escura)
REGIONS = {
    "south_america": {"box": [-84, -57, -32, 14], "wrap": False, "nav": [-60, -15]},
    "central_america": {"box": [-93, 5, -58, 28], "wrap": False, "nav": [-80, 15]},
    "north_america": {"box": [-170, 14, -10, 84], "wrap": False, "nav": [-100, 45]},
    "europe": {"box": [-25, 34, 60, 72], "wrap": False, "nav": [15, 50]},
    "africa": {"box": [-26, -36, 60, 38], "wrap": False, "nav": [20, 5]},
    "asia": {"box": [25, -12, 150, 60], "wrap": False, "nav": [90, 35]},
    "oceania": {"box": [110, -50, 235, 22], "wrap": True, "nav": [145, -25]},
}


def area(ring):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def quantize(ring):
    """Arredonda para centésimos de grau, tira a repetição do último ponto e pontos seguidos iguais."""
    pts = [(round(x * Q), round(y * Q)) for x, y in ring]
    if pts and pts[0] == pts[-1]:
        pts.pop()
    out = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    return out if len(out) >= 3 else None


def polygons(feature):
    geo = feature["geometry"]
    raw = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
    result = []
    for poly in raw:
        outer = quantize(poly[0])
        if outer is None:
            continue
        holes = [h for h in (quantize(r) for r in poly[1:]) if h]
        result.append({"outer": outer, "holes": holes})
    return result


def flat(ring, scale=1):
    return [round(v * scale) if scale != 1 else v for point in ring for v in point]


# ---------------------------------------------------------------- posição das fases

def seg_dist2(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    ex, ey = ax + t * dx - px, ay + t * dy - py
    return ex * ex + ey * ey


def candidates(poly, k, step):
    """Pontos de grade DENTRO do polígono (já sem buracos), com a distância até a borda (coordenadas x*k)."""
    rings = [poly["outer"]] + poly["holes"]
    edges = []
    for ring in rings:
        for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
            edges.append((ax * k, ay, bx * k, by))
    xs, ys = [e[0] for e in edges], [e[1] for e in edges]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    step = min(step, max(x1 - x0, y1 - y0) / 12) or step
    found = []
    y = y0 + step / 2
    while y < y1:
        x = x0 + step / 2
        while x < x1:
            inside = False
            for ax, ay, bx, by in edges:
                if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                    inside = not inside
            if inside:
                d2 = min(seg_dist2(x, y, *e) for e in edges)
                found.append((x, y, math.sqrt(d2)))
            x += step
        y += step
    return found


def order_path(points, boss):
    """Caminho que começa no ponto mais distante do chefão, termina nele e evita cruzar a si mesmo."""
    dist = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    rest = list(points)
    start = max(rest, key=lambda p: dist(p, boss))
    rest.remove(start)
    path = [start]
    while rest:
        nearest = min(rest, key=lambda p: dist(p, path[-1]))
        rest.remove(nearest)
        path.append(nearest)
    path.append(boss)
    length = lambda route: sum(dist(a, b) for a, b in zip(route, route[1:]))
    improved = True
    while improved:  # 2-opt com as pontas fixas
        improved = False
        for i in range(1, len(path) - 2):
            for j in range(i + 1, len(path) - 1):
                trial = path[:i] + path[i:j + 1][::-1] + path[j + 1:]
                if length(trial) < length(path) - 1e-12:
                    path, improved = trial, True
    return path


def place_stages(polys, main_index):
    """Devolve as 10 posições (lon, lat), a fase 10 por último, todas dentro das formas `polys`."""
    pts = [p for poly in polys for p in poly["outer"]]
    lat_mid = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2 / Q
    k = max(0.25, math.cos(math.radians(lat_mid)))
    span = max((max(p[0] for p in pts) - min(p[0] for p in pts)) * k, max(p[1] for p in pts) - min(p[1] for p in pts))
    for refine in (1, 2, 4, 8):
        step = span / (34 * refine)
        per_poly = [candidates(poly, k, step) for poly in polys]
        for factor in (0.35, 0.15, 0.0):
            chosen = []
            for found in per_poly:
                if found:
                    deepest = max(c[2] for c in found)
                    chosen.extend((x, y, d) for x, y, d in found if d >= factor * deepest)
            if len(chosen) >= STAGES:
                break
        if len(chosen) >= STAGES:
            break
    if len(chosen) < STAGES:
        raise RuntimeError("poucos pontos candidatos")
    boss_pool = per_poly[main_index] or chosen
    boss = max(boss_pool, key=lambda c: c[2])
    picked = [boss]
    gap = [math.hypot(c[0] - boss[0], c[1] - boss[1]) for c in chosen]
    while len(picked) < STAGES:
        i = max(range(len(chosen)), key=lambda n: gap[n])
        picked.append(chosen[i])
        gap = [min(g, math.hypot(c[0] - chosen[i][0], c[1] - chosen[i][1])) for g, c in zip(gap, chosen)]
    route = order_path([(c[0], c[1]) for c in picked[1:]], (boss[0], boss[1]))
    return [(x / k / Q, y / Q) for x, y in route]


def blob(poly, seed):
    """Mancha irregular de ilha (em centésimos de grau fracionários) para países que são só um ponto."""
    xs, ys = [p[0] for p in poly["outer"]], [p[1] for p in poly["outer"]]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    radius = max(5.0, 0.9 * max(max(xs) - min(xs), max(ys) - min(ys)))
    rng = zlib.crc32(seed.encode())
    ring = []
    for i in range(14):
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        wobble = 0.82 + 0.36 * (rng % 1000) / 1000
        angle = 2 * math.pi * i / 14
        ring.append((cx + radius * wobble * math.cos(angle), cy + radius * wobble * math.sin(angle)))
    return {"outer": ring, "holes": []}


# ---------------------------------------------------------------- principal

def build():
    world = json.loads(WORLD.read_text(encoding="utf-8"))
    wanted = {c for region in world["order"] for c in region["countries"]}
    features = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    countries, blobs = {}, []
    for feature in sorted(features, key=lambda f: f["properties"]["id"]):
        cid = feature["properties"]["id"]
        polys = polygons(feature)
        if not polys:
            continue
        areas = [area(p["outer"]) for p in polys]
        main = max(range(len(polys)), key=lambda i: areas[i])
        focus = [i for i in range(len(polys)) if areas[i] >= 0.15 * areas[main]]
        focus_polys = [polys[i] for i in focus]
        main_in_focus = focus.index(main)
        spans = (max(p[0] for p in polys[main]["outer"]) - min(p[0] for p in polys[main]["outer"]),
                 max(p[1] for p in polys[main]["outer"]) - min(p[1] for p in polys[main]["outer"]))
        use_blob = len(polys[main]["outer"]) <= 6 or max(spans) < 15
        if use_blob:
            focus_polys, main_in_focus = [blob(polys[main], cid)], 0
            blobs.append(cid)
        # países que cruzam a linha de data (Fiji, Kiribati): empurra o lado oeste para +360
        lons = [p[0] / Q for poly in focus_polys for p in poly["outer"]]
        wrap = min(lons) < -90 and max(lons) > 90
        if wrap:
            focus_polys = [{"outer": [((x + 360 * Q) if x < 0 else x, y) for x, y in poly["outer"]],
                            "holes": [[((x + 360 * Q) if x < 0 else x, y) for x, y in h] for h in poly["holes"]]}
                           for poly in focus_polys]
        nodes = place_stages(focus_polys, main_in_focus)
        pts = [p for poly in focus_polys for p in poly["outer"]]
        entry = {
            "r": [flat(p["outer"]) for p in polys],
            "f": focus,
            "n": [[round(lon, 4), round(lat, 4)] for lon, lat in nodes],
            "c": [round(nodes[-1][0], 4), round(nodes[-1][1], 4)],
            "box": [round(min(p[0] for p in pts) / Q, 3), round(min(p[1] for p in pts) / Q, 3),
                    round(max(p[0] for p in pts) / Q, 3), round(max(p[1] for p in pts) / Q, 3)],
        }
        holes = [flat(h) for poly in polys for h in poly["holes"]]
        if holes:
            entry["h"] = holes
        if use_blob:
            entry["bl"] = [round(v / Q, 4) for point in focus_polys[0]["outer"] for v in point]
        if wrap:
            entry["w"] = 1
        countries[cid] = entry
    missing = sorted(wanted - set(countries))
    if missing:
        raise SystemExit(f"países da jornada sem desenho no GeoJSON: {missing}")
    data = {"version": 1, "q": Q, "world": {"box": WORLD_BOX}, "regions": REGIONS, "countries": countries}
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"{len(countries)} países, {len(blobs)} com mancha de ilha: {' '.join(blobs)}")
    print(f"gravado {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
