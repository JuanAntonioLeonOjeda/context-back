# ADR-0002: Five-year history from outlet archives first, GDELT as a complement

- **Status:** Accepted
- **Date:** 2026-10-13 (revised 2026-10-13 after the sources audit)
- **Phase:** foundation

## Context

Traceability needs articles from the last five years, but RSS feeds and news sitemaps
only expose recent items. Sources must be free, and republishing article bodies is a
copyright risk (only headline and link are published; `docs/sources-audit.md`, section 7).

The first draft chose GDELT plus sitemaps. The sources audit (section 4) then showed that
GDELT's coverage of Spanish outlets is very uneven: on the same day La Razón had 75
articles and El Español, OKdiario, Telemadrid and RTVC had none, and coverage of an
outlet changes from year to year (La Vanguardia: 25 in 2021, 0 in 2026). A history built
mainly from GDELT would over-represent some outlets, and with them some editorial lines:
a neutrality problem, not only a technical one. Per-outlet archive sitemaps are not
verified either: RTVE's ends in March 2025 and 3Cat publishes none.

## Options considered

### Option A — Outlet archives first, GDELT as a complement (chosen, with C)
Each outlet's archive sitemaps or archive pages where they exist and are allowed; GDELT
fills what they miss.
- Pros: free; coverage per outlet does not depend on a third party's crawl; metadata is
  enough to classify and link.
- Cons: per-outlet work; archive availability is unverified for most outlets and must be
  checked one by one at the start of `history-trace`.

### Option B — Accumulate from today, GDELT to fill the past
- Pros: simplest; clean legally.
- Cons: the past depends almost entirely on GDELT, with the bias above.

### Option C — Show the coverage (chosen, with A)
For every outlet and month, the portal knows how many articles it holds. Antecedents are
not traced where coverage is below a minimum, and the gaps are shown, not hidden.
- Pros: the reader can see what the history is built from; a gap is never mistaken for
  "nothing happened".
- Cons: some stories will show a shorter history.

### Option D — Paid news archive
- Pros: complete and licensed.
- Cons: a recurring cost.

## Decision

Options A and C: outlet archives first, GDELT as a complement, and the coverage of every
outlet and month made visible. In the author's words: what matters is keeping the
traceability; a history with visible gaps is better than a complete-looking one that is
biased. A paid archive is out because this is a pilot project and the author cannot take
on recurring costs for it now.

## Consequences

- What gets easier: free history; small storage; the bias of each source can be measured
  and shown, because coverage per outlet and month is data.
- What gets harder / what we accept: per-outlet collectors for archives; shorter history
  for outlets without an archive; a coverage indicator in the API and the web app.
- What would make us revisit this: an outlet's source stops being maintained, or an
  outlet has no articles at all for two months in a row. Then that outlet's source is
  replaced or the outlet is marked without history for that period.

## Verification

- Verified 2026-10-13: GDELT coverage bias (`docs/sources-audit.md`, section 4); RTVE's
  archive sitemap ends 2025-03-17; 3Cat publishes no sitemap.
- UNVERIFIED: archive availability, terms and `robots.txt` of the other outlets. Checked
  outlet by outlet at the start of `history-trace`.
