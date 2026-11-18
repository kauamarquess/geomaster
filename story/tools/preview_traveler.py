"""Gera a folha de visualização do viajante (todas as expressões e animações) em story/viajante-preview.png.

Uso (na pasta principal do projeto):  python story/tools/preview_traveler.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame

import traveler

SCALE = 8
LABELS = {"idle0": "parado", "idle1": "respirando", "walk0": "andando 1", "walk1": "andando 2",
          "happy": "acertou", "hurt": "errou", "down": "derrotado"}

pygame.init()
pygame.display.set_mode((10, 10))
font = pygame.font.Font(None, 22)
cell_w, cell_h = traveler.W * SCALE + 24, traveler.H * SCALE + 46
sheet = pygame.Surface((cell_w * len(LABELS) + 24 + 150, cell_h + 24))
sheet.fill((11, 29, 51))
for i, (name, label) in enumerate(LABELS.items()):
    x = 24 + i * cell_w
    sheet.blit(traveler.frame(name, SCALE), (x, 12))
    text = font.render(label, True, (240, 244, 250))
    sheet.blit(text, (x + (traveler.W * SCALE - text.get_width()) // 2, traveler.H * SCALE + 20))
x = 24 + len(LABELS) * cell_w
sheet.blit(traveler.mini(SCALE), (x, 12))
sheet.blit(font.render("mapa", True, (240, 244, 250)), (x, traveler.H * SCALE + 20))
out = Path(__file__).resolve().parent.parent / "viajante-preview.png"
pygame.image.save(sheet, str(out))
print("gravado", out)
