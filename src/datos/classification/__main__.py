"""Command line: uv run python -m datos.classification <command>

- `classify-new [--rules-dir PATH] [--model DIR [--promote FAMILY ...]]`: classifies the articles
  the classifier has not seen yet (a new version of the rules, that is, any change in
  data/classification/, classifies everything again). Run it after each collection. With `--model`
  the own model (needs the `ml` group, so it runs on the author's machine) takes the promoted
  families (`sectors` by default, as the evaluation of 2026-10-26 decided) and the rules the rest;
  the result is stored as the `composite` classifier, beside the rules' rows, which stay.
- `sample --set train|eval --name NAME --size N --seed S --until ISO-DATETIME [--dry-run]`: draws a
  sample for hand labelling (data/sampling/README.md). Refuses to overwrite a sample: a sample is
  frozen, a new one gets a new name.
- `train --training-set PATH --seed S [--encoder NAME] [--models-dir PATH]`: trains the own model on
  the hand-labelled training set (needs the `ml` group: `uv run --group ml ...`). Refuses a set that
  shares an article with the blind test set, and never overwrites a model.
- `export-labels --set train|eval --sample NAME --export PATH [--name NAME]`: turns Label Studio's
  JSON export into the labelled set (`data/train/train-set-v1.jsonl` or
  `data/eval/test-set-v1.jsonl`): ids and labels only. Names the articles not answered yet and
  refuses anything outside the sample or the vocabulary.
- `evaluate --model DIR [--test-set PATH] [--seed S]`: the own model against the rules on the blind
  test set, per family (ADR-0016, task 18). Labels in memory, stores nothing in the database, and
  writes a new report in `data/eval/reports/` every run (D18).
- `learning-curve --seed S [--training-set PATH] [--run-folds 0 1] [--dry-run]`: the learning curve
  inside the training set (ADR-0016, D11 and D12). Writes each point as it ends and carries on from
  the file if run again.
"""

import argparse
import json
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import structlog
from sqlalchemy import Engine

from datos.classification.application.classifier import ArticleClassifier
from datos.classification.application.composite_classifier import Family, promoted_classifier
from datos.classification.application.evaluate_model import evaluate_model
from datos.classification.application.learning_curve import (
    CurvePlan,
    CurvePoint,
    CurveSettings,
    plan_curve,
    run_curve,
)
from datos.classification.application.sample_for_labelling import Sample, sample_for_labelling
from datos.classification.application.store_classifications import classify_new
from datos.classification.application.train_model import (
    CARD_FILE,
    ModelCard,
    TrainingConfig,
    TrainingPlan,
    TrainingSetInfo,
    fit_model,
    plan_training,
)
from datos.classification.domain.labelled_export import Assembly, assemble
from datos.classification.domain.training_set import TrainingSetError
from datos.classification.infrastructure.curve_file import JsonlCurveStore
from datos.classification.infrastructure.evaluation_report import (
    REPORTS_DIR,
    RunInfo,
    write_report,
)
from datos.classification.infrastructure.label_studio_export import read_label_studio_export
from datos.classification.infrastructure.labelled_set_file import (
    read_sample_strata,
    write_labelled_set,
)
from datos.classification.infrastructure.local_model_store import LocalModelStore
from datos.classification.infrastructure.pg_article_outlet_reader import PgArticleOutletReader
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
from datos.classification.infrastructure.setfit_classifier import (
    DEFAULT_THRESHOLD,
    SetFitClassifier,
)
from datos.classification.infrastructure.setfit_predictor import SetFitPredictor
from datos.classification.infrastructure.setfit_trainer import (
    SetFitModelTrainer,
    count_pairs,
    device_name,
)
from datos.classification.infrastructure.tag_stoplist_file import tag_stoplist_version
from datos.classification.infrastructure.training_set_file import read_training_set
from datos.classification.report import (
    duration,
    format_point,
    format_summary,
    format_verdicts,
)
from datos.config import load_settings
from datos.db import build_engine
from datos.log_setup import configure_logging

DEFAULT_RULES_DIR = Path("data/classification")
DEFAULT_TERMS = Path("data/sampling/enrichment-terms.csv")
DEFAULT_TRAINING_SET = Path("data/train/train-set-v1.jsonl")
DEFAULT_TEST_SET = Path("data/eval/test-set-v1.jsonl")
DEFAULT_ENCODER = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"  # ADR-0016
MODELS_DIR = Path("models")
SET_DIRS = {"train": Path("data/train"), "eval": Path("data/eval")}
TASKS_DIR = Path("var/labelstudio")
# D11: 4 folds, 2 of them measured, subsets of 100, 200 and 300 (ADR-0016).
CURVE_FOLDS = 4
CURVE_RUN_FOLDS = (0, 1)
CURVE_SIZES = (100, 200, 300)
SET_FILE_NAMES = {"train": "train-set-v1", "eval": "test-set-v1"}
SECONDS_PER_STEP = 8.6  # measured on the author's Mac on 2026-10-15 (MPS)

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="datos.classification")
    commands = parser.add_subparsers(dest="command", required=True)
    classify = commands.add_parser("classify-new", help="classify the articles not seen yet")
    classify.add_argument("--rules-dir", type=Path, default=DEFAULT_RULES_DIR)
    classify.add_argument("--model", type=Path, default=None, help="a model directory in models/")
    classify.add_argument(
        "--promote",
        nargs="+",
        choices=[family.value for family in Family],
        default=[Family.SECTORS.value],
        help="the families the model gives (default: sectors); the rules give the rest",
    )
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
    export = commands.add_parser("export-labels", help="Label Studio export → the labelled set")
    export.add_argument("--set", choices=sorted(SET_DIRS), required=True)
    export.add_argument("--sample", required=True, help="the sample the tasks came from")
    export.add_argument("--export", type=Path, required=True, help="Label Studio's JSON export")
    export.add_argument("--name", default=None, help="default: train-set-v1 or test-set-v1")
    evaluate = commands.add_parser("evaluate", help="the own model against the rules, test set")
    evaluate.add_argument("--model", type=Path, required=True, help="a model directory in models/")
    evaluate.add_argument("--test-set", type=Path, default=DEFAULT_TEST_SET)
    evaluate.add_argument("--seed", type=int, default=20261105, help="of the bootstrap intervals")
    curve = commands.add_parser(
        "learning-curve", help="the learning curve inside the training set (folds, 3 sizes)"
    )
    curve.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    curve.add_argument("--seed", type=int, required=True)
    curve.add_argument("--encoder", default=DEFAULT_ENCODER)
    curve.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    curve.add_argument("--folds", type=int, default=CURVE_FOLDS)
    curve.add_argument(
        "--run-folds", type=int, nargs="+", default=list(CURVE_RUN_FOLDS), help="folds to measure"
    )
    curve.add_argument("--sizes", type=int, nargs="+", default=list(CURVE_SIZES))
    curve.add_argument("--num-iterations", type=int, default=None)
    curve.add_argument("--dry-run", action="store_true", help="show the plan and stop")
    arguments = parser.parse_args()

    settings = load_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)
    engine = build_engine(str(settings.database_url))
    repository = PgClassificationRepository(engine)
    if arguments.command == "sample":
        _sample(arguments, repository, PgCandidateReader(engine), PgArticleTextReader(engine))
        return
    if arguments.command == "train":
        _train(arguments, repository, engine)
        return
    if arguments.command == "export-labels":
        _export_labels(arguments, repository)
        return
    if arguments.command == "evaluate":
        _evaluate(arguments, repository, engine)
        return
    if arguments.command == "learning-curve":
        _learning_curve(arguments, repository, engine)
        return
    try:
        sector_ids = repository.sector_ids()
        classifier: ArticleClassifier = load_rules_classifier(
            arguments.rules_dir, sector_ids=sector_ids
        )
        if arguments.model is not None:
            classifier = promoted_classifier(
                classifier,
                _load_model(arguments.model, sector_ids),
                [Family(name) for name in arguments.promote],
            )
    except (InvalidRulesFileError, FileNotFoundError) as error:
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
            tag_stoplist=tag_stoplist_version(),
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


def _export_labels(arguments: argparse.Namespace, repository: PgClassificationRepository) -> None:
    out_dir: Path = SET_DIRS[arguments.set]
    name = arguments.name or SET_FILE_NAMES[arguments.set]
    try:
        strata = read_sample_strata(out_dir / f"{arguments.sample}.jsonl")
        assembly = assemble(
            read_label_studio_export(arguments.export),
            strata,
            sector_ids=repository.sector_ids(),
        )
    except TrainingSetError as error:
        log.error("labels_not_exported", reason=str(error))
        raise SystemExit(1) from error
    target = out_dir / f"{name}.jsonl"
    replaced = target.exists()
    write_labelled_set(target, assembly.rows)
    _show_export(assembly, len(strata), target, replaced=replaced)


def _show_export(assembly: Assembly, sample_size: int, target: Path, *, replaced: bool) -> None:
    rows = assembly.rows
    print(f"Answered     : {len(rows)} of {sample_size} in the sample")
    print(f"Not answered : {len(assembly.unlabelled)} skipped or still to do in the tool")
    print(f"Not in tool  : {len(assembly.not_in_tool)} of the sample were never imported")
    print(f"Unsure       : {sum(r.unsure for r in rows)}")
    print(f"No label     : {sum(not (r.sectors or r.government_levels) for r in rows)}")
    print(f"Written      : {target}{' (replaced)' if replaced else ''}")


def _load_model(model_dir: Path, sector_ids: frozenset[str]) -> SetFitClassifier:
    """The trained model of a directory, as a classifier of sectors and levels."""
    card = json.loads((model_dir / CARD_FILE).read_text(encoding="utf-8"))
    return SetFitClassifier(
        SetFitPredictor.load(model_dir),
        model_version=card["model_version"],
        sector_ids=sector_ids,
        threshold=card["threshold"],
    )


def _evaluate(
    arguments: argparse.Namespace, repository: PgClassificationRepository, engine: Engine
) -> None:
    model_dir: Path = arguments.model
    test_set: Path = arguments.test_set
    sector_ids = repository.sector_ids()
    try:
        card = json.loads((model_dir / CARD_FILE).read_text(encoding="utf-8"))
        rules = load_rules_classifier(DEFAULT_RULES_DIR, sector_ids=sector_ids)
        candidate = _load_model(model_dir, sector_ids)
        examples = read_training_set(test_set, sector_ids=sector_ids)
        family_verdicts = evaluate_model(
            examples,
            sector_ids=sector_ids,
            texts=PgArticleTextReader(engine),
            outlets=PgArticleOutletReader(engine),
            rules=rules,
            candidate=candidate,
            seed=arguments.seed,
        )
    except (TrainingSetError, InvalidRulesFileError, FileNotFoundError) as error:
        log.error("model_not_evaluated", reason=str(error))
        raise SystemExit(1) from error
    info = RunInfo(
        test_set={
            "name": test_set.stem,
            "file_hash": file_version(test_set),
            "size": len(examples),
        },
        rules_version=rules.model_version,
        tag_stoplist=tag_stoplist_version(),
        model={"name": card["name"], "version": card["model_version"]},
        seed=arguments.seed,
        run_at=datetime.now(UTC),
    )
    path = write_report(REPORTS_DIR, info, family_verdicts)
    print(f"Model    : {card['name']} ({card['model_version']})")
    print(f"Rules    : {rules.model_version}")
    print(f"Test set : {test_set} ({len(examples)} articles)")
    print(format_verdicts(family_verdicts))
    print(f"\nReport   : {path} (one per run, never replaced)")


def _learning_curve(
    arguments: argparse.Namespace, repository: PgClassificationRepository, engine: Engine
) -> None:
    path: Path = arguments.training_set
    sector_ids = repository.sector_ids()
    config = _config(arguments)
    settings = CurveSettings(
        training_set=TrainingSetInfo(path.stem, file_version(path)),
        config=config,
        folds=arguments.folds,
        threshold=DEFAULT_THRESHOLD,
        tag_stoplist=tag_stoplist_version(),
    )
    results = (
        arguments.models_dir / f"{path.stem}-{_encoder_name(config)}-seed{config.seed}-curve.jsonl"
    )
    store = JsonlCurveStore(results)
    try:
        plan = plan_curve(
            examples=read_training_set(path, sector_ids=sector_ids),
            settings=settings,
            run_folds=arguments.run_folds,
            sizes=arguments.sizes,
            sector_ids=sector_ids,
            test_ids=labelled_ids([Path("data/eval")]),
            texts=PgArticleTextReader(engine),
            store=store,
        )
    except TrainingSetError as error:
        log.error("curve_not_measured", reason=str(error))
        raise SystemExit(1) from error
    _show_curve_plan(plan, settings, results)
    if arguments.dry_run:
        print("\nDry run: nothing trained, nothing stored.")
        return
    if plan.pending:
        print("\nMeasuring. Each point is stored when it ends; Ctrl+C keeps the ones done.\n")
        run_curve(
            plan,
            trainer=SetFitModelTrainer(),
            store=store,
            settings=settings,
            timer=time.perf_counter,
            on_point=_show_point,
        )
    print(format_summary(store.points()))


def _encoder_name(config: TrainingConfig) -> str:
    return config.encoder.rsplit("/", 1)[-1]


def _show_curve_plan(plan: CurvePlan, settings: CurveSettings, results: Path) -> None:
    """What the author reads before an overnight run: the work left and how long it takes."""
    config = settings.config
    pairs = [count_pairs(*plan.training_inputs(split), config) for split in plan.pending]
    steps = sum(-(-n // config.batch_size) for n in pairs)
    print(f"Results      : {results}")
    print(f"Encoder      : {config.encoder}")
    print(f"Device       : {device_name()}")
    print(
        f"Settings     : seed {config.seed}, {settings.folds} folds, "
        f"threshold {settings.threshold}, iterations {config.num_iterations}"
    )
    print(f"Measured     : {len(plan.done)} points already in the file")
    print(
        f"To measure   : {len(plan.pending)} points, {sum(pairs):,} sentence pairs, {steps:,} steps"
    )
    print(
        f"Time         : about {duration(steps * SECONDS_PER_STEP)} at {SECONDS_PER_STEP} s per "
        "step, measured on the author's Mac (2026-10-15)"
    )


def _show_point(point: CurvePoint) -> None:
    print(format_point(point, point.training_seconds), flush=True)


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
        f"so about {duration(steps * SECONDS_PER_STEP)}; the bar below gives the live estimate"
    )


def _show_result(card: ModelCard, models_dir: Path) -> None:
    print(f"\nTrained in {duration(card.training_seconds)}.")
    print(f"Version : {card.model_version}")
    print(f"Model   : {models_dir / card.name}")
    print(f"Card    : {models_dir / card.name / 'model-card.json'}")


def _config(arguments: argparse.Namespace) -> TrainingConfig:
    config = TrainingConfig(encoder=arguments.encoder, seed=arguments.seed)
    if arguments.num_iterations is None:
        return config
    return replace(config, num_iterations=arguments.num_iterations)


def _sample(
    arguments: argparse.Namespace,
    repository: PgClassificationRepository,
    reader: PgCandidateReader,
    texts: PgArticleTextReader,
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
        tags_by_id={
            i: t.tags for i, t in texts.texts([a.article_id for a in drawn.articles]).items()
        },
        tag_stoplist=tag_stoplist_version(),
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
