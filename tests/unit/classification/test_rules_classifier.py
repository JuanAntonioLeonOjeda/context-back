"""The rules classifier with the real data files: guide cases, real headlines, file checks."""

import shutil
from pathlib import Path

import pytest

from datos.classification.infrastructure.rules_classifier import (
    InvalidRulesFileError,
    load_rules_classifier,
)
from datos.governments.application.published import CompetenceLevel

DATA = Path("data/classification")
SECTORS = frozenset({"education", "health", "housing"})
CLASSIFIER = load_rules_classifier(DATA, sector_ids=SECTORS)
STATE, CCAA, LOCAL = CompetenceLevel.STATE, CompetenceLevel.CCAA, CompetenceLevel.LOCAL


@pytest.mark.parametrize(
    ("headline", "communities", "levels", "sectors"),
    [
        # Invented examples of docs/labelling-guide.md.
        ("The Government approves", set(), set(), set()),
        (
            "El Gobierno aprueba un decreto para limitar las subidas del alquiler",
            set(),
            {STATE},
            {"housing"},
        ),
        (
            "La Generalitat de Catalunya declara 40 nuevas zonas tensionadas",
            {"ccaa-09"},
            {CCAA},
            {"housing"},
        ),
        (
            "Más Madrid acusa a la Comunidad de Madrid de infrafinanciar la atención primaria",
            {"ccaa-13"},
            set(),
            {"health"},
        ),
        (
            "La Xunta y el ministerio chocan por la financiación de las plazas MIR",
            {"ccaa-12"},
            {CCAA, STATE},
            {"health"},
        ),
        (
            "El Cabildo de Lanzarote construye 200 viviendas públicas",
            {"ccaa-05"},
            {LOCAL},
            {"housing"},
        ),
        ("L'Ajuntament de Girona tanca un CAP per obres", {"ccaa-09"}, {LOCAL}, {"health"}),
        ("La Junta abre la matrícula de FP", set(), {CCAA}, {"education"}),
        # Real headlines from the feed fixtures (tests/fixtures/feeds/).
        (
            "Detenido en Tenerife un hombre buscado por un presunto robo con fuerza",
            {"ccaa-05"},
            set(),
            set(),
        ),
        (
            "Prudencia en Marruecos ante la primera visita de un rey de España a Ceuta y Melilla"
            " en dos décadas",
            {"ccaa-18", "ccaa-19"},
            set(),
            set(),
        ),
        (
            "Clavijo alerta de que el problema de los menores migrantes lo vamos a volver a tener",
            set(),
            set(),
            set(),
        ),
    ],
)
def test_labels_of_guide_cases_and_real_headlines(
    headline: str, communities: set[str], levels: set[CompetenceLevel], sectors: set[str]
) -> None:
    labels = CLASSIFIER.classify(headline, None)

    assert (labels.communities, labels.levels, labels.sectors) == (
        frozenset(communities),
        frozenset(levels),
        frozenset(sectors),
    )


def test_an_ambiguous_institution_gives_the_level_but_not_a_community() -> None:
    labels = CLASSIFIER.classify("La Junta aprueba el plan de vivienda", None)

    assert (labels.communities, labels.levels) == (frozenset(), frozenset({CCAA}))


def test_the_pope_is_not_the_province_of_leon() -> None:
    assert (
        CLASSIFIER.classify("El Papa León XIV ingresa en el hospital", None).communities
        == frozenset()
    )


def test_the_lead_counts_as_well_as_the_headline() -> None:
    labels = CLASSIFIER.classify("Nuevo plan", "La Junta de Andalucía amplía las becas")

    assert (labels.communities, labels.sectors) == (
        frozenset({"ccaa-01"}),
        frozenset({"education"}),
    )


def test_the_version_is_a_hash_of_the_files_and_changes_with_any_term(tmp_path: Path) -> None:
    copy = tmp_path / "rules"
    shutil.copytree(DATA, copy)
    before = load_rules_classifier(copy, sector_ids=SECTORS).model_version
    with (copy / "sectors.csv").open("a", encoding="utf-8") as file:
        file.write("ambulatorio,health,es\n")

    after = load_rules_classifier(copy, sector_ids=SECTORS).model_version

    assert before == CLASSIFIER.model_version and len(before) == 12
    assert after != before


@pytest.mark.parametrize(
    ("file", "row", "message"),
    [
        ("levels.csv", "Pleno,provincial,es\n", "levels.csv line"),
        ("places.csv", "Atlantis,ccaa-99x,,city,es\n", "not a community id"),
        ("sectors.csv", "museo,culture,es\n", "unknown sector culture"),
        ("levels.csv", "Gobierno,state,es\n", "term listed twice: Gobierno"),
    ],
)
def test_an_invalid_row_is_refused_with_its_file_and_line(
    tmp_path: Path, file: str, row: str, message: str
) -> None:
    copy = tmp_path / "rules"
    shutil.copytree(DATA, copy)
    with (copy / file).open("a", encoding="utf-8") as handle:
        handle.write(row)

    with pytest.raises(InvalidRulesFileError, match=message):
        load_rules_classifier(copy, sector_ids=SECTORS)
