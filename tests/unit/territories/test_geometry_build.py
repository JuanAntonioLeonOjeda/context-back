"""Rules of the geometry build, on hand-made squares (the real file is tested below)."""

import json
from pathlib import Path

from shapely.geometry import MultiPolygon, shape

from datos.territories.geometry_build import BuildSettings, build_feature_collection
from datos.territories.gml_source import CommunityShape, Polygon

NO_SIMPLIFY = BuildSettings(tolerance_deg=0.0, min_part_area_deg2=0.5, grid_deg=0.001)


def _square(x: float, y: float, size: float) -> list[tuple[float, float]]:
    return [(x, y), (x + size, y), (x + size, y + size), (x, y + size), (x, y)]


def _geometry(collection: dict[str, object], territory_id: str) -> MultiPolygon:
    features = collection["features"]
    assert isinstance(features, list)
    feature = next(f for f in features if f["id"] == territory_id)
    geometry = shape(feature["geometry"])
    assert isinstance(geometry, MultiPolygon)
    return geometry


def test_an_islet_is_dropped_but_never_the_largest_part() -> None:
    mainland: Polygon = [_square(0, 0, 2)]
    islet: Polygon = [_square(5, 5, 0.1)]  # 0.01 < 0.5, touches nobody
    tiny_city: Polygon = [_square(10, 10, 0.1)]  # smaller than the minimum, but its only part
    shapes = [
        CommunityShape("ccaa-01", "A", [mainland, islet]),
        CommunityShape("ccaa-18", "Ceuta-like", [tiny_city]),
    ]

    collection = build_feature_collection(shapes, attribution="test", settings=NO_SIMPLIFY)

    assert len(_geometry(collection, "ccaa-01").geoms) == 1
    assert len(_geometry(collection, "ccaa-18").geoms) == 1


def test_a_small_enclave_inside_a_neighbour_is_kept_and_its_hole_too() -> None:
    # B is a big square with a hole; A owns a small enclave exactly in that hole.
    hole = _square(1, 1, 0.1)
    b: Polygon = [_square(0, 0, 3), list(reversed(hole))]
    a_main: Polygon = [_square(3, 0, 3)]
    a_enclave: Polygon = [hole]
    shapes = [
        CommunityShape("ccaa-08", "A", [a_main, a_enclave]),
        CommunityShape("ccaa-13", "B", [b]),
    ]

    collection = build_feature_collection(shapes, attribution="test", settings=NO_SIMPLIFY)

    assert len(_geometry(collection, "ccaa-08").geoms) == 2
    assert len(_geometry(collection, "ccaa-13").geoms[0].interiors) == 1


def test_a_hole_that_no_community_occupies_is_filled() -> None:
    lake = _square(1, 1, 0.2)
    shapes = [CommunityShape("ccaa-01", "A", [[_square(0, 0, 3), list(reversed(lake))]])]

    collection = build_feature_collection(shapes, attribution="test", settings=NO_SIMPLIFY)

    assert len(_geometry(collection, "ccaa-01").geoms[0].interiors) == 0


def test_features_carry_the_territory_id_and_the_collection_the_attribution() -> None:
    shapes = [CommunityShape("ccaa-02", "B", [[_square(0, 0, 1)]])]

    collection = build_feature_collection(
        shapes, attribution="CC-BY 4.0 ign.es", settings=NO_SIMPLIFY
    )

    assert collection["attribution"] == "CC-BY 4.0 ign.es"
    assert json.loads(json.dumps(collection))["features"][0]["id"] == "ccaa-02"


# --- the versioned file the API serves ---------------------------------------------

GEOJSON = Path("data/geo/ccaa.geojson")
MAX_BYTES = 300_000


def test_the_versioned_geometry_has_the_19_communities_valid_and_light() -> None:
    collection = json.loads(GEOJSON.read_text(encoding="utf-8"))
    territory_ids = {
        line.split(",")[0]
        for line in Path("data/territories/territories.csv")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("ccaa-")
    }

    geometries = {f["id"]: shape(f["geometry"]) for f in collection["features"]}

    assert set(geometries) == territory_ids
    assert all(g.is_valid and not g.is_empty for g in geometries.values())
    assert "CC-BY 4.0 ign.es" in collection["attribution"]
    assert GEOJSON.stat().st_size < MAX_BYTES
