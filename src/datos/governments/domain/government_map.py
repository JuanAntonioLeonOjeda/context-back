"""What the map shows for each community on a date: the parties that govern it.

Pure. Rules (spec AC3, AC6):
- Only governing parties colour the map; external support never does (it is shown in
  the community card, not as if those parties governed).
- Parties are ordered alphabetically by id, so the stripes of a coalition never suggest
  who leads it or who is bigger.
- A community without a term on that date is still returned, marked without data, so the
  map never has a silent hole.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from datos.governments.domain.government_term import GovernmentTerm, in_force_on


@dataclass(frozen=True, slots=True)
class CommunityOnMap:
    territory_id: str
    governing_party_ids: tuple[str, ...]  # alphabetical; empty when has_data is False
    is_caretaker: bool
    has_data: bool


def map_on(
    terms: Iterable[GovernmentTerm], community_ids: Sequence[str], day: date
) -> list[CommunityOnMap]:
    """One entry per community, in the order given (the caller passes INE order)."""
    all_terms = list(terms)
    return [_community(all_terms, territory_id, day) for territory_id in community_ids]


def _community(terms: list[GovernmentTerm], territory_id: str, day: date) -> CommunityOnMap:
    term = in_force_on(terms, territory_id, day)
    if term is None:
        return CommunityOnMap(territory_id, (), is_caretaker=False, has_data=False)
    return CommunityOnMap(
        territory_id,
        tuple(sorted(term.governing_party_ids)),
        is_caretaker=term.is_caretaker,
        has_data=True,
    )
