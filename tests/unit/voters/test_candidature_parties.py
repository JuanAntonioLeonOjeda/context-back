"""Reading the candidature → party table: a bad file stops the load with its line."""

from pathlib import Path

import pytest

from datos.voters.infrastructure.candidature_parties import (
    InvalidCandidaturePartiesError,
    read_candidature_parties,
)

HEADER = "election_id,national_head_code,acronym_in_file,party_id\n"


def _file(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "candidature-parties.csv"
    path.write_text(HEADER + "".join(f"{row}\n" for row in rows), encoding="utf-8")
    return path


def test_gives_the_party_of_each_national_head_by_election(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        "congreso-2023-07,000002,PSOE,psoe",
        "congreso-2023-07,000005,PP,pp",
        "congreso-2019-11,000002,PP,pp",  # the same code is another candidature in another election
    )

    assert read_candidature_parties(path) == {
        "congreso-2023-07": {"000002": "psoe", "000005": "pp"},
        "congreso-2019-11": {"000002": "pp"},
    }


def test_the_real_file_reads() -> None:
    table = read_candidature_parties(Path("data/voters/candidature-parties.csv"))

    assert table["congreso-2023-07"]["000002"] == "psoe"


def test_a_national_head_written_twice_stops_the_load_with_its_line(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        "congreso-2023-07,000002,PSOE,psoe",
        "congreso-2023-07,000005,PP,pp",
        "congreso-2023-07,000002,PSOE,pp",
    )

    with pytest.raises(InvalidCandidaturePartiesError, match=r"\.csv:4: national head 000002"):
        read_candidature_parties(path)


@pytest.mark.parametrize(
    "row",
    [
        "Congreso 2023,000002,PSOE,psoe",  # not an election id
        "congreso-2023-07,2,PSOE,psoe",  # the code lost its leading zeros
        "congreso-2023-07,000002,PSOE,",  # no party
        "congreso-2023-07,000002,,psoe",  # no acronym
        "congreso-2023-07,000002,PSOE",  # a missing cell
    ],
)
def test_a_row_that_does_not_validate_stops_the_load_with_its_line(
    tmp_path: Path, row: str
) -> None:
    path = _file(tmp_path, "congreso-2023-07,000005,PP,pp", row)

    with pytest.raises(InvalidCandidaturePartiesError, match=r"\.csv:3: "):
        read_candidature_parties(path)


def test_a_missing_file_is_reported_as_such(tmp_path: Path) -> None:
    with pytest.raises(InvalidCandidaturePartiesError, match="not found"):
        read_candidature_parties(tmp_path / "nowhere.csv")
