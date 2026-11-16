"""Relatórios em texto simples (sem cores, funcionam em qualquer terminal)."""
from __future__ import annotations

from .bank import QuestionBank
from .checks import ERROR, ValidationResult
from .models import DIFFICULTIES, MATCH_COMPOSITION, FlagQuestion, OptionsQuestion

TYPE_LABELS = {"multiple_choice": "múltipla escolha", "map": "mapa", "flag": "bandeira"}


def _table(headers: list[str], rows: list[list[object]]) -> str:
    cells = [headers] + [[str(c) for c in row] for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    lines = ["  ".join(cell.ljust(widths[i]) if i == 0 else cell.rjust(widths[i]) for i, cell in enumerate(row))
             for row in cells]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join("  " + line for line in lines)


class ReportBuilder:
    def validation(self, result: ValidationResult, bank: QuestionBank, source: str, examples: int = 8) -> str:
        lines = [f"Banco: {source} — {len(bank)} perguntas", f"Verificações: {len(result.checks)}", ""]
        for check in result.checks:
            found = [i for i in result.issues if i.check == check.name]
            errors = sum(1 for i in found if i.severity == ERROR)
            warnings = len(found) - errors
            status = "OK   " if not found else ("ERRO " if errors else "AVISO")
            detail = "" if not found else f" — {errors} erro(s), {warnings} aviso(s)"
            lines.append(f"[{status}] {check.name}{detail}")
            for issue in found[:examples]:
                where = f"{issue.question_id}: " if issue.question_id else ""
                lines.append(f"        ({issue.severity}) {where}{issue.message}")
            if len(found) > examples:
                lines.append(f"        ... e mais {len(found) - examples}")
        lines += ["", f"Resultado: {len(result.errors)} erro(s), {len(result.warnings)} aviso(s)."]
        return "\n".join(lines)

    def stats(self, bank: QuestionBank, source: str) -> str:
        valid = bank.valid_questions
        lines = [f"Banco: {source} — {len(bank)} perguntas ({len(valid)} válidas)", ""]

        types = bank.count_by(lambda q: q.type)
        lines += ["Por tipo:", _table(["tipo", "perguntas"], [[TYPE_LABELS.get(t, t), n] for t, n in sorted(types.items())]), ""]

        matrix = bank.count_by(lambda q: (q.type, q.difficulty))
        rows = [[TYPE_LABELS.get(t, t)] + [matrix.get((t, d), 0) for d in DIFFICULTIES] for t in sorted(types)]
        lines += ["Tipo x dificuldade:", _table(["tipo", *DIFFICULTIES], rows), ""]

        categories = bank.count_by(lambda q: q.category)
        lines += ["Por categoria:", _table(["categoria", "perguntas"], sorted(categories.items())), ""]

        positions = bank.count_by(lambda q: q.correct_index + 1 if isinstance(q, OptionsQuestion) else None)
        positions.pop(None, None)
        total = sum(positions.values()) or 1
        lines += ["Posição da resposta certa (perguntas com alternativas):",
                  _table(["alternativa", "perguntas", "%"],
                         [[p, n, f"{n / total:.0%}"] for p, n in sorted(positions.items())]), ""]

        rows = []
        matches = []
        for type_name, needed in MATCH_COMPOSITION.items():
            available = types.get(type_name, 0)
            possible = available // needed
            matches.append(possible)
            rows.append([TYPE_LABELS.get(type_name, type_name), needed, available, possible])
        lines += ["Partidas sem repetir pergunta (3 múltipla escolha + 3 mapa + 4 bandeira):",
                  _table(["tipo", "por partida", "no banco", "partidas"], rows),
                  f"  => dá para jogar {min(matches)} partidas seguidas sem repetir nenhuma pergunta.", ""]

        flag_countries = {q.target_id for q in valid if isinstance(q, FlagQuestion)}
        if flag_countries:
            lines += [f"Bandeiras: {types.get('flag', 0)} perguntas sobre {len(flag_countries)} países diferentes "
                      "(cada bandeira volta com alternativas diferentes).", ""]

        lines.append(f"Pontos possíveis no banco todo: {sum(q.points for q in valid)}")
        return "\n".join(lines)
