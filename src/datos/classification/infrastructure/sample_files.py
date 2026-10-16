"""The files of a labelling sample: the enrichment terms it reads, the sets it must avoid, and what
it writes. In git, ids, URLs and strata only; the headlines and leads for the labelling tool go out
of git (sources audit: the lead is processed, never published)."""

import csv
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from datos.classification.application.sample_for_labelling import Sample
from datos.classification.domain.sampling import EnrichmentTerm, MatchKind
from datos.classification.domain.text import tags_line

LABELLED_SET_DIRS = (Path("data/train"), Path("data/eval"))


class InvalidEnrichmentTermsError(Exception):
    """The terms file is missing, empty or has a row that does not validate."""


class _TermRow(BaseModel):
    stem: str
    sector_id: str
    match: MatchKind
    language: str


def read_enrichment_terms(path: Path, *, sector_ids: Iterable[str]) -> list[EnrichmentTerm]:
    known = set(sector_ids)
    terms: list[EnrichmentTerm] = []
    try:
        with path.open(encoding="utf-8", newline="") as file:
            for line, raw in enumerate(csv.DictReader(file), start=2):
                try:
                    row = _TermRow.model_validate(raw)
                except ValidationError as error:
                    raise InvalidEnrichmentTermsError(f"{path}:{line}: {error}") from error
                if not row.stem.strip() or row.sector_id not in known:
                    raise InvalidEnrichmentTermsError(
                        f"{path}:{line}: empty stem or unknown sector"
                    )
                terms.append(EnrichmentTerm(row.stem.strip(), row.sector_id, row.match))
    except FileNotFoundError as error:
        raise InvalidEnrichmentTermsError(f"{path}: not found") from error
    if not terms:
        raise InvalidEnrichmentTermsError(f"{path}: no terms")
    return terms


def file_version(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def labelled_ids(directories: Iterable[Path] = LABELLED_SET_DIRS) -> set[int]:
    """The ids of every article in any labelled set or sample, so a new sample avoids them."""
    ids: set[int] = set()
    for directory in directories:
        for path in sorted(directory.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    ids.add(int(json.loads(line)["article_id"]))
    return ids


def write_sample(
    sample: Sample,
    *,
    name: str,
    out_dir: Path,
    tasks_dir: Path,
    seed: int,
    until: datetime,
    terms_version: str,
    tags_by_id: Mapping[int, Sequence[str]],
    tag_stoplist: str,
) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)
    lines = out_dir / f"{name}.jsonl"
    meta = out_dir / f"{name}.meta.json"
    tasks = tasks_dir / f"{name}.json"
    lines.write_text(
        "".join(
            json.dumps(
                {
                    "article_id": a.article_id,
                    "outlet_id": a.outlet_id,
                    "url": a.url,
                    "stratum": a.stratum.value,
                },
                ensure_ascii=False,
            )
            + "\n"
            for a in sample.articles
        ),
        encoding="utf-8",
    )
    meta.write_text(
        json.dumps(
            {
                "name": name,
                "size": len(sample.articles),
                "seed": seed,
                "until": until.isoformat(),
                "enrichment_terms_version": terms_version,
                "tag_stoplist_version": tag_stoplist,  # the tags the author saw while labelling
                "quotas": {
                    o: {"random": q.random, "enriched": q.enriched}
                    for o, q in sample.quotas.items()
                },
                "enriched_available": sample.enriched_available,
                "shortfalls": [
                    {"outlet_id": s.outlet_id, "stratum": s.stratum.value, "missing": s.missing}
                    for s in sample.shortfalls
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # The labelling tool sees the headline, the tags and the lead, never the outlet (labelling
    # guide). The tags are the ones the model will read: filtered, in order, at most eight.
    tasks.write_text(
        json.dumps(
            [
                {
                    "data": {
                        "article_id": a.article_id,
                        "headline": sample.texts[a.article_id].headline,
                        "tags": tags_line(tags_by_id.get(a.article_id, ())),
                        "lead": sample.texts[a.article_id].lead or "",
                    }
                }
                for a in sample.articles
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return lines, meta, tasks
