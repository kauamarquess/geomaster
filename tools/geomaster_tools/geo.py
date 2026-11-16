"""Catálogo de países do mapa (data/geojson/countries.geojson)."""
from __future__ import annotations

import json
from pathlib import Path


class CountryCatalog:
    """Sabe quais ids de país existem no mapa e como se chamam."""

    def __init__(self, names_by_id: dict[str, str]) -> None:
        self._names = dict(names_by_id)

    @classmethod
    def from_file(cls, path: str | Path) -> "CountryCatalog":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        names: dict[str, str] = {}
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            country_id = props.get("id")
            if isinstance(country_id, str) and country_id:
                names[country_id] = props.get("name") or ""
        return cls(names)

    def __contains__(self, country_id: object) -> bool:
        return country_id in self._names

    def __len__(self) -> int:
        return len(self._names)

    def name_of(self, country_id: str) -> str | None:
        return self._names.get(country_id)

    @property
    def ids(self) -> set[str]:
        return set(self._names)
