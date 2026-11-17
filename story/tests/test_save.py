"""Testes do salvamento (sem pygame). Rodar: python -m unittest discover -s story/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webstore
from progress import Progress

ORDER = ["BRA", "ARG", "CHL"]


class Fake:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


class Broken:
    def get(self, key):
        raise RuntimeError("bloqueado")

    def set(self, key, value):
        raise RuntimeError("cota cheia")


def sample():
    p = Progress(ORDER)
    for s in range(1, 11):
        p.clear("BRA", s)
    p.clear("ARG", 1)
    p.add_power("fogo"); p.add_power("fogo"); p.add_power("gelo")
    return p


class SaveFormat(unittest.TestCase):
    def test_ida_e_volta_preserva_tudo(self):
        original = sample()
        back = Progress.loads(original.dumps(), ORDER)
        self.assertEqual(back.cleared, original.cleared)
        self.assertEqual(back.powers, original.powers)
        self.assertEqual(back.levels, original.levels)
        self.assertEqual(back.equipped, original.equipped)
        self.assertGreater(back.saved_at, 0)

    def test_save_antigo_sem_data_ainda_abre(self):
        old = json.dumps({"version": 1, "cleared": [["BRA", 1]], "powers": ["fogo"], "equipped": ["fogo"], "levels": {"fogo": 1}})
        back = Progress.loads(old, ORDER)
        self.assertEqual(back.cleared, {("BRA", 1)})
        self.assertEqual(back.saved_at, 0)

    def test_texto_danificado_comeca_do_zero(self):
        for bad in ("", "{", "null", "[]", '{"cleared": 5, "powers": []}', "undefined"):
            self.assertFalse(Progress.loads(bad, ORDER).has_progress(), bad)

    def test_ignora_paises_e_fases_que_nao_existem(self):
        text = json.dumps({"cleared": [["BRA", 1], ["XXX", 1], ["BRA", 99]], "powers": []})
        self.assertEqual(Progress.loads(text, ORDER).cleared, {("BRA", 1)})

    def test_arquivo_ida_e_volta_e_sem_sobras(self):
        folder = Path(tempfile.mkdtemp())
        path = folder / "save.json"
        self.assertTrue(sample().save(path))
        self.assertEqual(Progress.load(path, ORDER).cleared, sample().cleared)
        self.assertEqual([f.name for f in folder.iterdir()], ["save.json"])  # o .tmp foi trocado, não ficou

    def test_arquivo_inexistente_comeca_do_zero(self):
        self.assertFalse(Progress.load(Path(tempfile.mkdtemp()) / "nada.json", ORDER).has_progress())

    def test_pasta_inexistente_nao_derruba_o_jogo(self):
        self.assertFalse(sample().save(Path(tempfile.mkdtemp()) / "nao-existe" / "save.json"))


class NewestSave(unittest.TestCase):
    def make(self, stamp, stages):
        p = Progress(ORDER)
        p.saved_at = stamp
        for s in range(1, stages + 1):
            p.clear("BRA", s)
        return p

    def test_o_mais_recente_vence_mesmo_com_menos_fases(self):
        old_big, new_small = self.make(100, 8), self.make(200, 2)  # ex.: o jogador começou uma nova aventura
        self.assertIs(Progress.newest(old_big, new_small), new_small)

    def test_empate_de_data_vale_quem_tem_mais_fases(self):
        a, b = self.make(100, 2), self.make(100, 5)
        self.assertIs(Progress.newest(a, b), b)

    def test_empate_total_vale_o_primeiro(self):
        a, b = self.make(100, 3), self.make(100, 3)
        self.assertIs(Progress.newest(a, b), a)

    def test_save_antigo_sem_data_perde_para_um_com_data(self):
        antigo, novo = self.make(0, 9), self.make(5, 1)
        self.assertIs(Progress.newest(antigo, novo), novo)


class BrowserStore(unittest.TestCase):
    def tearDown(self):
        webstore.override = None

    def test_grava_e_le(self):
        webstore.override = Fake()
        self.assertTrue(webstore.write("abc"))
        self.assertEqual(webstore.read(), "abc")

    def test_vazio_e_nulo_do_javascript_viram_none(self):
        webstore.override = Fake()
        for raw in (None, "", "null", "undefined"):
            webstore.override.data[webstore.KEY] = raw
            self.assertIsNone(webstore.read(), raw)

    def test_navegador_bloqueado_nao_derruba_nada(self):
        webstore.override = Broken()
        self.assertFalse(webstore.write("abc"))
        self.assertIsNone(webstore.read())

    def test_no_pc_nao_ha_onde_gravar(self):
        webstore.override = None  # fora do navegador
        self.assertIsNone(webstore.write("abc"))
        self.assertIsNone(webstore.read())

    def test_o_texto_do_arquivo_e_o_do_navegador_sao_o_mesmo(self):
        webstore.override = Fake()
        p = sample()
        text = p.dumps()
        path = Path(tempfile.mkdtemp()) / "save.json"
        p.save(path, text); webstore.write(text)
        self.assertEqual(path.read_text(encoding="utf-8"), webstore.read())


if __name__ == "__main__":
    unittest.main()
