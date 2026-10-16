"""A classifier made of others: each family of labels comes from the classifier assigned to it.

ADR-0016 promotes the own model per family: it can take sectors and levels while the rules keep
communities, or take only one of them. This composite is what is stored and read; its version
says which classifier, at which version, produced each family, so every stored label can still
be traced to what made it (ADR-0015).
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum

from datos.classification.application.classifier import ArticleClassifier
from datos.classification.domain.labels import Labels


class Family(StrEnum):
    COMMUNITIES = "communities"
    SECTORS = "sectors"
    LEVELS = "levels"


# How an evidence entry says which family it belongs to ("community:ccaa-05", "sector:health").
EVIDENCE_PREFIX = {
    Family.COMMUNITIES: "community:",
    Family.SECTORS: "sector:",
    Family.LEVELS: "level:",
}


class CompositeClassifier:
    model_id = "composite"

    def __init__(self, sources: Mapping[Family, ArticleClassifier]) -> None:
        missing = set(Family) - set(sources)
        if missing:
            raise ValueError(f"no classifier for {sorted(missing)}")
        self._sources = dict(sources)

    @property
    def model_version(self) -> str:
        # Every family, always in the same order, with its source: two composites built from the
        # same classifiers have the same version, and any change in a source changes it.
        return ";".join(
            f"{family}={source.model_id}@{source.model_version}"
            for family, source in ((f, self._sources[f]) for f in Family)
        )

    def classify(self, headline: str, lead: str | None, tags: Sequence[str] = ()) -> Labels:
        # Each source runs once per article even if it supplies two families; sources are taken
        # in the order of the families they supply first.
        sources: list[ArticleClassifier] = []
        prefixes: dict[int, tuple[str, ...]] = {}
        for family in Family:
            source = self._sources[family]
            if id(source) not in prefixes:
                sources.append(source)
                prefixes[id(source)] = ()
            prefixes[id(source)] += (EVIDENCE_PREFIX[family],)
        results = {id(source): source.classify(headline, lead, tags) for source in sources}

        def taken(family: Family) -> Labels:
            return results[id(self._sources[family])]

        return Labels(
            communities=taken(Family.COMMUNITIES).communities,
            sectors=taken(Family.SECTORS).sectors,
            levels=taken(Family.LEVELS).levels,
            # Only the evidence and the scores of the families each source supplies (the rules'
            # sector terms say nothing once the sectors come from the model), in the order each
            # source gave them.
            evidence=tuple(
                evidence
                for source in sources
                for evidence in results[id(source)].evidence
                if evidence.gives.startswith(prefixes[id(source)])
            ),
            scores=tuple(
                score
                for source in sources
                for score in results[id(source)].scores
                if score.label.startswith(prefixes[id(source)])
            ),
        )
