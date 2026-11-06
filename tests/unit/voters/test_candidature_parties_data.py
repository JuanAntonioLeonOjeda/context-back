"""The curated candidature → party table (data/voters/candidature-parties.csv) stays sound."""

import csv
import re
from pathlib import Path


def _rows(path: str) -> list[dict[str, str]]:
    return list(csv.DictReader(Path(path).read_text(encoding="utf-8").splitlines()))


ROWS = _rows("data/voters/candidature-parties.csv")
PARTY_IDS = {row["id"] for row in _rows("data/governments/parties.csv")}


def test_every_row_names_a_party_of_the_party_table() -> None:
    assert ROWS
    assert [r["party_id"] for r in ROWS if r["party_id"] not in PARTY_IDS] == []


def test_one_row_per_election_and_national_head_with_well_formed_codes() -> None:
    keys = [(r["election_id"], r["national_head_code"]) for r in ROWS]

    assert len(keys) == len(set(keys))
    assert all(re.fullmatch(r"[a-z]+-\d{4}-\d{2}", election) for election, _ in keys)
    assert all(re.fullmatch(r"\d{6}", head) for _, head in keys)


def test_two_heads_never_share_a_party_in_the_same_election() -> None:
    pairs = [(r["election_id"], r["party_id"]) for r in ROWS]

    assert len(pairs) == len(set(pairs))
