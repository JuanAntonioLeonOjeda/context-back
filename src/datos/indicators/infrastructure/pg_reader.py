"""PostgreSQL reader of indicators and current observations (the read side of the API)."""

from sqlalchemy import Connection, text

from datos.indicators.application.read_indicators import IndicatorInfo, StoredValue

_INDICATORS = text(
    "SELECT id, name, unit, scale_factor, periodicity, source_table_id FROM indicators ORDER BY id"
)
_CURRENT = text(
    """
    SELECT c.indicator_id, c.period_year, c.period_code, c.value, c.source_series_code,
           d.fetched_at
    FROM current_observations c
    JOIN downloads d ON d.id = c.download_id
    WHERE c.territory_id = :territory_id
    """
)


class PgIndicatorReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def indicators(self) -> list[IndicatorInfo]:
        return [
            IndicatorInfo(
                row.id, row.name, row.unit, row.scale_factor, row.periodicity, row.source_table_id
            )
            for row in self._connection.execute(_INDICATORS)
        ]

    def current_values(self, territory_id: str) -> list[StoredValue]:
        rows = self._connection.execute(_CURRENT, {"territory_id": territory_id})
        return [
            StoredValue(
                row.indicator_id,
                row.period_year,
                row.period_code,
                row.value,
                row.source_series_code,
                row.fetched_at,
            )
            for row in rows
        ]
