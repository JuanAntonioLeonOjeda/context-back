# Phase 0 — foundation: plan

## Modules created in this phase

| Module | Layers | Content |
|---|---|---|
| `territories` | domain, infrastructure, interface (CLI) | `Territory` (INE code, name, level, parent), loader from a versioned CSV |
| `governments` | domain, application, infrastructure, interface (CLI) | `Party`, `GovernmentTerm`, `Competence`; term validation (no overlaps, no gaps); loaders |
| `news` | infrastructure only (minimal) | RSS collector used to build the test set: fetch, parse, store metadata idempotently |
| `api` | interface | FastAPI app with `/health` |
| `config.py`, `main.py` | — | settings and composition root |

Domain rules worth testing as pure functions: term overlap and gap detection, government
every term has at least one governing party; coalition and external support are derived
from the parties (≥ 2 governing; ≥ 1 external support), external-support party), resolving the term in force on a given date.

## Schema (first migration)

```
territories(id PK text, ine_code NULL, name, level, parent_id FK NULL)
parties(id PK slug, name, short_name, colour_hex)
government_terms(id PK, territory_id FK, president_name, is_caretaker, valid_from, valid_to NULL, source_url,
                 EXCLUDE no overlapping periods per territory)
government_term_parties(term_id FK, party_id FK, role, source_url, PK(term_id, party_id))
sectors(id PK slug, name)
competences(id PK, sector_id FK, activity, description, level, function, territory_id FK NULL,
            legal_basis, source_url, UNIQUE NULLS NOT DISTINCT(sector_id, activity, level, function, territory_id))
outlets(id PK slug, name, home_url, scope, region_id FK NULL)
articles(id PK, outlet_id FK, url, published_at, fetched_at, headline, lead, UNIQUE(outlet_id, url))
```

Decided with the author on 2026-10-13 (to be argued in ADR-0011):

- **Territory ids are prefixed text** (`es`, `ccaa-01`, `prov-28`), with the INE code in
  its own column. INE numbers communities 01–19 and provinces 01–52, so the INE code alone
  is ambiguous (01 is both Andalucía and Álava).
- **The row `es` (level `state`) is only an anchor for the central government's terms**, so
  national and regional governments share one table and one query (needed by ADR-0005 for
  state-level competences). The map and the community lists never show it. Confirmed with
  the author on 2026-10-13.
- **A government term ends on any change** of president, of the parties in government or
  supporting it, or of caretaker status. Attribution depends on who
  governed on the exact date.
- **No `kind` column** (decided with the author on 2026-10-13): kinds overlap (a coalition
  can also rely on external support, or be caretaker) and would duplicate the parties
  table. Coalition and external support are derived from `government_term_parties`;
  only `is_caretaker` is stored. Majority vs. minority needs seats and waits for election
  data (phase `context-voters`).
- **Sectors are rows in `sectors`**, not a fixed list (ADR-0007): a new sector is data.
- **Shared competences are several rows**, one per level, each with its `function`
  (`basic_legislation | development_legislation | execution`). A value `shared` would
  not tell attribution who does what. Competence levels reuse the territory vocabulary:
  `state | ccaa | local`. Decided with the author on 2026-10-13.
- **Articles keep metadata only.** `lead` is capped at 1,000 characters so an accidental
  full-text insert fails. `published_at` is required: items without a date are dropped by
  the collector. Feed URLs per outlet are decided in task 18 (collector).
- **Competences per territory** (decided 2026-10-13, task 13): `competences.territory_id`
  is empty for rows that apply to every community; a row for one community replaces the
  general rows of that sector and activity there. Needed because Ceuta and Melilla do not
  manage education or health care (their statutes give them only "sanidad e higiene" and
  a right to propose; INGESA and the Ministry manage them).
- **Function `legislation`** added (full legislation, e.g. regional housing under CE art.
  148.1.3ª, or state pharmaceutical legislation), next to basic legislation, development
  legislation and execution. State funding plans count as state `execution`.
- **Periods are half-open** `[valid_from, valid_to)`; `valid_to IS NULL` means in force.
- **No overlaps, enforced twice:** in the domain before loading, and in PostgreSQL with
  an exclusion constraint on `(territory_id, daterange(valid_from, valid_to, '[)'))`
  (extension `btree_gist`).
- Migrations are SQL inside `op.execute`, so constraints read exactly as PostgreSQL sees
  them.

`level` is `state | ccaa | province` (Ceuta and Melilla are `ccaa`: INE codes 18 and 19). `role` is
`governing | external_support`. Enums are `text` with `CHECK` constraints (easier to
extend than Postgres enums). The `vector` extension is created now; no vector columns yet.

## Governments dataset rules (task 11)

Decided with the author on 2026-10-13.

- **Method.** Wikidata is only the checklist of terms, so none is forgotten. Every row of
  `data/governments/` cites an official document (BOE, regional bulletin, parliament
  record); Wikidata is never a source.
- **Parties are the brand in government**: PSC, Unidas Podemos, Navarra Suma… as they
  appear, not folded into a national party.
- **A term starts** on the publication date of the decree that appoints the president
  (BOE), or of the regional bulletin decree that changes the composition (a partner
  entering or leaving).
- **Caretaker periods are modelled**: a caretaker term starts on election day and ends
  when the next president's appointment is published. Checked against every statute or
  government law: 15 territories say "after the election"; Asturias, Cataluña and the
  Comunitat Valenciana are ambiguous and Murcia and La Rioja say "dissolution". The
  author chose one convention for all, documented per territory in
  `data/governments/README.md`.
- **Caretaker without an election:** a government is also caretaker from the date its
  president ceases for another reason (resignation, disqualification) until the successor
  is appointed. Added with the author after batch 3.
- **External support** = parties that voted yes in the investiture and do not enter the
  government, as recorded in the parliament's session diary. Withdrawals of support
  during the legislature are not modelled.
- **Each party role has its own source** (`government_term_parties.source_url`): the
  vice-president's appointment for a coalition partner, the investiture vote for external
  support. A caretaker term keeps the parties and supporters of the term it continues.
- **Sources for communities** (decided 2026-10-13, after batch 1): the term date comes from
  the BOE appointment decree; parties and supporters come from the Instituto de Derecho
  Público's yearly "Informe Comunidades Autónomas" for that community and year, checked
  against the press when in doubt. Where no report exists yet (current year), the regional
  bulletin or the parliament's record is cited instead.
- **A party that leaves a government does not become its external support**, even if it
  voted yes in the investiture (e.g. Vox in Aragón, July 2024).
- **PSOE federations** (PSIB, PSdeG, PSPV, PSE-EE…) are `psoe`; legally separate parties
  (PSC) keep their own id.
- **Abstaining is not supporting**: only yes votes count as external support.
- **Work in batches** with the author's review: the State first, then communities in
  groups of five.
- Party colours are provisional placeholders, reviewed in the front (contrast and
  neutrality checks) before anything is shown.

## Decisions

| Decision | Choice | Record |
|---|---|---|
| Migration tool | Alembic, operations written by hand, forward-only (no downgrades; fix forward) | ADR-0010 (Proposed) |
| Query layer | SQLAlchemy Core 2.0 (no ORM) with `psycopg` 3; repositories write explicit SQL expressions | approved by the author on 2026-10-13 |
| Reference data format | CSV under `data/`, one row per fact, with `source_url` column; loaders validate with Pydantic | plan only |
| CLI | `argparse` (stdlib): `uv run python -m datos.governments load` | plan only |
| Test set storage | ids, URLs and labels in git; headline and lead only in the local database | spec AC9 |

## Dependencies (approved 2026-10-13)

Runtime: `fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `psycopg[binary]`,
`alembic`, `structlog`, `httpx`, `feedparser`.
Dev: `ruff`, `mypy`, `pytest`, `testcontainers[postgres]`.

## Docker Compose

- `db`: PostgreSQL with pgvector (official `pgvector/pgvector` image, version pinned after
  checking the current tags), healthcheck with `pg_isready`, named volume.
- `labelstudio`: Label Studio (version pinned after checking), its own volume, healthcheck.

## Configuration (`.env.example`)

`DATABASE_URL`, `LOG_LEVEL`, `LABEL_STUDIO_PORT`. No LLM key in this phase.

## Outlet selection criterion (task 14)

Decided with the author on 2026-10-13. Published as is on the portal so anyone can
reproduce the list; the assistant does not label outlets by ideology.

1. **National:** general-news outlets that appear in the monthly GfK DAM top 10 in any of
   the last six published months. Sports and entertainment outlets are excluded.
2. **Public broadcaster:** RTVE.
3. **Measured diversity:** using an external measure of each outlet's audience ideology
   (CIS or Reuters Digital News Report; availability to verify in task 15), every third of
   the spectrum must have at least three outlets; if not, the next most-read outlet of
   that third is added. If no such measure exists, steps 1 and 2 stand alone and the
   audience figures are published.
4. **Regional, per pilot community:** the regional public broadcaster and the most-read
   private regional outlet according to GfK DAM regional data. In Canarias, where the
   press is split by island, the most-read private outlet of each province.
5. An outlet without usable feeds (task 15) is replaced by the next one under the same rule.

## Pilot and scope (task 17, decided with the author on 2026-10-13)

- **Pilot communities:** Canarias (`ccaa-05`, both provinces), Comunidad de Madrid
  (`ccaa-13`) and Cataluña (`ccaa-09`).
- **Whole country from day one** for what is already cheap: the map, governments and
  competences of the 19 communities, and national outlets, whose news covers every
  community.
- **Pilot only** for regional outlets, the thorough label validation and the per-community
  metrics; other communities are added in batches once the validation flow and the
  per-outlet and per-party metrics hold.
- **Languages:** Cataluña brings Catalan-language outlets. Embeddings and the LLM are
  multilingual; the own model of phase 2b must be multilingual too (RoBERTa-BNE is
  Spanish only), to be reflected when ADR-0008 is reviewed.

## Sources audit method

- Outlets: candidate list by criterion (national outlets of varied editorial lines, the
  public broadcaster, one or two regional outlets per pilot community). For each: section
  feeds found, a fetch of each feed, items per day, presence of lead and date, terms of
  use and `robots.txt` notes.
- GDELT: query a sample week for the pilot communities and compare with the RSS items of
  the same week.
- INE: identify the table ids for population, income, education level and housing prices
  by community; one request each.
- Election results: where regional and general results by municipality are published.
- Output: `docs/sources-audit.md` (dated), skill `.claude/skills/news-sources/SKILL.md`
  (verified facts only).

## Blind test set method

1. The collector fetches the approved feeds for ~2 weeks (or until enough items exist).
2. A stratified sample of 200: by outlet, by pilot vs. non-pilot community, and including
   articles outside the three sectors (negatives).
3. `docs/labelling-guide.md`: definitions and edge cases for community, sector and
   government level, with examples from every party.
4. Label Studio project with that configuration; the author labels with no proposals
   loaded.
5. Export → `data/eval/test-set-v1.jsonl`. The file is frozen; a new version gets a new
   name.

## Risks

- Outlets without RSS → fewer outlets, or sitemaps (verify terms first).
- Government data errors → every row has a source; tests on overlaps and gaps; author
  review.
- Labelling fatigue → two sessions of 100; the guide resolves ambiguous cases before
  starting.
