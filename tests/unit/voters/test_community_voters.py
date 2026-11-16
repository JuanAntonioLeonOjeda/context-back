"""Which election, income year and dimension the profile of a community uses."""

from datetime import UTC, date, datetime
from decimal import Decimal

from datos.voters.application.community_voters import (
    CandidatureCount,
    ElectionInfo,
    IncomeDownloadInfo,
    MunicipalRow,
    community_voters,
)
from datos.voters.domain.dimensions import INCOME, SIZE

LATEST = ElectionInfo("congreso-2026-11", date(2026, 11, 29), "02202611_MUNI.zip")
EARLIER = ElectionInfo("congreso-2023-07", date(2023, 7, 23), "02202307_MUNI.zip")
ROWS = [
    MunicipalRow("35016", 300, 0, Decimal("15000"), (CandidatureCount("000005", "PP", 300),)),
    MunicipalRow("38038", 200, 0, Decimal("14000"), (CandidatureCount("000074", "U.P.N.", 200),)),
]


DOWNLOAD = IncomeDownloadInfo(2023, "https://example.org/ine", datetime(2026, 11, 6, tzinfo=UTC))


class _Reader:
    def __init__(self, download: IncomeDownloadInfo | None = None) -> None:
        self.asked: list[tuple[str, int]] = []
        self._download = download

    def elections(self) -> list[ElectionInfo]:
        return [LATEST, EARLIER]

    def municipal_rows(
        self, territory_id: str, election_id: str, income_year: int
    ) -> list[MunicipalRow]:
        self.asked.append((election_id, income_year))
        return ROWS

    def income_download(self, year: int) -> IncomeDownloadInfo | None:
        return self._download


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


def test_income_is_the_default_dimension_and_names_its_download() -> None:
    found = community_voters(
        _Reader(DOWNLOAD), {}, territory_id="ccaa-05", election_id="congreso-2023-07"
    )

    assert found is not None
    assert (found.dimension, found.download) == (INCOME, DOWNLOAD)


def test_size_groups_by_the_census_and_has_no_download_to_name() -> None:
    found = community_voters(
        _Reader(DOWNLOAD),
        {},
        territory_id="ccaa-05",
        election_id="congreso-2023-07",
        dimension=SIZE,
    )

    assert found is not None and found.profile is not None
    assert found.download is None  # the census is the election's own, not an INE download
    # Censuses 300 and 200, both below 1,500 electors: the first of four bands, by census value.
    assert [len(b.municipality_codes) for b in found.profile.bands] == [2, 0, 0, 0]
    assert (found.profile.bands[0].value_min, found.profile.bands[0].value_max) == (
        Decimal(200),
        Decimal(300),
    )


def test_size_has_a_value_for_a_municipality_whose_income_the_ine_hides() -> None:
    hidden = [
        MunicipalRow("35016", 300, 0, None, (CandidatureCount("000005", "PP", 300),)),
        MunicipalRow("38038", 200, 0, None, (CandidatureCount("000074", "U.P.N.", 200),)),
    ]

    class _Hidden(_Reader):
        def municipal_rows(
            self, territory_id: str, election_id: str, income_year: int
        ) -> list[MunicipalRow]:
            return hidden

    by_income = community_voters(_Hidden(), {}, territory_id="ccaa-05", election_id=None)
    by_size = community_voters(
        _Hidden(), {}, territory_id="ccaa-05", election_id=None, dimension=SIZE
    )

    assert by_income is not None and by_income.profile is None  # no income, no profile
    assert by_size is not None and by_size.profile is not None
    assert by_size.profile.without_value == ()
