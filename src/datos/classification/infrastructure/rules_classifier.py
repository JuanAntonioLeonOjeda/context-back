"""The rules classifier, built from the versioned files in data/classification/."""

import csv
import hashlib
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from datos.classification.domain.labels import Labels
from datos.classification.domain.rules import (
    LevelTerm,
    PlaceTerm,
    Rules,
    SectorTerm,
    Term,
    classify_text,
    compile_rules,
)
from datos.governments.application.published import CompetenceLevel

FILES = ("places.csv", "levels.csv", "sectors.csv", "exclusions.csv")


class InvalidRulesFileError(Exception):
    pass


class RulesClassifier:
    model_id = "rules"

    def __init__(self, rules: Rules, version: str) -> None:
        self._rules = rules
        self._version = version

    @property
    def model_version(self) -> str:
        return self._version

    def classify(self, headline: str, lead: str | None, tags: Sequence[str] = ()) -> Labels:
        # The rules read the text of the article, not its tags: their version is the files they
        # are built from, and they must say the same whatever the tags (ADR-0019).
        return classify_text(f"{headline}. {lead or ''}", self._rules)


def load_rules_classifier(directory: Path, *, sector_ids: frozenset[str]) -> RulesClassifier:
    """Reads and validates the four files; the version is a hash of their bytes."""
    places = [_place(r, directory, i) for i, r in _rows(directory / "places.csv")]
    levels = [_level(r, directory, i) for i, r in _rows(directory / "levels.csv")]
    sectors = [_sector(r, directory, i, sector_ids) for i, r in _rows(directory / "sectors.csv")]
    exclusions = [r["phrase"] for _, r in _rows(directory / "exclusions.csv")]
    terms: list[Term] = [*places, *levels, *sectors]
    _refuse_duplicates(terms)
    return RulesClassifier(compile_rules(terms, exclusions), _version(directory))


class _PlaceRow(BaseModel):
    term: str
    territory_id: str
    level: CompetenceLevel | None

    @field_validator("level", mode="before")
    @classmethod
    def _empty_as_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("territory_id")
    @classmethod
    def _community(cls, value: str) -> str:
        if not (value.startswith("ccaa-") and value[5:].isdigit() and len(value) == 7):
            raise ValueError(f"not a community id: {value}")
        return value


class _LevelRow(BaseModel):
    term: str
    level: CompetenceLevel


class _SectorRow(BaseModel):
    term: str
    sector_id: str


def _rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as file:
        return [(i + 2, row) for i, row in enumerate(csv.DictReader(file))]


def _place(row: dict[str, str], directory: Path, line: int) -> PlaceTerm:
    parsed = _parse(_PlaceRow, row, directory / "places.csv", line)
    return PlaceTerm(parsed.term, parsed.territory_id, parsed.level)


def _level(row: dict[str, str], directory: Path, line: int) -> LevelTerm:
    parsed = _parse(_LevelRow, row, directory / "levels.csv", line)
    return LevelTerm(parsed.term, parsed.level)


def _sector(
    row: dict[str, str], directory: Path, line: int, sector_ids: frozenset[str]
) -> SectorTerm:
    parsed = _parse(_SectorRow, row, directory / "sectors.csv", line)
    if parsed.sector_id not in sector_ids:
        raise InvalidRulesFileError(f"sectors.csv line {line}: unknown sector {parsed.sector_id}")
    return SectorTerm(parsed.term, parsed.sector_id)


def _parse[T: BaseModel](model: type[T], row: dict[str, str], path: Path, line: int) -> T:
    try:
        return model.model_validate(row)
    except ValidationError as error:
        raise InvalidRulesFileError(f"{path.name} line {line}: {error}") from error


def _refuse_duplicates(terms: list[Term]) -> None:
    # The same term twice would make its meaning depend on the file order.
    seen: set[str] = set()
    for term in terms:
        if term.term in seen:
            raise InvalidRulesFileError(f"term listed twice: {term.term}")
        seen.add(term.term)


def _version(directory: Path) -> str:
    digest = hashlib.sha256()
    for name in FILES:
        digest.update((directory / name).read_bytes())
    return digest.hexdigest()[:12]
