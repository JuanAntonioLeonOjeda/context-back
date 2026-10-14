"""Builds the light community boundaries the web app draws (`data/geo/ccaa.geojson`).

Build-time only: needs the `geo` dependency group (shapely). The API serves the result,
it never runs this.

Steps, all with the 19 communities at once:
1. Simplify them as one **coverage**, so neighbours keep one shared border; simplifying
   each community alone would open gaps and overlaps between them.
2. Drop islets: parts smaller than a minimum area that touch no other community. Never a
   community's largest part (Ceuta and Melilla stay), never an enclave (the part of
   Castilla-La Mancha inside Madrid touches Madrid).
3. Snap coordinates to a grid, which keeps the file small and the geometries valid.
4. Fill holes that no other community occupies: snapping can open tiny artefacts, while
   a real hole holds an enclave (Treviño, of Castilla y León, inside the País Vasco).
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import shapely
from shapely.geometry import MultiPolygon, Polygon, mapping

from datos.territories.gml_source import CommunityShape

# Degrees. 0.005° is about 450 m in latitude: invisible at the scale of a map of Spain.
DEFAULT_TOLERANCE_DEG = 0.005
# About 1 km² at Spanish latitudes (1° x 1° ≈ 111 km x 85 km).
DEFAULT_MIN_PART_AREA_DEG2 = 0.0001
GRID_DEG = 0.001  # about 100 m


@dataclass(frozen=True, slots=True)
class BuildSettings:
    tolerance_deg: float = DEFAULT_TOLERANCE_DEG
    min_part_area_deg2: float = DEFAULT_MIN_PART_AREA_DEG2
    grid_deg: float = GRID_DEG


class InvalidGeometryError(Exception):
    pass


def build_feature_collection(
    shapes: Sequence[CommunityShape], *, attribution: str, settings: BuildSettings
) -> dict[str, object]:
    """GeoJSON FeatureCollection keyed by territory id, ordered by id."""
    ordered = sorted(shapes, key=lambda s: s.territory_id)
    simplified = list(
        shapely.coverage_simplify([_multipolygon(s) for s in ordered], settings.tolerance_deg)
    )
    without_islets = [
        _without_islets(g, _others(simplified, i), settings.min_part_area_deg2)
        for i, g in enumerate(simplified)
    ]
    snapped = [shapely.set_precision(g, settings.grid_deg) for g in without_islets]
    cleaned = [_without_empty_holes(g, _others(snapped, i)) for i, g in enumerate(snapped)]
    features = []
    for shape, geometry in zip(ordered, cleaned, strict=True):
        if geometry.is_empty or not geometry.is_valid:
            raise InvalidGeometryError(f"{shape.territory_id}: empty or invalid after building")
        features.append(
            {
                "type": "Feature",
                "id": shape.territory_id,
                "properties": {},
                "geometry": mapping(geometry),
            }
        )
    return {"type": "FeatureCollection", "attribution": attribution, "features": features}


def write_feature_collection(collection: dict[str, object], path: Path) -> int:
    """Write compact JSON; return the size in bytes."""
    text = json.dumps(collection, ensure_ascii=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    return path.stat().st_size


def _multipolygon(shape: CommunityShape) -> MultiPolygon:
    parts = [Polygon(rings[0], rings[1:]) for rings in shape.polygons]
    geometry = MultiPolygon(parts)
    if not geometry.is_valid:
        # The IGN file is valid; a repair here would hide a reading error, so fail instead.
        raise InvalidGeometryError(f"{shape.territory_id}: invalid source geometry")
    return geometry


def _others(geometries: Sequence[shapely.Geometry], index: int) -> shapely.Geometry:
    return shapely.union_all([g for i, g in enumerate(geometries) if i != index])


def _parts(geometry: shapely.Geometry) -> list[Polygon]:
    return list(getattr(geometry, "geoms", [geometry]))


def _without_islets(
    geometry: shapely.Geometry, others: shapely.Geometry, min_area: float
) -> MultiPolygon:
    parts = _parts(geometry)
    largest = max(parts, key=lambda p: p.area)
    return MultiPolygon(
        [p for p in parts if p is largest or p.area >= min_area or p.intersects(others)]
    )


def _without_empty_holes(geometry: shapely.Geometry, others: shapely.Geometry) -> MultiPolygon:
    filled = []
    for part in _parts(geometry):
        holes = [ring for ring in part.interiors if Polygon(ring).intersection(others).area > 0]
        filled.append(Polygon(part.exterior, holes))
    return MultiPolygon(filled)
