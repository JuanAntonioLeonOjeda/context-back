"""Load the curated organisation files: check them all, then make the database mirror them."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from datos.organization.domain.body import Body, Holder
from datos.organization.domain.boxes import Competence
from datos.organization.domain.dataset import dataset_problems


class OrganizationRepository(Protocol):
    def territory_ids(self) -> set[str]: ...

    def sector_ids(self) -> set[str]: ...

    def replace_all(
        self,
        bodies: Sequence[Body],
        holders: Sequence[Holder],
        competences: Sequence[Competence],
    ) -> None:
        """Make the stored bodies, holders and competences mirror these (one transaction)."""
        ...


class InvalidOrganizationError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__(f"{len(problems)} problem(s):\n- " + "\n- ".join(problems))
        self.problems = list(problems)


@dataclass(frozen=True, slots=True)
class OrganizationCounts:
    bodies: int
    holders: int
    competences: int


def load_organization(
    repository: OrganizationRepository,
    bodies: Sequence[Body],
    holders: Sequence[Holder],
    competences: Sequence[Competence],
) -> OrganizationCounts:
    """Check the three files together and, only if nothing is wrong, replace what is stored.

    The files are the whole truth: what they no longer have is removed from the database, and
    their history (periods with an end) stays in them and in git.
    """
    problems = dataset_problems(
        bodies,
        holders,
        competences,
        territory_ids=repository.territory_ids(),
        sector_ids=repository.sector_ids(),
    )
    if problems:
        raise InvalidOrganizationError(problems)
    repository.replace_all(bodies, holders, competences)
    return OrganizationCounts(len(bodies), len(holders), len(competences))
