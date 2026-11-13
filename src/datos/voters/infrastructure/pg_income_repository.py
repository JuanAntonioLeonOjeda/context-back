"""PostgreSQL storage of municipal income (migration 0015), append-only like the observations."""

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Engine, text

from datos.voters.application.load_income import IncomeDownload
from datos.voters.domain.income import MunicipalIncome

_PROVINCES = text("SELECT id FROM territories WHERE level = 'province'")
# The latest download wins: a revision of the INE is a newer row.
_LATEST = text(
    "SELECT DISTINCT ON (municipality_code) municipality_code, euros_per_person"
    " FROM municipal_income WHERE year = :year"
    " ORDER BY municipality_code, download_id DESC"
)
_INSERT_DOWNLOAD = text(
    "INSERT INTO downloads (source, url, sha256) VALUES ('ine', :url, :sha256) RETURNING id"
)
_INSERT_INCOME = text(
    "INSERT INTO municipal_income (municipality_code, year, euros_per_person, series_code,"
    " download_id)"
    " VALUES (:code, :year, :euros, :series, :download_id)"
)


class PgIncomeRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def province_ids(self) -> set[str]:
        with self._engine.connect() as connection:
            return set(connection.execute(_PROVINCES).scalars())

    def latest_incomes(self, year: int) -> dict[str, Decimal]:
        with self._engine.connect() as connection:
            rows = connection.execute(_LATEST, {"year": year})
            return {row.municipality_code: row.euros_per_person for row in rows}

    def record(self, download: IncomeDownload, incomes: Sequence[MunicipalIncome]) -> None:
        with self._engine.begin() as connection:
            download_id = connection.execute(
                _INSERT_DOWNLOAD, {"url": download.url, "sha256": download.sha256}
            ).scalar_one()
            connection.execute(
                _INSERT_INCOME,
                [
                    {
                        "code": i.municipality_code,
                        "year": i.year,
                        "euros": i.euros_per_person,
                        "series": i.series_code,
                        "download_id": download_id,
                    }
                    for i in incomes
                ],
            )
