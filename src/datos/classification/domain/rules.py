"""The rules classifier: terms from data/classification/ matched in a headline and lead.

Pure. How terms match (data/classification/README.md):
1. exclusions are removed from the text first;
2. a term that starts with a capital matches only with that capital; a lower-case term matches
   in any case;
3. whole words only;
4. the longest term wins; shorter terms overlapping it are ignored.
The outlet is never an input, and no term names a party or a politician (ADR-0015).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from datos.classification.domain.labels import Evidence, Labels
from datos.governments.application.published import CompetenceLevel


@dataclass(frozen=True, slots=True)
class PlaceTerm:
    term: str
    territory_id: str
    level: CompetenceLevel | None  # institutions also give the level


@dataclass(frozen=True, slots=True)
class LevelTerm:
    term: str
    level: CompetenceLevel


@dataclass(frozen=True, slots=True)
class SectorTerm:
    term: str
    sector_id: str


type Term = PlaceTerm | LevelTerm | SectorTerm


@dataclass(frozen=True, slots=True)
class Rules:
    """Compiled once; `classify_text` reuses them for every article."""

    patterns: tuple[tuple[re.Pattern[str], Term], ...]  # longest term first
    exclusions: tuple[re.Pattern[str], ...]


def compile_rules(terms: Iterable[Term], exclusions: Iterable[str]) -> Rules:
    ordered = sorted(terms, key=lambda t: (-len(t.term), t.term))
    return Rules(
        patterns=tuple((_pattern(t.term), t) for t in ordered),
        exclusions=tuple(_pattern(phrase) for phrase in exclusions),
    )


def classify_text(text: str, rules: Rules) -> Labels:
    for exclusion in rules.exclusions:
        text = exclusion.sub(" ", text)
    taken: list[tuple[int, int]] = []
    found: list[Term] = []
    for pattern, term in rules.patterns:
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in taken):
                continue  # inside a longer term already matched
            taken.append((match.start(), match.end()))
            found.append(term)
    return _labels(found)


def _pattern(term: str) -> re.Pattern[str]:
    flags = 0 if term[:1].isupper() else re.IGNORECASE
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", flags)


def _labels(found: list[Term]) -> Labels:
    communities: set[str] = set()
    sectors: set[str] = set()
    levels: set[CompetenceLevel] = set()
    evidence: list[Evidence] = []
    for term in found:
        match term:
            case PlaceTerm(territory_id=territory_id, level=level):
                communities.add(territory_id)
                evidence.append(Evidence(term.term, f"community:{territory_id}"))
                if level is not None:
                    levels.add(level)
                    evidence.append(Evidence(term.term, f"level:{level.value}"))
            case LevelTerm(level=level):
                levels.add(level)
                evidence.append(Evidence(term.term, f"level:{level.value}"))
            case SectorTerm(sector_id=sector_id):
                sectors.add(sector_id)
                evidence.append(Evidence(term.term, f"sector:{sector_id}"))
    return Labels(frozenset(communities), frozenset(sectors), frozenset(levels), tuple(evidence))
