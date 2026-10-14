# Phase 1 — map-governments: spec

## What it solves

The portal has curated governments and territories in the database but nothing that shows
them. This phase makes them visible: a navigable map of the 19 communities coloured by the
party or parties that govern each one on a given date, a card per community (president,
parties, how long the legislature has run) and five basic statistical indicators from the
INE, each with its source. There are no news yet: the map must be useful and trustworthy on
its own.

It is also the first public surface of the project, so neutrality is part of the
acceptance criteria: one code path for every party, a stable documented order, and no
wording that evaluates a government.

## Out of scope

- News, outlets and classification on the map (phase `news-live` and later).
- A date picker in the web app. The API takes a date; the web app shows today. A picker
  needs the 2020–2026 history to be browsable and is added later.
- Seats, majority or minority, and election results (phase `context-voters`).
- Deflators and series-break treatment beyond showing the break note (phase
  `context-voters`, ADR on indicator definitions).
- Municipal governments and provinces on the map (provinces only appear in statistics).
- Public deployment.

## Acceptance criteria

**AC1 — territories.**
Given the loaded reference data, when a client asks `GET /territories?level=ccaa`, then the
response lists the 19 communities with `id` (`ccaa-NN`), `ine_code` and `name`, in a
documented stable order, and never the state anchor `es`.

**AC2 — government in force on a date.**
Given the governments dataset, when a client asks
`GET /communities/{id}/governments?date=YYYY-MM-DD`, then the response holds the term in
force on that date: president, `valid_from`, `is_caretaker`, the parties with their role
(`governing` or `external_support`), and the `source_url` of the term and of each role.
Ceuta and Melilla go through the same path. A date with no term in the dataset (before
2020-01-01) answers 404 with a reason, not an empty body. Omitting `date` means today,
read once from the clock, never from the domain.

**AC3 — map payload.**
Given the same data, when a client asks `GET /map/governments?date=...`, then it gets the 19
communities with the parties that govern each one (not those that only support it), in an
order that does not depend on size, votes or position: alphabetical by `party_id`. A
coalition lists every governing party; a caretaker term is marked.

**AC4 — geometries.**
Given the official administrative boundaries, when the build step runs, then a simplified
file holds the 19 communities keyed by the same `ccaa-NN` ids, with the Canary Islands in an
inset and Ceuta and Melilla as visible markers, a total size small enough to load on a
phone, and the source and licence attribution in the file and in the README.

**AC5 — indicators.**
Given the INE API, when the ETL runs, then five indicators (population, risk of poverty or
exclusion, education level, unemployment rate, housing price index) are stored per
community and period in an append-only `observation` table, each with its unit, its source
table id and the download that produced it. Running it twice adds nothing; a revised value
is a new row, never an update. `GET /communities/{id}/indicators` returns, for each
indicator, the latest value, the period, the unit, the source and the series.

**AC6 — neutrality.**
Given the diff of the phase, when `neutrality-reviewer` runs, then there is no party-specific
branch, colour or wording outside the parties table; stripes for coalitions are drawn by
one rule; external support appears in the card but never colours the map; and the page
states the date of the legislature and the source of every claim without evaluative text.

**AC7 — web app.**
Given the API, when a visitor opens the map, then the 19 communities are drawn from the
backend data, coloured and striped as in AC3, with a legend that is always visible; the
visitor can choose a community with the mouse, a touch or the keyboard; the card shows
president, governing parties, external support, caretaker note, start of the term, the
indicators with period and source, and a link to each source. Every community has a text
alternative. Tests with Testing Library and axe pass in both themes.

**AC8 — quality gates.**
Given both repos, when CI runs, then lint, types, unit and integration tests (backend) and
lint, typecheck, tests and build (web app) are green; `AGENTS.md` statuses and the data
README are updated; the decisions of the phase are ADRs.

## Open questions

Blocking, to be settled in `plan.md` before implementing:

1. **Party colour palette.** Decided in principle (recognisable colours, checked for
   contrast and colour-blindness, stripes and labels for pairs that look alike); the actual
   values are the author's choice.
2. **Income indicator.** The INE publishes household income by province (ADRH). Aggregating
   it to a community needs a method (population-weighted mean of provincial means is
   approximate). Proposal: leave income out of this phase and note it for
   `context-voters`.
3. **Units of the INE series.** The series listing does not carry the unit; read it from
   the series metadata and verify it for each of the five indicators.
4. **Geometry licence text.** The IGN boundaries are published under the IGN terms of use
   (`ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf`); read them and write the
   exact attribution. The files come at 1:25,000 precision and must be simplified.

Not blocking:

- The state government becomes caretaker after the general election of 2026-11-29; that
  term must be added when it happens. The map shows communities only.
