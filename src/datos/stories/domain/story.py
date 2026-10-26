"""The values of story grouping: a candidate pair of articles, the settings and the result.

A story is a claim that several articles tell the same event, so it carries how strongly each
article is tied to the others (`link_similarity`), never a score of how good the story is.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GroupingSettings:
    """What counts as a link. Provisional until pairs are labelled by hand (spec, decision 1)."""

    threshold: float  # minimum cosine similarity of the two vectors
    window_days: int  # maximum days between the two publication dates


@dataclass(frozen=True, slots=True)
class CandidatePair:
    """Two articles with the similarity of their vectors; `article_a_id < article_b_id`."""

    article_a_id: int
    article_b_id: int
    outlet_a_id: str
    outlet_b_id: str
    similarity: float
    days_apart: float


@dataclass(frozen=True, slots=True)
class StoryMember:
    article_id: int
    link_similarity: float  # the strongest accepted link this article has inside the story


@dataclass(frozen=True, slots=True)
class Story:
    members: tuple[StoryMember, ...]  # sorted by article id; at least two articles, two outlets
