# ADR-0006: Voter profiles from results, INE data and CIS

- **Status:** Proposed
- **Date:** 2026-10-13
- **Phase:** context-voters

## Context

The portal should show voter profiles by community. Official results say what was voted by area, not by whom.

## Options considered

### Option A — Municipal results crossed with INE data, plus CIS (chosen)
Join results by municipality with income, age and education; add CIS survey data for self-placement and concerns.
- Pros: Official sources; CIS adds individual-level information.
- Cons: Ecological inference: groups of voters cannot be inferred from areas.

### Option B — CIS only
Survey data.
- Pros: Individual data.
- Cons: Small samples in small communities.

### Option C — Results only
Votes by area.
- Pros: Simple.
- Cons: Says what is voted, not by whom.

## Decision

Results crossed with INE data plus CIS, with the method explained on the page and wording about areas where a party won, not about individuals.

## Consequences

- What gets easier: all open data.
- What gets harder / what we accept: careful wording; municipalities with few residents.
- What would make us revisit this: if better individual-level open data appears

## Verification

UNVERIFIED: availability of regional election results by municipality and the CIS licence.
