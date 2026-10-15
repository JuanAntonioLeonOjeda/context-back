import io
from pathlib import Path

import pytest

from datos.territories.gml_source import InvalidBoundariesFileError, read_communities, territory_id

FIXTURE = Path("tests/fixtures/geo/ceuta-melilla-and-unassigned.gml")


def test_reads_the_communities_and_skips_units_outside_any_community() -> None:
    with FIXTURE.open("rb") as gml:
        shapes = read_communities(gml)

    assert [s.territory_id for s in shapes] == ["ccaa-18", "ccaa-19"]
    assert shapes[0].name == "Ciudad Autónoma de Ceuta"


def test_coordinates_are_longitude_first_as_geojson_wants() -> None:
    # The IGN file is EPSG:4258 with latitude first; Ceuta is near 35.9 N, 5.3 W.
    with FIXTURE.open("rb") as gml:
        [ceuta, _] = read_communities(gml)

    longitude, latitude = ceuta.polygons[0][0][0]
    assert -5.5 < longitude < -5.2 and 35.8 < latitude < 36.0


@pytest.mark.parametrize(
    ("code", "expected"),
    [("34010000000", "ccaa-01"), ("34190000000", "ccaa-19"), ("34200000000", None)],
)
def test_national_codes_map_to_territory_ids(code: str, expected: str | None) -> None:
    assert territory_id(code) == expected


def test_an_unexpected_national_code_is_refused() -> None:
    with pytest.raises(InvalidBoundariesFileError, match="unexpected national code"):
        territory_id("2801")


def test_a_file_without_communities_is_refused() -> None:
    empty = (
        b'<?xml version="1.0"?><wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"/>'
    )

    with pytest.raises(InvalidBoundariesFileError, match="no autonomous community"):
        read_communities(io.BytesIO(empty))
