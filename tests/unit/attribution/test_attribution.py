"""The attribution rule on the real curated dataset (data/governments/), case by case."""

from dataclasses import replace
from datetime import date
from pathlib import Path

from datos.attribution.domain.attribution import (
    AttributionEntry,
    Confidence,
    Reason,
    attribute,
)
from datos.governments.application.published import (
    Competence,
    CompetenceFunction,
    CompetenceLevel,
)
from datos.governments.infrastructure.csv_source import read_competences, read_terms

DATA = Path("data/governments")
TERMS = read_terms(DATA / "government_terms.csv", DATA / "government_term_parties.csv")
COMPETENCES = read_competences(DATA / "competences.csv")
TODAY = date(2026, 10, 14)

STATE, CCAA, LOCAL = CompetenceLevel.STATE, CompetenceLevel.CCAA, CompetenceLevel.LOCAL


def _attribute(
    community: str,
    sector: str,
    levels: set[CompetenceLevel],
    on: date = TODAY,
    competences: list[Competence] = COMPETENCES,
) -> list[AttributionEntry]:
    return attribute(
        community_id=community,
        sector_id=sector,
        levels=levels,
        published_on=on,
        terms=TERMS,
        competences=competences,
    )


def test_a_named_level_with_competence_gives_its_governing_parties_with_high_confidence() -> None:
    [entry] = _attribute("ccaa-05", "health", {CCAA})

    assert entry.confidence is Confidence.HIGH
    assert (entry.level, entry.territory_id) == (CCAA, "ccaa-05")
    assert entry.party_ids == ("coalicion-canaria", "pp")
    assert entry.competences and all(c.level is CCAA for c in entry.competences)
    assert entry.reason is None


def test_parties_that_only_supported_the_investiture_are_never_responsible() -> None:
    # The PSC governs Cataluña with the external support of ERC and Comuns.
    [entry] = _attribute("ccaa-09", "education", {CCAA})

    assert entry.party_ids == ("psc",)


def test_the_state_level_gives_the_government_of_spain() -> None:
    [entry] = _attribute("ccaa-13", "housing", {STATE})

    assert (entry.territory_id, entry.party_ids) == ("es", ("psoe", "sumar"))


def test_a_coalition_lists_every_governing_partner() -> None:
    [entry] = _attribute("ccaa-15", "education", {CCAA})

    assert entry.party_ids == ("contigo-zurekin", "geroa-bai", "psoe")


def test_no_level_named_is_not_determined_because_competences_are_shared() -> None:
    assert _attribute("ccaa-05", "health", set()) == [
        AttributionEntry(
            None, None, Confidence.NOT_DETERMINED, (), False, (), Reason.NO_LEVEL_NAMED
        )
    ]


def test_a_local_government_is_not_modelled_yet() -> None:
    [entry] = _attribute("ccaa-05", "housing", {LOCAL})

    assert (entry.confidence, entry.reason) == (
        Confidence.NOT_DETERMINED,
        Reason.LOCAL_NOT_MODELLED,
    )
    assert entry.party_ids == ()


def test_a_named_level_with_no_competence_in_the_sector_is_not_determined() -> None:
    # The real table gives every level some competence in the three sectors; this table does not.
    only_state = [
        Competence(
            "health", "x", "d", STATE, CompetenceFunction.EXECUTION, None, "law", "https://x"
        )
    ]

    [entry] = _attribute("ccaa-05", "health", {CCAA}, competences=only_state)

    assert (entry.confidence, entry.reason) == (Confidence.NOT_DETERMINED, Reason.NO_COMPETENCE)


def test_a_date_without_a_government_in_the_dataset_is_not_determined() -> None:
    [entry] = _attribute("ccaa-13", "health", {CCAA}, on=date(2010, 1, 1))

    assert entry.reason is Reason.NO_GOVERNMENT_ON_DATE


def test_the_government_changes_on_the_exact_day_of_the_new_term() -> None:
    # Canarias: the caretaker term of Ángel Víctor Torres ends and Clavijo's starts on 14 July 2023.
    [before] = _attribute("ccaa-05", "health", {CCAA}, on=date(2023, 7, 13))
    [after] = _attribute("ccaa-05", "health", {CCAA}, on=date(2023, 7, 14))

    assert before.party_ids == ("asg", "nueva-canarias", "podemos", "psoe")
    assert before.is_caretaker is True
    assert after.party_ids == ("coalicion-canaria", "pp")
    assert after.is_caretaker is False


def test_in_ceuta_public_health_care_is_the_states_not_the_citys() -> None:
    # Ceuta's own row (INGESA, the State) replaces the general regional row for health care.
    entries = _attribute("ccaa-18", "health", {STATE, CCAA})
    state = next(e for e in entries if e.level is STATE)
    city = next(e for e in entries if e.level is CCAA)

    assert any(
        c.activity == "healthcare-services" and c.territory_id == "ccaa-18"
        for c in state.competences
    )
    assert all(c.activity != "healthcare-services" for c in city.competences)


def test_entries_come_state_first_whatever_the_order_the_levels_were_found_in() -> None:
    entries = _attribute("ccaa-01", "education", {LOCAL, CCAA, STATE})

    assert [e.level for e in entries] == [STATE, CCAA, LOCAL]


def test_swapping_party_ids_in_the_data_swaps_them_in_the_result_and_nothing_else() -> None:
    # Neutrality: no party id is special to the rule.
    swap = {"pp": "psoe", "psoe": "pp"}
    swapped = [
        replace(
            t,
            parties=tuple(replace(p, party_id=swap.get(p.party_id, p.party_id)) for p in t.parties),
        )
        for t in TERMS
    ]

    original = _attribute("ccaa-08", "health", {STATE, CCAA})
    renamed = attribute(
        community_id="ccaa-08",
        sector_id="health",
        levels={STATE, CCAA},
        published_on=TODAY,
        terms=swapped,
        competences=COMPETENCES,
    )

    expected = [
        replace(e, party_ids=tuple(sorted(swap.get(p, p) for p in e.party_ids))) for e in original
    ]
    assert renamed == expected
