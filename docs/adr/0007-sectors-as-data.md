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
