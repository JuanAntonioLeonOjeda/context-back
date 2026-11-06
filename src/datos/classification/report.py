"""How the training commands write to the terminal: plain text for the author to read."""

from collections.abc import Sequence

from datos.classification.domain.bootstrap import Interval
from datos.classification.domain.learning_curve import (
    MIN_RISE,
    RISE_FROM_SIZE,
    RISE_TO_SIZE,
    ScoredPoint,
    label_more,
    rise_verdicts,
    summarise,
)
from datos.classification.domain.metrics import FamilyScore
from datos.classification.domain.promotion import MAX_OUTLET_LOSS, MIN_GAIN, FamilyVerdict


def duration(seconds: float) -> str:
    """ "2h 24m 05s", "3m 40s", "18s": how long, as a person reads it."""
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def _f1(value: float | None) -> str:
    return "  -  " if value is None else f"{value:.3f}"


def format_point(point: ScoredPoint, training_seconds: float) -> str:
    """One line per point: fold, size, time and each family's macro-F1 with its labels."""
    families = " | ".join(_family(score) for score in point.scores)
    return (
        f"fold {point.fold} · {point.size} examples · trained in {duration(training_seconds)} · "
        f"{families}"
    )


def _family(score: FamilyScore) -> str:
    labels = ", ".join(f"{b.label.split(':', 1)[1]} {_f1(b.f1).strip()}" for b in score.labels)
    return f"{score.family} {_f1(score.macro_f1).strip()} ({labels})"


def format_summary(points: Sequence[ScoredPoint]) -> str:
    """The curve as a table per family, and the rule of D12 applied to it."""
    lines: list[str] = []
    summary = summarise(points)
    for family in dict.fromkeys(s.family for s in summary):
        lines.append(f"\n{family}")
        lines.append("  examples   mean   per fold")
        for s in (s for s in summary if s.family == family):
            folds = ", ".join(f"{v:.3f}" for v in s.fold_scores)
            lines.append(f"  {s.size:>8}  {_f1(s.mean_macro_f1)}   {folds}")
    verdicts = rise_verdicts(points)
    lines.append(
        f"\nRule (D12): label 100 more if the mean macro-F1 rises at least {MIN_RISE * 100:.0f} "
        f"points from {RISE_FROM_SIZE} to {RISE_TO_SIZE}, in either family."
    )
    for v in verdicts:
        if v.rise is None:
            lines.append(f"  {v.family}: cannot be told, no fold has both sizes")
            continue
        answer = "yes" if v.still_rises else "no"
        lines.append(
            f"  {v.family}: {v.rise * 100:+.1f} points over {v.folds} fold(s): rises? {answer}"
        )
    decision = label_more(verdicts)
    lines.append(
        "Decision: "
        + (
            "label 100 more"
            if decision
            else "cannot be told yet"
            if decision is None
            else "no more labels needed by this rule"
        )
    )
    return "\n".join(lines)


def format_verdicts(family_verdicts: Sequence[FamilyVerdict]) -> str:
    """Per family: the decision, criterion 1 with its interval, and every outlet left behind."""
    lines: list[str] = []
    for v in family_verdicts:
        gain = v.gain
        lines.append(
            f"\n{v.family}: "
            + ("PROMOTED, the model takes it" if v.promoted else "stays with the rules")
        )
        interval = "" if gain.interval is None else f" (95 % interval {_points(gain.interval)})"
        change = "cannot be computed" if gain.gain is None else f"{gain.gain * 100:+.1f} points"
        lines.append(
            f"  1. Overall, random half ({gain.articles} articles):"
            f" rules {_f1(gain.rules_macro_f1)}, model {_f1(gain.candidate_macro_f1)},"
            f" {change}{interval}:"
            f" {'passes' if gain.passes else 'fails'} (needs +{MIN_GAIN * 100:.0f})"
        )
        behind = [o for o in v.outlets.outlets if o.difference < -MAX_OUTLET_LOSS]
        lines.append(
            f"  2. Outlets ({len(v.outlets.outlets)}): "
            + ("passes" if v.outlets.passes else "fails")
            + f" (none more than {MAX_OUTLET_LOSS} articles worse)"
        )
        lines.extend(
            f"     {o.outlet_id}: {o.candidate_right} vs {o.rules_right} of {o.articles} right"
            for o in behind
        )
    return "\n".join(lines)


def _points(interval: Interval) -> str:
    return f"{interval.low * 100:+.1f} to {interval.high * 100:+.1f}"
