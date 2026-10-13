# ADR-0004: Frontend: React with React Router v7

- **Status:** Accepted
- **Date:** 2026-10-13
- **Phase:** foundation

## Context

The web app is an interactive map plus story pages. Search inside the portal is done by the backend. What depends on the framework is indexing by search engines and link previews when a story page is shared.

## Options considered

### Option A — React and Vite with React Router v7 (chosen)
Start as a single-page app; enable server rendering or prerendering per route later.
- Pros: Plain React to begin; no framework migration to add server rendering.
- Cons: Until enabled, shared links show a generic preview.

### Option B — Next.js from the start
Server rendering from day one.
- Pros: SEO and previews solved early.
- Cons: More concepts for a benefit that matters from `story-contrast` on.

### Option C — Pure single-page app
No server rendering ever.
- Pros: Simplest.
- Cons: Poorer indexing; messaging apps show no headline.

## Decision

React with React Router v7. The author questioned whether Next.js was needed; the in-portal search is a backend concern and server rendering can wait until there are story pages to share.

## Consequences

- What gets easier: simple start, upgrade path.
- What gets harder / what we accept: server rendering must be planned before story pages go public.
- What would make us revisit this: when story pages are published

## Verification

Map: d3-geo SVG with the Canary Islands repositioned; MapLibre only if zoom below CCAA is needed.
