# ADR-0027: Each news item names the bodies with competence in its topic

- **Status:** Accepted
- **Date:** 2026-11-26
- **Phase:** org-chart (competent bodies)
- **Relates to:** ADR-0018 (complemented, not amended: no news item is attributed to a party),
  ADR-0025 (the organisation charts this reads), ADR-0011 (the competence table)

## Context

ADR-0025 brought back the competences as facts of a body, curated by hand with a source per row, and
left out on purpose the link between a news item and the body that holds the competence: "it would
reopen ADR-0018, it needs its own ADR". The charts now cover the State, Canarias, Madrid and Cataluña,
and every news item already carries, from the active classifier, its communities, its sectors and
(sometimes) its level of government. Joining them answers a question a reader has in front of a
news item: which administration manages this.

Two facts measured on the local database (2026-11-26) shape the rule:

- **The level is often missing.** Of the 1,577 news items of the three pilot communities that have a
  sector, 414 (26 %) have a level of government; the rules give it only when the text names an
  institution.
- **A sector can map to several departments.** The sector tags of the competences were written for the
  chart, not for this join: education in Cataluña reaches four departments, sports among them.

## Options considered

### How a news item reaches a body
- **A — A lookup** (chosen): community, sector and level of the news item against the competences of
  the bodies in force on its publication date. Pros: deterministic; each answer can be explained
  with the article of the law and its link. Cons: as good as the classification and the sector tags.
- **B — Similarity between the text and each competence's summary** (with the stored vectors). Pros:
  finer (it could tell waiting lists from medical colleges). Cons: a threshold to tune, wrong
  matches that are hard to explain, and a model's judgement shown as a fact.

### A news item with no level
- **A — Show nothing.** Never guesses, but three of every four news items would show no body.
- **B — The levels the competence table gives for the sector, said to be shared** (chosen): the
  table of ADR-0011, from the BOE, already says which level does what in each sector (in health the
  State sets the bases and the community manages). The news item shows both bodies under a label
  that says the competence is shared, without saying which one this news item is about, which is
  exactly what is not known.
- **C — Only the community's body.** Cleaner, right most of the time, wrong for a news item about a
  state law.

### A sector with several bodies
- **A — Every body whose competences carry the sector, as tagged today.** Noisy.
- **B — Review the sector tags by hand first** (chosen), so a sector leads only to the departments
  that manage it; then show every body left (one or two in the pilot).

## Decision

Option A to reach a body, B for a news item with no level, B for a sector with several bodies.

The reasons, in the author's words: the news item is not attributed to a party, it is attributed to
the body that holds the competence.

What is shown is a fact of the body, with its source: "Organismo con competencia" (or "competencia
compartida" when the level comes from the table), the body's name and a link to its chart. Never the
holder's name next to the news item, never a party, and never "responsable".

The rule, for each sector of a news item:

1. The levels are the news item's own; when it has none, the levels the competence table gives for
   that sector, and the answer says the competence is shared.
2. State level: the State's bodies with a competence in that sector. Community level: the bodies of
   each community of the news item that has a chart. Local level: the generic local bodies.
3. Only bodies in force on the news item's publication date.
4. A community with no chart yet, or a news item with no sector, shows no body.

## Consequences

- What gets easier: a reader sees which administration manages what a news item is about, and can
  open the body's chart, its competence and the law that gives it.
- What gets harder / what we accept: a wrong sector or level leads to a wrong body; a body's chart
  names its holder, and the community's page names who governs, so the reader is one click away
  from a party: that is a fact with its source (ADR-0018 keeps "who governs"), not an attribution of
  the news item. The sector tags must be reviewed for every new community.
- What would make us revisit this: the level classified for most news items (the table would no
  longer be needed); evidence in the error analysis that the bodies shown are wrong often enough to
  mislead.

## Verification

- Level coverage and the education example: queries on the local database, 2026-11-26 (above).
- The competence table and its sources: `data/governments/competences.csv` (ADR-0011).
- The bodies and competences in force: `data/organization/` (ADR-0025), each row with its source.
