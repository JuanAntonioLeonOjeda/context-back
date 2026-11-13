"""The curated organisation files of the repository stay sound (data/organization/)."""

from pathlib import Path

from datos.governments.infrastructure.csv_source import read_sectors
from datos.organization.domain.dataset import dataset_problems
from datos.organization.infrastructure.csv_source import read_organization
from datos.territories.csv_source import read_territories


def test_the_files_are_read_and_have_no_problem_against_the_real_territories_and_sectors() -> None:
    bodies, holders, competences = read_organization(Path("data/organization"))
    territories = read_territories(Path("data/territories/territories.csv"))
    sectors = read_sectors(Path("data/governments/sectors.csv"))

    problems = dataset_problems(
        bodies,
        holders,
        competences,
        territory_ids={t.id for t in territories},
        sector_ids={s.id for s in sectors},
    )

    assert problems == []
