# ADR-0009: Label Studio for labelling

- **Status:** Proposed
- **Date:** 2026-10-13
- **Phase:** foundation

> Draft written from the design conversation; the author reviews and rewrites the
> reasoning before it is Accepted.

## Context

The author labels the blind test set and the training set of the own model (ADR-0008). The tool must support multi-label classification, entities and pairs of texts, and import proposals as pre-annotations.

## Options considered

### Option A — Label Studio, self-hosted (chosen)
Open source, runs with Docker next to PostgreSQL, exports JSON, imports pre-annotations.
- Pros: Covers all label types; validating means accepting or fixing.
- Cons: One more service to maintain.

### Option B — Own screen in the web app
Built for exactly our labels.
- Pros: Tailored.
- Cons: Development time before labelling can start.

### Option C — Spreadsheet
A table.
- Pros: No setup.
- Cons: Fine for sector, not for entities or story pairs.

## Decision

Label Studio. Pre-annotations make validation fast and it needs no development.

## Consequences

- What gets easier: labelling starts in foundation.
- What gets harder / what we accept: another container and an export step.
- What would make us revisit this: if the review flow outgrows it

## Verification

UNVERIFIED: pre-annotation import for the exact label config; checked in `foundation`.
