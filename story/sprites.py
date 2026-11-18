"""Sprites de monstros em pixel art detalhada, guiadas pelo nome e pela lenda.
Cada criatura recebe silhueta, anatomia, ornamentos e marcas determinísticas próprias.
"""
import math
import random
from functools import lru_cache
import pygame

SCALE = 3
INK = (10, 14, 26)
LIGHT = (255, 239, 190)


def hex_to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _family(text):
    s = text.lower()
    rules = {
        'serpent': ('serpente','cobra','naga','wyrm','worm','boitata','dragão-serpente','hydra','hidra','basilisco','leviatã','leviathan','quetzal','jiboia'),
        'bird': ('ave','pássaro','passaro','corvo','águia','aguia','harpia','fênix','fenix','phoenix','roc','garuda','albatroz','arara','grifo'),
        'quadruped': ('lobo','wolf','cão','cao','cachorro','raposa','fox','gato','tigre','leão','leao','urso','bear','javali','cavalo','cervo','touro','cerbero','cérbero','mula','pantera','onça','onca'),
        'aquatic': ('peixe','boto','sereia','sereio','tubarão','tubarao','baleia','polvo','kraken','nessie','monstro marinho','salamandra aquática'),
        'insect': ('aranha','besouro','mariposa','borboleta','vespa','formiga','gafanhoto','escorpião','escorpiao','centopeia','mosquito','inseto'),
        'ghost': ('fantasma','espectro','banshee','alma','espírito','espirito','sombra','wraith','phantom','poltergeist','fogo-fátuo','fogo fatuo','soucouyant'),
        'dragon': ('dragão','dragao','drake','wyvern','demônio','demonio','diabo','oni','ogro','gigante','titã','tita','beemote','troll'),
    }
    for family, words in rules.items():
        if any(w in s for w in words):
            return family
    return 'humanoid'


def _draw_pixel(s, x, y, color):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((x, y), color)


def _outline(s):
    src = s.copy()
    for y in range(s.get_height()):
        for x in range(s.get_width()):
            if src.get_at((x, y)).a and any(
                not (0 <= x + dx < s.get_width() and 0 <= y + dy < s.get_height())
                or not src.get_at((x + dx, y + dy)).a
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))
            ):
                _draw_pixel(s, x, y, INK)



def _folklore_base(monster_id, palette, boss=False, name="", legend=""):
    """Sprites autorais para as lendas brasileiras do primeiro conjunto de fases."""
    W = H = 32
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    ink=(18,12,22); skin=(173,103,61); light=(255,220,160)
    green=(43,112,55); darkgreen=(20,65,42); red=(205,38,35)
    def poly(c, pts): pygame.draw.polygon(s,c,pts)
    def ell(c, rect): pygame.draw.ellipse(s,c,rect)
    def line(c, pts, width=1): pygame.draw.lines(s,c,False,pts,width)
    ell((5,8,12,125),(5,27,22,4))
    mid=f'{monster_id} {name} {legend}'.lower()
    if 'saci' in mid:
        # Menino de gorro vermelho, uma perna e redemoinho de vento.
        ell(skin,(10,9,13,13)); ell((20,20,20),(12,13,3,2)); ell(ink,(16,14,2,2))
        poly(red,[(8,12),(7,7),(11,3),(19,3),(24,7),(22,10),(15,8),(10,12)])
        poly((245,75,48),[(11,5),(15,2),(20,4),(22,7),(15,6)])
        poly((54,91,55),[(9,19),(13,17),(20,18),(23,23),(19,26),(10,25)])
        line(skin,[(10,18),(6,22),(9,24)],3); line(skin,[(20,18),(25,19),(27,16)],3)
        line(skin,[(16,24),(15,29),(19,29)],3)
        pygame.draw.arc(s,(183,125,75),(2,17,29,29),.1,5.8,1)
        ell((255,180,80),(25,14,2,2))
    elif 'curupira' in mid:
        # Guardião da mata: cabelo em chamas e pés voltados para trás.
        ell(skin,(10,10,13,12)); ell(ink,(13,15,2,2)); ell(ink,(19,15,2,2))
        for pts in [[(10,12),(5,8),(8,7),(7,2),(12,5)],[(13,9),(12,2),(16,0),(17,6)],[(17,8),(21,2),(24,4),(21,10)],[(20,10),(27,7),(25,13)]]: poly((238,76,25),pts)
        poly((255,177,40),[(12,7),(14,2),(16,6),(19,3),(18,9)])
        poly(darkgreen,[(10,20),(7,17),(10,16),(15,18),(21,16),(24,20),(21,26),(11,26)])
        line(skin,[(11,19),(6,22),(8,25)],3); line(skin,[(21,19),(25,22),(23,25)],3)
        # Calcanhares apontam para a frente: detalhe gráfico dos pés invertidos.
        poly((205,145,96),[(5,24),(2,22),(3,26),(8,27)]); poly((205,145,96),[(22,24),(26,22),(25,26),(21,27)])
        ell(green,(8,18,3,3)); ell(green,(21,18,3,3))
    elif 'boto' in mid:
        # Boto-cor-de-rosa, corpo de golfinho e chapéu branco da versão encantada.
        poly((232,112,151),[(3,19),(8,12),(17,11),(24,14),(29,12),(26,19),(20,23),(10,23)])
        poly((255,177,196),[(7,17),(14,14),(22,16),(26,16),(21,20),(11,20)])
        poly((222,91,139),[(7,18),(2,14),(4,22)]); poly((222,91,139),[(23,15),(28,10),(26,17)])
        ell(ink,(22,15,2,2)); poly((255,255,238),[(12,9),(14,5),(20,5),(23,9),(21,10),(14,10)])
        line((130,215,240),[(5,25),(8,27),(11,25)],1)
    elif 'mula' in mid and ('cabeca' in mid or 'cabeça' in mid):
        # Corpo equino sem cabeça, com labaredas no pescoço.
        ell((102,53,35),(7,13,19,11)); ell((75,39,31),(21,12,7,8))
        for x in (9,13,21,25): line((58,35,29),[(x,21),(x-1,29)],2)
        poly((255,91,16),[(20,14),(17,9),(20,10),(21,3),(24,9),(27,5),(25,14)])
        poly((255,194,45),[(21,12),(21,6),(23,10),(25,7),(24,14)])
        line((255,100,20),[(8,14),(5,9),(8,11),(9,6)],2)
    elif 'iara' in mid:
        # Sereia dos rios, cabelos escuros e cauda verde-azulada.
        ell(skin,(12,5,10,10)); ell(ink,(15,9,2,2)); ell(ink,(20,9,2,2))
        line((20,24,42),[(13,7),(9,3),(13,1),(17,4),(22,1),(25,5),(23,13)],3)
        poly((22,151,145),[(13,14),(21,14),(23,20),(18,24),(11,21)])
        poly((37,202,174),[(18,21),(24,22),(29,27),(22,26),(18,29),(14,25)])
        poly((38,112,112),[(13,15),(9,18),(13,19)]); poly((38,112,112),[(21,15),(25,18),(21,19)])
        ell((66,225,203),(17,19,2,2)); ell((66,225,203),(21,23,2,2))
    elif 'cuca' in mid:
        # Bruxa-crocodilo: focinho comprido, escamas e cabelo desgrenhado.
        ell((72,145,62),(6,9,20,15)); poly((95,174,72),[(19,13),(29,15),(26,20),(18,19)])
        poly((45,104,49),[(9,11),(5,6),(12,8),(15,3),(18,8),(24,5),(22,12)])
        ell((255,225,90),(21,13,2,2)); ell(ink,(22,13,1,1))
        poly((235,225,176),[(24,18),(27,17),(26,20),(24,20)])
        for x in (11,15,19): line((35,92,43),[(x,22),(x-2,27)],2)
        poly((107,65,145),[(7,21),(4,25),(10,24)])
    elif 'lobisomem' in mid:
        # Licantropo de pelo cinza, focinho, garras e olhos âmbar.
        ell((83,82,100),(6,9,20,16)); poly((101,95,112),[(18,10),(22,5),(24,12),(29,15),(23,20)])
        poly((67,64,83),[(8,12),(4,5),(12,8),(16,3),(19,9),(25,6),(23,14)])
        ell((255,190,55),(20,13,2,2)); ell(ink,(21,13,1,1))
        poly((230,220,207),[(25,18),(28,18),(26,21),(24,20)])
        for x in (8,13,20,24): line((53,48,64),[(x,22),(x-1,29)],2)
        line((230,220,207),[(24,20),(23,22),(25,22)],1)
    elif 'caipora' in mid:
        # Guardiã da mata, cocar de folhas, lança e companheiro caititu sugerido.
        ell(skin,(11,8,12,12)); ell(ink,(14,13,2,2)); ell(ink,(19,13,2,2))
        poly((190,57,36),[(8,9),(5,4),(10,6),(12,1),(15,6),(19,1),(21,7),(25,4),(22,10)])
        poly(green,[(8,19),(12,17),(20,18),(24,23),(20,26),(10,25)])
        line(skin,[(10,19),(6,23),(8,25)],3); line(skin,[(21,19),(25,22),(24,25)],3)
        line((142,102,59),[(25,18),(29,8)],1); ell((75,91,46),(25,6,4,4))
        ell((100,65,48),(2,25,7,4)); ell((100,65,48),(1,24,3,3))
    elif 'mapinguari' in mid:
        # Gigante peludo, um olho central e boca vertical no ventre.
        ell((93,53,40),(5,7,22,22));
        for x,y in ((7,9),(12,5),(20,6),(25,11),(6,19),(25,21),(11,27),(21,28)):
            poly((55,38,34),[(x,y),(x+3,y-3),(x+2,y+2)])
        ell((255,215,80),(14,11,5,5)); ell(ink,(16,12,2,3))
        ell((35,16,20),(12,19,9,8)); line((240,220,190),[(14,21),(16,24),(19,21)],1)
        line((75,43,35),[(9,23),(6,29)],3); line((75,43,35),[(23,23),(26,29)],3)
    elif 'boitata' in mid or 'boitatá' in mid:
        # Serpente de fogo com escamas luminosas e olhos de brasa.
        line((176,75,24),[(3,25),(7,21),(5,17),(11,14),(17,16),(21,11),(18,7),(23,4),(28,7)],6)
        line((255,124,24),[(3,24),(7,20),(6,17),(12,14),(17,15),(21,10),(19,7),(24,5),(28,7)],3)
        line((255,224,95),[(6,22),(9,19),(8,17),(13,15),(17,15),(21,10),(20,8)],1)
        ell((255,245,130),(25,5,2,2)); ell(ink,(26,5,1,1))
        poly((255,168,38),[(27,7),(31,5),(29,9)])
    else:
        return None
    if boss:
        pygame.draw.circle(s,(255,205,85),(16,3),2)
        pygame.draw.circle(s,(255,245,190),(16,3),1)
    # Contorno pixelado de alto contraste.
    src=s.copy()
    for y in range(H):
        for x in range(W):
            if src.get_at((x,y)).a and any(not(0<=x+dx<W and 0<=y+dy<H) or not src.get_at((x+dx,y+dy)).a for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))):
                s.set_at((x,y),ink)
    return s


def _base(monster_id, country_id, palette, boss, name, legend):
    if str(country_id).upper() == 'BRA':
        folklore = _folklore_base(monster_id, palette, boss, name, legend)
        if folklore is not None:
            return folklore
    seed_text = f'{country_id}:{monster_id}:{name}:{legend}'
    rng = random.Random(seed_text)
    family = 'humanoid' if 'medusa' in (monster_id + ' ' + name).lower() else _family(f'{monster_id} {name} {legend}')
    p = [hex_to_rgb(c) for c in palette]
    deep, mid, glow, main = p[0], p[1], p[2], p[3]
    # Cores auxiliares com contraste alto, sem perder a identidade da região.
    shade = tuple(max(0, int(c * .55)) for c in main)
    highlight = tuple(min(255, int(c * .72 + 75)) for c in main)
    accent = glow
    W, H = 24, 25
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    trait = (name + ' ' + legend).lower()
    fire = any(k in trait for k in ('fogo','chama','incênd','incend','brasas','vulc','sol','lava'))
    ice = any(k in trait for k in ('gelo','neve','frio','inverno','geada'))
    stone = any(k in trait for k in ('pedra','rocha','montanha','metal','ferro','armadura','forja'))
    venom = any(k in trait for k in ('veneno','tóxico','toxico','peçonha','peconha','mordida'))
    plant = any(k in trait for k in ('floresta','mata','árvore','arvore','raiz','folha','madeira','flor'))
    aquatic = family == 'aquatic' or any(k in trait for k in ('mar','rio','água','agua','oceano','lago'))
    wings = family == 'bird' or any(k in trait for k in ('asa','asas','voa','voar','voador','alado'))
    horns = any(k in trait for k in ('chifre','chifres','touro','carneiro','cabra','demônio','demonio','diabo'))
    extra_eyes = any(k in trait for k in ('muitos olhos','olhos múltiplos','olhos multiplos','ciclope','um olho','olho só','olho unico','olho único'))
    multiple_heads = any(k in trait for k in ('três cabeças','tres cabecas','muitas cabeças','muitas cabecas','hidra','duas cabeças','duas cabecas','cérbero','cerbero','cerberus'))
    snake_hair = any(k in trait for k in ('cabelos de serpente','cabelo de serpente','cobras no cabelo','serpentes na cabeça','serpentes na cabeca')) or 'medusa' in trait
    single_leg = any(k in trait for k in ('uma perna só','uma perna so','perna única','perna unica')) or 'saci' in trait
    backwards_feet = any(k in trait for k in ('pés virados para trás','pes virados para tras','pés ao contrário','pes ao contrario')) or 'curupira' in trait
    headless = any(k in trait for k in ('sem cabeça','sem cabeca','no lugar da cabeça','no lugar da cabeca'))
    tail = family in ('serpent','dragon','quadruped') or any(k in trait for k in ('cauda','rabo'))

    # Sombra no chão e corpo central: cada família tem proporções diferentes.
    pygame.draw.ellipse(s, (5, 9, 18, 125), (4, 21, 16, 3))
    if family == 'serpent':
        pygame.draw.lines(s, shade, False, [(5,20),(4,17),(7,15),(5,12),(8,10),(9,7),(12,5)], 5)
        pygame.draw.ellipse(s, main, (7,3,11,13))
        pygame.draw.polygon(s, main, [(9,10),(14,8),(19,11),(17,18),(11,20),(7,16)])
        pygame.draw.polygon(s, highlight, [(10,4),(13,2),(17,4),(15,7),(11,7)])
        pygame.draw.polygon(s, accent, [(8,4),(5,1),(11,3)])
        pygame.draw.polygon(s, accent, [(17,4),(20,1),(19,6)])
    elif family == 'bird':
        pygame.draw.polygon(s, shade, [(11,9),(2,4),(4,12),(8,16),(12,14)])
        pygame.draw.polygon(s, main, [(13,8),(22,3),(19,13),(16,17),(12,15)])
        pygame.draw.ellipse(s, main, (7,5,11,14))
        pygame.draw.ellipse(s, highlight, (9,3,8,7))
        pygame.draw.polygon(s, accent, [(15,7),(22,8),(16,10)])
        pygame.draw.polygon(s, shade, [(9,17),(7,23),(11,20),(13,23),(15,17)])
        pygame.draw.polygon(s, accent, [(10,5),(12,1),(14,5)])
    elif family == 'quadruped':
        pygame.draw.ellipse(s, main, (3,9,17,10))
        pygame.draw.ellipse(s, highlight, (13,5,9,9))
        pygame.draw.polygon(s, main, [(15,8),(14,3),(18,6),(20,4),(22,9)])
        for x in (5,9,15,18):
            pygame.draw.rect(s, shade, (x,16,3,6))
            pygame.draw.rect(s, main, (x,17,2,4))
        pygame.draw.polygon(s, shade, [(4,11),(1,7),(2,14),(6,15)])
        pygame.draw.polygon(s, accent, [(17,6),(19,7),(18,9)])
    elif family == 'aquatic':
        pygame.draw.ellipse(s, main, (4,6,16,13))
        pygame.draw.polygon(s, shade, [(5,12),(0,7),(1,17),(7,16)])
        pygame.draw.polygon(s, accent, [(18,11),(23,6),(22,17)])
        pygame.draw.polygon(s, highlight, [(8,7),(11,4),(15,7),(13,10)])
        pygame.draw.polygon(s, shade, [(10,17),(8,22),(13,19),(16,22),(16,17)])
        for x in (8,12,16): pygame.draw.arc(s, accent, (x,10,x+4,15), 0, math.pi, 1)
    elif family == 'insect':
        pygame.draw.ellipse(s, shade, (2,7,9,12)); pygame.draw.ellipse(s, shade, (14,7,9,12))
        pygame.draw.ellipse(s, highlight, (3,8,7,9)); pygame.draw.ellipse(s, highlight, (14,8,7,9))
        pygame.draw.ellipse(s, main, (8,5,9,15))
        pygame.draw.ellipse(s, accent, (9,2,7,7))
        for x in (8,10,14,16):
            pygame.draw.line(s, shade, (12,13),(x-5 if x<12 else x+5,20),2)
        pygame.draw.line(s, accent, (10,4),(7,0),1); pygame.draw.line(s, accent, (15,4),(18,0),1)
    elif family == 'ghost':
        pygame.draw.ellipse(s, main, (5,3,14,15))
        pygame.draw.polygon(s, main, [(5,13),(4,22),(8,19),(12,23),(16,19),(20,22),(19,13)])
        pygame.draw.ellipse(s, highlight, (8,5,8,5))
        pygame.draw.arc(s, accent, (5,8,19,21), math.pi, math.tau, 1)
    elif family == 'dragon':
        pygame.draw.ellipse(s, main, (4,8,16,11))
        pygame.draw.ellipse(s, highlight, (13,4,9,9))
        pygame.draw.polygon(s, shade, [(7,10),(1,3),(3,13),(9,16)])
        pygame.draw.polygon(s, main, [(14,10),(22,2),(20,14),(15,17)])
        pygame.draw.polygon(s, accent, [(15,5),(13,0),(17,4)])
        pygame.draw.polygon(s, accent, [(19,6),(23,3),(22,9)])
        for x in (6,10,14,18): pygame.draw.polygon(s, shade, [(x,9),(x+2,5),(x+4,10)])
        pygame.draw.polygon(s, shade, [(5,16),(2,23),(10,19)])
    else:
        # Humanoides: cabeça, ombros, tronco, braços e pernas em camadas.
        pygame.draw.polygon(s, shade, [(5,11),(2,16),(5,20),(19,20),(22,15),(18,10)])
        pygame.draw.rect(s, main, (7,10,10,10))
        pygame.draw.ellipse(s, highlight, (7,3,10,10))
        pygame.draw.polygon(s, main, [(6,12),(2,15),(5,19),(9,17)])
        pygame.draw.polygon(s, main, [(17,12),(22,15),(19,19),(15,17)])
        pygame.draw.rect(s, shade, (8,18,3,5)); pygame.draw.rect(s, shade, (14,18,3,5))
        pygame.draw.polygon(s, accent, [(7,5),(5,1),(10,4)])
        pygame.draw.polygon(s, accent, [(16,5),(19,1),(18,7)])

    # Traços anatômicos guiados pela descrição da criatura.
    if wings and family not in ('bird','dragon'):
        pygame.draw.polygon(s, shade, [(8,10),(1,4),(3,14),(9,16)])
        pygame.draw.polygon(s, main, [(16,10),(23,4),(21,15),(15,17)])
        for y in (7,10,13):
            pygame.draw.line(s, highlight, (3,y),(8,14),1)
            pygame.draw.line(s, highlight, (20,y),(16,14),1)
    if horns:
        pygame.draw.polygon(s, highlight, [(8,6),(5,0),(11,4)])
        pygame.draw.polygon(s, highlight, [(16,6),(20,0),(18,7)])
    if snake_hair:
        # Serpentes individuais formam uma coroa viva ao redor da cabeça.
        for sx, sy in ((7,4),(9,1),(12,0),(15,1),(18,4)):
            pygame.draw.lines(s, shade, False, [(12,6),(sx,sy),(sx-1, max(0,sy-2))], 2)
            pygame.draw.circle(s, accent, (sx,sy), 1)
            pygame.draw.circle(s, (255,235,160), (sx,sy), 0)
    if multiple_heads:
        for x in (3,17):
            pygame.draw.ellipse(s, main, (x,1,6,7))
            pygame.draw.polygon(s, accent, [(x+1,2),(x-1,0),(x+3,2)])
            pygame.draw.line(s, INK, (x+2,4),(x+4,4),1)
    if single_leg:
        pygame.draw.rect(s, shade, (11,17,3,6))
        pygame.draw.rect(s, main, (12,18,2,4))
        pygame.draw.line(s, highlight, (12,22),(15,23),1)
    if backwards_feet:
        pygame.draw.polygon(s, highlight, [(7,20),(3,22),(8,23)])
        pygame.draw.polygon(s, highlight, [(16,20),(20,22),(15,23)])
    if headless:
        pygame.draw.rect(s, shade, (8,2,8,8))
        pygame.draw.polygon(s, (255,170,55), [(8,3),(6,0),(10,2),(12,0),(14,3),(17,0),(16,5)])
    if tail and family not in ('serpent',):
        pygame.draw.lines(s, shade, False, [(5,17),(2,19),(3,22),(1,24)], 3)
        pygame.draw.polygon(s, accent, [(1,23),(0,20),(4,22)])
    if aquatic:
        for x,y in ((4,8),(19,9),(8,17)):
            pygame.draw.circle(s, highlight, (x,y), 1)
    if fire:
        for x,y in ((5,3),(20,5),(4,16),(19,17)):
            pygame.draw.polygon(s, (255,180,65), [(x,y+2),(x-1,y),(x,y-3),(x+2,y)])
    if ice:
        for x,y in ((4,5),(20,4),(4,17),(19,18)):
            pygame.draw.line(s, (190,240,255), (x-2,y),(x+2,y),1)
            pygame.draw.line(s, (190,240,255), (x,y-2),(x,y+2),1)
    if stone:
        for x,y in ((6,11),(17,12),(11,17)):
            pygame.draw.rect(s, highlight, (x,y,3,2))
            pygame.draw.line(s, shade, (x,y+2),(x+2,y+3),1)
    if plant:
        pygame.draw.line(s, (65,150,75), (4,17),(2,12),2)
        pygame.draw.ellipse(s, (105,190,85), (1,9,5,4))
        pygame.draw.line(s, (65,150,75), (19,17),(22,12),2)
        pygame.draw.ellipse(s, (105,190,85), (19,9,5,4))
    if venom:
        pygame.draw.circle(s, (120,240,95), (18,14), 2)
        pygame.draw.line(s, (180,255,120), (18,14),(20,17),1)
    if family in ('serpent','dragon') or horns:
        pygame.draw.polygon(s, highlight, [(16,8),(21,9),(17,11)])
    # Face: eyes with glow, pupils, brow and mouth; special one-eyed creatures.
    eye_y = 8 if family not in ('bird','serpent') else 6
    if extra_eyes:
        pygame.draw.circle(s, (255,245,180), (12,7), 3)
        pygame.draw.circle(s, INK, (12,7), 1)
    else:
        for ex in (10,16):
            pygame.draw.rect(s, (255,245,190), (ex,eye_y,3,2))
            pygame.draw.rect(s, INK, (ex+1,eye_y,1,2))
        pygame.draw.line(s, shade, (9,eye_y-1),(12,eye_y-2),1)
        pygame.draw.line(s, shade, (16,eye_y-2),(19,eye_y-1),1)
    pygame.draw.line(s, INK, (12,12),(15,12),1)
    if venom or family in ('dragon','quadruped'):
        pygame.draw.line(s, LIGHT, (13,12),(13,14),1)
        pygame.draw.line(s, LIGHT, (16,12),(16,14),1)
    # Belly plates / armor / scales add the handcrafted look.
    if family in ('serpent','dragon','aquatic'):
        for y in (15,17,19):
            pygame.draw.line(s, highlight, (10,y),(15,y),1)
    elif family in ('quadruped','humanoid'):
        pygame.draw.line(s, shade, (9,15),(15,15),1)
        pygame.draw.line(s, highlight, (10,16),(14,16),1)
    # Unique deterministic markings: spots, scars, runes and scale glints.
    for _ in range(9 if boss else 6):
        x, y = rng.randrange(3,21), rng.randrange(9,21)
        if s.get_at((x,y)).a and rng.random() < .72:
            _draw_pixel(s, x, y, accent if rng.random() < .55 else highlight)
    if boss:
        pygame.draw.polygon(s, (255,205,85), [(12,0),(14,3),(12,5),(10,3)])
        pygame.draw.line(s, (255,90,90), (8,8),(17,8),1)
        for x in (4,20): pygame.draw.circle(s, (255,190,75), (x,5), 1)
    _outline(s)
    return s


@lru_cache(maxsize=4096)
def _frame(monster_id, country_id, palette, boss, name, legend, pose):
    base = _base(monster_id, country_id, palette, boss, name, legend)
    s = base.copy()
    if pose == 'attack':
        s = pygame.transform.scale(base, (base.get_width()+2, base.get_height()+1))
        pygame.draw.line(s, (255,220,130), (s.get_width()-7,12),(s.get_width()+1,9),2)
    elif pose == 'hurt':
        s.fill((255,90,90,85), special_flags=pygame.BLEND_RGBA_ADD)
        for x in (4,19): pygame.draw.line(s, (255,245,200), (x,4),(x+2,1),1)
    elif pose == 'defeat':
        s = pygame.transform.rotate(base, 90)
    elif pose == 'idle_b':
        s.blit(s.copy(), (0,-1))
    return pygame.transform.scale(s, (s.get_width()*SCALE, s.get_height()*SCALE))


def monster_sprite(monster_id, country_id, palette, boss=False, t=0.0, action='idle', name='', legend=''):
    """Retorna sprite pixel-art animado e individualizado pelos dados da lenda."""
    pose = action if action in ('attack','hurt','defeat') else ('idle_b' if int(t*2)%2 else 'idle')
    return _frame(str(monster_id), str(country_id), tuple(palette), bool(boss), str(name), str(legend), pose)
