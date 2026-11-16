"""Monstros em pixel art gerados por código: cada monstro tem sempre o mesmo desenho (sorteado pelo id).
São desenhos provisórios, simétricos, no estilo "invasores do espaço"; arte feita à mão pode substituí-los depois."""
import random
from functools import lru_cache

import pygame

SCALE = 3


def hex_to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


@lru_cache(maxsize=512)
def monster_sprite(monster_id, country_id, palette, boss=False):
    """Devolve uma Surface já ampliada (pixels nítidos). `palette` é uma tupla de 4 cores hex."""
    size = 13 if boss else 11
    half = (size + 1) // 2
    rng = random.Random(f"{country_id}:{monster_id}")
    body, shade = hex_to_rgb(palette[3]), hex_to_rgb(palette[1])
    cells = [[False] * size for _ in range(size)]
    for y in range(1, size - 1):
        for x in range(half):
            edge = x < 2 or y in (1, size - 2)
            cells[y][x] = cells[y][size - 1 - x] = rng.random() < (0.45 if edge else 0.72)
        cells[y][half - 1] = cells[y][size - half] = 2 <= y <= size - 3  # coluna central contínua
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    for y in range(size):
        for x in range(size):
            if cells[y][x]:
                surface.set_at((x, y), body if (x + y) % 3 else shade)
    for y in range(size):  # contorno escuro nos pixels vazios vizinhos
        for x in range(size):
            if not cells[y][x] and any(0 <= y + dy < size and 0 <= x + dx < size and cells[y + dy][x + dx]
                                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                surface.set_at((x, y), (10, 14, 26))
    eye_y, eye_x = size // 3, max(2, half - 3)
    for x in (eye_x, size - 1 - eye_x):  # olhos
        surface.set_at((x, eye_y), (255, 255, 255))
        surface.set_at((x, eye_y + 1), (220, 40, 40) if boss else (20, 20, 30))
    return pygame.transform.scale(surface, (size * SCALE, size * SCALE))
