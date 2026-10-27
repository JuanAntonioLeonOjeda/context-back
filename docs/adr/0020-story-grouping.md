# ADR-0020: Grouping the articles of the same story with embeddings, a threshold and a window

- **Status:** Proposed (drafted with the measurements below; the author confirms the reasoning)
- **Date:** 2026-10-27
- **Phase:** story-contrast

## Context

The portal lists news one article after another, and several outlets usually cover the same event.
Phase 3 groups the articles that tell the same story so a reader sees every outlet's headline side
by side. A group is a claim, so it must be traceable (project priority: neutrality and traceability
over features) and it must not need an LLM or anything outside the machine.

Constraints that shape it:

- **Only headline and lead are available** (`docs/sources-audit.md`, section 7); no bodies.
- **The same encoder as the classifier** (`paraphrase-multilingual-mpnet-base-v2`, 768 dimensions,
  ADR-0016) already runs on the author's machine; the `ml` group never goes in the API image.
- **No hand-labelled pairs exist yet**, so any threshold is provisional.

## Options considered

### How two articles are judged to be the same story
- **A. Same URL or exact title.** Pros: trivial. Cons: two outlets never share either.
- **B. Keyword overlap (TF-IDF).** Pros: no model. Cons: breaks across Spanish and Catalan and
  across rewordings of the same event.
- **C. Embeddings, cosine similarity above a threshold, inside a time window** (chosen). Pros:
  works across wording and language, cheap to run (17,462 articles in 136 s), explainable by a
  number. Cons: the threshold is a judgement; similar-topic events can score close to same-event ones.
- **D. An LLM as judge.** Pros: reads nuance. Cons: cost, an external dependency, and outlets flagged
  `external_llm_allowed = false` could not be sent.

### How the pairs become groups
- **Connected components of the accepted links** (chosen): deterministic and simple. Known risk:
  chaining (A~B and B~C put A and C together).
- A clustering with a cohesion check: avoids chaining, more machinery. Kept as the next step.

## Decision

Option C with connected components, on the headline and the lead without tags (each outlet writes its
own, so they pull two outlets covering the same event apart). Provisional values: **cosine >= 0.88,
at most 3 days apart, two outlets at least per story**. pgvector computes the similarities in the
database (no new dependency), a pure function decides the groups, and every run is immutable: it
stores the encoder version, the threshold and the window.

## Consequences

- What gets easier: a story is a row with the numbers that made it; the API and the web read them.
- What we accept: **coverage is low** (1,375 of 17,462 articles, 7.9 %, belong to a story) because
  precision was preferred; and the self-join takes about 2 min 50 s without a vector index.
- What would make us revisit this: hand-labelled pairs to set the threshold; chaining in bigger
  groups; a volume that makes the join slow (then an HNSW index or a per-day join).

## Verification

Measured on the real database on 2026-10-26 over 37,774 candidate pairs (similarity >= 0.70):

| Threshold | Stories | Largest | Reading |
|---|---|---|---|
| 0.80-0.82 | about 1,050 | 556 / 120 | chains unrelated events (weather forecasts, campaign news) |
| 0.85 | 766 | 43 | mostly one matter, but already mixes steps of a process |
| 0.88 | 509 | 10 | every group read was one event, with 7-9 outlets |

Pairs between 0.70 and 0.75 were the same topic, not the same event. Tests: unit tests of the
grouping rule (threshold and window edges, order independence, chaining as a documented risk) and
integration tests of the queries against PostgreSQL with pgvector.
