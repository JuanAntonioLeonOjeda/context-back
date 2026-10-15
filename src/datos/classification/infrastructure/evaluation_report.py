"""The report of one evaluation run on the blind test set, kept in git (ADR-0016, D18).

Every run writes a new file and never overwrites one: how many times the test set was looked at,
and with which model, is on record. The file holds numbers, ids and versions, never a headline.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from datos.classification.domain.bootstrap import Interval
from datos.classification.domain.promotion import FamilyVerdict

REPORTS_DIR = Path("data/eval/reports")


@dataclass(frozen=True, slots=True)
class RunInfo:
    test_set: Mapping[str, object]  # name, file hash, size
    rules_version: str
    model: Mapping[str, object]  # name and version of the candidate, from its card
    seed: int
    run_at: datetime  # with its zone


def report(info: RunInfo, family_verdicts: tuple[FamilyVerdict, ...]) -> dict[str, object]:
    return {
        "run_at": info.run_at.isoformat(),
        "test_set": dict(info.test_set),
        "rules_version": info.rules_version,
        "model": dict(info.model),
        "seed": info.seed,
        "families": [_family(v) for v in family_verdicts],
    }


def write_report(
    directory: Path, info: RunInfo, family_verdicts: tuple[FamilyVerdict, ...]
) -> Path:
    """`<run time>-<model version>.json`; refuses to replace a report that exists."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = info.run_at.strftime("%Y%m%dT%H%M%S%z")
    path = directory / f"{stamp}-{info.model.get('version', 'unknown')}.json"
    with path.open("x", encoding="utf-8") as file:  # "x": fails if the file exists
        json.dump(report(info, family_verdicts), file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    return path


def _family(verdict: FamilyVerdict) -> dict[str, object]:
    gain = verdict.gain
    return {
        "family": verdict.family,
        "promoted": verdict.promoted,
        "criterion_1_overall": {
            "articles": gain.articles,
            "rules_macro_f1": gain.rules_macro_f1,
            "candidate_macro_f1": gain.candidate_macro_f1,
            "gain": gain.gain,
            "interval_95": _interval(gain.interval),
            "passes": gain.passes,
        },
        "criterion_2_outlets": {
            "passes": verdict.outlets.passes,
            "outlets": [
                {
                    "outlet_id": o.outlet_id,
                    "articles": o.articles,
                    "rules_right": o.rules_right,
                    "candidate_right": o.candidate_right,
                    "difference": o.difference,
                }
                for o in verdict.outlets.outlets
            ],
        },
    }


def _interval(interval: Interval | None) -> dict[str, object] | None:
    if interval is None:
        return None
    return {"low": interval.low, "high": interval.high, "resamples": interval.resamples}
