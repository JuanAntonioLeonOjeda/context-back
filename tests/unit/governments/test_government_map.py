from dataclasses import replace
from datetime import date

from datos.governments.domain.government_map import CommunityOnMap, map_on
from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty

SOURCE = "https://www.boe.es/example"
DAY = date(2026, 10, 13)


def _term(
    territory_id: str,
    parties: dict[str, PartyRole],
    *,
    valid_from: date = date(2023, 7, 1),
    is_caretaker: bool = False,
) -> GovernmentTerm:
    return GovernmentTerm(
        territory_id=territory_id,
        president_name="President",
        valid_from=valid_from,
        valid_to=None,
        parties=tuple(TermParty(p, r, SOURCE) for p, r in parties.items()),
        is_caretaker=is_caretaker,
        source_url=SOURCE,
    )


G, S = PartyRole.GOVERNING, PartyRole.EXTERNAL_SUPPORT


def test_external_support_never_colours_the_map() -> None:
    terms = [_term("ccaa-09", {"psc": G, "erc": S, "comuns": S})]

    [cataluna] = map_on(terms, ["ccaa-09"], DAY)

    assert cataluna.governing_party_ids == ("psc",)


def test_coalition_parties_are_alphabetical_whatever_the_order_in_the_data() -> None:
    terms = [_term("ccaa-05", {"pp": G, "coalicion-canaria": G})]

    [canarias] = map_on(terms, ["ccaa-05"], DAY)

    assert canarias.governing_party_ids == ("coalicion-canaria", "pp")


def test_communities_come_in_the_order_given_with_no_data_marked_not_dropped() -> None:
    terms = [_term("ccaa-13", {"pp": G})]

    result = map_on(terms, ["ccaa-01", "ccaa-13"], DAY)

    assert result == [
        CommunityOnMap("ccaa-01", (), is_caretaker=False, has_data=False),
        CommunityOnMap("ccaa-13", ("pp",), is_caretaker=False, has_data=True),
    ]


def test_a_date_before_a_term_starts_has_no_data() -> None:
    terms = [_term("ccaa-13", {"pp": G}, valid_from=date(2023, 6, 23))]

    [madrid] = map_on(terms, ["ccaa-13"], date(2023, 6, 22))

    assert madrid.has_data is False


def test_a_caretaker_government_is_marked() -> None:
    terms = [_term("ccaa-12", {"pp": G}, is_caretaker=True)]

    [galicia] = map_on(terms, ["ccaa-12"], DAY)

    assert galicia.is_caretaker is True and galicia.has_data is True


def test_swapping_party_ids_swaps_the_output_and_nothing_else() -> None:
    # Neutrality: no party id is special. Renaming parties in the data must rename them in
    # the map and change nothing else (order is recomputed alphabetically after renaming).
    terms = [
        _term("ccaa-05", {"pp": G, "coalicion-canaria": G, "asg": S}),
        _term("ccaa-08", {"psoe": G}),
        _term("ccaa-13", {"pp": G}, is_caretaker=True),
    ]
    swap = {"pp": "psoe", "psoe": "pp"}
    swapped = [
        replace(
            t,
            parties=tuple(replace(p, party_id=swap.get(p.party_id, p.party_id)) for p in t.parties),
        )
        for t in terms
    ]
    ids = ["ccaa-05", "ccaa-08", "ccaa-13"]

    original = map_on(terms, ids, DAY)
    renamed = map_on(swapped, ids, DAY)

    expected = [
        replace(c, governing_party_ids=tuple(sorted(swap.get(p, p) for p in c.governing_party_ids)))
        for c in original
    ]
    assert renamed == expected
