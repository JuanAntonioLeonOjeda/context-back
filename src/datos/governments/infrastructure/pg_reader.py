"""PostgreSQL reader of parties and government terms (the read side of the API)."""

from sqlalchemy import Connection, Row, text

from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party

# One row per (term, party); a term always has at least one governing party (domain rule),
# so the inner join never drops a term.
_TERMS = text(
    """
    SELECT t.id, t.territory_id, t.president_name, t.valid_from, t.valid_to,
           t.is_caretaker, t.source_url,
           p.party_id, p.role, p.source_url AS party_source_url
    FROM government_terms t
    JOIN government_term_parties p ON p.term_id = t.id
    WHERE CAST(:territory_id AS text) IS NULL OR t.territory_id = :territory_id
    ORDER BY t.territory_id, t.valid_from, p.party_id
    """
)
_PARTIES = text("SELECT id, name, short_name, colour_hex FROM parties ORDER BY id")


class PgGovernmentsReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def terms(self, territory_id: str | None = None) -> list[GovernmentTerm]:
        rows = self._connection.execute(_TERMS, {"territory_id": territory_id}).all()
        by_term: dict[int, list[Row[tuple[object, ...]]]] = {}
        for row in rows:
            by_term.setdefault(row.id, []).append(row)
        return [_term(term_rows) for term_rows in by_term.values()]

    def parties(self) -> list[Party]:
        rows = self._connection.execute(_PARTIES)
        return [Party(row.id, row.name, row.short_name, row.colour_hex) for row in rows]


def _term(rows: list[Row[tuple[object, ...]]]) -> GovernmentTerm:
    first = rows[0]
    return GovernmentTerm(
        territory_id=first.territory_id,
        president_name=first.president_name,
        valid_from=first.valid_from,
        valid_to=first.valid_to,
        parties=tuple(
            TermParty(row.party_id, PartyRole(row.role), row.party_source_url) for row in rows
        ),
        is_caretaker=first.is_caretaker,
        source_url=first.source_url,
    )
