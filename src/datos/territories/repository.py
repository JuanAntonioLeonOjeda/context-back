"""PostgreSQL storage of territories."""

from sqlalchemy import Connection, text

from datos.territories.territory import Territory, parents_first

# Upsert: loading twice is a no-op, and a corrected name in the CSV updates the row.
_UPSERT = text(
    """
    INSERT INTO territories (id, ine_code, name, level, parent_id)
    VALUES (:id, :ine_code, :name, :level, :parent_id)
    ON CONFLICT (id) DO UPDATE
    SET ine_code = EXCLUDED.ine_code,
        name = EXCLUDED.name,
        level = EXCLUDED.level,
        parent_id = EXCLUDED.parent_id
    """
)


class PgTerritoryRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert_all(self, territories: list[Territory]) -> None:
        for territory in parents_first(territories):
            self._connection.execute(
                _UPSERT,
                {
                    "id": territory.id,
                    "ine_code": territory.ine_code,
                    "name": territory.name,
                    "level": territory.level.value,
                    "parent_id": territory.parent_id,
                },
            )
