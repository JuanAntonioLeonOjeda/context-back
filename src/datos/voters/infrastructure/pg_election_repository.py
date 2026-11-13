"""PostgreSQL storage of an election's results (migration 0015)."""

from sqlalchemy import Connection, text

from datos.voters.domain.election import ElectionFile

_PROVINCES = text("SELECT id FROM territories WHERE level = 'province'")
_STORED_SHA = text("SELECT source_sha256 FROM elections WHERE id = :id")
_INSERT_ELECTION = text(
    "INSERT INTO elections (id, kind, held_on, source_file, source_sha256)"
    " VALUES (:id, :kind, :held_on, :source_file, :sha256)"
)
_INSERT_CANDIDATURE = text(
    "INSERT INTO election_candidatures (election_id, code, acronym, name, national_head_code)"
    " VALUES (:election_id, :code, :acronym, :name, :head)"
)
_INSERT_RESULT = text(
    "INSERT INTO municipal_results (election_id, municipality_code, municipality_name, census,"
    " blank_votes, null_votes, candidature_votes)"
    " VALUES (:election_id, :code, :name, :census, :blank, :null, :candidature_votes)"
)
_INSERT_VOTES = text(
    "INSERT INTO municipal_candidature_votes"
    " (election_id, municipality_code, candidature_code, votes)"
    " VALUES (:election_id, :municipality, :candidature, :votes)"
)


class PgElectionRepository:
    """Writes inside the caller's transaction: a failed load leaves nothing behind."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def province_ids(self) -> set[str]:
        return set(self._connection.execute(_PROVINCES).scalars())

    def stored_sha256(self, election_id: str) -> str | None:
        stored: str | None = self._connection.execute(
            _STORED_SHA, {"id": election_id}
        ).scalar_one_or_none()
        return stored

    def add(self, file: ElectionFile) -> None:
        election_id = file.election.id
        self._connection.execute(
            _INSERT_ELECTION,
            {
                "id": election_id,
                "kind": file.election.kind.value,
                "held_on": file.election.held_on,
                "source_file": file.source_file,
                "sha256": file.sha256,
            },
        )
        # A list of parameter sets is sent as one executemany: about 90,000 vote rows for a
        # general election, in seconds and without building SQL by hand.
        self._connection.execute(
            _INSERT_CANDIDATURE,
            [
                {
                    "election_id": election_id,
                    "code": c.code,
                    "acronym": c.acronym,
                    "name": c.name,
                    "head": c.national_head_code,
                }
                for c in file.candidatures
            ],
        )
        self._connection.execute(
            _INSERT_RESULT,
            [
                {
                    "election_id": election_id,
                    "code": r.municipality_code,
                    "name": r.municipality_name,
                    "census": r.census,
                    "blank": r.blank_votes,
                    "null": r.null_votes,
                    "candidature_votes": r.candidature_votes,
                }
                for r in file.results
            ],
        )
        self._connection.execute(
            _INSERT_VOTES,
            [
                {
                    "election_id": election_id,
                    "municipality": v.municipality_code,
                    "candidature": v.candidature_code,
                    "votes": v.votes,
                }
                for v in file.votes
            ],
        )
