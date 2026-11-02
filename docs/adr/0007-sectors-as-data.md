# ADR-0007: Sectors as data, three at launch

- **Status:** Accepted
- **Date:** 2026-10-13
- **Phase:** foundation

## Context

Education, health and housing come first; more sectors are expected.

## Options considered

### Option A — Design for N, launch with 3 (chosen)
A sector is configuration: taxonomy entry, keywords, competences and indicators.
- Pros: Adding a sector needs no code changes in classification or attribution.
- Cons: The taxonomy must be reviewed when new sectors arrive.

### Option B — Launch with five or more
More sectors from the start.
- Pros: More complete.
- Cons: More indicators to find and validate before anything ships.

## Decision

Design for N sectors and launch with education, health and housing. Candidates for later: social services and dependency, employment, regional taxation, water and environment, transport.

## Consequences

- What gets easier: new sectors without refactoring.
- What gets harder / what we accept: a generic model for indicators and competences.
- What would make us revisit this: when the fourth sector is added

## Verification

Candidate sectors are regional competences with public data by community (to confirm per sector).

## Amendment (2026-10-15): a taxonomy of 12, three active

Decided with the author (D15): the sectors are the 12 topics that elcongresoentumano.es uses for
laws (housing, work, taxes, health, education, rights, justice, environment, economy,
institutional, pensions, migration), so news and parliament votes (phase 7) share them. Only the
three of launch are active. A planned sector is a row with `is_active = false` (migration 0007),
chosen over a separate taxonomy file because the database then knows every topic; the cost is that
every reader of the sectors must filter on it, and the two readers that exist do, with tests. The
candidates listed in the Decision are superseded by this list.

## Amendment (2026-11-02): justice, work and taxes are activated

Decided with the author after the evaluation of 2026-10-26 (sector gain of +6.0 points with a 95 %
interval from −5.6 to +22.2) and a check of the volume of the collected news (about 24,000 in the
last 30 days; keyword probes put justice, taxes and work among the topics with the most news).
Activation follows the rule above: a batch with competences, rules terms, sampling terms and
labels. The three sectors are active in the data; the live database and the web take them after the
loader runs, which waits for the retrained model (the old one labels only the first three, and
the composite takes the sectors family from the model).

What this changes:
- The labelling interface and guide have the three new sectors; the 500 training and 200 test
  articles labelled before have to be looked at again for them (every one that had no sector, plus
  a check of the rest), and extra enriched samples are drawn for the new sectors.
- The promotion criteria of ADR-0016 are measured again for the sectors family on the relabelled
  test set, which needs enough positives of each new sector (about 50) to mean anything.
