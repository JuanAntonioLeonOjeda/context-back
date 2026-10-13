import re
from pathlib import Path

from datos.governments.infrastructure.csv_source import read_parties

# The neutral grey of a party with no standard colour (data/governments/README.md, "Party colours").
NEUTRAL_GREY = "#9e9e9e"
PARTIES_WITHOUT_STANDARD_COLOUR = {"convocatoria-por-asturias"}


def test_every_party_has_a_lowercase_hex_colour_and_no_two_share_one() -> None:
    parties = read_parties(Path("data/governments/parties.csv"))

    colours = [p.colour_hex for p in parties]

    assert len(parties) == 34
    assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in colours)
    assert len(set(colours)) == len(colours)


def test_only_the_documented_party_uses_the_neutral_grey() -> None:
    parties = read_parties(Path("data/governments/parties.csv"))

    grey = {p.id for p in parties if p.colour_hex == NEUTRAL_GREY}

    assert grey == PARTIES_WITHOUT_STANDARD_COLOUR


def test_the_readme_names_the_wikidata_item_of_every_party_with_a_standard_colour() -> None:
    readme = Path("data/governments/README.md").read_text(encoding="utf-8")
    parties = read_parties(Path("data/governments/parties.csv"))

    missing = [
        p.id
        for p in parties
        if p.id not in PARTIES_WITHOUT_STANDARD_COLOUR
        and not re.search(rf"`{re.escape(p.id)}` \| Q\d+", readme)
    ]

    assert missing == []
