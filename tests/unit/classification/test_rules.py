"""The matching conventions of data/classification/README.md, on minimal hand-made rules."""

from datos.classification.domain.rules import (
    LevelTerm,
    PlaceTerm,
    SectorTerm,
    classify_text,
    compile_rules,
)
from datos.governments.application.published import CompetenceLevel

STATE, CCAA, LOCAL = CompetenceLevel.STATE, CompetenceLevel.CCAA, CompetenceLevel.LOCAL

RULES = compile_rules(
    [
        PlaceTerm("Santander", "ccaa-06", None),
        PlaceTerm("Palma", "ccaa-04", None),
        PlaceTerm("La Palma", "ccaa-05", None),
        PlaceTerm("Gobierno de Canarias", "ccaa-05", CCAA),
        LevelTerm("Gobierno", STATE),
        LevelTerm("Consell", CCAA),
        LevelTerm("Consell de Mallorca", LOCAL),
        LevelTerm("ajuntament", LOCAL),
        SectorTerm("hospital", "health"),
        SectorTerm("CAP", "health"),
    ],
    exclusions=["Banco Santander"],
)


def test_an_exclusion_is_removed_before_anything_matches() -> None:
    labels = classify_text("Banco Santander abre una oficina", RULES)

    assert labels.communities == frozenset()


def test_a_capitalised_term_matches_only_with_its_capital() -> None:
    assert classify_text("La palma de la mano", RULES).communities == frozenset()
    assert classify_text("Una calle de Palma", RULES).communities == {"ccaa-04"}


def test_a_lower_case_term_matches_in_any_case() -> None:
    assert classify_text("HOSPITAL colapsado", RULES).sectors == {"health"}
    assert classify_text("L'Ajuntament aprova el pressupost", RULES).levels == {LOCAL}


def test_terms_match_whole_words_only() -> None:
    assert classify_text("La capital de la provincia", RULES).sectors == frozenset()
    assert classify_text("Tanca un CAP per obres", RULES).sectors == {"health"}


def test_the_longest_term_wins_and_shorter_overlapping_terms_are_ignored() -> None:
    canarias = classify_text("El Gobierno de Canarias aprueba el plan", RULES)
    mallorca = classify_text("El Consell de Mallorca aprova el pla", RULES)

    assert (canarias.communities, canarias.levels) == (frozenset({"ccaa-05"}), frozenset({CCAA}))
    assert mallorca.levels == {LOCAL}
    assert classify_text("La Palma recibe ayudas", RULES).communities == {"ccaa-05"}


def test_two_separate_terms_both_count() -> None:
    labels = classify_text("El Gobierno y el Gobierno de Canarias firman", RULES)

    assert labels.levels == {STATE, CCAA}


def test_every_label_comes_with_the_term_that_produced_it() -> None:
    labels = classify_text("El Gobierno de Canarias abre un hospital", RULES)

    assert {(e.term, e.gives) for e in labels.evidence} == {
        ("Gobierno de Canarias", "community:ccaa-05"),
        ("Gobierno de Canarias", "level:ccaa"),
        ("hospital", "sector:health"),
    }


def test_an_empty_text_has_no_labels() -> None:
    labels = classify_text("", RULES)

    assert (labels.communities, labels.sectors, labels.levels) == (
        frozenset(),
        frozenset(),
        frozenset(),
    )
