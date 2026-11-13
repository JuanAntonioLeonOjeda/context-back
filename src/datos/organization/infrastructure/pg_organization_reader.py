"""PostgreSQL reader of the organisation (migration 0016): every row, for the chart to assemble."""

from sqlalchemy import Connection, text

from datos.organization.domain.body import Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence

_BODIES = text(
    "SELECT id, kind, level, territory_id, name, parent_id, dir3_id, source_url"
    " FROM bodies ORDER BY id"
)
_HOLDERS = text(
    "SELECT body_id, post_title, holder_name, valid_from, valid_to, source_url"
    " FROM body_holders ORDER BY body_id, valid_from"
)
# The ids of competences grow in the order of the file they were loaded from, which is the order
# a body's competences are shown in; a competence with no sector (the loader refuses it) would
# still come, with none.
_COMPETENCES = text(
    """
    SELECT c.body_id, c.summary, c.legal_basis, c.source_url,
           coalesce(array_agg(s.sector_id ORDER BY s.sector_id)
                    FILTER (WHERE s.sector_id IS NOT NULL), '{}') AS sector_ids
    FROM body_competences c
    LEFT JOIN body_competence_sectors s ON s.competence_id = c.id
    GROUP BY c.id
    ORDER BY c.id
    """
)
_SECTORS = text("SELECT id, name FROM sectors")


class PgOrganizationReader:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def bodies(self) -> list[Body]:
        return [
            Body(
                id=r.id,
                kind=BodyKind(r.kind),
                level=BodyLevel(r.level),
                territory_id=r.territory_id,
                name=r.name,
                parent_id=r.parent_id,
                dir3_id=r.dir3_id,
                source_url=r.source_url,
            )
            for r in self._connection.execute(_BODIES)
        ]

    def holders(self) -> list[Holder]:
        return [
            Holder(
                body_id=r.body_id,
                post_title=r.post_title,
                holder_name=r.holder_name,
                valid_from=r.valid_from,
                valid_to=r.valid_to,
                source_url=r.source_url,
            )
            for r in self._connection.execute(_HOLDERS)
        ]

    def competences(self) -> list[Competence]:
        return [
            Competence(
                body_id=r.body_id,
                summary=r.summary,
                legal_basis=r.legal_basis,
                sector_ids=tuple(r.sector_ids),
                source_url=r.source_url,
            )
            for r in self._connection.execute(_COMPETENCES)
        ]

    def sector_names(self) -> dict[str, str]:
        return {r.id: r.name for r in self._connection.execute(_SECTORS)}
