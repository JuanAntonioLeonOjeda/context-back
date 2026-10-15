"""The promotion criteria of ADR-0016, per label family: may the own model replace the rules?

Pure: the gold, rules' and candidate's labels of each test-set article in, the two criteria out.
The candidate is the composite classifier with the model in this family and the rules elsewhere.
Both criteria were set by the author before any training; the numbers are written here once:

1. Better overall: its macro-F1 on the random half is at least 5 points above the rules'.
2. No outlet left behind: for every outlet, its articles with this family exactly right are no
   more than 2 below the rules' (counted on the whole test set, D18).

The third criterion (no party wronged) was dropped with the attribution (ADR-0018).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from datos.classification.domain.bootstrap import Interval, bootstrap_interval
from datos.classification.domain.metrics import family_of, family_scores

MIN_GAIN = 0.05  # criterion 1: 5 points of macro-F1
MAX_OUTLET_LOSS = 2  # criterion 2: articles exactly right, per outlet
RANDOM = "random"


@dataclass(frozen=True, slots=True)
class EvaluatedArticle:
    """One test-set article with the labels of the three sources, as `sector:x` and `level:y`."""

    article_id: int
    outlet_id: str
    stratum: str
    gold: frozenset[str]
    rules: frozenset[str]
    candidate: frozenset[str]


@dataclass(frozen=True, slots=True)
class GainResult:
    rules_macro_f1: float | None
    candidate_macro_f1: float | None
    gain: float | None  # candidate - rules; None when either is undefined
    interval: Interval | None  # paired bootstrap of the gain, shown, never deciding
    articles: int  # the random half
    passes: bool  # an undefined gain does not pass: nothing was shown to be better


@dataclass(frozen=True, slots=True)
class OutletResult:
    outlet_id: str
    articles: int
    rules_right: int
    candidate_right: int

    @property
    def difference(self) -> int:
        return self.candidate_right - self.rules_right


@dataclass(frozen=True, slots=True)
class OutletsResult:
    outlets: tuple[OutletResult, ...]  # by outlet id
    passes: bool


def overall_gain(
    articles: Sequence[EvaluatedArticle], labels: Sequence[str], family: str, *, seed: int
) -> GainResult:
    """Criterion 1, on the random half: the enriched half was drawn with keywords and favours a
    keyword classifier."""
    family_labels = [label for label in labels if family_of(label) == family]
    random_half = [a for a in articles if a.stratum == RANDOM]

    def gain_on(positions: Sequence[int]) -> float | None:
        sample = [random_half[p] for p in positions]
        rules = _macro(sample, family_labels, family, _rules)
        candidate = _macro(sample, family_labels, family, _candidate)
        return None if rules is None or candidate is None else candidate - rules

    everything = range(len(random_half))
    rules_f1 = _macro(random_half, family_labels, family, _rules)
    candidate_f1 = _macro(random_half, family_labels, family, _candidate)
    gain = gain_on(everything)
    return GainResult(
        rules_macro_f1=rules_f1,
        candidate_macro_f1=candidate_f1,
        gain=gain,
        interval=bootstrap_interval(len(random_half), gain_on, seed=seed) if random_half else None,
        articles=len(random_half),
        # Rounded: 0.83 - 0.78 is 0.04999… in floating point, and five points are five points.
        passes=gain is not None and round(gain, 9) >= MIN_GAIN,
    )


def outlets_left_behind(articles: Sequence[EvaluatedArticle], family: str) -> OutletsResult:
    """Criterion 2, on every article: per outlet, how many have this family's labels exactly as
    the gold ones, for the rules and for the candidate."""
    outlets = sorted({a.outlet_id for a in articles})
    results = tuple(
        OutletResult(
            outlet_id=outlet,
            articles=sum(a.outlet_id == outlet for a in articles),
            rules_right=sum(
                a.outlet_id == outlet and _same(a.rules, a.gold, family) for a in articles
            ),
            candidate_right=sum(
                a.outlet_id == outlet and _same(a.candidate, a.gold, family) for a in articles
            ),
        )
        for outlet in outlets
    )
    return OutletsResult(results, all(r.difference >= -MAX_OUTLET_LOSS for r in results))


def _rules(article: EvaluatedArticle) -> frozenset[str]:
    return article.rules


def _candidate(article: EvaluatedArticle) -> frozenset[str]:
    return article.candidate


def _macro(
    articles: Sequence[EvaluatedArticle],
    family_labels: Sequence[str],
    family: str,
    labels_of: Callable[[EvaluatedArticle], frozenset[str]],
) -> float | None:
    gold = [a.gold for a in articles]
    predicted = [labels_of(a) for a in articles]
    [score] = [s for s in family_scores(gold, predicted, family_labels) if s.family == family]
    return score.macro_f1


def _same(predicted: frozenset[str], gold: frozenset[str], family: str) -> bool:
    return {x for x in predicted if family_of(x) == family} == {
        x for x in gold if family_of(x) == family
    }
