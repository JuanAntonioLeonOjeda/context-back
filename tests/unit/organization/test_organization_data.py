"""The curated organisation files of the repository stay sound (data/organization/)."""

from datetime import date
from pathlib import Path

from datos.governments.infrastructure.csv_source import read_sectors
from datos.organization.domain.body import BodyKind
from datos.organization.domain.chart import ChartStatus, executive_chart
from datos.organization.domain.dataset import dataset_problems
from datos.organization.infrastructure.csv_source import read_organization
from datos.territories.csv_source import read_territories

DATA = Path("data/organization")


def test_the_files_are_read_and_have_no_problem_against_the_real_territories_and_sectors() -> None:
    bodies, holders, competences = read_organization(DATA)
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


def test_every_body_has_a_competence_and_the_states_holders_cite_the_boe() -> None:
    bodies, holders, competences = read_organization(DATA)

    with_competences = {c.body_id for c in competences}
    assert [b.id for b in bodies if b.id not in with_competences] == []
    state = {b.id for b in bodies if b.territory_id == "es"}
    assert [h.body_id for h in holders if h.body_id in state and "boe.es" not in h.source_url] == []


def test_the_states_executive_is_complete_on_the_day_it_was_curated() -> None:
    bodies, holders, _ = read_organization(DATA)

    chart = executive_chart(bodies, holders, "es", date(2026, 11, 13))

    assert chart.status is ChartStatus.COMPLETE
    assert chart.head is not None
    assert chart.head.holder.holder_name == "Pedro Sánchez Pérez-Castejón"
    # The 22 ministries of Real Decreto 829/2023 (article 1), each with a holder in force.
    assert len(chart.departments) == 22
    assert all(p.body.kind is BodyKind.DEPARTMENT for p in chart.departments)


def test_the_ministry_without_a_minister_is_shown_with_who_has_its_ordinary_business() -> None:
    bodies, holders, _ = read_organization(DATA)

    chart = executive_chart(bodies, holders, "es", date(2026, 11, 13))

    transport = next(p for p in chart.departments if p.body.id == "es-transportes")
    assert transport.holder.holder_name == "Carlos Cuerpo Caballero"
    assert "despacho ordinario" in transport.holder.post_title
    # Before the minister left (RD 974/2026, of 4 November) the data has no holder for it.
    assert executive_chart(bodies, holders, "es", date(2026, 11, 3)).status is ChartStatus.NO_DATA
