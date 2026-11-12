"""The Infoelectoral reader on real lines of the July 2023 Congreso file (trimmed to two
municipalities, Las Palmas de Gran Canaria and Santa Cruz de Tenerife, and one district row of
Madrid). The files are zipped here, as the Ministerio publishes them."""

import hashlib
import zipfile
from datetime import date
from pathlib import Path

import pytest

from datos.voters.domain.election import Candidature, ElectionKind
from datos.voters.infrastructure.infoelectoral import (
    InvalidElectionFileError,
    parse_candidature_votes,
    parse_municipal_result,
    read_election_zip,
)

FIXTURE = Path("tests/fixtures/infoelectoral/02202307_MUNI")
NAMES = ("01022307.DAT", "02022307.DAT", "03022307.DAT", "05022307.DAT", "06022307.DAT")


def _zip(tmp_path: Path, *, replace: dict[str, bytes] | None = None, name: str = "") -> Path:
    path = tmp_path / (name or "02202307_MUNI.zip")
    with zipfile.ZipFile(path, "w") as archive:
        for file_name in NAMES:
            content = (replace or {}).get(file_name, (FIXTURE / file_name).read_bytes())
            archive.writestr(file_name, content)
    return path


def _lines(file_name: str) -> list[str]:
    return (FIXTURE / file_name).read_bytes().decode("cp1252").splitlines()


def test_reads_the_election_and_the_file_it_came_from(tmp_path: Path) -> None:
    path = _zip(tmp_path)

    read = read_election_zip(path)

    assert read.election.kind is ElectionKind.CONGRESO
    assert read.election.held_on == date(2023, 7, 23)
    assert read.election.id == "congreso-2023-07"
    assert read.source_file == "02202307_MUNI.zip"
    assert read.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_reads_each_candidature_with_its_national_head(tmp_path: Path) -> None:
    read = read_election_zip(_zip(tmp_path))

    by_code = {c.code: c for c in read.candidatures}
    assert len(by_code) == 12
    assert by_code["000002"] == Candidature("000002", "PSOE", by_code["000002"].name, "000002")
    # Sumar's list in the Canaries adds up to Sumar nationally.
    assert (by_code["000033"].acronym, by_code["000033"].national_head_code) == ("SUMAR", "000010")


def test_reads_the_municipal_totals_and_leaves_out_district_rows(tmp_path: Path) -> None:
    read = read_election_zip(_zip(tmp_path))

    assert [(r.municipality_code, r.municipality_name) for r in read.results] == [
        ("35016", "Las Palmas de Gran Canaria"),
        ("38038", "Santa Cruz de Tenerife"),
    ]
    assert not any(v.municipality_code == "28079" for v in read.votes)


def test_the_votes_of_each_municipality_add_up_to_its_votes_to_candidatures(
    tmp_path: Path,
) -> None:
    read = read_election_zip(_zip(tmp_path))

    for result in read.results:
        votes = sum(v.votes for v in read.votes if v.municipality_code == result.municipality_code)
        assert votes == result.candidature_votes
        assert result.valid_votes == result.candidature_votes + result.blank_votes
        assert 0 < result.valid_votes <= result.census


def test_a_district_row_is_not_a_municipal_total() -> None:
    district = next(line for line in _lines("05022307.DAT") if line[11:18] == "2807901")

    assert parse_municipal_result((district, "05 line 3")) is None
    assert parse_candidature_votes((_lines("06022307.DAT")[-1], "06 line 21")) is None


def test_refuses_a_line_of_another_length_with_its_file_and_line(tmp_path: Path) -> None:
    lines = _lines("05022307.DAT")
    lines[1] = lines[1][:-1]
    broken = ("\n".join(lines) + "\n").encode("cp1252")

    with pytest.raises(InvalidElectionFileError, match=r"05022307\.DAT line 2: 232 characters"):
        read_election_zip(_zip(tmp_path, replace={"05022307.DAT": broken}))


def test_refuses_a_line_of_another_election_than_the_file_name(tmp_path: Path) -> None:
    lines = _lines("06022307.DAT")
    lines[0] = lines[0][:2] + "2019" + lines[0][6:]
    other = ("\n".join(lines) + "\n").encode("cp1252")

    with pytest.raises(InvalidElectionFileError, match="another election"):
        read_election_zip(_zip(tmp_path, replace={"06022307.DAT": other}))


def test_refuses_results_not_marked_as_official(tmp_path: Path) -> None:
    lines = _lines("05022307.DAT")
    lines[0] = lines[0][:-1] + "N"
    unofficial = ("\n".join(lines) + "\n").encode("cp1252")

    with pytest.raises(
        InvalidElectionFileError, match=r"05022307\.DAT line 1: the data is not marked as official"
    ):
        read_election_zip(_zip(tmp_path, replace={"05022307.DAT": unofficial}))


def test_refuses_a_count_that_is_not_a_number(tmp_path: Path) -> None:
    lines = _lines("06022307.DAT")
    lines[0] = lines[0][:22] + "00001x00" + lines[0][30:]
    garbled = ("\n".join(lines) + "\n").encode("cp1252")

    with pytest.raises(
        InvalidElectionFileError, match=r"06022307\.DAT line 1: votes is not a number"
    ):
        read_election_zip(_zip(tmp_path, replace={"06022307.DAT": garbled}))


def test_refuses_an_election_kind_it_does_not_load(tmp_path: Path) -> None:
    with pytest.raises(InvalidElectionFileError, match="not a supported Infoelectoral file name"):
        read_election_zip(_zip(tmp_path, name="04202305_MUNI.zip"))


def test_a_file_that_is_not_there_is_reported_as_such(tmp_path: Path) -> None:
    with pytest.raises(InvalidElectionFileError, match=r"02202307_MUNI\.zip: cannot be read"):
        read_election_zip(tmp_path / "02202307_MUNI.zip")


def test_a_file_that_is_not_a_zip_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "02202307_MUNI.zip"
    path.write_bytes(b"<html>Just a moment...</html>")  # what a bot challenge saves

    with pytest.raises(InvalidElectionFileError, match="not a zip"):
        read_election_zip(path)


def test_a_zip_damaged_inside_is_refused(tmp_path: Path) -> None:
    path = _zip(tmp_path)
    data = bytearray(path.read_bytes())
    stored = (FIXTURE / "05022307.DAT").read_bytes()
    at = data.index(stored) + 150  # inside the census of the first municipality
    data[at] = ord("9") if data[at] != ord("9") else ord("8")
    path.write_bytes(bytes(data))

    with pytest.raises(InvalidElectionFileError, match="damaged"):
        read_election_zip(path)


def test_bytes_that_are_not_cp1252_text_are_refused_with_their_file(tmp_path: Path) -> None:
    content = bytearray((FIXTURE / "03022307.DAT").read_bytes())
    content[20] = 0x81  # one of the five bytes cp1252 does not define
    path = _zip(tmp_path, replace={"03022307.DAT": bytes(content)})

    with pytest.raises(InvalidElectionFileError, match=r"03022307\.DAT: byte 21 is not cp1252"):
        read_election_zip(path)
