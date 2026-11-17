"""PostgreSQL reader of voter profiles (migrations 0015 and 0017)."""

from collections import defaultdict

from sqlalchemy import Connection, text

from datos.voters.application.community_voters import (
    CandidatureCount,
    ElectionInfo,
    MunicipalRow,
    SourceInfo,
)
from datos.voters.domain.dimensions import DimensionId

_ELECTIONS = text("SELECT id, held_on, source_file FROM elections ORDER BY held_on DESC, id")
# One row per municipality and candidature, as the file names it and not added up to its national
# head: whether a candidature counts as a party is decided by the curated table. A municipality
# reaches its community through its province (`province_id` is generated from the INE code). Its
# income and its education are the latest of the year: a revision of the INE is a newer row. A
# municipality where no candidature got a vote has no vote rows: it still comes, once and without
# a candidature, because its census and its blank votes count in its band.
_ROWS = text(
    """
    SELECT r.municipality_code, r.census, r.blank_votes, i.euros_per_person AS income,
           e.value AS loaded_value, c.code, c.acronym, v.votes
    FROM municipal_results r
    JOIN territories p ON p.id = r.province_id
    LEFT JOIN municipal_candidature_votes v
      ON v.election_id = r.election_id AND v.municipality_code = r.municipality_code
    LEFT JOIN election_candidatures c
      ON c.election_id = v.election_id AND c.code = v.candidature_code
    LEFT JOIN LATERAL (
        SELECT euros_per_person FROM municipal_income mi
        WHERE mi.municipality_code = r.municipality_code AND mi.year = :year
        ORDER BY mi.download_id DESC LIMIT 1
    ) i ON true
    LEFT JOIN LATERAL (
        SELECT mv.value FROM municipal_values mv
        JOIN municipal_value_loads l ON l.id = mv.load_id
        WHERE mv.municipality_code = r.municipality_code AND mv.year = :year
          AND l.dimension = :dimension
        ORDER BY mv.load_id DESC LIMIT 1
    ) e ON true
    WHERE r.election_id = :election_id AND p.parent_id = :territory_id
    ORDER BY r.municipality_code, c.code
    """
)
_INCOME_DOWNLOAD = text(
    """
    SELECT d.url, d.fetched_at FROM downloads d
    WHERE d.id = (SELECT max(download_id) FROM municipal_income WHERE year = :year)
    """
)
_VALUES_LOAD = text(
    """
    SELECT max(l.loaded_at) AS loaded_at
    FROM municipal_value_loads l
    WHERE l.dimension = :dimension
      AND EXISTS (SELECT 1 FROM municipal_values v WHERE v.load_id = l.id AND v.year = :year)
    """
)
# The INE's operation the table files (66620, 66621 and 66623) belong to: their pages link to it,
# and the API names one source. Each load keeps the URL of its own table.
CENSO_ANUAL_URL = (
    "https://www.ine.es/dyngs/INEbase/es/operacion.htm"
    "?c=Estadistica_C&cid=1254736176992&menu=resultados&idp=1254735572981"
)


class PgVotersReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def elections(self) -> list[ElectionInfo]:
        rows = self._connection.execute(_ELECTIONS)
        return [ElectionInfo(r.id, r.held_on, r.source_file) for r in rows]

    def municipal_rows(
        self, territory_id: str, election_id: str, income_year: int, dimension: DimensionId
    ) -> list[MunicipalRow]:
        # The dimension's id is the name its loads are stored under; for income and size no load
        # has that name, and the value comes out empty.
        rows = self._connection.execute(
            _ROWS,
            {
                "territory_id": territory_id,
                "election_id": election_id,
                "year": income_year,
                "dimension": dimension.value,
            },
        ).all()
        counts: dict[str, list[CandidatureCount]] = defaultdict(list)
        first: dict[str, MunicipalRow] = {}
        for r in rows:
            if r.code is not None:
                counts[r.municipality_code].append(
                    CandidatureCount(r.code, r.acronym, int(r.votes))
                )
            first.setdefault(
                r.municipality_code,
                MunicipalRow(
                    r.municipality_code, r.census, r.blank_votes, r.income, (), r.loaded_value
                ),
            )
        return [
            MunicipalRow(
                m.code, m.census, m.blank_votes, m.income, tuple(counts[code]), m.loaded_value
            )
            for code, m in first.items()
        ]

    def income_download(self, year: int) -> SourceInfo | None:
        row = self._connection.execute(_INCOME_DOWNLOAD, {"year": year}).one_or_none()
        return None if row is None else SourceInfo(year, row.url, row.fetched_at)

    def values_source(self, dimension: DimensionId, year: int) -> SourceInfo | None:
        loaded_at = self._connection.execute(
            _VALUES_LOAD, {"year": year, "dimension": dimension.value}
        ).scalar_one()
        return None if loaded_at is None else SourceInfo(year, CENSO_ANUAL_URL, loaded_at)
