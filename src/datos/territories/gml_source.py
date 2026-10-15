"""Reads the IGN autonomous communities (INSPIRE `AdministrativeUnit`, 2nd order) from GML.

Source: IGN, Base de Datos de Límites Jurisdiccionales de España, ATOM download
`lineas_limite_gml.zip`, member `au_AdministrativeUnit_2ndOrder0.gml` (CC BY 4.0).
"""

# The standard library parser is safe here: Expat >= 2.4.1 rejects entity-expansion
# attacks and ElementTree never resolves external entities.
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterator
from dataclasses import dataclass
from typing import IO

_GML = "{http://www.opengis.net/gml/3.2}"
_AU = "{http://inspire.ec.europa.eu/schemas/au/4.0}"
_GN = "{http://inspire.ec.europa.eu/schemas/gn/4.0}"
# EPSG:4258 is ETRS89 geographic, with axes in latitude, longitude order.
_ETRS89 = "http://www.opengis.net/def/crs/EPSG/0/4258"

type Ring = list[tuple[float, float]]  # (longitude, latitude), as GeoJSON wants them
type Polygon = list[Ring]  # exterior ring first, then holes


class InvalidBoundariesFileError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class CommunityShape:
    territory_id: str  # ccaa-NN
    name: str  # as the IGN writes it
    polygons: list[Polygon]


def read_communities(gml: IO[bytes]) -> list[CommunityShape]:
    """The communities in the file, skipping units that belong to none (code 20)."""
    shapes = [shape for shape in _units(gml) if shape is not None]
    if not shapes:
        raise InvalidBoundariesFileError("no autonomous community found")
    return shapes


def territory_id(national_code: str) -> str | None:
    """`34NN0000000` → `ccaa-NN`; None for 20 (territories outside any community)."""
    if len(national_code) != 11 or not national_code.startswith("34"):
        raise InvalidBoundariesFileError(f"unexpected national code {national_code}")
    number = national_code[2:4]
    return None if number == "20" else f"ccaa-{number}"


def _units(gml: IO[bytes]) -> Iterator[CommunityShape | None]:
    # iterparse keeps memory flat: each unit is cleared once read.
    for _, element in ElementTree.iterparse(gml, events=("end",)):  # noqa: S314 - safe, see above
        if element.tag != f"{_AU}AdministrativeUnit":
            continue
        yield _unit(element)
        element.clear()


def _unit(element: ElementTree.Element) -> CommunityShape | None:
    code = element.findtext(f"{_AU}nationalCode")
    if code is None:
        raise InvalidBoundariesFileError("administrative unit without nationalCode")
    identifier = territory_id(code.strip())
    if identifier is None:
        return None
    name = element.findtext(f".//{_GN}text") or ""
    polygons = [_polygon(p) for p in element.iter(f"{_GML}Polygon")]
    return CommunityShape(identifier, name.strip(), polygons)


def _polygon(element: ElementTree.Element) -> Polygon:
    srs = element.get("srsName")
    if srs is not None and srs != _ETRS89:
        raise InvalidBoundariesFileError(f"unexpected reference system {srs}")
    exterior = element.find(f"{_GML}exterior/{_GML}LinearRing/{_GML}posList")
    if exterior is None or not exterior.text:
        raise InvalidBoundariesFileError("polygon without exterior ring")
    holes = element.findall(f"{_GML}interior/{_GML}LinearRing/{_GML}posList")
    return [_ring(exterior.text)] + [_ring(h.text or "") for h in holes]


def _ring(pos_list: str) -> Ring:
    values = [float(v) for v in pos_list.split()]
    if len(values) % 2:
        raise InvalidBoundariesFileError("odd number of coordinates in a ring")
    # GML gives latitude first (EPSG:4258 axis order); GeoJSON wants longitude first.
    return [(values[i + 1], values[i]) for i in range(0, len(values), 2)]
