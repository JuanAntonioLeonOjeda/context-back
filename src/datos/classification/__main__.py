"""Command line: uv run python -m datos.classification <command>

- `classify-new [--rules-dir PATH]`: classifies the articles the rules classifier has not seen yet
  (a new version of the rules, that is, any change in data/classification/, classifies everything
  again). Run it after each collection.
- `sample --set train|eval --name NAME --size N --seed S --until ISO-DATETIME [--dry-run]`: draws a
  sample for hand labelling (data/sampling/README.md). Refuses to overwrite a sample: a sample is
  frozen, a new one gets a new name.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import structlog

from datos.classification.application.sample_for_labelling import Sample, sample_for_labelling
from datos.classification.application.store_classifications import classify_new
from datos.classification.infrastructure.pg_candidate_reader import PgCandidateReader
from datos.classification.infrastructure.pg_repository import PgClassificationRepository
from datos.classification.infrastructure.rules_classifier import (
    InvalidRulesFileError,
    load_rules_classifier,
)
from datos.classification.infrastructure.sample_files import (
    InvalidEnrichmentTermsError,
    file_version,
    labelled_ids,
    read_enrichment_terms,
    write_sample,
)
from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging

DEFAULT_RULES_DIR = Path("data/classification")
DEFAULT_TERMS = Path("data/sampling/enrichment-terms.csv")
SET_DIRS = {"train": Path("data/train"), "eval": Path("data/eval")}
TASKS_DIR = Path("var/labelstudio")

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.classification")
    commands = parser.add_subparsers(dest="command", required=True)
    classify = commands.add_parser("classify-new", help="classify the articles not seen yet")
    classify.add_argument("--rules-dir", type=Path, default=DEFAULT_RULES_DIR)
    sample = commands.add_parser("sample", help="draw a sample for hand labelling")
    sample.add_argument("--set", choices=sorted(SET_DIRS), required=True)
    sample.add_argument("--name", required=True, help="e.g. train-sample-v1")
    sample.add_argument("--size", type=int, required=True)
    sample.add_argument("--seed", type=int, required=True)
    sample.add_argument("--until", type=datetime.fromisoformat, required=True)
    sample.add_argument("--terms", type=Path, default=DEFAULT_TERMS)
    sample.add_argument("--dry-run", action="store_true", help="show the allocation, write nothing")
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    repository = PgClassificationRepository(engine)
    if arguments.command == "sample":
        _sample(arguments, repository, PgCandidateReader(engine))
        return
    try:
        classifier = load_rules_classifier(arguments.rules_dir, sector_ids=repository.sector_ids())
    except InvalidRulesFileError as error:
        log.error("articles_not_classified", reason=str(error))
        raise SystemExit(1) from error
    classify_new(classifier, repository)


def _sample(
    arguments: argparse.Namespace,
    repository: PgClassificationRepository,
    reader: PgCandidateReader,
) -> None:
    until: datetime = arguments.until
    if until.tzinfo is None:
        log.error("sample_not_drawn", reason="--until needs a time zone, e.g. +02:00")
        raise SystemExit(1)
    out_dir: Path = SET_DIRS[arguments.set]
    if (out_dir / f"{arguments.name}.jsonl").exists() and not arguments.dry_run:
        log.error("sample_not_drawn", reason=f"{arguments.name} exists: a sample is frozen")
        raise SystemExit(1)
    try:
        terms = read_enrichment_terms(arguments.terms, sector_ids=repository.sector_ids())
    except InvalidEnrichmentTermsError as error:
        log.error("sample_not_drawn", reason=str(error))
        raise SystemExit(1) from error
    drawn = sample_for_labelling(
        reader=reader,
        terms=terms,
        size=arguments.size,
        seed=arguments.seed,
        until=until,
        excluded_ids=labelled_ids(),
    )
    if arguments.dry_run:
        print(
            json.dumps(_summary(drawn), ensure_ascii=False, indent=2)
        )  # a report for the author, not a log event
        return
    paths = write_sample(
        drawn,
        name=arguments.name,
        out_dir=out_dir,
        tasks_dir=TASKS_DIR,
        seed=arguments.seed,
        until=until,
        terms_version=file_version(arguments.terms),
    )
    log.info("sample_drawn", size=len(drawn.articles), files=[str(p) for p in paths])


def _summary(sample: Sample) -> dict[str, object]:
    return {
        "size": len(sample.articles),
        "per_outlet": {
            outlet: {
                "random": quota.random,
                "enriched": quota.enriched,
                "enriched_available": sample.enriched_available[outlet],
            }
            for outlet, quota in sample.quotas.items()
        },
        "shortfalls": [
            {"outlet_id": s.outlet_id, "stratum": s.stratum.value, "missing": s.missing}
            for s in sample.shortfalls
        ],
    }


if __name__ == "__main__":
    main()
