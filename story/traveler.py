"""A skin do viajante: um explorador de chapéu de aba larga, cachecol vermelho e cajado, em pixel art 16x20.

O desenho é feito em camadas de texto (cabeça, corpo, pernas) e montado em quadros:
  idle0/idle1 (respirando), walk0/walk1 (andando), happy (acertou), hurt (errou) e down (derrotado).
Cada letra é uma cor da PALETTE; "." é transparente. Para mudar o visual basta editar as cores ou as letras.
"""
import pygame

W, H = 16, 20

PALETTE = {
    "K": (10, 14, 26),     # contorno
    "H": (166, 104, 58),   # chapéu
    "h": (118, 70, 40),    # sombra do chapéu
    "G": (242, 201, 76),   # faixa do chapéu, fivela e ponta do cajado
    "F": (240, 190, 150),  # pele
    "f": (206, 144, 112),  # pele na sombra do chapéu
    "E": (24, 26, 44),     # olhos
    "M": (104, 44, 52),    # boca
    "R": (240, 120, 120),  # bochecha corada
    "S": (214, 72, 72),    # cachecol
    "s": (150, 42, 54),    # sombra do cachecol
    "C": (52, 140, 150),   # capa/túnica
    "c": (34, 98, 116),    # sombra da capa
    "B": (112, 72, 42),    # alças da mochila
    "b": (176, 128, 80),   # fivela do cinto
    "P": (74, 84, 124),    # calça
    "T": (62, 42, 32),     # botas
    "L": (200, 154, 98),   # cajado
    "W": (150, 210, 245),  # gota de suor
}

# chapéu (linhas 0 a 4) — igual em todos os quadros
HAT = [
    ".....KKKKKK.....",
    "....KHHhHHHK....",
    "....KGGGGGGK....",
    ".KHHHHHHHHHHHHK.",
    ".KKKKKKKKKKKKKK.",
]

# rosto (linhas 5 a 10), uma variante por expressão
FACES = {
    "neutral": ["....KffffffK....", "....KFEFFEFK....", "....KFFFFFFK....", "....KFFFFFFK....", "....KFFMMFFK....", "....KFFFFFFK...."],
    "happy":   ["....KffffffK....", "....KEEFFEEK....", "....KRFFFFRK....", "....KFMMMMFK....", "....KFFMMFFK....", "....KFFFFFFK...."],
    "hurt":    ["....KffffffK....", "....KEEFFEEK...W", "....KFFFFFFK....", "....KFFMMFFK....", "....KFFMMFFK....", "....KFFFFFFK...."],
    "down":    ["....KffffffK....", "....KEFFFFEK....", "....KFEFFEFK....", "....KFFFFFFK....", "....KFFMMFFK....", "....KFFFFFFK...."],
}

# corpo (linhas 11 a 16): pescoço com cachecol, túnica com braços e mãos, cinto
BODY = [
    "....KSSSSSSK....",
    "...KCCSssSCCK...",
    "..KCBCCCCCCBCK..",
    "..KCBCCCCCCBCK..",
    "..KFCCbGGbCCFK..",
    "..KKcCCCCCCcKK..",
]

# pernas (linhas 17 a 19), dois passos de caminhada
LEGS = {
    "stand": ["....KPPKKPPK....", "....KPPK.KPPK...", "....KTTK.KTTK..."],
    "step_a": ["....KPPKKPPK....", "...KPPK..KPPK...", "...KTTK..KTTK..."],
    "step_b": ["....KPPKKPPK....", "....KPPK..KPPK..", "....KTTK..KTTK.."],
}

FRAMES = {  # quadro -> (rosto, pernas, deslocamento da cabeça, deslocamento do corpo todo)
    "idle0": ("neutral", "stand", 0, (0, 0)),
    "idle1": ("neutral", "stand", 1, (0, 0)),
    "walk0": ("neutral", "step_a", 0, (0, 0)),
    "walk1": ("neutral", "step_b", 1, (0, 0)),
    "happy": ("happy", "stand", 0, (0, 0)),
    "hurt": ("hurt", "stand", 1, (-1, 0)),
    "down": ("down", "stand", 2, (0, 0)),
}


def _grid(frame):
    """Monta o quadro como lista de linhas de texto (16x20)."""
    face, legs, head_drop, (dx, _) = FRAMES[frame]
    head = HAT + FACES[face]  # 11 linhas (0 a 10)
    rows = [list("." * W) for _ in range(H)]

    def paste(lines, top):
        for i, line in enumerate(lines):
            y = top + i
            if 0 <= y < H:
                for x, ch in enumerate(line):
                    if ch != "." and 0 <= x + dx < W:
                        rows[y][x + dx] = ch

    paste(BODY + LEGS[legs], 11)
    paste(head, head_drop)  # a cabeça desce (respirar, golpe) e cobre um pouco do cachecol
    top = 6 + min(head_drop, 1)  # o cajado na mão direita acompanha o corpo
    for y in range(top + 1, H):
        if rows[y][14 + dx] == ".":
            rows[y][14 + dx] = "L"
    rows[top][14 + dx] = "G"
    return ["".join(r) for r in rows]


def _surface(grid, scale):
    surface = pygame.Surface((W, H), pygame.SRCALPHA)
    for y, line in enumerate(grid):
        for x, ch in enumerate(line):
            if ch != ".":
                surface.set_at((x, y), PALETTE[ch])
    return pygame.transform.scale(surface, (W * scale, H * scale)) if scale != 1 else surface


_cache = {}


def frame(name, scale=1):
    """Surface do viajante no quadro `name` (veja FRAMES), ampliada `scale` vezes sem borrar."""
    key = (name, scale)
    if key not in _cache:
        _cache[key] = _surface(_grid(name), scale)
    return _cache[key]


def idle(t, scale=1):
    """O viajante respirando: troca de quadro a cada meio segundo."""
    return frame("idle1" if int(t * 2) % 2 else "idle0", scale)


def walking(t, scale=1):
    return frame("walk1" if int(t * 4) % 2 else "walk0", scale)


def portrait(name="idle0", scale=1):
    """Só o chapéu, o rosto e o cachecol (16x12), para o painel de vida do combate."""
    key = ("portrait", name, scale)
    if key not in _cache:
        _cache[key] = frame(name, scale).subsurface((0, 0, W * scale, 12 * scale)).copy()
    return _cache[key]


MINI = [
    "..KKKKK..",
    ".KHHGHHK.",
    "KKKKKKKKK",
    ".KFEFEFK.",
    ".KFFFFFK.",
    ".KSSSSSK.",
    "KCCCCCCCK",
    "KCCbGbCCK",
    ".KPPKPPK.",
    ".KTTKTTK.",
]


def mini(scale=1):
    """Versão minúscula (9x10) para marcar 'você está aqui' nos mapas."""
    key = ("mini", scale)
    if key not in _cache:
        surface = pygame.Surface((9, 10), pygame.SRCALPHA)
        for y, line in enumerate(MINI):
            for x, ch in enumerate(line):
                if ch != ".":
                    surface.set_at((x, y), PALETTE[ch])
        _cache[key] = pygame.transform.scale(surface, (9 * scale, 10 * scale)) if scale != 1 else surface
    return _cache[key]
