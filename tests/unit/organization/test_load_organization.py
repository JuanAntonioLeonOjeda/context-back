"""Loading the organisation: all checked first, and nothing written unless nothing is wrong."""

from collections.abc import Sequence
from datetime import date

import pytest

from datos.organization.application.load_organization import (
    InvalidOrganizationError,
    OrganizationCounts,
    load_organization,
)
from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence

SOURCE = "https://example.org/source"
HEAD = Body("es-gobierno", BodyKind.EXECUTIVE_HEAD, BodyLevel.STATE, "es", "G", None, None, SOURCE)
MINISTRY = Body(
    "es-hacienda", BodyKind.DEPARTMENT, BodyLevel.STATE, "es", "H", "es-gobierno", None, SOURCE
)
HOLDERS = [
    Holder(b.id, "Post", f"Holder of {b.id}", date(2023, 11, 21), None, SOURCE)
    for b in (HEAD, MINISTRY)
]
COMPETENCES = [Competence("es-hacienda", "Runs the taxes", "Art. 1", ("taxes",), SOURCE)]


class _Repository:
    def __init__(self) -> None:
        self.written: list[tuple[int, int, int]] = []

    def territory_ids(self) -> set[str]:
        return {"es", "ccaa-13"}

    def sector_ids(self) -> set[str]:
        return {"taxes", "health"}

    def replace_all(
        self,
        bodies: Sequence[Body],
        holders: Sequence[Holder],
        competences: Sequence[Competence],
    ) -> None:
        self.written.append((len(bodies), len(holders), len(competences)))


def test_a_sound_dataset_is_written_once_and_counted() -> None:
    repository = _Repository()

    counts = load_organization(repository, [HEAD, MINISTRY], HOLDERS, COMPETENCES)

    assert counts == OrganizationCounts(bodies=2, holders=2, competences=1)
    assert repository.written == [(2, 2, 1)]


def test_a_dataset_with_problems_writes_nothing_and_lists_every_one() -> None:
    repository = _Repository()
    orphan = Holder("es-nada", "Post", "Nobody", date(2023, 1, 1), None, SOURCE)
    no_sector = Competence("es-hacienda", "Does things", "Art. 2", (), SOURCE)

    with pytest.raises(InvalidOrganizationError) as error:
        load_organization(repository, [HEAD, MINISTRY], [*HOLDERS, orphan], [no_sector])

    assert len(error.value.problems) == 2
    assert str(error.value).startswith("2 problem(s):\n- ")
    assert repository.written == []


def test_the_territories_and_the_sectors_come_from_the_repository() -> None:
    elsewhere = Body(
        "ccaa-99-gobierno",
        BodyKind.EXECUTIVE_HEAD,
        BodyLevel.CCAA,
        "ccaa-99",
        "G",
        None,
        None,
        SOURCE,
    )
    unknown_sector = Competence("es-hacienda", "Does things", "Art. 2", ("nowhere",), SOURCE)
    repository = _Repository()

    with pytest.raises(InvalidOrganizationError) as error:
        load_organization(repository, [HEAD, MINISTRY, elsewhere], HOLDERS, [unknown_sector])

    assert any("unknown territory ccaa-99" in p for p in error.value.problems)
    assert any("unknown sector nowhere" in p for p in error.value.problems)
    assert repository.written == []


def test_an_empty_dataset_is_loaded_as_empty() -> None:
    repository = _Repository()

    assert load_organization(repository, [], [], []) == OrganizationCounts(0, 0, 0)
    assert repository.written == [(0, 0, 0)]
