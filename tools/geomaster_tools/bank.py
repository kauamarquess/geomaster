"""O banco de perguntas: carregar, juntar partes, comparar e salvar."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from .models import Question, QuestionFactory, is_non_empty_string


class QuestionBankError(Exception):
    """Problema ao ler ou montar o banco (arquivo faltando, JSON quebrado...)."""


@dataclass
class BankComparison:
    only_here: list[str] = field(default_factory=list)
    only_there: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return not (self.only_here or self.only_there or self.changed)


class QuestionBank:
    """Uma coleção de perguntas (objetos `Question`) com versão e descrição."""

    def __init__(self, questions: Iterable[Question] = (), version: int = 2, description: str = "") -> None:
        self.questions: list[Question] = list(questions)
        self.version = version
        self.description = description

    # ---------- criação ----------
    @classmethod
    def from_raw(cls, items: Iterable[Any], version: int = 2, description: str = "") -> "QuestionBank":
        return cls((QuestionFactory.create(item) for item in items), version, description)

    @classmethod
    def from_file(cls, path: str | Path) -> "QuestionBank":
        data = cls._read_json(Path(path))
        items = data if isinstance(data, list) else (data.get("questions") if isinstance(data, dict) else None)
        if not isinstance(items, list):
            raise QuestionBankError(
                f'{Path(path).name}: o banco precisa ser uma lista de perguntas ou um objeto com a chave "questions".'
            )
        meta = data if isinstance(data, dict) else {}
        return cls.from_raw(items, meta.get("version", 1), meta.get("description", ""))

    @classmethod
    def from_parts(cls, directory: str | Path, pattern: str = "questions-part-*.json") -> "QuestionBank":
        files = sorted(Path(directory).glob(pattern))
        if not files:
            raise QuestionBankError(f"Nenhuma parte encontrada em {directory} ({pattern}).")
        items: list[Any] = []
        version = 1
        for file in files:
            data = cls._read_json(file)
            part = data.get("questions") if isinstance(data, dict) else data
            if not isinstance(part, list):
                raise QuestionBankError(f'{file.name}: não encontrei a lista "questions".')
            items.extend(part)
            if isinstance(data, dict) and isinstance(data.get("version"), int):
                version = max(version, data["version"])
        description = f"Banco oficial GeoMaster — {len(items)} perguntas (montado a partir de {len(files)} partes)."
        return cls.from_raw(items, version, description)

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise QuestionBankError(f"Arquivo não encontrado: {path}") from None
        except json.JSONDecodeError as error:
            raise QuestionBankError(f"JSON inválido em {path.name} (linha {error.lineno}): {error.msg}") from None

    # ---------- consulta ----------
    def __len__(self) -> int:
        return len(self.questions)

    def __iter__(self) -> Iterator[Question]:
        return iter(self.questions)

    @cached_property
    def valid_questions(self) -> list[Question]:
        """Só as perguntas sem problema de estrutura (as demais verificações usam esta lista)."""
        return [q for q in self.questions if not q.validate()]

    def count_by(self, getter: Callable[[Question], Any], only_valid: bool = True) -> Counter:
        source = self.valid_questions if only_valid else self.questions
        return Counter(getter(q) for q in source)

    # ---------- comparação ----------
    def compare(self, other: "QuestionBank") -> BankComparison:
        mine = {q.id: q.to_dict() for q in self.questions if is_non_empty_string(q.id)}
        theirs = {q.id: q.to_dict() for q in other.questions if is_non_empty_string(q.id)}
        return BankComparison(
            only_here=sorted(set(mine) - set(theirs)),
            only_there=sorted(set(theirs) - set(mine)),
            changed=sorted(i for i in set(mine) & set(theirs) if mine[i] != theirs[i]),
        )

    # ---------- salvar ----------
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "description": self.description,
            "questions": [q.to_dict() for q in self.questions],
        }

    def save(self, path: str | Path, overwrite: bool = False) -> Path:
        target = Path(path)
        if target.exists() and not overwrite:
            raise QuestionBankError(f"{target} já existe. Use --overwrite se quiser substituir.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target
