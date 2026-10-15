"""PostgreSQL storage of parties and government terms."""

from collections.abc import Sequence

from sqlalchemy import Connection, text

from datos.governments.domain.competence import Competence, Sector
from datos.governments.domain.government_term import GovernmentTerm
from datos.governments.domain.party import Party

_UPSERT_PARTY = text(
    """
    INSERT INTO parties (id, name, short_name, colour_hex)
    VALUES (:id, :name, :short_name, :colour_hex)
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name, short_name = EXCLUDED.short_name, colour_hex = EXCLUDED.colour_hex
    """
)
_INSERT_TERM = text(
    """
    INSERT INTO government_terms
        (territory_id, president_name, is_caretaker, valid_from, valid_to, source_url)
    VALUES (:territory_id, :president_name, :is_caretaker, :valid_from, :valid_to, :source_url)
    RETURNING id
    """
)
_INSERT_TERM_PARTY = text(
    """
    INSERT INTO government_term_parties (term_id, party_id, role, source_url)
    VALUES (:term_id, :party_id, :role, :source_url)
    """
)

_UPSERT_SECTOR = text(
    "INSERT INTO sectors (id, name, is_active) VALUES (:id, :name, :is_active)"
    " ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, is_active = EXCLUDED.is_active"
)
_INSERT_COMPETENCE = text(
    """
    INSERT INTO competences (sector_id, activity, description, level, function, territory_id,
                             legal_basis, source_url)
    VALUES (:sector_id, :activity, :description, :level, :function, :territory_id,
            :legal_basis, :source_url)
    """
)


class PgGovernmentRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def government_territory_ids(self) -> set[str]:
        rows = self._connection.execute(
            text("SELECT id FROM territories WHERE level IN ('state', 'ccaa')")
        )
        return {row[0] for row in rows}

    def replace_all(self, parties: Sequence[Party], terms: Sequence[GovernmentTerm]) -> None:
        """Make the stored terms mirror the dataset (callers run this in one transaction).

        Term ids are internal and change on every load: other tables must refer to a
        government by (territory, date), never by term id. Parties are upserted and
        never deleted, so removing one from the CSV leaves it stored but unused.
        """
        for party in parties:
            self._connection.execute(
                _UPSERT_PARTY,
                {
                    "id": party.id,
                    "name": party.name,
                    "short_name": party.short_name,
                    "colour_hex": party.colour_hex,
                },
            )
        self._connection.execute(text("DELETE FROM government_terms"))  # cascades to parties
        for term in terms:
            term_id = self._connection.execute(
                _INSERT_TERM,
                {
                    "territory_id": term.territory_id,
                    "president_name": term.president_name,
                    "is_caretaker": term.is_caretaker,
                    "valid_from": term.valid_from,
                    "valid_to": term.valid_to,
                    "source_url": term.source_url,
                },
            ).scalar_one()
            for term_party in term.parties:
                self._connection.execute(
                    _INSERT_TERM_PARTY,
                    {
                        "term_id": term_id,
                        "party_id": term_party.party_id,
                        "role": term_party.role.value,
                        "source_url": term_party.source_url,
                    },
                )

    def replace_competences(
        self, sectors: Sequence[Sector], competences: Sequence[Competence]
    ) -> None:
        """Make the stored competences mirror the dataset; sectors are upserted, never deleted."""
        for sector in sectors:
            self._connection.execute(
                _UPSERT_SECTOR,
                {"id": sector.id, "name": sector.name, "is_active": sector.is_active},
            )
        self._connection.execute(text("DELETE FROM competences"))
        for c in competences:
            self._connection.execute(
                _INSERT_COMPETENCE,
                {
                    "sector_id": c.sector_id,
                    "activity": c.activity,
                    "description": c.description,
                    "level": c.level.value,
                    "function": c.function.value,
                    "territory_id": c.territory_id,
                    "legal_basis": c.legal_basis,
                    "source_url": c.source_url,
                },
            )
