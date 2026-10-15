"""The sampling method of data/sampling/README.md, case by case."""

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from datos.classification.application.sample_for_labelling import sample_for_labelling
from datos.classification.domain.sampling import (
    Candidate,
    MatchKind,
    Quota,
    Stratum,
    allocate,
    draw,
    enrichment_pattern,
    is_enriched,
    normalise,
)
from datos.classification.infrastructure.sample_files import read_enrichment_terms

SECTORS = frozenset({"education", "health", "housing"})
TERMS = read_enrichment_terms(Path("data/sampling/enrichment-terms.csv"), sector_ids=SECTORS)
PATTERN = enrichment_pattern(TERMS)
UNTIL = datetime(2026, 10, 21, tzinfo=UTC)


def article(
    article_id: int, outlet_id: str, headline: str = "Un titular", lead: str | None = None
) -> Candidate:
    return Candidate(
        article_id, outlet_id, f"https://{outlet_id}.example/{article_id}", headline, lead
    )


def outlet_pool(outlet_id: str, start: int, plain: int, sector: int) -> list[Candidate]:
    return [article(start + i, outlet_id) for i in range(plain)] + [
        article(start + plain + i, outlet_id, "El hospital amplía su plantilla")
        for i in range(sector)
    ]


class FixedReader:
    def __init__(self, candidates: list[Candidate]) -> None:
        self._candidates = candidates

    def candidates(self, *, until: datetime) -> list[Candidate]:
        return list(self._candidates)


def test_text_is_compared_without_accents_and_case() -> None:
    assert normalise("Sanitària ÉDUCACIÓN") == "sanitaria educacion"


@pytest.mark.parametrize(
    ("headline", "expected"),
    [
        ("Los hospitales de Madrid amplían horario", True),  # prefix: hospital → hospitales
        ("La Generalitat obre una nova escola a Girona", True),  # Catalan
        ("Educación convoca 3.000 plazas", True),  # accents and case
        ("Récord de MIR en la convocatoria", True),  # acronym as a whole word
        ("El Real Madrid gana en Miranda", False),  # 'mir' inside a word is not the acronym
        ("El Gobierno aprueba los presupuestos", False),
    ],
)
def test_an_article_is_enriched_by_a_broad_sector_term(headline: str, expected: bool) -> None:
    assert is_enriched(article(1, "a", headline), PATTERN) is expected


def test_the_lead_counts_as_well_as_the_headline() -> None:
    assert is_enriched(article(1, "a", "Pleno del lunes", "Se debate el alquiler"), PATTERN)


def test_the_size_is_split_evenly_among_outlets_with_the_remainder_by_id() -> None:
    quotas = allocate(["c", "a", "b", "a"], 10)

    assert {o: q.random + q.enriched for o, q in quotas.items()} == {"a": 4, "b": 3, "c": 3}
    assert sum(q.random + q.enriched for q in quotas.values()) == 10


def test_an_odd_article_goes_to_the_random_half() -> None:
    assert allocate(["a"], 7) == {"a": Quota(random=4, enriched=3)}


def test_the_same_seed_gives_the_same_sample_and_another_seed_another() -> None:
    pool = outlet_pool("a", 1, 40, 40) + outlet_pool("b", 100, 40, 40)
    quotas = allocate(["a", "b"], 20)

    first, _ = draw(pool, quotas, PATTERN, seed=7)
    again, _ = draw(list(reversed(pool)), quotas, PATTERN, seed=7)
    other, _ = draw(pool, quotas, PATTERN, seed=8)

    assert first == again  # the order the candidates come in does not matter
    assert first != other


def test_each_outlet_gets_its_quota_half_random_half_enriched_and_nothing_twice() -> None:
    pool = outlet_pool("a", 1, 40, 40) + outlet_pool("b", 100, 40, 40)

    sample, shortfalls = draw(pool, allocate(["a", "b"], 20), PATTERN, seed=1)

    assert Counter((s.outlet_id, s.stratum) for s in sample) == {
        ("a", Stratum.RANDOM): 5,
        ("a", Stratum.ENRICHED): 5,
        ("b", Stratum.RANDOM): 5,
        ("b", Stratum.ENRICHED): 5,
    }
    assert len({s.article_id for s in sample}) == 20
    assert shortfalls == []
    enriched_ids = {s.article_id for s in sample if s.stratum is Stratum.ENRICHED}
    assert all(is_enriched(c, PATTERN) for c in pool if c.article_id in enriched_ids)


def test_an_outlet_short_of_enriched_articles_is_filled_with_random_ones_and_says_so() -> None:
    pool = outlet_pool("a", 1, 30, 2)

    sample, shortfalls = draw(pool, {"a": Quota(random=5, enriched=5)}, PATTERN, seed=1)

    assert len(sample) == 10
    assert len({s.article_id for s in sample}) == 10
    assert shortfalls[0].outlet_id == "a"
    assert shortfalls[0].stratum is Stratum.ENRICHED
    assert 1 <= shortfalls[0].missing <= 5


def test_an_outlet_with_too_few_articles_gives_what_it_has_and_says_so() -> None:
    sample, shortfalls = draw(
        outlet_pool("a", 1, 3, 0), {"a": Quota(random=5, enriched=5)}, PATTERN, seed=1
    )

    assert len(sample) == 3
    assert {(s.stratum, s.missing) for s in shortfalls} == {
        (Stratum.ENRICHED, 5),
        (Stratum.RANDOM, 7),
    }


def test_the_random_half_is_a_plain_draw_that_can_include_sector_articles() -> None:
    # Drawn first, from all the outlet's articles: sometimes it takes sector articles too. Drawn
    # after the enriched half, it never could, and it would under-count sector news.
    pool = outlet_pool("a", 1, 25, 5)
    sector_ids = {c.article_id for c in pool if is_enriched(c, PATTERN)}

    random_halves = [
        {
            s.article_id
            for s in draw(pool, {"a": Quota(random=5, enriched=5)}, PATTERN, seed)[0]
            if s.stratum is Stratum.RANDOM
        }
        for seed in range(40)
    ]

    assert any(half & sector_ids for half in random_halves)


def test_with_only_sector_articles_both_halves_are_still_filled() -> None:
    sample, shortfalls = draw(
        outlet_pool("a", 1, 0, 30), {"a": Quota(random=5, enriched=5)}, PATTERN, seed=1
    )

    assert Counter(s.stratum for s in sample) == {Stratum.RANDOM: 5, Stratum.ENRICHED: 5}
    assert shortfalls == []


def test_articles_already_in_a_labelled_set_are_never_drawn() -> None:
    pool = outlet_pool("a", 1, 20, 20) + outlet_pool("b", 100, 20, 20)
    excluded = {c.article_id for c in pool[::2]}

    sample = sample_for_labelling(
        reader=FixedReader(pool),
        terms=TERMS,
        size=20,
        seed=3,
        until=UNTIL,
        excluded_ids=excluded,
    )

    assert not {a.article_id for a in sample.articles} & excluded


def test_the_sample_keeps_the_text_for_the_labelling_tool_and_counts_what_could_be_enriched() -> (
    None
):
    pool = outlet_pool("a", 1, 20, 6)

    sample = sample_for_labelling(
        reader=FixedReader(pool), terms=TERMS, size=10, seed=3, until=UNTIL, excluded_ids=()
    )

    assert set(sample.texts) == {a.article_id for a in sample.articles}
    assert sample.enriched_available == {"a": 6}


def test_the_terms_file_is_valid_and_uses_known_sectors_and_both_languages() -> None:
    assert {t.sector_id for t in TERMS} == SECTORS
    assert any(t.match is MatchKind.WORD for t in TERMS)
    assert len({t.stem for t in TERMS}) == len(TERMS)
