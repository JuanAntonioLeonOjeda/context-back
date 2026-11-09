"""PostgreSQL reader of voter profiles (migration 0015)."""

from collections import defaultdict

from sqlalchemy import Connection, text

from datos.voters.application.community_voters import (
    CandidatureCount,
    ElectionInfo,
    IncomeDownloadInfo,
    MunicipalRow,
)

_ELECTIONS = text("SELECT id, held_on, source_file FROM elections ORDER BY held_on DESC, id")
# One row per municipality and national head. A municipality reaches its community through its
# province (`province_id` is generated from the INE code). Its income is the latest download of the
# year: a revision of the INE is a newer row.
_ROWS = text(
    """
    SELECT r.municipality_code, r.census, r.blank_votes, i.euros_per_person AS income,
           h.code AS head_code, h.acronym AS head_acronym, sum(v.votes) AS votes
    FROM municipal_results r
    JOIN territories p ON p.id = r.province_id
    JOIN municipal_candidature_votes v
      ON v.election_id = r.election_id AND v.municipality_code = r.municipality_code
    JOIN election_candidatures c
      ON c.election_id = v.election_id AND c.code = v.candidature_code
    JOIN election_candidatures h
      ON h.election_id = c.election_id AND h.code = c.national_head_code
    LEFT JOIN LATERAL (
        SELECT euros_per_person FROM municipal_income mi
        WHERE mi.municipality_code = r.municipality_code AND mi.year = :year
        ORDER BY mi.download_id DESC LIMIT 1
    ) i ON true
    WHERE r.election_id = :election_id AND p.parent_id = :territory_id
    GROUP BY r.municipality_code, r.census, r.blank_votes, i.euros_per_person, h.code, h.acronym
    ORDER BY r.municipality_code, h.code
    """
)
_INCOME_DOWNLOAD = text(
    """
    SELECT d.url, d.fetched_at FROM downloads d
    WHERE d.id = (SELECT max(download_id) FROM municipal_income WHERE year = :year)
    """
)


class PgVotersReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def elections(self) -> list[ElectionInfo]:
        rows = self._connection.execute(_ELECTIONS)
        return [ElectionInfo(r.id, r.held_on, r.source_file) for r in rows]

    def municipal_rows(
        self, territory_id: str, election_id: str, income_year: int
    ) -> list[MunicipalRow]:
        rows = self._connection.execute(
            _ROWS, {"territory_id": territory_id, "election_id": election_id, "year": income_year}
        ).all()
        counts: dict[str, list[CandidatureCount]] = defaultdict(list)
        first: dict[str, MunicipalRow] = {}
        for r in rows:
            counts[r.municipality_code].append(
                CandidatureCount(r.head_code, r.head_acronym, int(r.votes))
            )
            first.setdefault(
                r.municipality_code,
                MunicipalRow(r.municipality_code, r.census, r.blank_votes, r.income, ()),
            )
        return [
            MunicipalRow(m.code, m.census, m.blank_votes, m.income, tuple(counts[code]))
            for code, m in first.items()
        ]

    def income_download(self, year: int) -> IncomeDownloadInfo | None:
        row = self._connection.execute(_INCOME_DOWNLOAD, {"year": year}).one_or_none()
        return None if row is None else IncomeDownloadInfo(year, row.url, row.fetched_at)
