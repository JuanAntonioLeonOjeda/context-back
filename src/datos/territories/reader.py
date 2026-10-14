"""PostgreSQL reader of territories (the read side of the API)."""

from sqlalchemy import Connection, text

from datos.territories.territory import Level, Territory

# Ordered by INE code: a stable order that does not depend on size or politics.
_BY_LEVEL = text(
    "SELECT id, ine_code, name, level, parent_id FROM territories"
    " WHERE level = :level ORDER BY ine_code"
)


class PgTerritoryReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def by_level(self, level: Level) -> list[Territory]:
        rows = self._connection.execute(_BY_LEVEL, {"level": level.value})
        return [
            Territory(row.id, row.ine_code, row.name, Level(row.level), row.parent_id)
            for row in rows
        ]
