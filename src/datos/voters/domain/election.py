"""An election's official results by municipality, as the Ministerio del Interior publishes them."""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class ElectionKind(StrEnum):
    """The elections this project loads (spec decision 1: general elections only)."""

    CONGRESO = "congreso"


@dataclass(frozen=True, slots=True)
class Election:
    kind: ElectionKind
    held_on: date

    @property
    def id(self) -> str:
        """`congreso-2023-07`: the kind and the month, as the Ministerio names its files."""
        return f"{self.kind}-{self.held_on:%Y-%m}"


@dataclass(frozen=True, slots=True)
class Candidature:
    code: str
    acronym: str
    name: str
    # The candidature its votes add up to nationally (PSC → PSOE); a head is its own.
    national_head_code: str


@dataclass(frozen=True, slots=True)
class MunicipalResult:
    municipality_code: str  # INE: province (2) + municipality (3)
    municipality_name: str
    census: int  # INE census of the municipality
    blank_votes: int
    null_votes: int
    candidature_votes: int

    @property
    def valid_votes(self) -> int:
        """Spanish electoral law counts blank votes as valid; null votes are not."""
        return self.blank_votes + self.candidature_votes


@dataclass(frozen=True, slots=True)
class CandidatureVotes:
    municipality_code: str
    candidature_code: str
    votes: int


@dataclass(frozen=True, slots=True)
class ElectionFile:
    """Everything one downloaded file says, before it is checked or stored."""

    source_file: str
    sha256: str
    election: Election
    candidatures: tuple[Candidature, ...]
    results: tuple[MunicipalResult, ...]
    votes: tuple[CandidatureVotes, ...]


def file_problems(file: ElectionFile, province_ids: Collection[str]) -> list[str]:
    """Every reason not to store the file, as readable messages (empty when it is sound).

    The database refuses most of these too; checking them first reports all at once, before
    anything is written, the way the governments loader does.
    """
    problems: list[str] = []
    candidature_codes = {c.code for c in file.candidatures}
    problems.extend(
        f"candidature {c.code}: national head {c.national_head_code} is not in the file"
        for c in file.candidatures
        if c.national_head_code not in candidature_codes
    )
    problems.extend(_duplicates([r.municipality_code for r in file.results], "municipality"))
    problems.extend(
        _duplicates([f"{v.municipality_code}/{v.candidature_code}" for v in file.votes], "votes of")
    )
    problems.extend(
        f"municipality {r.municipality_code}: province prov-{r.municipality_code[:2]} is unknown"
        for r in file.results
        if f"prov-{r.municipality_code[:2]}" not in province_ids
    )
    problems.extend(_vote_problems(file, candidature_codes))
    return problems


def _vote_problems(file: ElectionFile, candidature_codes: set[str]) -> list[str]:
    totals: dict[str, int] = defaultdict(int)
    problems: list[str] = []
    for v in file.votes:
        totals[v.municipality_code] += v.votes
        if v.candidature_code not in candidature_codes:
            problems.append(
                f"votes of {v.municipality_code}: unknown candidature {v.candidature_code}"
            )
    results = {r.municipality_code: r for r in file.results}
    problems.extend(
        f"votes of {code}: no municipal total" for code in sorted(totals) if code not in results
    )
    # Files 05 and 06 are two views of the same count: they must agree municipality by municipality.
    problems.extend(
        f"municipality {code}: its candidatures add up to {totals.get(code, 0)},"
        f" its total says {r.candidature_votes}"
        for code, r in results.items()
        if totals.get(code, 0) != r.candidature_votes
    )
    return problems


def _duplicates(keys: list[str], what: str) -> list[str]:
    seen: set[str] = set()
    repeated: list[str] = []
    for key in keys:
        if key in seen:
            repeated.append(f"{what} {key} is repeated")
        seen.add(key)
    return repeated
