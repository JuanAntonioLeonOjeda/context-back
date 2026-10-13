"""Use case: validate the governments dataset and load it.

Nothing is written unless the whole dataset passes every rule.
"""

from collections.abc import Collection, Sequence
from datetime import date
from typing import Protocol

from datos.governments.domain.government_term import (
    EmptyPeriod,
    Gap,
    GovernmentTerm,
    NoGoverningParty,
    Overlap,
    term_problems,
    timeline_problems,
)
from datos.governments.domain.party import Party


class GovernmentRepository(Protocol):
    def government_territory_ids(self) -> set[str]:
        """Territories that must have a government: the State and the communities."""
        ...

    def replace_all(self, parties: Sequence[Party], terms: Sequence[GovernmentTerm]) -> None: ...


class InvalidGovernmentsDatasetError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__(f"{len(problems)} problem(s):\n- " + "\n- ".join(problems))
        self.problems = list(problems)


def dataset_problems(
    parties: Sequence[Party],
    terms: Sequence[GovernmentTerm],
    territory_ids: Collection[str],
    *,
    since: date,
    today: date,
) -> list[str]:
    """Every rule of the dataset, as readable messages (empty when it is valid)."""
    problems: list[str] = []
    party_ids = {p.id for p in parties}
    for term in terms:
        where = f"{term.territory_id} from {term.valid_from}"
        if term.territory_id not in territory_ids:
            problems.append(f"{where}: territory has no government in this dataset")
        problems.extend(
            f"{where}: unknown party {p.party_id}"
            for p in term.parties
            if p.party_id not in party_ids
        )
        problems.extend(f"{where}: {_describe(p)}" for p in term_problems(term))
    problems.extend(
        _describe(p)
        for p in timeline_problems(terms, sorted(territory_ids), since=since, today=today)
    )
    used = {p.party_id for t in terms for p in t.parties}
    problems.extend(f"party {p.id} is not used by any term" for p in parties if p.id not in used)
    return problems


def _describe(problem: NoGoverningParty | EmptyPeriod | Overlap | Gap) -> str:
    match problem:
        case NoGoverningParty():
            return "no governing party"
        case EmptyPeriod():
            return "the period lasts less than one day"
        case Overlap(first=first, second=second):
            return (
                f"{first.territory_id}: terms from {first.valid_from} and "
                f"{second.valid_from} overlap"
            )
        case Gap(territory_id=territory, start=start, end=end):
            return f"{territory}: no government from {start} to {end or 'today'}"


def load_governments(
    repository: GovernmentRepository,
    parties: Sequence[Party],
    terms: Sequence[GovernmentTerm],
    *,
    since: date,
    today: date,
) -> None:
    problems = dataset_problems(
        parties, terms, repository.government_territory_ids(), since=since, today=today
    )
    if problems:
        raise InvalidGovernmentsDatasetError(problems)
    repository.replace_all(parties, terms)
