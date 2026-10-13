# ADR-0002: Five-year history from GDELT and sitemaps

- **Status:** Proposed
- **Date:** 2026-10-13
- **Phase:** foundation

> Draft written from the design conversation; the author reviews and rewrites the
> reasoning before it is Accepted.

## Context

Traceability needs articles from the last five years, but RSS feeds only expose recent items. Sources must be free, and republishing article bodies is a copyright risk.

## Options considered

### Option A — GDELT plus outlet sitemaps (chosen)
Discover articles by date through GDELT and per-date sitemaps; store only headline, lead, date, outlet and URL.
- Pros: Free; metadata is enough to classify and link; lower legal risk.
- Cons: Regional press coverage unverified; terms and `robots.txt` to check outlet by outlet.

### Option B — Accumulate from today
Only what the RSS jobs collect from now on.
- Pros: Simplest and cleanest legally.
- Cons: Five-year traceability would take five years.

### Option C — Paid news archive
A provider with licensed archive.
- Pros: Complete, licensed.
- Cons: High cost for a personal project.

## Decision

GDELT plus sitemaps, metadata only. The author wants the history without paying, and linking events does not need the full text.

## Consequences

- What gets easier: free history, small storage, fewer copyright issues.
- What gets harder / what we accept: gaps for outlets GDELT misses; per-outlet scrapers for sitemaps.
- What would make us revisit this: if coverage of the pilot communities is below an agreed minimum

## Verification

UNVERIFIED: GDELT coverage of Spanish regional press, and each outlet's terms. Checked in `foundation`.
