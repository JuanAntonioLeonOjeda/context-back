"""Command line: uv run python -m datos.classification <command>

- `classify-new [--rules-dir PATH]`: classifies the articles the rules classifier has not seen yet
  (a new version of the rules, that is, any change in data/classification/, classifies everything
  again). Run it after each collection.
- `sample --set train|eval --name NAME --size N --seed S --until ISO-DATETIME [--dry-run]`: draws a
  sample for hand labelling (data/sampling/README.md). Refuses to overwrite a sample: a sample is
  frozen, a new one gets a new name.
- `train --training-set PATH --seed S [--encoder NAME] [--models-dir PATH]`: trains the own model on
  the hand-labelled training set (needs the `ml` group: `uv run --group ml ...`). Refuses a set that
  shares an article with the blind test set, and never overwrites a model.
"""

import argparse
import json
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import structlog
from sqlalchemy import Engine

from datos.classification.application.sample_for_labelling import Sample, sample_for_labelling
from datos.classification.application.store_classifications import classify_new
from datos.classification.application.train_model import (
    ModelCard,
    TrainingConfig,
    TrainingPlan,
    TrainingSetInfo,
    fit_model,
    plan_training,
)
from datos.classification.domain.training_set import TrainingSetError
from datos.classification.infrastructure.local_model_store import LocalModelStore
from datos.classification.infrastructure.pg_article_text_reader import PgArticleTextReader
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
from datos.classification.infrastructure.setfit_classifier import DEFAULT_THRESHOLD
from datos.classification.infrastructure.setfit_trainer import (
    SetFitModelTrainer,
    count_pairs,
    device_name,
)
from datos.classification.infrastructure.training_set_file import read_training_set
from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging

DEFAULT_RULES_DIR = Path("data/classification")
DEFAULT_TERMS = Path("data/sampling/enrichment-terms.csv")
DEFAULT_TRAINING_SET = Path("data/train/train-set-v1.jsonl")
DEFAULT_ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # ADR-0016
MODELS_DIR = Path("models")
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
    train = commands.add_parser("train", help="train the own model on the hand-labelled set")
    train.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    train.add_argument("--seed", type=int, required=True)
    train.add_argument("--encoder", default=DEFAULT_ENCODER)
    train.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    train.add_argument(
        "--dry-run", action="store_true", help="show the plan (examples, labels, pairs) and stop"
    )
    train.add_argument(
        "--num-iterations",
        type=int,
        default=None,
        help="sentence pairs per example (default: the config's); written in the model's card",
    )
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    repository = PgClassificationRepository(engine)
    if arguments.command == "sample":
        _sample(arguments, repository, PgCandidateReader(engine))
        return
    if arguments.command == "train":
        _train(arguments, repository, engine)
        return
    try:
        classifier = load_rules_classifier(arguments.rules_dir, sector_ids=repository.sector_ids())
    except InvalidRulesFileError as error:
        log.error("articles_not_classified", reason=str(error))
        raise SystemExit(1) from error
    classify_new(classifier, repository)


def _train(
    arguments: argparse.Namespace, repository: PgClassificationRepository, engine: Engine
) -> None:
    path: Path = arguments.training_set
    sector_ids = repository.sector_ids()
    config = _config(arguments)
    store = LocalModelStore(arguments.models_dir)
    try:
        examples = read_training_set(path, sector_ids=sector_ids)
        plan = plan_training(
            examples=examples,
            training_set=TrainingSetInfo(path.stem, file_version(path)),
            sector_ids=sector_ids,
            test_ids=labelled_ids([Path("data/eval")]),
            texts=PgArticleTextReader(engine),
            store=store,
            config=config,
        )
    except TrainingSetError as error:
        log.error("model_not_trained", reason=str(error))
        raise SystemExit(1) from error
    _show_plan(plan, config, arguments.models_dir)
    if arguments.dry_run:
        print("\nDry run: nothing trained, nothing stored.")
        return
    print("\nTraining. SetFit's own progress follows; stop with Ctrl+C, nothing is stored then.\n")
    card = fit_model(
        plan,
        trainer=SetFitModelTrainer(),
        store=store,
        config=config,
        threshold=DEFAULT_THRESHOLD,
        now=lambda: datetime.now(UTC),
        timer=time.perf_counter,
    )
    _show_result(card, arguments.models_dir)


def _show_plan(plan: TrainingPlan, config: TrainingConfig, models_dir: Path) -> None:
    """What the author reads before the run starts, as the TFM's training prints its setup."""
    described = plan.description
    pairs = count_pairs(plan.texts, plan.targets, config)
    steps = -(-pairs // config.batch_size)
    print(f"Model        : {models_dir / plan.name}")
    print(
        f"Training set : {described['name']} ({described['size']} examples; "
        f"strata {described['per_stratum']}; {described['unsure']} unsure; "
        f"{described['no_label']} with no label)"
    )
    positives = [sum(row[i] for row in plan.targets) for i in range(len(plan.labels))]
    print(
        "Per label    : "
        + " | ".join(f"{label} {n}" for label, n in zip(plan.labels, positives, strict=True))
    )
    print(f"Encoder      : {config.encoder}")
    print(f"Device       : {device_name()}")
    print(
        f"Settings     : seed {config.seed}, epochs {config.num_epochs}, "
        f"batch {config.batch_size}, learning rate {config.body_learning_rate}, "
        f"iterations {config.num_iterations}"
    )
    print(f"Work         : {pairs:,} sentence pairs = {steps:,} steps of {config.batch_size}")
    print(
        "Time         : about 9 s per step on the author's Mac (measured 2026-10-15), "
        f"so about {_duration(steps * 8.6)}; the bar below gives the live estimate"
    )


def _show_result(card: ModelCard, models_dir: Path) -> None:
    print(f"\nTrained in {_duration(card.training_seconds)}.")
    print(f"Version : {card.model_version}")
    print(f"Model   : {models_dir / card.name}")
    print(f"Card    : {models_dir / card.name / 'model-card.json'}")


def _duration(seconds: float) -> str:
    """ "2h 24m 05s", "3m 40s", "18s": how long, as a person reads it."""
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def _config(arguments: argparse.Namespace) -> TrainingConfig:
    config = TrainingConfig(encoder=arguments.encoder, seed=arguments.seed)
    if arguments.num_iterations is None:
        return config
    return replace(config, num_iterations=arguments.num_iterations)


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
