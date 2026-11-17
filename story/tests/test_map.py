"""Testes do mapa (sem pygame). Rodar: python -m unittest discover -s story/tests"""
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mapgeo import View, bbox, clip_ring, pick_direction, point_in_ring

STORY = Path(__file__).resolve().parent.parent
MAP = json.loads((STORY / "data/map.json").read_text(encoding="utf-8"))
WORLD = json.loads((STORY / "data/world-order.json").read_text(encoding="utf-8"))
Q = MAP["q"]


def rings(flat):
    return [(flat[i] / Q, flat[i + 1] / Q) for i in range(0, len(flat), 2)]


class MapData(unittest.TestCase):
    def test_todo_pais_da_jornada_tem_desenho_e_dez_fases(self):
        for region in WORLD["order"]:
            for cid in region["countries"]:
                entry = MAP["countries"][cid]
                self.assertEqual(len(entry["n"]), 10, cid)
                self.assertEqual(entry["c"], entry["n"][-1], cid)  # o chefão (fase 10) é o centro do país

    def test_todo_continente_tem_caixa_e_ponto_de_navegacao(self):
        for region in WORLD["order"]:
            spec = MAP["regions"][region["id"]]
            lon0, lat0, lon1, lat1 = spec["box"]
            self.assertTrue(lon0 < lon1 and lat0 < lat1)
            self.assertEqual(len(spec["nav"]), 2)

    def test_fases_ficam_dentro_do_pais(self):
        for cid, entry in MAP["countries"].items():
            if "bl" in entry:
                shape = [list(zip(entry["bl"][0::2], entry["bl"][1::2]))]
                holes = []
            else:
                shape = [rings(entry["r"][i]) for i in entry["f"]]
                holes = [rings(h) for h in entry.get("h", [])]
            for lon, lat in entry["n"]:
                if entry.get("w"):
                    shape_ok = any(point_in_ring((lon, lat), [(x + 360 if x < 0 else x, y) for x, y in ring]) for ring in shape)
                else:
                    shape_ok = any(point_in_ring((lon, lat), ring) for ring in shape)
                self.assertTrue(shape_ok, f"{cid}: fase fora do país em {lon},{lat}")
                inside_hole = any(point_in_ring((lon, lat), hole) for hole in holes)
                self.assertFalse(inside_hole, f"{cid}: fase dentro de um buraco (enclave)")

    def test_fases_nao_se_sobrepoem(self):
        journey = {c for region in WORLD["order"] for c in region["countries"]}
        for cid in journey:
            entry = MAP["countries"][cid]
            box = entry["box"]
            size = max(box[2] - box[0], box[3] - box[1])
            nodes = entry["n"]
            gaps = [math.dist(a, b) for i, a in enumerate(nodes) for b in nodes[i + 1:]]
            self.assertGreater(min(gaps), size * 0.02, f"{cid}: duas fases quase no mesmo lugar")

    def test_arquivo_continua_leve(self):
        self.assertLess((STORY / "data/map.json").stat().st_size, 600_000)


class Geometry(unittest.TestCase):
    def test_vista_encaixa_a_caixa_no_retangulo(self):
        view = View((-10, 40, 30, 60), (0, 0, 320, 100))
        x0, y0 = view.project(-10, 60)
        x1, y1 = view.project(30, 40)
        self.assertTrue(0 <= x0 < x1 <= 320 and 0 <= y0 < y1 <= 100)
        self.assertTrue(abs((y1 - y0) - 100) < 1 or abs((x1 - x0) - 320) < 1)  # encosta em pelo menos um lado

    def test_vista_com_linha_de_data(self):
        view = View((170, -20, 200, 0), (0, 0, 200, 100), wrap=True)
        self.assertAlmostEqual(view.project(-170, -10)[0], view.project(190, -10)[0])  # -170° == 190°

    def test_visivel_descarta_o_que_esta_longe(self):
        view = View((-10, 40, 30, 60), (0, 0, 320, 100))
        self.assertTrue(view.visible((0, 45, 5, 50)))
        self.assertFalse(view.visible((100, 45, 110, 50)))

    def test_ponto_no_poligono(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        self.assertTrue(point_in_ring((5, 5), square))
        self.assertFalse(point_in_ring((15, 5), square))

    def test_recorte_mantem_so_o_que_cabe(self):
        out = clip_ring([(-50, -50), (150, -50), (150, 150), (-50, 150)], (0, 0, 100, 100))
        self.assertEqual(bbox(out), (0, 0, 100, 100))
        self.assertEqual(clip_ring([(200, 200), (300, 200), (300, 300)], (0, 0, 100, 100)), [])

    def test_direcao_escolhe_o_vizinho_certo(self):
        spots = [(50, 50), (80, 52), (20, 48), (52, 90), (51, 10)]
        self.assertEqual(pick_direction(0, spots, 1, 0), 1)
        self.assertEqual(pick_direction(0, spots, -1, 0), 2)
        self.assertEqual(pick_direction(0, spots, 0, 1), 3)
        self.assertEqual(pick_direction(0, spots, 0, -1), 4)
        self.assertEqual(pick_direction(1, spots, 1, 0), 1)  # ninguém mais à direita: fica onde está


if __name__ == "__main__":
    unittest.main()
