"""Testes do progresso e do salvamento. Rodar na pasta principal: python -m unittest discover story/tests"""
import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from progress import Progress

ORDER = ["BRA", "ARG", "CHL"]


class ProgressRules(unittest.TestCase):
    def test_first_country_open_next_locked_until_complete(self):
        p = Progress(ORDER)
        self.assertTrue(p.is_unlocked("BRA"))
        self.assertFalse(p.is_unlocked("ARG"))
        for stage in range(1, 10):
            p.clear("BRA", stage)
        self.assertFalse(p.is_unlocked("ARG"))  # 9 de 10 ainda não basta
        p.clear("BRA", 10)
        self.assertTrue(p.is_complete("BRA") and p.is_unlocked("ARG"))
        self.assertEqual(p.current_country(), "ARG")

    def test_stages_done_counts_only_consecutive_stages(self):
        p = Progress(ORDER)
        p.clear("BRA", 1); p.clear("BRA", 3)
        self.assertEqual(p.stages_done("BRA"), 1)

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "save.json"
            p = Progress(ORDER)
            p.clear("BRA", 1); p.add_power("fogo_fatuo"); p.add_power("fogo_fatuo")
            self.assertTrue(p.save(path))
            loaded = Progress.load(path, ORDER)
            self.assertEqual(loaded.cleared, {("BRA", 1)})
            self.assertEqual(loaded.powers, ["fogo_fatuo"])  # poder repetido não duplica

    def test_missing_or_corrupted_save_starts_fresh(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "save.json"
            self.assertFalse(Progress.load(path, ORDER).has_progress())
            path.write_text("{isso não é json", encoding="utf-8")
            self.assertFalse(Progress.load(path, ORDER).has_progress())
            path.write_text('{"cleared": [["XXX", 1], ["BRA", 99], ["BRA", 2]], "powers": []}', encoding="utf-8")
            self.assertEqual(Progress.load(path, ORDER).cleared, {("BRA", 2)})  # ignora país e fase inválidos

    def test_equipment_has_three_slots_and_survives_saving(self):
        p = Progress(ORDER)
        for power in ("a", "b", "c", "d"):
            p.add_power(power)
        self.assertEqual(p.equipped, ["a", "b", "c"])  # o quarto não cabe
        self.assertFalse(p.toggle_equipped("d"))
        self.assertTrue(p.toggle_equipped("a") and p.toggle_equipped("d"))
        self.assertFalse(p.toggle_equipped("zzz"))  # poder não conquistado
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "save.json"
            p.save(path)
            self.assertEqual(Progress.load(path, ORDER).equipped, ["b", "c", "d"])
            path.write_text('{"cleared": [], "powers": ["a", "b"]}', encoding="utf-8")  # save antigo, sem "equipped"
            self.assertEqual(Progress.load(path, ORDER).equipped, ["a", "b"])

    def test_repeated_power_levels_up_to_the_cap_and_persists(self):
        p = Progress(ORDER)
        self.assertEqual(p.add_power("x"), 1)
        for expected in (2, 3, 4, 5, 5):
            self.assertEqual(p.add_power("x"), expected)
        self.assertEqual(p.powers, ["x"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "save.json"
            p.save(path)
            self.assertEqual(Progress.load(path, ORDER).level("x"), 5)

    def test_unwritable_path_returns_false_instead_of_crashing(self):
        self.assertFalse(Progress(ORDER).save("/pasta/que/nao/existe/save.json"))


if __name__ == "__main__":
    unittest.main()
