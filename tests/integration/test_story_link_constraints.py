"""A story has one parent, inside the grouping run the tree run was made on (migration 0011)."""

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def _run(db: Connection) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO story_runs (encoder_version, threshold, window_days)"
                " VALUES ('v1', 0.88, 3) RETURNING id"
            )
        ).scalar_one()
    )


def _story(db: Connection, run_id: int) -> int:
    return int(
        db.execute(
            text("INSERT INTO stories (run_id) VALUES (:run) RETURNING id"), {"run": run_id}
        ).scalar_one()
    )


def _tree_run(db: Connection, story_run_id: int) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO story_tree_runs (story_run_id, threshold, window_days)"
                " VALUES (:run, 0.75, 14) RETURNING id"
            ),
            {"run": story_run_id},
        ).scalar_one()
    )


def _link(
    db: Connection, tree_run_id: int, story_run_id: int, story_id: int, parent_id: int
) -> None:
    db.execute(
        text(
            "INSERT INTO story_links"
            " (tree_run_id, story_run_id, story_id, parent_story_id, similarity)"
            " VALUES (:tree, :run, :story, :parent, 0.8)"
        ),
        {"tree": tree_run_id, "run": story_run_id, "story": story_id, "parent": parent_id},
    )


def test_a_story_has_at_most_one_parent_in_a_tree_run(db: Connection) -> None:
    run = _run(db)
    parent_a, parent_b, child = _story(db, run), _story(db, run), _story(db, run)
    tree = _tree_run(db, run)
    _link(db, tree, run, child, parent_a)

    with pytest.raises(IntegrityError):
        _link(db, tree, run, child, parent_b)


def test_the_same_story_can_have_another_parent_in_another_tree_run(db: Connection) -> None:
    run = _run(db)
    parent_a, parent_b, child = _story(db, run), _story(db, run), _story(db, run)
    _link(db, _tree_run(db, run), run, child, parent_a)

    _link(db, _tree_run(db, run), run, child, parent_b)


def test_a_story_cannot_be_its_own_parent(db: Connection) -> None:
    run = _run(db)
    story = _story(db, run)

    with pytest.raises(IntegrityError):
        _link(db, _tree_run(db, run), run, story, story)


def test_a_link_cannot_join_stories_of_another_grouping_run(db: Connection) -> None:
    run, other = _run(db), _run(db)
    child, foreign_parent = _story(db, run), _story(db, other)

    with pytest.raises(IntegrityError):
        _link(db, _tree_run(db, run), run, child, foreign_parent)


def test_a_tree_run_needs_a_threshold_in_range(db: Connection) -> None:
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO story_tree_runs (story_run_id, threshold, window_days)"
                " VALUES (:run, 1.5, 14)"
            ),
            {"run": _run(db)},
        )
