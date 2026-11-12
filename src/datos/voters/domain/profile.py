"""Voter profile of a community: its municipalities in income bands, and the votes of each band.

Descriptive and about areas, never people (spec decisions 2, 5, 7 and 9): a band is a group of
municipalities, and its shares say how those municipalities voted, not how their richer or poorer
residents did (ecological fallacy).
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

BANDS = 5  # spec decision 5
SHOWN_FROM_PERCENT = 3  # spec decision 7: a group is shown from 3 % of the community's valid votes
OTHERS = "otras"  # every group below the threshold, added up
LIST_PREFIX = "lista:"  # a candidature without a party in the table, by its acronym (decision 6)


def vote_group(national_head_code: str, acronym: str, party_by_head: Mapping[str, str]) -> str:
    """The group a candidature's votes count for: its party, or its own acronym when the curated
    table (data/voters/candidature-parties.csv) gives it none."""
    return party_by_head.get(national_head_code, f"{LIST_PREFIX}{acronym}")


@dataclass(frozen=True, slots=True)
class MunicipalVotes:
    code: str
    census: int
    income: Decimal | None  # None: the INE gives none (statistical secrecy)
    blank_votes: int
    votes: Mapping[str, int]  # group (vote_group) -> votes

    @property
    def valid_votes(self) -> int:
        return self.blank_votes + sum(self.votes.values())


@dataclass(frozen=True, slots=True)
class Band:
    index: int  # 0 = the lowest incomes
    municipality_codes: tuple[str, ...]
    census: int
    income_min: Decimal | None  # None when the band is empty
    income_max: Decimal | None
    valid_votes: int
    blank_votes: int
    votes: Mapping[str, int]  # shown groups and OTHERS


@dataclass(frozen=True, slots=True)
class VoterProfile:
    bands: tuple[Band, ...]
    shown_groups: tuple[str, ...]  # the groups above the threshold, sorted by key
    census: int  # of the municipalities with income
    without_income: tuple[str, ...]  # municipalities left out, by code


def band_index(census_before: int, census: int, total: int) -> int:
    """The band of a municipality whose census starts at `census_before` of `total`: where its
    midpoint falls, floor(BANDS · (before + census / 2) / total), in integers so no rounding
    decides a border; the last municipality cannot fall past the last band. `total` is not 0."""
    return min(BANDS - 1, (2 * census_before + census) * BANDS // (2 * total))


def voter_profile(municipalities: Sequence[MunicipalVotes]) -> VoterProfile | None:
    """The profile of a community's municipalities, or None when fewer than two have income
    (one municipality cannot be split into bands: Ceuta, Melilla) or when those with income
    have no census at all (there is no population to split)."""
    placed = sorted(
        (m for m in municipalities if m.income is not None),
        key=lambda m: (m.income, m.code),  # ties in income: by INE code, so it is deterministic
    )
    if len(placed) < 2:
        return None
    total = sum(m.census for m in placed)
    if total == 0:
        return None
    shown = _shown_groups(municipalities)
    members: list[list[MunicipalVotes]] = [[] for _ in range(BANDS)]
    before = 0
    for m in placed:
        members[band_index(before, m.census, total)].append(m)
        before += m.census
    return VoterProfile(
        bands=tuple(_band(i, ms, shown) for i, ms in enumerate(members)),
        shown_groups=tuple(sorted(shown)),
        census=total,
        without_income=tuple(sorted(m.code for m in municipalities if m.income is None)),
    )


def _shown_groups(municipalities: Sequence[MunicipalVotes]) -> set[str]:
    """Groups with at least SHOWN_FROM_PERCENT of the community's valid votes, all its
    municipalities counted (with or without income). Integers: votes·100 ≥ 3·valid."""
    totals: dict[str, int] = defaultdict(int)
    for m in municipalities:
        for group, votes in m.votes.items():
            totals[group] += votes
    valid = sum(m.valid_votes for m in municipalities)
    return {g for g, v in totals.items() if v * 100 >= SHOWN_FROM_PERCENT * valid}


def _band(index: int, members: Sequence[MunicipalVotes], shown: set[str]) -> Band:
    votes: dict[str, int] = defaultdict(int)
    for m in members:
        for group, count in m.votes.items():
            votes[group if group in shown else OTHERS] += count
    incomes = [m.income for m in members if m.income is not None]
    return Band(
        index=index,
        municipality_codes=tuple(m.code for m in members),
        census=sum(m.census for m in members),
        income_min=min(incomes) if incomes else None,
        income_max=max(incomes) if incomes else None,
        valid_votes=sum(m.valid_votes for m in members),
        blank_votes=sum(m.blank_votes for m in members),
        votes=dict(votes),
    )
