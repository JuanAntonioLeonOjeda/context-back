"""The curated candidature → party table (data/voters/candidature-parties.csv) stays sound."""

import csv
import re
from pathlib import Path

import pytest


def _rows(path: str) -> list[dict[str, str]]:
    return list(csv.DictReader(Path(path).read_text(encoding="utf-8").splitlines()))


ROWS = _rows("data/voters/candidature-parties.csv")
PARTY_IDS = {row["id"] for row in _rows("data/governments/parties.csv")}


def test_every_row_names_a_party_of_the_party_table() -> None:
    assert ROWS
    assert [r["party_id"] for r in ROWS if r["party_id"] not in PARTY_IDS] == []


def test_one_row_per_election_and_candidature_with_well_formed_codes() -> None:
    keys = [(r["election_id"], r["candidature_code"]) for r in ROWS]

    assert len(keys) == len(set(keys))
    assert all(re.fullmatch(r"[a-z]+-\d{4}-\d{2}", election) for election, _ in keys)
    assert all(re.fullmatch(r"\d{6}", code) for _, code in keys)


def _party_of_2023(acronym: str) -> set[str]:
    return {
        r["party_id"]
        for r in ROWS
        if r["election_id"] == "congreso-2023-07" and r["acronym_in_file"] == acronym
    }


def test_a_party_with_its_own_row_in_the_party_table_is_not_its_national_head() -> None:
    assert _party_of_2023("PSC") == {"psc"}


@pytest.mark.parametrize("acronym", ["PSIB-PSOE", "PSdeG-PSOE", "PSN-PSOE", "PSE-EE (PSOE)"])
def test_a_federation_of_a_party_counts_as_the_party(acronym: str) -> None:
    assert _party_of_2023(acronym) == {"psoe"}


@pytest.mark.parametrize(
    "acronym",
    [
        "SUMAR - ECP",
        "SUMAR - COMPROMÍS",
        "MÉS PER MALLORCA-MÉS PER MENORCA-SUMAR",
        "CUP-PR",
        "NC-bc",
        "EXISTE",
    ],
)
def test_a_coalition_has_no_row_so_it_is_shown_apart_by_its_acronym(acronym: str) -> None:
    assert _party_of_2023(acronym) == set()
