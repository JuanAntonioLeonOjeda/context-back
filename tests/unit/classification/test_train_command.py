"""The pieces of the train command that are plain functions."""

import pytest

from datos.classification.report import duration


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0, "0s"),
        (18.04, "18s"),
        (59.6, "1m 00s"),
        (220, "3m 40s"),
        (8_640, "2h 24m 00s"),
        (8_645.4, "2h 24m 05s"),
    ],
)
def test_a_duration_is_written_as_a_person_reads_it(seconds: float, text: str) -> None:
    assert duration(seconds) == text
