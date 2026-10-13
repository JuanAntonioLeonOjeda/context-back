from pathlib import Path

import pytest

from datos.governments.application.load_governments import (
    InvalidGovernmentsDatasetError,
    load_competences,
)
from datos.governments.domain.competence import (
    Competence,
    CompetenceFunction,
    CompetenceLevel,
    Sector,
    applicable_competences,
    competence_problems,
)
from datos.governments.infrastructure.csv_source import read_competences, read_sectors

DATA = Path("data/governments")
SOURCE = "https://example.org/law"
COMMUNITIES = {f"ccaa-{n:02d}" for n in range(1, 20)}
HEALTH = Sector("health", "Sanidad")


def _row(
    level: CompetenceLevel,
    function: CompetenceFunction = CompetenceFunction.EXECUTION,
    *,
    activity: str = "healthcare-services",
    territory_id: str | None = None,
    source_url: str = SOURCE,
) -> Competence:
    return Competence("health", activity, "d", level, function, territory_id, "basis", source_url)


GENERAL_CCAA = _row(CompetenceLevel.CCAA)
GENERAL_CCAA_LAW = _row(CompetenceLevel.CCAA, CompetenceFunction.DEVELOPMENT_LEGISLATION)
MELILLA_STATE = _row(CompetenceLevel.STATE, territory_id="ccaa-19")


# --- the versioned table ---------------------------------------------------------------


def test_the_versioned_competence_table_passes_every_rule() -> None:
    sectors = read_sectors(DATA / "sectors.csv")
    competences = read_competences(DATA / "competences.csv")

    assert competence_problems(sectors, competences, COMMUNITIES) == []


def test_in_the_versioned_table_the_state_runs_health_care_in_ceuta_and_melilla() -> None:
    competences = read_competences(DATA / "competences.csv")

    for territory in ("ccaa-18", "ccaa-19"):
        rows = applicable_competences(
            competences, sector_id="health", activity="healthcare-services", territory_id=territory
        )
        assert {(r.level, r.function) for r in rows} == {
            (CompetenceLevel.STATE, CompetenceFunction.EXECUTION)
        }


# --- which rows apply ------------------------------------------------------------------


def test_a_community_without_its_own_rows_gets_the_general_ones() -> None:
    rows = applicable_competences(
        [GENERAL_CCAA, GENERAL_CCAA_LAW, MELILLA_STATE],
        sector_id="health",
        activity="healthcare-services",
        territory_id="ccaa-13",
    )

    assert rows == [GENERAL_CCAA, GENERAL_CCAA_LAW]


def test_a_community_with_its_own_rows_gets_only_those() -> None:
    rows = applicable_competences(
        [GENERAL_CCAA, GENERAL_CCAA_LAW, MELILLA_STATE],
        sector_id="health",
        activity="healthcare-services",
        territory_id="ccaa-19",
    )

    assert rows == [MELILLA_STATE]


def test_rows_of_other_activities_never_apply() -> None:
    other = _row(CompetenceLevel.LOCAL, activity="public-health")

    rows = applicable_competences(
        [GENERAL_CCAA, other], sector_id="health", activity="public-health", territory_id="ccaa-01"
    )

    assert rows == [other]


# --- rules -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        pytest.param([GENERAL_CCAA, GENERAL_CCAA], "duplicate row", id="duplicate"),
        pytest.param(
            [_row(CompetenceLevel.STATE, territory_id="ccaa-19")],
            "territory row without general rows",
            id="override-without-general",
        ),
        pytest.param(
            [GENERAL_CCAA, _row(CompetenceLevel.STATE, territory_id="prov-28")],
            "territory is not a community",
            id="territory-not-community",
        ),
        pytest.param(
            [_row(CompetenceLevel.CCAA, source_url="http://example.org")],
            "source is not an https URL",
            id="insecure-source",
        ),
    ],
)
def test_reports_rule_violations(rows: list[Competence], expected: str) -> None:
    problems = competence_problems([HEALTH], rows, COMMUNITIES)

    assert any(expected in p for p in problems)


def test_reports_an_unknown_sector_and_an_unused_sector() -> None:
    education = Sector("education", "Educación")
    row = Competence(
        "transport",
        "x",
        "d",
        CompetenceLevel.STATE,
        CompetenceFunction.EXECUTION,
        None,
        "b",
        SOURCE,
    )

    problems = competence_problems([education], [row], COMMUNITIES)

    assert any("unknown sector" in p for p in problems)
    assert "sector education has no competences" in problems


class _Repository:
    def __init__(self) -> None:
        self.written = False

    def government_territory_ids(self) -> set[str]:
        return {"es"} | COMMUNITIES

    def replace_competences(self, sectors: object, competences: object) -> None:
        self.written = True


def test_nothing_is_written_when_the_table_is_invalid() -> None:
    repository = _Repository()

    with pytest.raises(InvalidGovernmentsDatasetError):
        load_competences(repository, [HEALTH], [GENERAL_CCAA, GENERAL_CCAA])  # type: ignore[arg-type]

    assert repository.written is False
