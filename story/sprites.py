"""Sprites procedurais de monstros em pixel art, com silhuetas por família e animações.
Cada criatura recebe uma identidade determinística pelo id, país e paleta; não há sprite genérico compartilhado.
"""
import random
from functools import lru_cache
import pygame

SCALE = 5
INK = (10, 14, 26)


def hex_to_rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _family(monster_id):
    s = monster_id.lower()
    groups = {
      'serpent': ('serp','cobra','naga','wyrm','worm','boitata','dragao','dragon','hydra','basilisk','basilisco','leviathan','leviata','sea_serpent','apep','aido_hwedo','bakunawa','amphiptere','quetzal'),
      'bird': ('bird','phoenix','fênix','fenix','eagle','raven','crow','harpy','harpia','roc','bennu','garuda','thunderbird','albatroz','albatroz','corvo','arara'),
      'quadruped': ('wolf','lobo','dog','cao','hound','fox','raposa','cat','tiger','lion','urso','bear','boar','porco','horse','cavalo','deer','stag','bull','touro','amaroq','amarok','cadejo','cerberus','lobisomem'),
      'aquatic': ('fish','peixe','boto','sereia','mermaid','merman','siren','sereio','shark','tubarao','whale','baleia','octopus','polvo','kraken','nessie','bunyip','water','kelpie','adaro'),
      'insect': ('spider','aranha','beetle','besouro','moth','mariposa','butterfly','borboleta','wasp','vespa','ant','formiga','locust','gafanhoto','scorpion','escorpiao','centipede','mosquito'),
      'ghost': ('ghost','fantasma','wraith','specter','banshee','alma','spirit','espirito','phantom','poltergeist','will_o','fatuo','sombra','shadow','djinn','jinn'),
      'dragon': ('dragon','dragao','drake','wyvern','demon','demonio','devil','diabo','oni','ogre','gigante','titan','behemoth','beemote','troll'),
    }
    for family, words in groups.items():
        if any(w in s for w in words): return family
    return ('humanoid','blob','insect','quadruped')[sum(map(ord,s)) % 4]


def _pixel(surface, x, y, color, scale):
    pygame.draw.rect(surface, color, (x*scale, y*scale, scale, scale))


@lru_cache(maxsize=2048)
def _base(monster_id, country_id, palette, boss):
    rng = random.Random(f'{country_id}:{monster_id}')
    family = _family(monster_id)
    p = [hex_to_rgb(c) for c in palette]
    main, shade, accent = p[3], p[1], p[2]
    size = 17 if boss else 15
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    # silhuetas distintas: corpo central + apêndices característicos por família
    if family == 'serpent':
        for y in range(3, size-2):
            cx = size//2 + round(2 * __import__('math').sin(y*.8))
            for x in range(max(1,cx-2), min(size-1,cx+3)):
                _pixel(s,x,y,main if (x+y)%4 else shade,1)
        for x in range(size//2-2,size//2+3): _pixel(s,x,2,accent,1)
        _pixel(s,size//2-1,1,INK,1); _pixel(s,size//2+1,1,INK,1)
        for x in range(2,size-2,3): _pixel(s,x,size-3,accent,1)
    elif family == 'bird':
        for y in range(4,size-3):
            for x in range(4,size-4):
                if abs(x-size//2) + abs(y-size//2)*.65 < 5: _pixel(s,x,y,main,1)
        for x in range(1,5):
            _pixel(s,x,6+(x%2),accent,1); _pixel(s,size-1-x,6+(x%2),accent,1)
        for x in range(size//2-1,size//2+2): _pixel(s,x,2,accent,1)
        _pixel(s,size//2,size//2,INK,1)
    elif family == 'quadruped':
        pygame.draw.rect(s, main, (3,5,size-6,6)); pygame.draw.rect(s, shade,(4,9,size-8,3))
        pygame.draw.rect(s, main,(size-6,3,4,5)); pygame.draw.rect(s,accent,(size-5,5,2,2))
        for x in (4,6,size-7,size-5): pygame.draw.rect(s,main,(x,10,2,4))
        pygame.draw.polygon(s,shade,[(3,6),(1,4),(2,9)])
        _pixel(s,size-4,4,(255,245,190),1)
    elif family == 'aquatic':
        pygame.draw.ellipse(s,main,(3,4,size-6,size-8)); pygame.draw.polygon(s,accent,[(size-4,7),(size-1,4),(size-1,11)])
        pygame.draw.polygon(s,shade,[(6,7),(2,3),(3,10)]); pygame.draw.polygon(s,shade,[(7,size-5),(5,size-1),(10,size-4)])
        for x in range(6,size-5,3): _pixel(s,x,8,accent,1)
    elif family == 'insect':
        pygame.draw.ellipse(s,main,(5,4,size-10,size-7)); pygame.draw.ellipse(s,shade,(3,6,size-6,6))
        for x in (3,5,size-6,size-4):
            pygame.draw.line(s,accent,(size//2,8),(x,3),1); pygame.draw.line(s,main,(size//2,9),(x,13),1)
        pygame.draw.line(s,accent,(6,4),(4,1),1); pygame.draw.line(s,accent,(size-7,4),(size-5,1),1)
    elif family == 'ghost':
        pygame.draw.ellipse(s,main,(3,2,size-6,size-5));
        for x in range(3,size-3,4): pygame.draw.polygon(s,main,[(x,size-5),(x+3,size-5),(x+1,size-1)])
        pygame.draw.ellipse(s,shade,(5,5,size-10,5))
    elif family == 'dragon':
        pygame.draw.ellipse(s,main,(3,5,size-6,size-8)); pygame.draw.rect(s,main,(size-7,3,5,5))
        pygame.draw.polygon(s,accent,[(4,7),(1,2),(7,5)]); pygame.draw.polygon(s,accent,[(size-5,7),(size-1,2),(size-8,5)])
        for x in range(5,size-4,3): _pixel(s,x,4,accent,1)
        pygame.draw.polygon(s,shade,[(4,9),(1,12),(6,11)])
    else:
        pygame.draw.ellipse(s,main,(3,2,size-6,size-3)); pygame.draw.rect(s,shade,(5,9,size-10,4))
        pygame.draw.polygon(s,accent,[(4,5),(2,1),(7,4)]); pygame.draw.polygon(s,accent,[(size-5,5),(size-3,1),(size-8,4)])
    # contorno, olhos e marcas individuais
    for y in range(size):
      for x in range(size):
        if s.get_at((x,y)).a and (x in (0,size-1) or y in (0,size-1) or any(not s.get_at((x+dx,y+dy)).a for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)) if 0<=x+dx<size and 0<=y+dy<size)):
          _pixel(s,x,y,INK,1)
    eye_y = 6 if family not in ('bird','serpent') else 4
    if family == 'serpent': eyes=[(size//2-2,3),(size//2+2,3)]
    else: eyes=[(size//2-3,eye_y),(size//2+3,eye_y)]
    for x,y in eyes:
      if 0<=x<size and 0<=y<size: _pixel(s,x,y,(255,245,190),1)
    if boss:
      pygame.draw.rect(s,(255,65,65),(size//2-1,eye_y,3,2))
      for x in range(1,size,4): _pixel(s,x,1,accent,1)
    # pequenas marcas exclusivas para cada criatura
    for _ in range(5):
      x,y=rng.randrange(2,size-2),rng.randrange(7,size-2)
      if s.get_at((x,y)).a: _pixel(s,x,y,accent if rng.random()<.65 else shade,1)
    return s


@lru_cache(maxsize=2048)
def _animated_frame(monster_id, country_id, palette, boss, pose):
    base = _base(monster_id,country_id,palette,boss)
    s=base.copy(); family=_family(monster_id)
    if pose == 'attack':
      s=pygame.transform.scale(base,(base.get_width()+2,base.get_height()+2))
      if family in ('serpent','dragon','quadruped'): pygame.draw.line(s,hex_to_rgb(palette[2]),(s.get_width()//2,s.get_height()-2),(s.get_width()//2+5, s.get_height()+2),2)
    elif pose == 'hurt':
      s.fill((255,100,100,90), special_flags=pygame.BLEND_RGBA_ADD)
    elif pose == 'defeat':
      s=pygame.transform.rotate(base,90)
    return pygame.transform.scale(s,(s.get_width()*SCALE,s.get_height()*SCALE))


def monster_sprite(monster_id, country_id, palette, boss=False, t=0.0, action='idle'):
    """Sprite grande animado; idle pulsa, attack avança, hurt pisca e defeat tomba."""
    pose = action if action in ('attack','hurt','defeat') else 'idle'
    if pose == 'idle' and int(t*3)%2: pose='idle_b'
    image = _animated_frame(monster_id,country_id,tuple(palette),boss,pose)
    if pose == 'idle_b':
      image=image.copy(); image.blit(image,(0,-2))
    return image
