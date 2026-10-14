"""Command line:
uv run python -m datos.territories load [--csv PATH]
uv run python -m datos.territories build-geometry [--source ZIP] [--out PATH]
"""

import argparse
import zipfile
from pathlib import Path

import structlog

from datos.config import LogLevel, load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging
from datos.territories.csv_source import read_territories
from datos.territories.repository import PgTerritoryRepository

DEFAULT_CSV = Path("data/territories/territories.csv")
# IGN ATOM download (see data/geo/README.md); kept out of git under data/raw/.
DEFAULT_SOURCE = Path("data/raw/ign/lineas_limite_gml.zip")
SOURCE_MEMBER = "au_AdministrativeUnit_2ndOrder0.gml"
DEFAULT_OUT = Path("data/geo/ccaa.geojson")
# Licence: CC BY 4.0, attribution required at the foot of the map (Orden FOM/2807/2015).
ATTRIBUTION = (
    "Obra derivada de Base de Datos de Límites Jurisdiccionales de España 2026 CC-BY 4.0 ign.es"
)

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.territories")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="load territories from the versioned CSV")
    load.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    build = commands.add_parser("build-geometry", help="build data/geo/ccaa.geojson (geo group)")
    build.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    build.add_argument("--out", type=Path, default=DEFAULT_OUT)
    arguments = parser.parse_args()

    if arguments.command == "build-geometry":
        _build_geometry(arguments.source, arguments.out)
    else:
        _load(arguments.csv)


def _load(csv: Path) -> None:
    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    territories = read_territories(csv)
    with build_engine(str(settings.database_url)).begin() as connection:
        PgTerritoryRepository(connection).upsert_all(territories)
    log.info("territories_loaded", count=len(territories), source=str(csv))


def _build_geometry(source: Path, out: Path) -> None:
    # Imported here: shapely is in the build-only `geo` group, and `load` must not need it.
    from datos.territories.geometry_build import (
        BuildSettings,
        build_feature_collection,
        write_feature_collection,
    )
    from datos.territories.gml_source import read_communities

    configure_logging(LogLevel.INFO, as_json=False)  # a build tool: no database settings
    with zipfile.ZipFile(source) as archive, archive.open(SOURCE_MEMBER) as gml:
        shapes = read_communities(gml)
    collection = build_feature_collection(shapes, attribution=ATTRIBUTION, settings=BuildSettings())
    size = write_feature_collection(collection, out)
    log.info("geometry_built", communities=len(shapes), out=str(out), bytes=size)


if __name__ == "__main__":
    main()
