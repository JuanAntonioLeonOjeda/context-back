"""What the curve command prints: one line per point, a table per family and the D12 decision."""

from dataclasses import dataclass

from datos.classification.domain.metrics import FamilyScore, LabelScore
from datos.classification.report import format_point, format_summary


@dataclass(frozen=True)
class Point:
    fold: int
    size: int
    scores: tuple[FamilyScore, ...]


def point(fold: int, size: int, sector: float, level: float | None = 0.5) -> Point:
    return Point(
        fold,
        size,
        (
            FamilyScore("sector", sector, (LabelScore("sector:health", 3, 3, sector),)),
            FamilyScore("level", level, (LabelScore("level:local", 0, 0, None),)),
        ),
    )


def test_a_point_line_says_fold_size_time_and_each_family_with_its_labels() -> None:
    line = format_point(point(1, 200, 0.6123), training_seconds=4_325)

    assert line == (
        "fold 1 · 200 examples · trained in 1h 12m 05s · "
        "sector 0.612 (health 0.612) | level 0.500 (local -)"
    )


def test_the_summary_has_a_table_per_family_with_each_folds_score() -> None:
    text = format_summary([point(0, 200, 0.6), point(1, 200, 0.7)])

    assert "sector\n  examples   mean   per fold\n       200  0.650   0.600, 0.700" in text


def test_the_summary_applies_the_rule_of_d12_and_decides() -> None:
    rising = format_summary([point(0, 200, 0.60), point(0, 300, 0.64)])
    flat = format_summary([point(0, 200, 0.60, 0.5), point(0, 300, 0.61, 0.5)])

    assert "sector: +4.0 points over 1 fold(s): rises? yes" in rising
    assert "Decision: label 100 more" in rising
    assert "Decision: no more labels needed by this rule" in flat


def test_the_summary_says_when_it_cannot_tell_yet() -> None:
    text = format_summary([point(0, 100, 0.5), point(0, 200, 0.6)])

    assert "cannot be told, no fold has both sizes" in text
    assert "Decision: cannot be told yet" in text
