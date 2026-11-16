"""Verificações de qualidade do banco.

Cada verificação é uma classe que herda de `Check` e implementa `run(bank)`.
Para criar uma regra nova, basta escrever outra classe e incluí-la em `default_checks`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from dataclasses import dataclass

from .bank import QuestionBank
from .geo import CountryCatalog
from .models import (
    FlagQuestion, MapQuestion, OptionsQuestion,
    is_non_empty_string, normalize_text,
)

ERROR = "erro"      # quebra o jogo ou a pergunta: precisa ser corrigido
WARNING = "aviso"   # funciona, mas merece atenção


@dataclass(frozen=True)
class Issue:
    severity: str
    check: str
    question_id: str | None
    message: str


class Check(ABC):
    name = "verificação"
    description = ""

    @abstractmethod
    def run(self, bank: QuestionBank) -> list[Issue]:
        ...

    def _issue(self, severity: str, question_id: str | None, message: str) -> Issue:
        return Issue(severity, self.name, question_id, message)


class StructureCheck(Check):
    name = "estrutura"
    description = "Campos obrigatórios e regras de cada tipo (mesmas do JavaScript)."

    def run(self, bank: QuestionBank) -> list[Issue]:
        issues = []
        for position, question in enumerate(bank, start=1):
            label = question.id if is_non_empty_string(question.id) else f"posição {position}"
            issues += [self._issue(ERROR, label, problem) for problem in question.validate()]
        return issues


class DuplicateIdCheck(Check):
    name = "ids repetidos"
    description = "Dois itens não podem ter o mesmo id."

    def run(self, bank: QuestionBank) -> list[Issue]:
        counts = Counter(q.id for q in bank if is_non_empty_string(q.id))
        return [
            self._issue(ERROR, question_id, f"id usado {times} vezes")
            for question_id, times in counts.items() if times > 1
        ]


class DuplicateTextCheck(Check):
    name = "enunciados repetidos"
    description = "Mesmo tipo e mesmo enunciado (ignorando acentos e maiúsculas)."

    def run(self, bank: QuestionBank) -> list[Issue]:
        seen: dict[tuple[str, str], str] = {}
        issues = []
        for question in bank.valid_questions:
            key = (question.type or "", normalize_text(question.text))
            if key in seen:
                issues.append(self._issue(ERROR, question.id, f"enunciado igual ao da pergunta {seen[key]}"))
            else:
                seen[key] = question.id
        return issues


class MapTargetCheck(Check):
    name = "alvos do mapa"
    description = "Todo desafio de mapa aponta para um país que existe no GeoJSON."

    def __init__(self, catalog: CountryCatalog) -> None:
        self.catalog = catalog

    def run(self, bank: QuestionBank) -> list[Issue]:
        issues = []
        seen_targets: dict[str, str] = {}
        for question in bank.valid_questions:
            if not isinstance(question, MapQuestion):
                continue
            if question.target_id not in self.catalog:
                issues.append(self._issue(
                    ERROR, question.id,
                    f"targetId {question.target_id!r} não existe no GeoJSON (impossível de acertar)",
                ))
                continue
            official = self.catalog.name_of(question.target_id)
            if question.target_name and official and normalize_text(question.target_name) != normalize_text(official):
                issues.append(self._issue(
                    WARNING, question.id,
                    f"targetName {question.target_name!r} difere do nome no GeoJSON ({official!r})",
                ))
            if question.target_id in seen_targets:
                issues.append(self._issue(
                    WARNING, question.id,
                    f"mesmo país da pergunta {seen_targets[question.target_id]} ({question.target_id})",
                ))
            else:
                seen_targets[question.target_id] = question.id
        return issues


class FlagConsistencyCheck(Check):
    name = "bandeiras"
    description = (
        "A alternativa correta é mesmo o país da bandeira. A mesma bandeira pode aparecer "
        "em várias perguntas, mas não com as mesmas 4 alternativas."
    )

    def __init__(self, catalog: CountryCatalog | None = None) -> None:
        self.catalog = catalog

    def run(self, bank: QuestionBank) -> list[Issue]:
        issues = []
        seen: dict[tuple[str, frozenset[str]], str] = {}
        for question in bank.valid_questions:
            if not isinstance(question, FlagQuestion):
                continue
            answer = question.correct_answer_text()
            if normalize_text(answer) != normalize_text(question.target_name):
                issues.append(self._issue(
                    ERROR, question.id,
                    f"a alternativa correta ({answer!r}) não é o país da bandeira ({question.target_name!r})",
                ))
            if self.catalog is not None and question.target_id not in self.catalog:
                issues.append(self._issue(
                    WARNING, question.id, f"targetId {question.target_id!r} não está no GeoJSON",
                ))
            key = (question.target_id, frozenset(normalize_text(o) for o in question.options))
            if key in seen:
                issues.append(self._issue(
                    WARNING, question.id,
                    f"mesma bandeira e mesmas alternativas da pergunta {seen[key]} (pergunta repetida na prática)",
                ))
            else:
                seen[key] = question.id
        return issues


class ExplanationCheck(Check):
    name = "explicações"
    description = "Toda pergunta deveria ter uma explicação para mostrar no feedback."

    def run(self, bank: QuestionBank) -> list[Issue]:
        return [
            self._issue(WARNING, q.id, "sem explicação")
            for q in bank.valid_questions if not is_non_empty_string(q.explanation)
        ]


class AnswerPositionCheck(Check):
    name = "posição da resposta"
    description = "A resposta certa não deve ficar sempre no mesmo lugar (jogador esperto perceberia)."

    def __init__(self, max_share: float = 0.40, min_questions: int = 40) -> None:
        self.max_share = max_share
        self.min_questions = min_questions

    def run(self, bank: QuestionBank) -> list[Issue]:
        by_type: dict[str, list[int]] = defaultdict(list)
        for question in bank.valid_questions:
            if isinstance(question, OptionsQuestion):
                by_type[question.type].append(question.correct_index)
        issues = []
        for type_name, positions in by_type.items():
            if len(positions) < self.min_questions:
                continue
            position, times = Counter(positions).most_common(1)[0]
            share = times / len(positions)
            if share > self.max_share:
                issues.append(self._issue(
                    WARNING, None,
                    f"{type_name}: a resposta certa está na alternativa {position + 1} em {share:.0%} das perguntas",
                ))
        return issues


def default_checks(catalog: CountryCatalog | None = None) -> list[Check]:
    checks: list[Check] = [StructureCheck(), DuplicateIdCheck(), DuplicateTextCheck()]
    if catalog is not None:
        checks.append(MapTargetCheck(catalog))
    checks += [FlagConsistencyCheck(catalog), ExplanationCheck(), AnswerPositionCheck()]
    return checks


@dataclass
class ValidationResult:
    issues: list[Issue]
    checks: list[Check]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors


class Validator:
    """Roda uma lista de verificações sobre um banco."""

    def __init__(self, checks: list[Check]) -> None:
        self.checks = checks

    def run(self, bank: QuestionBank) -> ValidationResult:
        issues: list[Issue] = []
        for check in self.checks:
            issues += check.run(bank)
        return ValidationResult(issues, self.checks)
