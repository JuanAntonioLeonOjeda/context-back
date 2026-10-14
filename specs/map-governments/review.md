# Review of the map-governments phase (2026-10-14)

Done with the criteria of `py-reviewer` and `neutrality-reviewer` (back) and `ts-reviewer` and
`accessibility-reviewer` (front), applied as mechanical checks over the code and a read of what
the phase added. The accessibility part is static plus axe in jsdom: it cannot show conformance.

## py-reviewer (back)

| Check | Result |
|---|---|
| Only ingestion and ETL reach external hosts (`news`, `indicators`); no request handler does | pass |
| `domain/` imports no I/O library and never reads the clock | pass |
| `application/` imports no adapter | pass |
| Everything from outside is validated: INE responses (Pydantic), CSVs (Pydantic), the IGN GML (checked shape, reference system and codes), query parameters (FastAPI) | pass |
| SQL parameterised; the `f-strings` found are XML paths, not SQL | pass |
| Observations append-only, enforced by a trigger, with the download that produced each row | pass |
| No party or outlet id in the code; the Canary Islands id is a layout fact of the map | pass |
| `Any`, `type: ignore`, `noqa`: each one has its code and its reason | pass |
| Interfaces of `governments` and `indicators` import the `TerritoryReader` port and the `Level` enum of `territories` | note |
| `main.py` reads `data/geo/ccaa.geojson` relative to the working directory (the repo root, `/app` in the image) | note |
| `/communities/{id}/governments` opens two connections (territories and terms) per request | note |

## neutrality-reviewer (back and front)

| Check | Result |
|---|---|
| One code path for every party: colours and names come only from the party table (`GET /parties`, `parties.ts`); a test fails on any colour written outside `src/design/` and on any map fill not in the table | pass |
| Order never ranks: communities by INE code, parties by id in the API, labels, legend and stripes; a backend test swaps party ids and expects the same shape | pass |
| Parties that only supported an investiture never colour the map; the card lists them apart, as "partidos que apoyaron la investidura sin entrar en el gobierno" | pass |
| Caretaker governments are said in the link name, the card and the API | pass |
| Wording names facts and sources, no evaluative words (`es.ts`, indicator names from the INE) | pass |
| The PSC and the PSOE have near-identical standard colours, so Cataluña and Castilla-La Mancha look alike on the map although they are distinct parties in the table | note: the legend and every link name tell them apart; colours are the parties' own (decided with the author) |

## ts-reviewer (front)

| Check | Result |
|---|---|
| Only the generated client calls the backend; only the features' data files import it, never a component | pass |
| No deep imports into another feature (the community page uses the map's public entry) | pass |
| API responses parsed with zod before use; a reply outside the contract is an error state, never a half-drawn view | pass |
| No `as`, `!`, `any` or `useEffect` for data; loading, error, empty and not-found states on every page | pass |
| User-facing text only in `es.ts` | **fixed**: a dash for "no period" was written in a component |
| Sorting in the browser: the legend orders the parties of all communities by id | note: the API has no legend; the order is the same rule the API uses |
| Inline styles: the markers' position and the parties' colours, both data | note: by design (ADR-0013) |

## accessibility-reviewer (front, static and axe)

| Check | Result |
|---|---|
| axe, WCAG 2.2 A and AA rules, on eight pages and states in both themes (map, its error, backend down, card, caretaker card, card error, unknown community, unknown address) | pass |
| Every community is a link with a name that states who governs; the map is a labelled group in a figure with its caption | pass |
| Ceuta and Melilla: HTML markers of a real 32 px whatever the width | pass |
| Colour never the only cue: stripes plus link names and legend | pass |
| Focus after a navigation inside the app stayed on the link used, so a screen reader did not know the page had changed (deferred from the `foundation` review) | **fixed**: the focus moves to `main` on every route change, not on the first page; mutation-checked |
| **Target size on phones (WCAG 2.5.8).** At 360 px the smallest side of La Rioja, Asturias and Cantabria is about 19–20 px; a map needs about 450 px of width for 24 px. Adjacent communities touch, so the spacing exception does not apply | **warning**: the standard remedy is an equivalent control on the same page, for example a list of the 19 communities as links under the map. The author's decision |
| Focus ring of an SVG community: the outer line turns the focus colour and thickens; on a blue-filled community the thin light inner line is what separates it from the fill | note: check in a real browser |
| Legend: short names (CxA, GBai) carry the full name only in `<abbr title>`, which touch and many screen readers do not expose | note: WCAG 3.1.4 is AAA; a visually hidden full name would fix it |

## Not verified (needs a real browser and assistive technology)

Enter on an SVG link (user-event activates only HTML links), the rendered contrast and focus
ring, zoom to 200 % and 400 %, forced-colours mode, touch sizes on a phone, VoiceOver and NVDA.
A Playwright-based check was proposed and is pending the author's approval.
