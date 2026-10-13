# ADR-0005: Responsible party from competences and government in force

- **Status:** Accepted
- **Date:** 2026-10-13
- **Phase:** foundation

## Context

Every piece of news must say which party is responsible for what it describes. Competences are split between the State, the regions and the town councils, and are shared in sectors such as housing. A wrong attribution is the fastest way to lose credibility.

## Options considered

### Option A — Competence rule plus extraction (chosen)
The model (or rules) only detects the government level and the actor mentioned; the party is derived from the competence table and the government in force on the article date.
- Pros: Consistent and auditable; handles shared competences; testable with plain unit tests.
- Cons: A competence table to maintain per sector.

### Option B — LLM only
Ask the model who is responsible.
- Pros: No maintenance.
- Cons: Inconsistent; hard to audit.

### Option C — Manual
A person assigns it.
- Pros: Most reliable.
- Cons: Does not scale.

## Decision

Competence rule plus extraction, with the confidence visible. The attribution has to be explainable to a reader: level, competence, government.

## Consequences

- What gets easier: every attribution can be explained and tested.
- What gets harder / what we accept: the competence table and the government dataset are curated data with cited sources.
- What would make us revisit this: if shared competences make the rule too coarse

## Rules verified while building the dataset

- A territory can override the general rows of an activity: in Ceuta and Melilla public
  education and health care are managed by the State (Ministry of Education, INGESA), so
  their own competence rows replace the general regional ones (`applicable_competences`).
- The government in force includes caretaker periods: from election day, or from the
  date the president otherwise ceases, until the new appointment is published in the BOE.
- Only parties in government are responsible. External support at the investiture is
  recorded, but it is not government and is never attributed.

## Verification

Verified in `foundation`: competences and governments since 2020 in `data/governments/`,
every row with its source (BOE, statutes, parliamentary records); rules in
`data/governments/README.md` and `specs/foundation/plan.md`.
