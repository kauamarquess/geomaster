"""Testes das ferramentas Python.  Rode na raiz do projeto:

    python -m unittest discover -s tools/tests -v
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from geomaster_tools.bank import QuestionBank, QuestionBankError  # noqa: E402
from geomaster_tools.checks import (  # noqa: E402
    AnswerPositionCheck, DuplicateIdCheck, DuplicateTextCheck, FlagConsistencyCheck,
    MapTargetCheck, StructureCheck, Validator, default_checks,
)
from geomaster_tools.cli import DEFAULT_BANK, DEFAULT_GEOJSON, main  # noqa: E402
from geomaster_tools.geo import CountryCatalog  # noqa: E402
from geomaster_tools.models import (  # noqa: E402
    FlagQuestion, InvalidQuestion, MapQuestion, MultipleChoiceQuestion,
    QuestionFactory, normalize_text,
)


def mc(**changes):
    base = {"id": "mc-1", "type": "multiple_choice", "difficulty": "easy", "category": "capitals",
            "text": "Qual é a capital da França?", "options": ["Paris", "Roma", "Lima", "Oslo"],
            "correctIndex": 0, "explanation": "Paris."}
    return {**base, **changes}


def flag(**changes):
    base = {"id": "fl-1", "type": "flag", "difficulty": "easy", "category": "flags",
            "text": "Qual país? (1)", "flagCode": "fr", "targetId": "FRA", "targetName": "França",
            "options": ["França", "Peru", "Chile", "Cuba"], "correctIndex": 0, "explanation": "França."}
    return {**base, **changes}


def mp(**changes):
    base = {"id": "mp-1", "type": "map", "difficulty": "easy", "category": "location",
            "text": "Localize: França.", "targetId": "FRA", "targetName": "França", "explanation": "França."}
    return {**base, **changes}


CATALOG = CountryCatalog({"FRA": "França", "BRA": "Brasil"})


class ModelTests(unittest.TestCase):
    def test_factory_escolhe_a_classe_certa(self):
        self.assertIsInstance(QuestionFactory.create(mc()), MultipleChoiceQuestion)
        self.assertIsInstance(QuestionFactory.create(flag()), FlagQuestion)
        self.assertIsInstance(QuestionFactory.create(mp()), MapQuestion)
        self.assertIsInstance(QuestionFactory.create(mc(type="quiz")), InvalidQuestion)
        self.assertIsInstance(QuestionFactory.create("texto solto"), InvalidQuestion)

    def test_perguntas_validas(self):
        for raw in (mc(), flag(), mp()):
            self.assertEqual(QuestionFactory.create(raw).validate(), [], raw["type"])

    def test_pontos_por_dificuldade(self):
        self.assertEqual(QuestionFactory.create(mc(difficulty="hard")).points, 30)

    def test_resposta_certa(self):
        self.assertEqual(QuestionFactory.create(mc(correctIndex=1)).correct_answer_text(), "Roma")
        self.assertEqual(QuestionFactory.create(mp()).correct_answer_text(), "França")

    def test_multipla_escolha_com_problemas(self):
        self.assertTrue(QuestionFactory.create(mc(options=["A", "a", "B"])).validate())   # repetida
        self.assertTrue(QuestionFactory.create(mc(correctIndex=9)).validate())            # fora da lista
        self.assertTrue(QuestionFactory.create(mc(correctIndex=True)).validate())         # bool não vale
        self.assertTrue(QuestionFactory.create(mc(options=["só uma"])).validate())        # poucas alternativas
        self.assertTrue(QuestionFactory.create(mc(difficulty="insane")).validate())
        self.assertTrue(QuestionFactory.create(mc(text="  ")).validate())

    def test_bandeira_exige_quatro_alternativas_e_codigo(self):
        self.assertTrue(QuestionFactory.create(flag(options=["França", "Peru", "Chile"])).validate())
        self.assertTrue(QuestionFactory.create(flag(flagCode="FRA")).validate())
        self.assertTrue(QuestionFactory.create(flag(targetName="")).validate())

    def test_mapa_exige_target_id(self):
        self.assertTrue(QuestionFactory.create(mp(targetId="")).validate())

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  São Tomé e Príncipe!! "), "sao tome e principe")


class CheckTests(unittest.TestCase):
    def run_check(self, check, *raws):
        return check.run(QuestionBank.from_raw(raws))

    def test_estrutura_aponta_item_quebrado(self):
        issues = self.run_check(StructureCheck(), mc(), mc(id="mc-2", correctIndex=9))
        self.assertEqual([i.question_id for i in issues], ["mc-2"])

    def test_ids_e_enunciados_repetidos(self):
        self.assertEqual(len(self.run_check(DuplicateIdCheck(), mc(), mc())), 1)
        issues = self.run_check(DuplicateTextCheck(), mc(), mc(id="mc-2", text="QUAL É A CAPITAL DA FRANÇA"))
        self.assertEqual(len(issues), 1)

    def test_alvo_do_mapa_inexistente(self):
        issues = self.run_check(MapTargetCheck(CATALOG), mp(), mp(id="mp-2", targetId="XXX", text="Outra"))
        self.assertEqual([(i.severity, i.question_id) for i in issues], [("erro", "mp-2")])

    def test_bandeira_com_resposta_errada(self):
        issues = self.run_check(FlagConsistencyCheck(CATALOG), flag(correctIndex=1))
        self.assertEqual(issues[0].severity, "erro")

    def test_mesma_bandeira_com_alternativas_diferentes_e_normal(self):
        other = flag(id="fl-2", text="Qual país? (2)", options=["França", "Peru", "Chile", "Japão"])
        self.assertEqual(self.run_check(FlagConsistencyCheck(CATALOG), flag(), other), [])

    def test_bandeira_repetida_na_pratica(self):
        issues = self.run_check(FlagConsistencyCheck(CATALOG), flag(), flag(id="fl-2", text="Qual país? (2)"))
        self.assertEqual([i.severity for i in issues], ["aviso"])

    def test_resposta_sempre_na_mesma_posicao(self):
        raws = [mc(id=f"mc-{n}", text=f"Pergunta {n}") for n in range(50)]  # sempre correctIndex 0
        issues = self.run_check(AnswerPositionCheck(), *raws)
        self.assertEqual(len(issues), 1)

    def test_validator_junta_tudo(self):
        bank = QuestionBank.from_raw([mc(), flag(), mp()])
        result = Validator(default_checks(CATALOG)).run(bank)
        self.assertTrue(result.ok)


class BankTests(unittest.TestCase):
    def test_juntar_partes_comparar_e_salvar(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for number, raws in enumerate([[mc()], [flag(), mp()]], start=1):
                (folder / f"questions-part-{number:02d}.json").write_text(
                    json.dumps({"version": number, "questions": raws}), encoding="utf-8")
            bank = QuestionBank.from_parts(folder)
            self.assertEqual((len(bank), bank.version), (3, 2))

            out = bank.save(folder / "merged.json")
            again = QuestionBank.from_file(out)
            self.assertTrue(bank.compare(again).identical)
            with self.assertRaises(QuestionBankError):     # nunca sobrescreve sem permissão
                bank.save(out)

            changed = QuestionBank.from_raw([mc(text="Outro texto"), flag()])
            diff = bank.compare(changed)
            self.assertEqual((diff.only_here, diff.changed), (["mp-1"], ["mc-1"]))

    def test_arquivo_inexistente_e_json_quebrado(self):
        with self.assertRaises(QuestionBankError):
            QuestionBank.from_file("nao-existe.json")
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "x.json"
            broken.write_text("{ quebrado", encoding="utf-8")
            with self.assertRaises(QuestionBankError):
                QuestionBank.from_file(broken)


class RealDataTests(unittest.TestCase):
    @unittest.skipUnless(DEFAULT_BANK.exists() and DEFAULT_GEOJSON.exists(), "banco real não encontrado")
    def test_banco_oficial_nao_tem_erros(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["validate"]), 0)
            self.assertEqual(main(["stats"]), 0)


if __name__ == "__main__":
    unittest.main()
