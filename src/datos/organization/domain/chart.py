"""The executive of a territory as the chart draws it on a given day.

Pure functions only: "today" is a parameter. The rule that matters is "complete or nothing": a
government is drawn only when its head and every department of the territory have a holder in
force that day. One missing holder and nothing of that executive is returned, never half a
government (spec AC5). Order never ranks: the head first, then the departments by name.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from datos.organization.domain.body import Body, BodyKind, Holder, holder_on


class ChartStatus(StrEnum):
    COMPLETE = "complete"
    NO_DATA = "no_data"  # the web app says "sin datos todavía"


@dataclass(frozen=True, slots=True)
class Post:
    """A body with the holder of its head post on the day asked."""

    body: Body
    holder: Holder


@dataclass(frozen=True, slots=True)
class ExecutiveChart:
    status: ChartStatus
    head: Post | None  # the president, or the prime minister for the State
    departments: tuple[Post, ...]  # consejerías or ministries, by name


_NO_DATA = ExecutiveChart(ChartStatus.NO_DATA, None, ())


def executive_chart(
    bodies: Iterable[Body], holders: Iterable[Holder], territory_id: str, day: date
) -> ExecutiveChart:
    """The head and the departments of `territory_id` with their holders on `day`.

    `no_data` when the territory has no bodies, no or more than one executive head, no
    department, or any of them without a holder in force that day.
    """
    held = list(holders)
    own = [b for b in bodies if b.territory_id == territory_id]
    heads = [b for b in own if b.kind is BodyKind.EXECUTIVE_HEAD]
    departments = [b for b in own if b.kind is BodyKind.DEPARTMENT]
    if len(heads) != 1 or not departments:
        return _NO_DATA
    posts = [_post(body, held, day) for body in (heads[0], *departments)]
    found = [post for post in posts if post is not None]
    if len(found) != len(posts):
        return _NO_DATA
    head, *others = found
    return ExecutiveChart(ChartStatus.COMPLETE, head, tuple(sorted(others, key=_by_name)))


def _post(body: Body, holders: list[Holder], day: date) -> Post | None:
    holder = holder_on(holders, body.id, day)
    return None if holder is None else Post(body, holder)


def _by_name(post: Post) -> tuple[str, str]:
    # Case-insensitive, with the id to break a tie: the same data always gives the same order.
    return (post.body.name.casefold(), post.body.id)
