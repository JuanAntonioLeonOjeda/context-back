# ADR-0014: Attribution computed on read, with a three-value confidence

- **Status:** Accepted
- **Date:** 2026-10-14
- **Phase:** news-live

## Context

ADR-0005 decided how the responsible party is found: the classifier detects the government
levels an article names, and the party comes from the competence table and the government in
force on the article's date. This ADR decides how that rule runs and what it says when it is
unsure.

Two facts shape it. The curated data it reads is corrected from time to time (a government term,
a competence row), and an attribution must follow the correction. And the competence table is per
activity (curriculum, schools, waiting lists), while the classifier gives the sector: at sector
level every function is shared, the execution in education, health and housing being state,
regional and local at once, also in Ceuta and Melilla (checked on `data/governments/competences.csv`,
2026-10-14).

## Options considered

### When it runs
- **A — computed on read** (chosen): a pure function of the stored classification, the
  competence table and the governments dataset, run when the API answers.
  - Pros: always consistent with the current curated data; nothing to recompute or migrate after a
    correction; testable as a pure function.
  - Cons: computed on every request (a page shows tens of articles: cheap).
- **B — stored when the article is classified.**
  - Cons: a correction of a term or a competence leaves every stored attribution wrong until a
    recomputation someone has to remember.

### What "not sure" looks like
- **A — a three-value confidence with a reason** (chosen): high, medium, not determined.
- **B — a numeric score.** Cons: a number suggests a precision the rule does not have, and the web
  would have to explain thresholds.

### What happens when the article names no government (D6)
- **A — not determined** (chosen): no level named means no attribution, because the sector's
  competences are shared by several levels.
- **B — classify the activity too**, which often has one executing level. Cons: a finer label, a
  new labelling guide and more training labels.
- **C — a curated "managing level" per sector** (the community for education and health; the
  State in Ceuta and Melilla). Cons: an editorial choice applied to every article that names no
  one.

## Decision

The attribution is computed on read, by one pure rule, with this scale:

- **High:** the article names a government level, and that level holds at least one competence
  of the sector in that community (the per-territory rows applied). The responsible parties are
  that government's governing parties on the article's date.
- **Medium:** unused for now. It is reserved for a later phase that adds option B or C.
- **Not determined**, always with its reason: the article names no level (the sector's
  competences are shared by several levels); it names a level with no competence in the sector;
  the level is local (not modelled yet); or there is no government in the dataset on that date.

Parties that only supported an investiture are never responsible. The classification, which is
costly and comes from versioned models, is stored; the attribution is not.

In the author's words (2026-10-14): show it as not determined rather than hide it, and keep the
rule strict until the project can tell which level runs a service.

## Consequences

- What gets easier: a correction of the curated data is reflected at once; the rule is one
  function with one test per case; the web shows the reason, so a reader sees why a piece of news
  has no responsible party.
- What gets harder / what we accept: many articles will be not determined while the classifier
  rarely detects the level; that share is measured on the blind test set.
- What would make us revisit this: the share of not determined on the test set, or a phase that
  classifies the activity or curates a managing level (then "medium" is used).

## Verification

- Shared functions per sector: summary of `data/governments/competences.csv` on 2026-10-14 (every
  function of the three sectors is held by more than one level, in every community).
- The rule's cases: unit tests of task 3 of `specs/news-live/tasks.md`.
