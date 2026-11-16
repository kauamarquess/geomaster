"""Teste da interface sem abrir janela (precisa de pygame). Rodar: python story/tests/test_ui.py"""
import os, sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame
import main

pygame.init()
surface = pygame.display.set_mode((main.W, main.H))
game = main.Game(surface)
key = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
name = lambda: type(game.scene).__name__

game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene"
game.frame([key(pygame.K_RIGHT)]); game.frame([key(pygame.K_RETURN)])
assert name() == "WorldScene" and "anterior" in game.scene.message  # fase 2 está bloqueada
game.frame([key(pygame.K_LEFT)]); game.frame([key(pygame.K_RETURN)]); assert name() == "CombatScene"

for stage in range(1, 4):  # vence as 3 primeiras fases, sempre acertando
    battle = game.scene.battle
    while battle.state not in ("won", "lost"):
        game.frame([key(pygame.K_1 + battle.question["correctIndex"])]); game.frame([], 0.2)
        if battle.state == "feedback":
            game.frame([key(pygame.K_RETURN)])
    game.frame([]); pygame.image.save(pygame.transform.scale(surface, (960, 540)), f"/tmp/combat_{stage}.png")
    assert battle.state == "won"
    game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene"
    assert ("BRA", stage) in game.cleared and game.scene.index == stage
    game.frame([key(pygame.K_RETURN)]); assert name() == "CombatScene"
print("interface ok; fases vencidas:", sorted(game.cleared))
