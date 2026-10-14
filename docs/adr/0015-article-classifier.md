# ADR-0015: One classifier port, rules as data, classifications append-only

- **Status:** Proposed
- **Date:** 2026-10-14
- **Phase:** news-live

## Context

Every article needs its communities, sectors and the government levels it names (the labels of
`docs/labelling-guide.md`). ADR-0008 decided the source of those labels: rules first, then the
author's own model, never an LLM. This ADR decides how they fit in the code and in the database,
so that the rules and the model can be swapped and compared, and so that every label shown can be
traced to what produced it.

## Options considered

### How classifiers plug in
- **A — one port, `ArticleClassifier`** (chosen): `classify(headline, lead) -> labels`, with a
  `model_id` and a `model_version`; rules and model are adapters; one contract test suite runs on
  both.
  - Pros: the use cases, the API and the evaluation do not change when the model arrives; rules and
    model are measured with the same code.
  - Cons: the port must fit both a dictionary and a neural model (labels plus a score).
- **B — the rules inside the use case, the model added later.** Cons: two paths, two evaluations.

### Where the rules live
- **A — data files** (chosen): `data/classification/*.csv` (places, levels, sectors, exclusions),
  read and validated at startup.
  - Pros: a new term is a row (open/closed); the author reviews the terms without reading code;
    the rules' version is the hash of the files, so a changed term changes the version.
  - Cons: matching conventions (case, longest match) must be documented next to the data.
- **B — terms in Python.** Cons: every review is a code review; the version is a manual number.

### How results are stored
- **A — append-only `classifications`** (chosen), one row per article and classifier version,
  never updated, as observations (ADR-0012).
  - Pros: the rules' and the model's labels of the same article sit side by side; a new version
    adds rows and keeps the old ones for comparison.
  - Cons: the current label needs a rule: the one of the active classifier.
- **B — labels as columns of `articles`.** Cons: each new classifier overwrites the previous one.

## Decision

Option A in the three questions. The `ArticleClassifier` port has two adapters (`RulesClassifier`
now, `SetFitClassifier` in November). The rules are data files with documented matching
conventions; their version is a hash of the files. Classifications are append-only with their
classifier id and version; the API uses the active classifier's rows. The outlet is never an input
of any classifier, and no rule names a party or a politician.

## Consequences

- What gets easier: comparing rules and model on the blind test set with one evaluation; adding a
  term; tracing any label to the classifier and version that produced it.
- What gets harder / what we accept: storing a row per article and version; choosing the active
  classifier in configuration.
- What would make us revisit this: labels that need context beyond headline and lead, or a model
  that labels in a shape the port cannot express.

## Verification

- Contract tests run the same suite on every adapter (task 6 of `specs/news-live/tasks.md`).
- Coverage of the rules on 2026-10-14: `data/classification/README.md` (not an evaluation).
