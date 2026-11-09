"""Reader of the curated candidature → party table (data/voters/candidature-parties.csv)."""

import csv
from pathlib import Path

from datos.voters.application.community_voters import PartyByHead


def read_candidature_parties(path: Path) -> PartyByHead:
    """election id → national head code → party id."""
    table: dict[str, dict[str, str]] = {}
    for row in csv.DictReader(path.read_text(encoding="utf-8").splitlines()):
        table.setdefault(row["election_id"], {})[row["national_head_code"]] = row["party_id"]
    return table
