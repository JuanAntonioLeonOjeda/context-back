# ADR-0022: The promoted model classifies on the author's machine, on a schedule

- **Status:** Proposed (the author chose option A on 2026-10-27; the reasoning is theirs to confirm)
- **Date:** 2026-10-27
- **Phase:** news-live (left open by ADR-0016, "where the model classifies once promoted")

## Context

The evaluation of 2026-10-26 promoted the own model for the sector family (rules 0.524, model 0.584
macro-F1 on the random half, interval -5.6 to +22.2, so the gain is not statistically established) and
kept the rules for government levels. Until now nothing used it: `classify-new` loaded only the rules
and the API read `ACTIVE_CLASSIFIER_ID = rules`.

Constraints that shape it:

- **`torch` never goes in the API image** (ADR-0016), and the collector shares that image.
- **Classifications are append-only** (ADR-0015): a classifier version adds rows and never changes
  old ones, so the classifier can be switched back by configuration.
- **The API shows only what the active classifier has classified.** An article the model has not seen
  yet is missing from the lists until it does.

## Options considered

- **A. On the author's machine, scheduled** (chosen): a command and a launchd agent. No image
  changes; the cost is that it only runs while the Mac is awake and is a second scheduler beside the
  collector.
- **B. A separate Docker service with `torch`:** automatic, but a multi-gigabyte image, CPU inference
  not measured, and the weights mounted as a volume.
- **C. Inside the collector image:** simplest to wire, and breaks ADR-0016's boundary for an image the
  API shares.

## Decision

Option A. `classify-new --model DIR` builds a composite classifier: the model gives the promoted
families (`sectors` by default) and the rules give communities and levels; rows are stored as
`composite`, beside the rules' rows. `scripts/classify-with-model.sh` runs it every hour through
launchd (`scripts/launchd/es.datos.classify-with-model.plist`), and the API reads `composite` through
`ACTIVE_CLASSIFIER_ID`.

## Consequences

- What gets easier: no image changes; the model, its weights and the `ml` group stay on one machine;
  returning to the rules is one variable.
- What we accept: articles collected while the Mac is off or asleep do not show until the next run;
  the displayed sectors come from a model whose gain over the rules is not yet established.
- What would make us revisit this: a deployment host (ADR-0017) instead of the author's Mac, which
  asks for option B; labelled data that changes which families are promoted.

## Verification

The first run over every stored article and its time are in the commit that adds the command. Tests:
a unit test of the promoted composite (sectors from the model, communities and levels from the rules,
the version naming both).
