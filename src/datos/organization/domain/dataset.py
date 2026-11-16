"""Every reason not to load the curated organisation files, as readable messages.

The database refuses most of these too (migration 0016); checking them first reports all of them
at once, before anything is written, the way the governments loader does. Pure: the territory ids
and the sector ids that exist arrive as arguments. Problems of one row on its own (a URL that is
not a URL, an empty name, a date that is not a date) are the readers' job and carry the file and
the line; these are the ones that need other rows.
"""

import re
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from datetime import date

from datos.organization.domain.body import HEADED_KINDS, Body, BodyKind, BodyLevel, Holder
from datos.organization.domain.boxes import Competence

_DIR3_FORMAT = re.compile(r"^[A-Z][0-9A-Z]{8}$")


def dataset_problems(
    bodies: Sequence[Body],
    holders: Sequence[Holder],
    competences: Sequence[Competence],
    *,
    territory_ids: Collection[str],
    sector_ids: Collection[str],
) -> list[str]:
    """Problems of the three files together, bodies first, then holders, then competences."""
    return [
        *_body_problems(bodies, territory_ids),
        *_holder_problems(holders, bodies),
        *_competence_problems(competences, bodies, sector_ids),
    ]


# --- bodies --------------------------------------------------------------------------


def _body_problems(bodies: Sequence[Body], territory_ids: Collection[str]) -> list[str]:
    by_id = {b.id: b for b in bodies}
    problems = [f"body {i}: the id is repeated" for i in _repeated(b.id for b in bodies)]
    problems += [f"body {i}: the DIR3 code is repeated" for i in _repeated_dir3(bodies)]
    for body in bodies:
        problems += _territory_problems(body, territory_ids)
        problems += _place_problems(body)
        problems += _dir3_problems(body)
        problems += _parent_problems(body, by_id)
    return problems + _executive_head_problems(bodies)


def _territory_problems(body: Body, territory_ids: Collection[str]) -> list[str]:
    if body.territory_id is not None and body.territory_id not in territory_ids:
        return [f"body {body.id}: unknown territory {body.territory_id}"]
    return []


def _place_problems(body: Body) -> list[str]:
    """The level, the territory and the id must fit one another (the CHECKs of `bodies`)."""
    territory = body.territory_id
    in_a_community = territory is not None and territory.startswith("ccaa-")
    problems: list[str] = []
    if territory is None and body.level is not BodyLevel.LOCAL:
        problems.append(f"body {body.id}: only a local body can have no territory")
    if body.level is BodyLevel.LOCAL and territory is not None and not in_a_community:
        problems.append(f"body {body.id}: a local body has no territory or belongs to a community")
    if body.level is BodyLevel.CCAA and not in_a_community:
        problems.append(f"body {body.id}: a body of a community belongs to a community")
    if body.level is BodyLevel.STATE and not _belongs_to_the_state(body, in_a_community):
        problems.append(f"body {body.id}: a State body belongs to the State, except a court")
    if body.valid_from and body.valid_to and body.valid_to <= body.valid_from:
        problems.append(f"body {body.id}: its period is empty")
    if body.kind in HEADED_KINDS and body.level is BodyLevel.LOCAL:
        problems.append(f"body {body.id}: a body with a holder is not a local body")
    prefix = "local-" if territory is None else f"{territory}-"
    if not body.id.startswith(prefix):
        problems.append(f"body {body.id}: the id must start with {prefix}")
    return problems


def _belongs_to_the_state(body: Body, in_a_community: bool) -> bool:
    # A court is a State body that sits in a community (a TSJ).
    return body.territory_id == "es" or (body.kind is BodyKind.JUDICIARY and in_a_community)


def _dir3_problems(body: Body) -> list[str]:
    if body.dir3_id is not None and not _DIR3_FORMAT.fullmatch(body.dir3_id):
        return [f"body {body.id}: the DIR3 code {body.dir3_id!r} is not one"]
    return []


def _parent_problems(body: Body, by_id: dict[str, Body]) -> list[str]:
    if body.parent_id is None:
        if body.kind is BodyKind.DEPARTMENT:
            return [f"body {body.id}: a department needs a parent"]
        return []
    if body.parent_id == body.id:
        return [f"body {body.id}: it is its own parent"]
    parent = by_id.get(body.parent_id)
    if parent is None:
        return [f"body {body.id}: the parent {body.parent_id} does not exist"]
    problems: list[str] = []
    if parent.kind is not BodyKind.EXECUTIVE_HEAD:
        problems.append(f"body {body.id}: the parent {parent.id} is not an executive head")
    if parent.territory_id != body.territory_id:
        problems.append(f"body {body.id}: the parent {parent.id} belongs to another territory")
    return problems


def _executive_head_problems(bodies: Sequence[Body]) -> list[str]:
    heads: dict[str | None, list[str]] = defaultdict(list)
    for body in bodies:
        if body.kind is BodyKind.EXECUTIVE_HEAD:
            heads[body.territory_id].append(body.id)
    return [
        f"territory {territory}: more than one executive head ({', '.join(ids)})"
        for territory, ids in heads.items()
        if len(ids) > 1
    ]


# --- holders -------------------------------------------------------------------------


def _holder_problems(holders: Sequence[Holder], bodies: Sequence[Body]) -> list[str]:
    kinds = {b.id: b.kind for b in bodies}
    problems: list[str] = []
    for holder in holders:
        problems += _holder_body_problems(holder, kinds)
        if holder.valid_to is not None and holder.valid_to <= holder.valid_from:
            problems.append(f"{_who(holder)}: the period is empty")
    return problems + _overlap_problems(holders)


def _holder_body_problems(holder: Holder, kinds: dict[str, BodyKind]) -> list[str]:
    kind = kinds.get(holder.body_id)
    if kind is None:
        return [f"{_who(holder)}: the body does not exist"]
    if kind not in HEADED_KINDS:
        return [f"{_who(holder)}: a {kind.value} has no holder"]
    return []


def _overlap_problems(holders: Sequence[Holder]) -> list[str]:
    by_body: dict[str, list[Holder]] = defaultdict(list)
    for holder in holders:
        by_body[holder.body_id].append(holder)
    problems: list[str] = []
    for body_id, rows in by_body.items():
        ordered = sorted(rows, key=lambda h: h.valid_from)
        # Compare each with the one reaching furthest so far, not only the previous one: a long
        # period can overlap several later ones.
        furthest = ordered[0]
        for current in ordered[1:]:
            if furthest.valid_to is None or furthest.valid_to > current.valid_from:
                problems.append(
                    f"holders of {body_id}: {furthest.holder_name} and {current.holder_name}"
                    " overlap"
                )
            if _ends_later(current.valid_to, furthest.valid_to):
                furthest = current
    return problems


def _ends_later(end: date | None, other: date | None) -> bool:
    if end is None:
        return other is not None
    return other is not None and end > other


def _who(holder: Holder) -> str:
    return f"holder {holder.holder_name} of {holder.body_id} from {holder.valid_from}"


# --- competences ---------------------------------------------------------------------


def _competence_problems(
    competences: Sequence[Competence], bodies: Sequence[Body], sector_ids: Collection[str]
) -> list[str]:
    body_ids = {b.id for b in bodies}
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for competence in competences:
        what = f"competence of {competence.body_id} ({competence.summary[:40]!r})"
        key = (competence.body_id, competence.summary)
        if key in seen:
            problems.append(f"{what}: it is listed twice")
        seen.add(key)
        if competence.body_id not in body_ids:
            problems.append(f"{what}: the body does not exist")
        if not competence.sector_ids:
            problems.append(f"{what}: it relates to no sector")
        problems += [
            f"{what}: unknown sector {s}" for s in competence.sector_ids if s not in sector_ids
        ]
        problems += [f"{what}: sector {s} is repeated" for s in _repeated(competence.sector_ids)]
    return problems


# --- helpers -------------------------------------------------------------------------


def _repeated(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    repeated: list[str] = []
    for value in values:
        if value in seen and value not in repeated:
            repeated.append(value)
        seen.add(value)
    return repeated


def _repeated_dir3(bodies: Sequence[Body]) -> list[str]:
    """The ids of the bodies whose DIR3 code an earlier body already has."""
    first: dict[str, str] = {}
    later: list[str] = []
    for body in bodies:
        if body.dir3_id is None:
            continue
        if body.dir3_id in first:
            later.append(body.id)
        else:
            first[body.dir3_id] = body.id
    return later
