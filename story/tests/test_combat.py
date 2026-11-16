"""Testes das regras de combate. Rodar na pasta principal: python -m unittest discover story/tests"""
import json, random, sys, unittest
from pathlib import Path

STORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STORY))
import combat

WORLD = json.loads((STORY / "data/world-order.json").read_text(encoding="utf-8"))
MONSTER = {"id": "saci", "name": "Saci-Pererê", "legend": "..."}


def new_bank(seed=1):
    return combat.load_bank(STORY, WORLD, random.Random(seed))


class CombatRules(unittest.TestCase):
    def test_progress_grows_from_zero_to_below_one(self):
        last = WORLD["order"][-1]["countries"][-1]
        self.assertEqual(combat.progress(WORLD, "BRA", 1), 0)
        self.assertLess(combat.progress(WORLD, "BRA", 10), combat.progress(WORLD, "ARG", 1))
        self.assertLess(combat.progress(WORLD, last, 10), 1)

    def test_difficulty_shifts_with_progress(self):
        start, end = combat.difficulty_weights(0), combat.difficulty_weights(1)
        self.assertGreater(start["easy"], start["hard"])
        self.assertGreater(end["hard"], end["easy"])

    def test_boss_is_stronger_and_damage_rewards_speed_and_streak(self):
        self.assertGreater(combat.monster_stats(10, True)[0], combat.monster_stats(9)[0])
        self.assertGreater(combat.hit_damage("easy", 30, 0), combat.hit_damage("easy", 1, 0))
        self.assertGreater(combat.hit_damage("hard", 10, 0), combat.hit_damage("easy", 10, 0))
        self.assertGreater(combat.hit_damage("easy", 10, 3), combat.hit_damage("easy", 10, 0))

    def test_bank_only_serves_multiple_choice_without_repeats(self):
        battle = combat.Battle(new_bank(), WORLD, "BRA", 1, MONSTER)
        seen = {battle.question["id"]}
        for _ in range(40):
            battle.next_question()
            self.assertEqual(battle.question["type"], "multiple_choice")
            self.assertNotIn(battle.question["id"], seen)
            seen.add(battle.question["id"])

    def test_hit_miss_and_timeout(self):
        battle = combat.Battle(new_bank(), WORLD, "BRA", 1, MONSTER)
        battle.answer(battle.question["correctIndex"])
        self.assertLess(battle.monster_hp, battle.monster_max)
        self.assertEqual(battle.hero_hp, 100)
        battle.next_question()
        wrong = (battle.question["correctIndex"] + 1) % 4
        battle.answer(wrong)
        self.assertEqual(battle.hero_hp, 100 - battle.monster_attack)
        battle.next_question()
        battle.tick(31)  # tempo esgotado
        self.assertEqual(battle.last["result"], "timeout")
        self.assertIsNone(battle.answer(0))  # não responde duas vezes a mesma pergunta

    def test_win_and_lose(self):
        win = combat.Battle(new_bank(), WORLD, "BRA", 1, MONSTER)
        while win.state != "won":
            win.answer(win.question["correctIndex"])
            if win.state == "feedback":
                win.next_question()
        self.assertEqual(win.monster_hp, 0)
        lose = combat.Battle(new_bank(), WORLD, "BRA", 10, MONSTER, boss=True)
        while lose.state != "lost":
            lose.answer(None)
            if lose.state == "feedback":
                lose.next_question()
        self.assertEqual(lose.hero_hp, 0)


POWERS = json.loads((STORY / "data/powers.json").read_text(encoding="utf-8"))
power = lambda *ids, **extra: [{**POWERS[i], "id": i, **extra} for i in ids]


def battle_with(*ids, seed=1, **extra):
    return combat.Battle(new_bank(seed), WORLD, "BRA", 1, MONSTER, powers=power(*ids, **extra), rng=random.Random(seed))


class Powers(unittest.TestCase):
    def test_passives_change_the_starting_numbers(self):
        b = battle_with("tempo_extra", "vida_extra", "sequencia_inicial", "escudo_lenda")
        self.assertEqual((b.question_seconds, b.hero_max, b.hero_hp, b.streak), (35, 120, 120, 2))
        self.assertLess(b.monster_attack, combat.monster_stats(1)[1])

    def test_levels_strengthen_powers(self):
        base, lvl3 = battle_with("vida_extra"), battle_with("vida_extra", level=3)
        self.assertEqual((base.hero_max, lvl3.hero_max), (120, 140))      # 20 → 40 de vida extra
        self.assertEqual(combat.power_uses({"usesPerBattle": 1, "level": 3}), 2)  # +1 uso a cada 2 níveis
        capped = battle_with("passo_leve", level=5)
        self.assertEqual(capped.dodge_chance, 0.6)                         # esquiva tem teto

    def test_eliminate_two_never_removes_the_right_answer_and_uses_run_out(self):
        b = battle_with("fogo_fatuo")
        self.assertTrue(b.use_power("fogo_fatuo"))
        self.assertEqual(len(b.eliminated), 2)
        self.assertNotIn(b.question["correctIndex"], b.eliminated)
        self.assertFalse(b.use_power("fogo_fatuo"))  # só 1 uso por combate
        self.assertIsNone(b.answer(next(iter(b.eliminated))))  # alternativa eliminada não vale
        self.assertEqual(b.state, "asking")

    def test_dica_unica_has_two_uses(self):
        b = battle_with("dica_unica")
        self.assertTrue(b.use_power("dica_unica") and b.use_power("dica_unica"))
        self.assertFalse(b.use_power("dica_unica"))
        self.assertEqual(len(b.eliminated), 2)

    def test_double_damage_doubles_only_the_next_hit(self):
        plain, boosted = battle_with("golpe_duplo"), battle_with("golpe_duplo")
        self.assertTrue(boosted.use_power("golpe_duplo"))
        for b in (plain, boosted):
            b.time_left = 10
            b.answer(b.question["correctIndex"])
        self.assertEqual(boosted.last["damage"], 2 * plain.last["damage"])
        self.assertFalse(boosted.double_armed)

    def test_heal_is_capped_and_needs_missing_life(self):
        b = battle_with("cura_leve")
        self.assertFalse(b.can_use("cura_leve"))  # vida cheia
        b.hero_hp = 50
        self.assertTrue(b.use_power("cura_leve"))
        self.assertEqual(b.hero_hp, 75)

    def test_freeze_timer_stops_the_clock_for_ten_seconds(self):
        b = battle_with("congelar_tempo")
        b.use_power("congelar_tempo")
        b.tick(10)
        self.assertEqual(b.time_left, 30)
        b.tick(5)
        self.assertEqual(b.time_left, 25)

    def test_retry_undoes_the_damage_and_blocks_the_wrong_option(self):
        b = battle_with("segunda_chance")
        self.assertFalse(b.can_use("segunda_chance"))  # ainda não errou
        wrong = (b.question["correctIndex"] + 1) % 4
        b.answer(wrong)
        self.assertEqual(b.hero_hp, 100 - b.monster_attack)
        self.assertTrue(b.use_power("segunda_chance"))
        self.assertEqual((b.hero_hp, b.state), (100, "asking"))
        self.assertIsNone(b.answer(wrong))  # a mesma errada não pode de novo
        self.assertEqual(b.answer(b.question["correctIndex"])["result"], "hit")

    def test_retry_can_save_the_hero_from_a_deadly_hit(self):
        b = battle_with("segunda_chance")
        b.hero_hp = 1
        b.answer(None)
        self.assertEqual(b.state, "lost")
        self.assertTrue(b.use_power("segunda_chance"))
        self.assertEqual((b.state, b.hero_hp), ("asking", 1))

    def test_dodge_and_first_hit_bonus(self):
        b = battle_with("passo_leve", value=1.0)  # 100% de esquiva só para o teste
        b.answer(None)
        self.assertEqual((b.hero_hp, b.last["dodged"]), (100, True))
        with_bonus, without = battle_with("forca_vento"), battle_with()
        for x in (with_bonus, without):
            x.time_left = 10
            x.answer(x.question["correctIndex"])
        self.assertGreater(with_bonus.last["damage"], without.last["damage"])


if __name__ == "__main__":
    unittest.main()
