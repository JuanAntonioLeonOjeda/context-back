"""PostgreSQL storage of indicator definitions, downloads and observations."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import Engine, text

from datos.indicators.domain.indicator import IndicatorDefinition, Observation

_UPSERT_INDICATOR = text(
    """
    INSERT INTO indicators (id, name, unit, scale_factor, periodicity, source_table_id,
                            description)
    VALUES (:id, :name, :unit, :scale_factor, :periodicity, :source_table_id, :description)
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name, unit = EXCLUDED.unit, scale_factor = EXCLUDED.scale_factor,
        periodicity = EXCLUDED.periodicity, source_table_id = EXCLUDED.source_table_id,
        description = EXCLUDED.description
    """
)
# Served by observations_latest_idx; same rule as the current_observations view.
_LATEST = text(
    """
    SELECT period_start, value FROM current_observations
    WHERE indicator_id = :indicator_id AND territory_id = :territory_id
    """
)
_INSERT_DOWNLOAD = text(
    "INSERT INTO downloads (source, url, sha256) VALUES ('ine', :url, :sha256) RETURNING id"
)
_INSERT_OBSERVATION = text(
    """
    INSERT INTO observations (indicator_id, territory_id, period_year, period_code,
                              period_start, value, source_series_code, download_id)
    VALUES (:indicator_id, :territory_id, :period_year, :period_code, :period_start, :value,
            :source_series_code, :download_id)
    """
)


class PgIndicatorRepository:
    """Each `record` is its own transaction: a download is stored with all its rows or none."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert_indicators(self, definitions: Sequence[IndicatorDefinition]) -> None:
        with self._engine.begin() as connection:
            for d in definitions:
                connection.execute(
                    _UPSERT_INDICATOR,
                    {
                        "id": d.id,
                        "name": d.name,
                        "unit": d.unit,
                        "scale_factor": d.scale_factor,
                        "periodicity": d.periodicity.value,
                        "source_table_id": d.source_table_id,
                        "description": d.description,
                    },
                )

    def latest_values(self, indicator_id: str, territory_id: str) -> dict[date, Decimal]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                _LATEST, {"indicator_id": indicator_id, "territory_id": territory_id}
            )
            return {row.period_start: row.value for row in rows}

    def record(self, *, url: str, sha256: str, observations: Sequence[Observation]) -> None:
        with self._engine.begin() as connection:
            download_id = connection.execute(
                _INSERT_DOWNLOAD, {"url": url, "sha256": sha256}
            ).scalar_one()
            for o in observations:
                connection.execute(
                    _INSERT_OBSERVATION,
                    {
                        "indicator_id": o.indicator_id,
                        "territory_id": o.territory_id,
                        "period_year": o.period_year,
                        "period_code": o.period_code,
                        "period_start": o.period_start,
                        "value": o.value,
                        "source_series_code": o.source_series_code,
                        "download_id": download_id,
                    },
                )
