"""Testes da skin do viajante. Rodar: python -m unittest discover -s story/tests"""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame

import traveler


class TravelerSkin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((10, 10))

    def test_todo_quadro_tem_16x20_e_so_usa_cores_da_paleta(self):
        for name in traveler.FRAMES:
            grid = traveler._grid(name)
            self.assertEqual(len(grid), traveler.H, name)
            for row in grid:
                self.assertEqual(len(row), traveler.W, name)
                for ch in row:
                    self.assertTrue(ch == "." or ch in traveler.PALETTE, f"{name}: letra {ch!r} sem cor")

    def test_pecas_do_desenho_tem_o_tamanho_certo(self):
        for part in (traveler.HAT, *traveler.FACES.values(), traveler.BODY, *traveler.LEGS.values(), traveler.MINI):
            width = len(part[0])
            self.assertTrue(all(len(line) == width for line in part))
        self.assertTrue(all(len(HAT_ROW) == 16 for HAT_ROW in traveler.HAT))
        for face in traveler.FACES.values():
            self.assertEqual(len(traveler.HAT) + len(face), 11)  # cabeça de 11 linhas
        self.assertEqual(len(traveler.BODY) + len(next(iter(traveler.LEGS.values()))), 9)  # corpo + pernas = 9 linhas

    def test_expressoes_e_passos_sao_diferentes_entre_si(self):
        grids = {name: tuple(traveler._grid(name)) for name in traveler.FRAMES}
        self.assertEqual(len(set(grids.values())), len(grids))

    def test_ampliacao_e_retrato_e_mini(self):
        self.assertEqual(traveler.frame("idle0", 3).get_size(), (48, 60))
        self.assertEqual(traveler.portrait("happy").get_size(), (16, 12))
        self.assertEqual(traveler.mini().get_size(), (9, 10))
        self.assertIsNotNone(traveler.idle(0.0)); self.assertIsNotNone(traveler.walking(0.3))

    def test_nenhum_quadro_fica_vazio(self):
        for name in traveler.FRAMES:
            self.assertGreater(pygame.mask.from_surface(traveler.frame(name)).count(), 120, name)


if __name__ == "__main__":
    unittest.main()
