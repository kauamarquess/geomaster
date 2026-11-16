"""Comandos de terminal:  validate, stats e merge."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bank import QuestionBank, QuestionBankError
from .checks import Validator, default_checks
from .geo import CountryCatalog
from .report import ReportBuilder

# tools/geomaster_tools/cli.py -> a raiz do projeto fica duas pastas acima de "geomaster_tools".
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BANK = ROOT / "data" / "questions.json"
DEFAULT_GEOJSON = ROOT / "data" / "geojson" / "countries.geojson"
DEFAULT_PARTS_DIR = ROOT / "data"
DEFAULT_MERGE_OUTPUT = ROOT / "data" / "questions.merged.json"


def _load_catalog(path: Path) -> CountryCatalog | None:
    if not path.exists():
        print(f"Aviso: GeoJSON não encontrado em {path}; as verificações do mapa foram puladas.\n")
        return None
    return CountryCatalog.from_file(path)


def _validate_and_print(bank: QuestionBank, source: str, geojson: Path):
    result = Validator(default_checks(_load_catalog(geojson))).run(bank)
    print(ReportBuilder().validation(result, bank, source))
    return result


def command_validate(args: argparse.Namespace) -> int:
    bank = QuestionBank.from_file(args.bank)
    result = _validate_and_print(bank, args.bank.name, args.geojson)
    if result.errors or (args.strict and result.warnings):
        return 1
    return 0


def command_stats(args: argparse.Namespace) -> int:
    bank = QuestionBank.from_file(args.bank)
    print(ReportBuilder().stats(bank, args.bank.name))
    return 0


def command_merge(args: argparse.Namespace) -> int:
    bank = QuestionBank.from_parts(args.parts_dir, args.pattern)
    result = _validate_and_print(bank, f"{args.pattern} (partes juntas)", args.geojson)

    if args.compare.exists():
        comparison = bank.compare(QuestionBank.from_file(args.compare))
        print(f"\nComparação com {args.compare.name}:")
        if comparison.identical:
            print("  idêntico (mesmas perguntas, sem nenhuma diferença).")
        else:
            print(f"  só nas partes: {len(comparison.only_here)} | só em {args.compare.name}: "
                  f"{len(comparison.only_there)} | alteradas: {len(comparison.changed)}")

    if result.errors:
        print("\nNada foi salvo: corrija os erros acima primeiro.")
        return 1
    saved = bank.save(args.output, overwrite=args.overwrite)
    print(f"\nBanco salvo em {saved} ({len(bank)} perguntas).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geomaster", description="Ferramentas de bastidores do GeoMaster.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="confere o banco de perguntas")
    validate.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    validate.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    validate.add_argument("--strict", action="store_true", help="avisos também fazem o comando falhar")
    validate.set_defaults(handler=command_validate)

    stats = sub.add_parser("stats", help="mostra números e equilíbrio do banco")
    stats.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    stats.set_defaults(handler=command_stats)

    merge = sub.add_parser("merge", help="junta as partes questions-part-*.json (sem sobrescrever o banco oficial)")
    merge.add_argument("--parts-dir", type=Path, default=DEFAULT_PARTS_DIR)
    merge.add_argument("--pattern", default="questions-part-*.json")
    merge.add_argument("--output", type=Path, default=DEFAULT_MERGE_OUTPUT)
    merge.add_argument("--compare", type=Path, default=DEFAULT_BANK, help="banco com o qual comparar o resultado")
    merge.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    merge.add_argument("--overwrite", action="store_true", help="permite substituir o arquivo de saída se já existir")
    merge.set_defaults(handler=command_merge)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")  # acentos corretos no Windows
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except QuestionBankError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2
