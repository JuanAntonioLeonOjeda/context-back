# ADR-0007: Sectors as data, three at launch

- **Status:** Proposed
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
