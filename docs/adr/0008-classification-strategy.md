# ADR-0008: Classification with rules, embeddings and an own model from the start; no LLM

- **Status:** Proposed
- **Date:** 2026-10-13 (revised 2026-10-13 after the sources audit)
- **Phase:** news-live

## Context

Every article must be assigned communities, sectors and government levels
(`docs/labelling-guide.md`), and articles must be grouped by story. The author worries
about the impartiality and consistency of a generative model, and has experience with
transfer learning.

The first draft chose a hybrid: an LLM proposes labels, the author validates them, and an
own model replaces the LLM later. The sources audit changed two facts:

- **7 of the 14 outlets may not be sent to an external LLM**: El Mundo, El País, ABC,
  El Confidencial, La Razón, La Vanguardia and Canarias7 block AI crawlers in their
  `robots.txt` (`data/news/README.md`). With the hybrid, half of the outlets would be
  labelled with proposals and half without: two paths, and possibly different quality
  per outlet.
- **3Cat publishes in Catalan**: any model must handle Catalan as well as Spanish
  (RoBERTa-BNE, for instance, is Spanish only).

## Options considered

### Option A — Rules, embeddings and an own model from the start (chosen)
Rules and dictionaries for communities and actors; embeddings from a fixed multilingual
model for similarity; the author labels a training set by hand, with no proposals; an own
multilingual classifier (for example SetFit on a multilingual sentence encoder, or a
fine-tuned XLM-R; chosen in `news-live`) is trained on it.
- Pros: one path for every outlet; deterministic and auditable; no external provider,
  key or per-article cost; no text leaves the machine.
- Cons: slower start: a training set must be labelled by hand before the model exists.

### Option B — Hybrid: LLM proposes, author validates, own model later
- Pros: faster start for the outlets that allow it.
- Cons: impossible for half of the outlets, so two labelling paths; proposals can bias
  the validator.

### Option C — Generative model for everything
- Pros: fastest to build.
- Cons: least consistent, hardest to audit, and still excluded for half of the outlets.

### Option D — Web search for related news
- Pros: finds articles we lack.
- Cons: Google's custom search API is closed to new customers and ends on 2027-01-01;
  ranking is opaque and not reproducible.

## Decision

Option A. The author labels without proposals for every outlet, and the project focuses
on its own model from the start; no LLM takes part in classification.

In the author's words: to keep the same criterion for everything and, as far as
possible, no black boxes inside the system.

## Consequences

- What gets easier: the same treatment for every outlet; reproducible labels (stored
  with `model_id`); no LLM cost or API key for classification; Catalan handled by the
  model choice, not by a provider.
- What gets harder / what we accept: a hand-labelled training set (size measured in
  `news-live`, separate from the blind test set, which is never used for training); the
  first live labels arrive later.
- Still open, decided in `news-live`: whether, once a first model exists, its proposals
  are shown while labelling more training data. If they are, it applies to every outlet
  alike, and never to the blind test set.
- The `external_llm_allowed` flag stays: it governs any later LLM use (for example story
  summaries, pending ADR).
- What would make us revisit this: the acceptance criteria of the own model (minimum
  score on test set v1, overall and per outlet and per party) are set in `news-live`,
  before training.

## Verification

- Verified 2026-10-13: the AI-crawler blocks of the 7 outlets (`docs/sources-audit.md`,
  section 7); 3Cat publishes in Catalan.
- UNVERIFIED: the training-set size needed for an acceptable model; measured in
  `news-live`.
