"""PostgreSQL storage of municipal values by dimension (migration 0017), append-only."""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Engine, text

from datos.voters.application.load_values import ValueLoad

_PROVINCES = text("SELECT id FROM territories WHERE level = 'province'")
# The latest load wins: a revision of the INE is a newer row (higher load id).
_LATEST = text(
    "SELECT DISTINCT ON (v.municipality_code) v.municipality_code, v.value"
    " FROM municipal_values v JOIN municipal_value_loads l ON l.id = v.load_id"
    " WHERE l.dimension = :dimension AND v.year = :year"
    " ORDER BY v.municipality_code, v.load_id DESC"
)
_INSERT_LOAD = text(
    "INSERT INTO municipal_value_loads (dimension, source_url, source_file, source_sha256)"
    " VALUES (:dimension, :url, :file, :sha256) RETURNING id"
)
_INSERT_VALUE = text(
    "INSERT INTO municipal_values (load_id, municipality_code, year, value)"
    " VALUES (:load_id, :code, :year, :value)"
)


class PgValueRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def province_ids(self) -> set[str]:
        with self._engine.connect() as connection:
            return set(connection.execute(_PROVINCES).scalars())

    def latest_values(self, dimension: str, year: int) -> dict[str, Decimal]:
        with self._engine.connect() as connection:
            rows = connection.execute(_LATEST, {"dimension": dimension, "year": year})
            return {row.municipality_code: row.value for row in rows}

    def record(self, dimension: str, loads: Sequence[ValueLoad]) -> None:
        # One transaction for all the loads: if one is refused (a file loaded before), none stays.
        with self._engine.begin() as connection:
            for load in loads:
                load_id = connection.execute(
                    _INSERT_LOAD,
                    {
                        "dimension": dimension,
                        "url": load.source_url,
                        "file": load.source_file,
                        "sha256": load.sha256,
                    },
                ).scalar_one()
                connection.execute(
                    _INSERT_VALUE,
                    [
                        {
                            "load_id": load_id,
                            "code": v.municipality_code,
                            "year": v.year,
                            "value": v.value,
                        }
                        for v in load.values
                    ],
                )
