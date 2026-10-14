# Review of the news-live phase (2026-10-14)

Done with the criteria of `py-reviewer` and `neutrality-reviewer` (back) and `ts-reviewer` and
`accessibility-reviewer` (front), applied as mechanical checks over the code and a read of what the
phase added: the back of `news-live` (attribution, classification, the news API, the collector) and
the front of `news-live` plus the UI refresh that followed it (header, footer, home hero, the
"Cómo funciona" page, the community page with its carousel). The accessibility part is static plus
axe in jsdom: it cannot show conformance.

No critical finding. Four warnings were fixed (decided by the author); the notes stay written down.

## py-reviewer (back)

| Check | Result |
|---|---|
| Only ingestion and ETL reach external hosts; nothing in `attribution`, `classification`, the news read side or the API does | pass |
| `domain/` imports no I/O library and never reads the clock | pass |
| `application/` imports no adapter; no router touches the database; no module imports another's `domain/` or `infrastructure/` | pass |
| Edges validated: the rules CSVs (refused with file and line), the `sector` query parameter (checked against the sectors table), settings (Pydantic) | pass |
| SQL parameterised; the one f-string is the endpoint's description | pass |
| Classifications append-only (trigger), one row per article and classifier version, with `model_id`, `model_version` and the evidence; the active classifier is a setting | pass |
| No party or outlet in the code or in the rules; the only party named is in a README example of a real misattribution | pass |
| `Any`, `type: ignore`, `noqa`: each one has its code and its reason | pass |
| **Connections.** Each reader opened its own connection: the news endpoint took four, and one community page about ten at once, against a pool of 15 | **fixed**: one connection per request, shared by every reader (`per_request`, `built_on` in `api/provider.py`), with unit tests |
| **News query.** It read and sorted every classification ever stored to keep a dozen (3 ms on 5,251 rows, growing with each article and each rules version) | **fixed** (core zone, explained to the author): the articles of the window first (index on `published_at`), then the latest classification of those only. Same rows on the real database for all 57 community-sector pairs; 1.0 ms instead of 3.1 ms when the window is a fraction of the archive; no gain yet while every article is in the window. A mutation that filters the community before choosing the latest classification fails the integration tests |
| `attribution/domain` and `classification/domain` import value types and pure rules of `governments` through its published API | note: decided in this phase (task 3); strictly, the rule says a domain imports nothing outside itself |
| `ACTIVE_CLASSIFIER_ID` is not checked: a typo gives an empty news list with no warning | note |
| The news endpoint reads the sector ids on every request | note: one small query |

## neutrality-reviewer (back and front)

| Check | Result |
|---|---|
| One code path for every party and outlet: the attribution rule, the rules classifier (the outlet is never an input), the news query, the stripes and chips (colours only from the party table) | pass |
| Attribution follows ADR-0005 and ADR-0014: the government in force on the publication day in Spain, governing parties only, shown with its confidence and basis; "sin determinar" always with its reason | pass |
| Order never ranks: news by publication time with ties by outlet id, at most 5 per outlet; parties by the name shown in the panel, by id elsewhere; communities alphabetically in the selector. Two tests fail if the panel is ordered by size | pass |
| Wording: interface texts and the "Cómo funciona" page state facts and sources; no evaluative word about a party, a government or an outlet | pass |
| Measurement: coverage of the rules reported per outlet (`data/classification/README.md`); precision, recall and the per-party breakdown wait for the blind test set (task 18) | note |
| **Hand-typed number.** "14 medios" was written in the "Cómo funciona" page: a change in the outlet list would have made it false | **fixed**: the page says "medios nacionales y regionales" |

## ts-reviewer (front)

| Check | Result |
|---|---|
| Only the generated client calls the backend; only the features' data files import it | pass |
| No deep imports into another feature: the community page and the shell use the public entries of `map` and `health` | pass |
| API responses parsed with zod; no `any`, no `as` outside tests, no `!`; `useEffect` only for the focus on route change and the carousel's size | pass |
| User-facing text only in `es.ts`; colours only from tokens and the party table | pass |
| The one `eslint-disable` (`tabIndex` on the carousel's scrolling region) carries its reason | pass |
| Computed in the browser: the communities per party, the grouping by day and the stripe colours | note: presentation of what the API sends, as the legend in the previous phase; the responsible party itself comes from the API |
| **Duplications.** The theme key was written in `index.html` and `theme.ts`; the repository URLs in the footer and the about page | **fixed**: a test fails if the theme key diverges; the URLs live in one constant of the shell |

## accessibility-reviewer (front, static and axe)

| Check | Result |
|---|---|
| axe, WCAG 2.2 A and AA rules, on every page and state in both themes, now including the home hero, the "Cómo funciona" page and the carousel | pass |
| The carousel: a named, focusable region (the keyboard scrolls it), arrows with names shown only when there is something to scroll to, `prefers-reduced-motion` respected | pass |
| Charts: a written name, the lowest and highest value in words and every point in a table | pass |
| Colour never the only cue: the stripes repeat what the text says, the party chips and rows carry the name | pass |
| **Focus under the sticky header (WCAG 2.4.11).** Nothing kept the header from covering an element scrolled into view by the focus | **fixed**: `scroll-padding-top` on `html` (7.5rem on a phone, where the header has two rows; 5rem from 40rem), with a test |
| The theme button's name changes with each press | note: screen readers may not announce the new name; three states do not fit `aria-pressed` |
| `aria-label` on the `<dl>` of the hero's figures; the carousel is a region inside the indicators region | note: a label on a `dl` may be ignored by assistive technology; harmless |

## Not verified (needs a real browser and assistive technology)

The rendered focus ring and the scroll padding in a real browser, zoom to 200 % and 400 %,
forced-colours mode, touch on a phone, VoiceOver and NVDA. The light theme and the footer on a phone
were looked at by the author (2026-10-14).
