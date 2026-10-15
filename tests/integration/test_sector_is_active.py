"""A sector is active unless it says otherwise (migration 0007)."""

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


def _is_active(db: Connection, sector_id: str) -> bool:
    return bool(
        db.execute(
            text("SELECT is_active FROM sectors WHERE id = :id"), {"id": sector_id}
        ).scalar_one()
    )


def test_a_sector_inserted_without_the_column_is_active(db: Connection) -> None:
    db.execute(text("INSERT INTO sectors (id, name) VALUES ('housing', 'Housing')"))

    assert _is_active(db, "housing")


def test_a_planned_sector_says_so(db: Connection) -> None:
    db.execute(text("INSERT INTO sectors (id, name, is_active) VALUES ('work', 'Work', false)"))

    assert not _is_active(db, "work")


def test_is_active_cannot_be_null(db: Connection) -> None:
    with pytest.raises(DBAPIError, match="is_active"):
        db.execute(text("INSERT INTO sectors (id, name, is_active) VALUES ('work', 'W', NULL)"))
