#!/usr/bin/env python3
"""Une TODAS as partes do banco (data/questions-part-*.json) em data/questions.json.

Versão atualizada: agora inclui as partes de bandeiras (6 a 8), confere o resultado
com as verificações de tools/ e se recusa a gravar se o banco novo ficar menor que o atual.

Uso (na pasta principal do projeto):  python scripts/merge-question-parts.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from geomaster_tools.bank import QuestionBank, QuestionBankError  # noqa: E402
from geomaster_tools.checks import Validator, default_checks  # noqa: E402
from geomaster_tools.geo import CountryCatalog  # noqa: E402
from geomaster_tools.report import ReportBuilder  # noqa: E402

DATA = ROOT / "data"
OUTPUT = DATA / "questions.json"
GEOJSON = DATA / "geojson" / "countries.geojson"


def describe(bank: QuestionBank) -> str:
    counts = bank.count_by(lambda q: q.type, only_valid=False)
    total = f"{len(bank):,}".replace(",", ".")  # 1550 -> 1.550
    return (
        f"Banco oficial GeoMaster — {total} perguntas mundiais: "
        f"{counts.get('multiple_choice', 0)} de múltipla escolha, "
        f"{counts.get('map', 0)} desafios no mapa e "
        f"{counts.get('flag', 0)} desafios de identificação de bandeiras."
    )


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        bank = QuestionBank.from_parts(DATA)
        bank.description = describe(bank)
        catalog = CountryCatalog.from_file(GEOJSON) if GEOJSON.exists() else None
        result = Validator(default_checks(catalog)).run(bank)
        print(ReportBuilder().validation(result, bank, "partes juntas"))
        if result.errors:
            print("\nNada foi gravado: corrija os erros acima primeiro.")
            return 1

        if OUTPUT.exists():
            current = QuestionBank.from_file(OUTPUT)
            if len(bank) < len(current):
                print(f"\nNada foi gravado: o banco novo ({len(bank)}) é menor que o atual ({len(current)}). "
                      "Confira se todas as partes estão em data/.")
                return 1
            diff = bank.compare(current)
            print(f"\nComparação com o questions.json atual: {len(diff.only_here)} nova(s), "
                  f"{len(diff.only_there)} removida(s), {len(diff.changed)} alterada(s).")

        bank.save(OUTPUT, overwrite=True)
        print(f"\nBanco criado: {OUTPUT} ({len(bank)} perguntas)")
        return 0
    except QuestionBankError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
