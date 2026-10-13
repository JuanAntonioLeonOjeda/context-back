# ADR-0008: Classification: rules and embeddings, LLM proposes, author validates, own model later

- **Status:** Proposed
- **Date:** 2026-10-13
- **Phase:** news-live

> Draft written from the design conversation; the author reviews and rewrites the
> reasoning before it is Accepted.

## Context

News must be assigned to a community, a sector and a government level, and grouped by story. The author worries about the impartiality and consistency of a generative model, and has experience with transfer learning.

## Options considered

### Option A — Hybrid with human validation, own model later (chosen)
Rules and dictionaries for community and actors; embeddings with a fixed model for similarity; an LLM proposes sector and level; the author validates; validated labels train an own classifier (SetFit or a Spanish RoBERTa) that replaces the LLM if it matches it on the blind test set.
- Pros: Starts quickly; every label is validated; ends with a deterministic, auditable model.
- Cons: The LLM's proposals can bias the validator; a classifier port is needed.

### Option B — Own model from the start
Hand-label first, train, then run.
- Pros: Deterministic from day one.
- Cons: Slow to start.

### Option C — Generative model for everything
LLM labels and links.
- Pros: Fastest to build.
- Cons: Least consistent and hardest to audit.

### Option D — Web search for related news
Search engine API to find related articles.
- Pros: Finds articles we lack.
- Cons: Google's custom search API is closed to new customers and ends on 2027-01-01; ranking is opaque and not reproducible.

## Decision

Hybrid with the author validating the labels, to start faster; the validated labels become the training set for an own model. The author first chose the own model from the start and then switched for speed.

## Consequences

- What gets easier: quick start; the LLM stays behind a port and is replaceable.
- What gets harder / what we accept: the 200-article test set must be labelled blind before seeing any proposal; metrics per outlet and per party.
- What would make us revisit this: when 500–1,000 validated labels exist

## Verification

Cost estimates (LLM under 40 EUR/month live, 40–80 EUR one-off for the history) are rough and must be measured on a sample in `foundation`.
