"""PostgreSQL storage of bodies, holders and competences (migration 0016)."""

from collections.abc import Sequence

from sqlalchemy import Connection, text

from datos.organization.domain.body import Body, BodyKind, Holder
from datos.organization.domain.boxes import Competence

_TERRITORIES = text("SELECT id FROM territories")
_SECTORS = text("SELECT id FROM sectors")
_INSERT_BODY = text(
    "INSERT INTO bodies (id, kind, level, territory_id, name, parent_id, dir3_id, source_url,"
    " valid_from, valid_to)"
    " VALUES (:id, :kind, :level, :territory_id, :name, :parent_id, :dir3_id, :source_url,"
    " :valid_from, :valid_to)"
)
_INSERT_HOLDER = text(
    "INSERT INTO body_holders (body_id, body_kind, post_title, holder_name, valid_from, valid_to,"
    " source_url)"
    " VALUES (:body_id, :body_kind, :post_title, :holder_name, :valid_from, :valid_to, :source_url)"
)
_INSERT_COMPETENCE = text(
    "INSERT INTO body_competences (body_id, summary, legal_basis, source_url)"
    " VALUES (:body_id, :summary, :legal_basis, :source_url) RETURNING id"
)
_INSERT_SECTOR = text(
    "INSERT INTO body_competence_sectors (competence_id, sector_id)"
    " VALUES (:competence_id, :sector_id)"
)


class PgOrganizationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def territory_ids(self) -> set[str]:
        return set(self._connection.execute(_TERRITORIES).scalars())

    def sector_ids(self) -> set[str]:
        return set(self._connection.execute(_SECTORS).scalars())

    def replace_all(
        self,
        bodies: Sequence[Body],
        holders: Sequence[Holder],
        competences: Sequence[Competence],
    ) -> None:
        """Make the stored rows mirror the dataset (callers run this in one transaction).

        Ids of competences are internal and change on every load. The dataset is checked first
        (`dataset_problems`): every holder and competence has its body, and a parent is the
        executive head of the same territory, so it has none itself.
        """
        self._connection.execute(text("DELETE FROM body_competences"))  # cascades to its sectors
        self._connection.execute(text("DELETE FROM body_holders"))
        self._connection.execute(text("DELETE FROM bodies"))
        # A parent goes in before its children (the foreign key is not deferred).
        for body in sorted(bodies, key=lambda b: b.parent_id is not None):
            self._connection.execute(_INSERT_BODY, _body_values(body))
        kinds = {body.id: body.kind for body in bodies}
        for holder in holders:
            self._connection.execute(_INSERT_HOLDER, _holder_values(holder, kinds[holder.body_id]))
        for competence in competences:
            competence_id = self._connection.execute(
                _INSERT_COMPETENCE,
                {
                    "body_id": competence.body_id,
                    "summary": competence.summary,
                    "legal_basis": competence.legal_basis,
                    "source_url": competence.source_url,
                },
            ).scalar_one()
            for sector_id in competence.sector_ids:
                self._connection.execute(
                    _INSERT_SECTOR, {"competence_id": competence_id, "sector_id": sector_id}
                )


def _body_values(body: Body) -> dict[str, object]:
    return {
        "id": body.id,
        "kind": body.kind.value,
        "level": body.level.value,
        "territory_id": body.territory_id,
        "name": body.name,
        "parent_id": body.parent_id,
        "dir3_id": body.dir3_id,
        "source_url": body.source_url,
        "valid_from": body.valid_from,
        "valid_to": body.valid_to,
    }


def _holder_values(holder: Holder, kind: BodyKind) -> dict[str, object]:
    return {
        "body_id": holder.body_id,
        "body_kind": kind.value,
        "post_title": holder.post_title,
        "holder_name": holder.holder_name,
        "valid_from": holder.valid_from,
        "valid_to": holder.valid_to,
        "source_url": holder.source_url,
    }
