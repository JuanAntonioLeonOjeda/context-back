"""Which election and which income year the profile of a community uses."""

from datetime import date
from decimal import Decimal

from datos.voters.application.community_voters import (
    CandidatureCount,
    ElectionInfo,
    IncomeDownloadInfo,
    MunicipalRow,
    community_voters,
)

LATEST = ElectionInfo("congreso-2026-11", date(2026, 11, 29), "02202611_MUNI.zip")
EARLIER = ElectionInfo("congreso-2023-07", date(2023, 7, 23), "02202307_MUNI.zip")
ROWS = [
    MunicipalRow("35016", 300, 0, Decimal("15000"), (CandidatureCount("000005", "PP", 300),)),
    MunicipalRow("38038", 200, 0, Decimal("14000"), (CandidatureCount("000074", "U.P.N.", 200),)),
]


class _Reader:
    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []

    def elections(self) -> list[ElectionInfo]:
        return [LATEST, EARLIER]

    def municipal_rows(
        self, territory_id: str, election_id: str, income_year: int
    ) -> list[MunicipalRow]:
        self.asked.append((election_id, income_year))
        return ROWS

    def income_download(self, year: int) -> IncomeDownloadInfo | None:
        return None


def test_without_an_election_the_latest_loaded_one_with_the_income_of_its_year() -> None:
    reader = _Reader()

    found = community_voters(reader, {}, territory_id="ccaa-05", election_id=None)

    assert found is not None and found.election == LATEST
    assert reader.asked == [("congreso-2026-11", 2026)]


def test_an_earlier_election_uses_the_income_of_its_own_year() -> None:
    reader = _Reader()

    community_voters(reader, {}, territory_id="ccaa-05", election_id="congreso-2023-07")

    assert reader.asked == [("congreso-2023-07", 2023)]


def test_an_unknown_election_gives_nothing() -> None:
    assert community_voters(_Reader(), {}, territory_id="ccaa-05", election_id="x-2019-04") is None


def test_candidatures_become_their_party_or_their_own_list() -> None:
    party_by_candidature = {"congreso-2023-07": {"000005": "pp"}}

    found = community_voters(
        _Reader(), party_by_candidature, territory_id="ccaa-05", election_id="congreso-2023-07"
    )

    assert found is not None and found.profile is not None
    assert found.profile.shown_groups == ("lista:U.P.N.", "pp")
