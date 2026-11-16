"""Modelos das perguntas do GeoMaster: uma classe para cada tipo de pergunta.

Como a programação orientada a objetos aparece aqui:

* `Question` é a classe-mãe. Guarda o que TODA pergunta tem (id, texto, dificuldade...)
  e define o contrato: toda pergunta sabe se validar (`validate`) e dizer qual é a
  resposta certa (`correct_answer_text`).
* `OptionsQuestion` é uma classe intermediária para as perguntas que têm alternativas.
* `MultipleChoiceQuestion`, `FlagQuestion` e `MapQuestion` são as classes-filhas. Cada
  uma valida as regras do seu tipo (herança + polimorfismo): quem usa a pergunta
  só chama `question.validate()` sem precisar saber qual é o tipo.
* `QuestionFactory` olha o campo "type" do JSON e cria a classe certa.

As regras espelham `js/core/questions.js` e `js/core/scoring.js`. Se você mudar uma
regra lá, mude aqui também.
"""
from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Any

DIFFICULTIES = ("easy", "medium", "hard")
CATEGORIES = (
    "countries", "capitals", "continents", "borders",
    "oceans", "location", "culture", "physical", "flags",
)
POINTS_BY_DIFFICULTY = {"easy": 10, "medium": 20, "hard": 30}
MIN_OPTIONS = 2
MAX_OPTIONS = 6
# Composição de cada partida (3 + 3 + 4 = 10 perguntas), igual a MATCH_COMPOSITION no JS.
MATCH_COMPOSITION = {"multiple_choice": 3, "map": 3, "flag": 4}


def normalize_text(value: Any) -> str:
    """Deixa o texto comparável: sem acentos, sem maiúsculas, sem pontuação."""
    text = unicodedata.normalize("NFD", "" if value is None else str(value))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def is_integer(value: Any) -> bool:
    # Em Python, True e False contam como inteiros; aqui eles NÃO são aceitos.
    return isinstance(value, int) and not isinstance(value, bool)


class Question(ABC):
    """Classe-mãe de todas as perguntas."""

    TYPE: str | None = None

    def __init__(self, raw: dict[str, Any]) -> None:
        self.raw = raw  # o dicionário original do JSON, preservado sem alterações
        self.id = raw.get("id")
        self.difficulty = raw.get("difficulty")
        self.category = raw.get("category")
        self.text = raw.get("text")
        self.explanation = raw.get("explanation")

    @property
    def type(self) -> str | None:
        return self.TYPE

    @property
    def points(self) -> int:
        return POINTS_BY_DIFFICULTY.get(self.difficulty, 0)

    def validate(self) -> list[str]:
        """Devolve a lista de problemas. Lista vazia = pergunta válida."""
        return self._validate_common() + self._validate_specific()

    def _validate_common(self) -> list[str]:
        problems: list[str] = []
        if not is_non_empty_string(self.id):
            problems.append("id ausente ou vazio")
        if self.difficulty not in DIFFICULTIES:
            problems.append(f"dificuldade inválida: {self.difficulty!r}")
        if self.category not in CATEGORIES:
            problems.append(f"categoria inválida: {self.category!r}")
        if not is_non_empty_string(self.text):
            problems.append("enunciado ausente ou vazio")
        if self.explanation is not None and not isinstance(self.explanation, str):
            problems.append("a explicação, quando existe, precisa ser texto")
        return problems

    @abstractmethod
    def _validate_specific(self) -> list[str]:
        """Regras que só existem em um tipo de pergunta (cada filha escreve a sua)."""

    @abstractmethod
    def correct_answer_text(self) -> str | None:
        """O texto da resposta certa, ou None se a pergunta estiver quebrada."""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.raw)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.id!r}>"


class OptionsQuestion(Question):
    """Perguntas com alternativas (múltipla escolha e bandeiras)."""

    MIN_OPTIONS = MIN_OPTIONS
    MAX_OPTIONS = MAX_OPTIONS

    def __init__(self, raw: dict[str, Any]) -> None:
        super().__init__(raw)
        self.options = raw.get("options")
        self.correct_index = raw.get("correctIndex")

    def _has_valid_answer_index(self) -> bool:
        return (
            isinstance(self.options, list)
            and is_integer(self.correct_index)
            and 0 <= self.correct_index < len(self.options)
        )

    def _validate_options(self) -> list[str]:
        problems: list[str] = []
        options = self.options
        if not isinstance(options, list) or not self.MIN_OPTIONS <= len(options) <= self.MAX_OPTIONS:
            if self.MIN_OPTIONS == self.MAX_OPTIONS:
                rule = f"exatamente {self.MIN_OPTIONS} itens"
            else:
                rule = f"{self.MIN_OPTIONS} a {self.MAX_OPTIONS} itens"
            return [f"as alternativas precisam ser uma lista de {rule}"]
        if not all(is_non_empty_string(option) for option in options):
            problems.append("há alternativa vazia ou que não é texto")
        elif len({normalize_text(option) for option in options}) != len(options):
            problems.append("há alternativas repetidas")
        if not self._has_valid_answer_index():
            problems.append("correctIndex precisa apontar para uma alternativa existente")
        return problems

    def correct_answer_text(self) -> str | None:
        return self.options[self.correct_index] if self._has_valid_answer_index() else None


class MultipleChoiceQuestion(OptionsQuestion):
    TYPE = "multiple_choice"

    def _validate_specific(self) -> list[str]:
        return self._validate_options()


class FlagQuestion(OptionsQuestion):
    """Desafio de bandeira: sempre exatamente 4 países como alternativas."""

    TYPE = "flag"
    MIN_OPTIONS = 4
    MAX_OPTIONS = 4

    def __init__(self, raw: dict[str, Any]) -> None:
        super().__init__(raw)
        self.flag_code = raw.get("flagCode")
        self.target_id = raw.get("targetId")
        self.target_name = raw.get("targetName")

    def _validate_specific(self) -> list[str]:
        problems: list[str] = []
        if not (isinstance(self.flag_code, str) and re.fullmatch(r"[a-z]{2}", self.flag_code)):
            problems.append("flagCode precisa ser um código ISO de duas letras minúsculas")
        if not is_non_empty_string(self.target_id):
            problems.append("targetId ausente ou vazio")
        if not is_non_empty_string(self.target_name):
            problems.append("targetName ausente ou vazio")
        return problems + self._validate_options()


class MapQuestion(Question):
    """Desafio no mapa: o jogador clica em um país (targetId = id no GeoJSON)."""

    TYPE = "map"

    def __init__(self, raw: dict[str, Any]) -> None:
        super().__init__(raw)
        self.target_id = raw.get("targetId")
        self.target_name = raw.get("targetName")

    def _validate_specific(self) -> list[str]:
        problems: list[str] = []
        if not is_non_empty_string(self.target_id):
            problems.append("targetId (identificador do país no GeoJSON) ausente ou vazio")
        if self.target_name is not None and not is_non_empty_string(self.target_name):
            problems.append("targetName, quando existe, precisa ser um texto não vazio")
        return problems

    def correct_answer_text(self) -> str | None:
        return self.target_name if is_non_empty_string(self.target_name) else self.target_id


class InvalidQuestion(Question):
    """Representa um item do JSON que não é uma pergunta reconhecível.

    Em vez de derrubar o programa, guardamos o item e explicamos o problema no
    relatório (o mesmo cuidado que o JavaScript tem ao carregar o banco).
    """

    def __init__(self, raw: Any, reason: str | None = None) -> None:
        super().__init__(raw if isinstance(raw, dict) else {})
        self._is_object = isinstance(raw, dict)
        self._reason = reason

    def validate(self) -> list[str]:
        if not self._is_object:
            return ["a pergunta precisa ser um objeto"]
        return self._validate_common() + self._validate_specific()

    def _validate_specific(self) -> list[str]:
        return [self._reason or f"tipo inválido: {self.raw.get('type')!r}"]

    def correct_answer_text(self) -> str | None:
        return None


class QuestionFactory:
    """Escolhe a classe certa de acordo com o campo "type" do JSON."""

    _registry: dict[str, type[Question]] = {
        cls.TYPE: cls for cls in (MultipleChoiceQuestion, FlagQuestion, MapQuestion)  # type: ignore[misc]
    }

    @classmethod
    def create(cls, raw: Any) -> Question:
        if not isinstance(raw, dict):
            return InvalidQuestion(raw)
        question_class = cls._registry.get(raw.get("type"))
        if question_class is None:
            return InvalidQuestion(raw)
        return question_class(raw)
