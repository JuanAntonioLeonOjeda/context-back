# ADR-0018: No responsible party per news item; laws and votes instead

- **Status:** Accepted
- **Date:** 2026-10-15 (accepted by the author the same day)
- **Phase:** news-live
- **Supersedes:** ADR-0005, ADR-0014

## Context

ADR-0005 and ADR-0014 gave every news item a responsible party: the classifier detects the levels
of government an article names, and the party comes from the competence table and the government
in force on the publication date, with a confidence of "high" or "not determined". The site shows
it next to each item, and ADR-0016 added a promotion criterion so that a model could not attribute
more items wrongly to any party than the rules.

On 2026-10-15 the author decided to stop. The attribution turns a classifier's reading of a
headline (a level, a sector, a community) into a statement that a party is responsible for what the
item describes. Every link of that chain can fail, the result names a party, and the reader sees one
line, not the chain. The project wants to show parties only through facts that come from an
official source: who governs (already shown, from the BOE) and, in phase 7, how each parliamentary
group voted on the laws related to an item (decided in D16 and D17, recorded in the brief).

## Options considered

### Option A — Remove the attribution from the site and the code (chosen)
- Pros: the site states only sourced facts about parties; no derived claim to defend item by item;
  less code and fewer concepts in the news read side.
- Cons: the site loses the line that answered "who is responsible?" until phase 7 gives laws and
  votes; the work of ADR-0005 and ADR-0014 leaves the running system (it stays in git and in these
  ADRs).

### Option B — Keep the code, hide it in the site
- Pros: nothing to remove; it can be shown again.
- Cons: code and tests nobody runs in the product; a reader of the repository cannot tell what is in
  use.

### Option C — Keep it as it is
- Cons: the reason for the change stands: a derived statement about a party next to every item.

## Decision

The site no longer attributes news items to a party (option A). The news endpoint drops its
`attribution` field, the web app drops the block that showed it, and the `attribution` module and
its tests are deleted (D21 = A). The "Cómo funciona" page stops describing a responsible party.

What stays (decided by the author the same day):

- **Who governs** (D20 = A): the map coloured by the governing parties and the government panel of
  a community. They are facts with a source (the BOE decree), not an attribution.
- **Levels of government** in the labels, the rules and the own model (D19 = A): in phase 7 they
  tell which parliament's laws to look at (a state-level item, the Congreso; a regional one, its
  parliament).
- **The competence table** as curated data, loaded and validated as before (ADR-0011); the site no
  longer reads it. It is kept for context and because each sector's activation already sources it.

In place of the attribution, phase 7 shows the laws related to an item, first by topic, then by
mention and similarity, with the final vote of each parliamentary group from official open data.

## Consequences

- What gets easier: no item says a party is responsible for it; the neutrality question becomes
  "is the data official and shown as published?", which can be checked against the source.
- What gets harder / what we accept:
  - Until phase 7 an item shows headline, outlet, date and sector, and nothing about parties.
  - ADR-0016 loses its third promotion criterion (no party attributions to compare); promotion rests
    on criteria 1 and 2.
  - The `news-live` spec, the "Cómo funciona" page, the API schema and the front's generated client
    change; the phase's review (`specs/news-live/review.md`) keeps its record of what was reviewed.
- What would make us revisit this: a source that states responsibility officially (it would be
  shown as such, not derived), or a need the votes cannot meet.

## Verification

- Where the attribution lives today (2026-10-15): `src/datos/attribution/`, its use in
  `src/datos/news/application/community_news.py` and `src/datos/news/interface/routes.py`, the
  competences reader wired only for it in `src/datos/main.py` and `src/datos/api/app.py`; in the
  front, `features/community/` (news card and section) and the texts in `i18n/es.ts`.
