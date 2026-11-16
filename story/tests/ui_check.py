"""Teste da interface sem abrir janela (precisa de pygame). Rodar: python story/tests/ui_check.py"""
import os, sys, tempfile
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame
import main

pygame.init()
surface = pygame.display.set_mode((main.W, main.H))
save = Path(tempfile.mkdtemp()) / "save.json"
key = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
shot = lambda name: pygame.image.save(pygame.transform.scale(surface, (960, 540)), f"/tmp/{name}.png")

game = main.Game(surface, save)
name = lambda: type(game.scene).__name__
game.frame([]); shot("t_menu")
game.frame([key(pygame.K_RETURN)]); assert name() == "WorldMapScene"      # Nova aventura → mapa-múndi
game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene"          # Brasil está liberado
game.frame([key(pygame.K_ESCAPE)]); assert name() == "WorldMapScene"
game.frame([key(pygame.K_RIGHT), key(pygame.K_RETURN)]); assert "Bloqueado" in game.scene.message  # Argentina bloqueada
game.frame([key(pygame.K_LEFT), key(pygame.K_RETURN)]); assert name() == "WorldScene"

game.frame([key(pygame.K_RETURN)]); assert name() == "CombatScene"
battle = game.scene.battle
while battle.state not in ("won", "lost"):  # vence a fase 1 sempre acertando
    game.frame([key(pygame.K_1 + battle.question["correctIndex"])]); game.frame([], 0.2)
    if battle.state == "feedback":
        game.frame([key(pygame.K_RETURN)])
game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene"
assert save.exists(), "o save deveria ter sido gravado após a vitória"

# Continuar: um jogo novo, com o mesmo arquivo de save, recupera o progresso
game = main.Game(surface, save)
game.frame([key(pygame.K_DOWN), key(pygame.K_RETURN)]); assert name() == "WorldMapScene"
assert ("BRA", 1) in game.progress.cleared

# Brasil concluído libera a Argentina, que já tem fases
for n in range(1, 11):
    game.progress.clear("BRA", n)
game.scene = main.WorldMapScene(game)
game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene" and game.scene.country["id"] == "ARG"

# América do Sul concluída: o mapa-múndi já aponta para o Panamá, que tem fases
for cid in game.world["order"][0]["countries"]:
    for n in range(1, 11):
        game.progress.clear(cid, n)
game.scene = main.WorldMapScene(game)
game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene" and game.scene.country["id"] == "PAN"

# Terminando a América Central e Caribe, a jornada segue para o México (América do Norte)
for cid in game.world["order"][1]["countries"]:
    for n in range(1, 11):
        game.progress.clear(cid, n)
game.scene = main.WorldMapScene(game)
game.frame([key(pygame.K_RETURN)]); assert name() == "WorldScene" and game.scene.country["id"] == "MEX"
game.frame([]); shot("t_map")

# Nova aventura com save existente pede confirmação
game.scene = main.MenuScene(game)
game.frame([key(pygame.K_RETURN)]); assert game.scene.confirm and name() == "MenuScene"
game.frame([key(pygame.K_ESCAPE)]); assert not game.scene.confirm
# Todo país com fases prontas abre a tela de fases e um combate de boss sem erros
import combat
for cid in game.order:
    if game.has_data(cid):
        scene = main.WorldScene(game, cid); game.scene = scene
        stage = scene.country["stages"][9]
        game.scene = main.CombatScene(game, combat.Battle(game.bank, game.world, cid, 10, stage["monster"], True), stage)
        game.frame([]); game.scene.battle.answer(0); game.frame([])
        assert game.scene.stage["rewardPower"] in game.powers_data
# Poderes: equipar na tela de poderes e usar no combate
game.progress.add_power("fogo_fatuo"); game.progress.add_power("golpe_duplo")
assert game.progress.equipped == ["fogo_fatuo", "golpe_duplo"]
game.scene = main.WorldMapScene(game)
game.frame([key(pygame.K_p)]); assert name() == "PowersScene"
game.frame([key(pygame.K_RETURN)]); assert game.progress.equipped == ["golpe_duplo"]  # tirou o primeiro
game.frame([key(pygame.K_RETURN)]); assert game.progress.equipped == ["golpe_duplo", "fogo_fatuo"]
game.frame([key(pygame.K_ESCAPE)]); assert name() == "WorldMapScene"
game.scene = main.WorldScene(game, "BRA")
game.frame([key(pygame.K_RETURN)]); assert name() == "CombatScene"
battle = game.scene.battle
game.frame([key(pygame.K_a)]); assert battle.double_armed          # A = Golpe Duplo
game.frame([key(pygame.K_s)]); assert len(battle.eliminated) == 2   # S = Fogo-Fátuo
game.frame([key(pygame.K_s)]); assert "não pode" in game.scene.note  # sem usos restantes
game.frame([]); shot("t_powers_combat")
game.frame([key(pygame.K_1 + battle.question["correctIndex"])]); assert battle.last["result"] == "hit"
print("interface ok;", sum(game.has_data(c) for c in game.order), "países com fases")
