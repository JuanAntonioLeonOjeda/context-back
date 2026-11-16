# Phase 8 — org-chart: plan

Proposed on 2026-11-13; the choices marked **(to confirm)** wait for the author.

## Module

A new module `src/datos/organization/`, with the usual layers. It reads territories and the
sector ids through the other modules' published APIs, never their internals. Data lives in
`data/organization/`, curated by hand, one source URL per row (`docs/sources-audit.md`, section 11).

## Data files

| File | One row per | Main columns |
|---|---|---|
| `bodies.csv` | body | `id` (slug starting with the territory id), `kind`, `level`, `territory_id`, `name` (official), `parent_id`, `dir3_id`, `source_url` |
| `holders.csv` | holder of the head post of a body, over a period | `body_id`, `post_title`, `holder_name`, `valid_from`, `valid_to`, `source_url` |
| `competences.csv` | competence of a body | `body_id`, `summary` (our words), `legal_basis` (article), `sector_ids` (`\|`-separated), `source_url` |

`kind` is one of `executive_head`, `department` (a consejería or ministry), `parliament`,
`judiciary`, `local`. `level` uses the vocabulary of the competence table (`state`, `ccaa`,
`local`). A `department` has the community's `executive_head` as parent. A local body has no
territory when it is generic (the same in every community: an ayuntamiento) and belongs to a
community when it exists there only (a cabildo in Canarias); the chart of a community shows both.

## Schema (migration `0016_organization`)

- `bodies (id PK, kind CHECK, level CHECK, territory_id NULL → territories, name, parent_id NULL →
  bodies, dir3_id NULL, source_url NOT NULL)`; a CHECK ties `level` and `territory_id` (`local` has
  none, the others have one), as `territories` ties level and code.
- `body_holders (id PK, body_id → bodies, post_title, holder_name, valid_from, valid_to NULL,
  source_url NOT NULL)` with an exclusion constraint so two holders of one body never overlap
  (`daterange(valid_from, valid_to, '[)')`, like `government_terms`; `btree_gist` is already
  there), and a CHECK that only `executive_head` and `department` bodies have holders.
- `body_competences (id PK, body_id → bodies, summary, legal_basis, source_url NOT NULL)` and
  `body_competence_sectors (competence_id → body_competences, sector_id → sectors, PK both)`.
- The existing `competences` table (sector × level × function) is left as it is: it says which level
  holds what in a sector, not what a body does.

## Domain (pure, no I/O, "today" is a parameter)

- `holder_on(holders, body_id, day)`: the holder in force, or none.
- `executive_chart(bodies, holders, territory_id, day)`: the president and the departments, ordered
  (president first, then the departments by name, case-insensitively), and a status `complete` only
  if the head and **every** department of that territory have a holder in force on `day`;
  otherwise `no_data`, never half a government.
- A territory with no bodies at all is `no_data` too.

## Loader (`python -m datos.organization load`)

Reads the three files, reports **all** problems at once with file and line (as `governments`):
a row without a source URL, an unknown kind, a body whose parent or territory does not exist, a
sector id that is not a sector, a holder of a body that cannot have one, two overlapping periods
for one body, a department without a parent. Then replaces the three tables in one transaction
(the CSV keeps the history through `valid_from` / `valid_to` and git; the database mirrors it).

## Read side and API

Two read-only endpoints, one connection per request like the others:
`GET /organization` (the general chart: State executive, parliament, judiciary and the generic local
boxes) and `GET /communities/{id}/organization`. Each body comes with its holder in force, its
competences (summary, legal basis, link, sectors) and its source. The answer carries the date it is
valid for, the executive's status and, for a community outside the pilot, `no_data`.

## Web (front repo, a branch of its own)

Routes `/organigrama` and `/comunidades/:territoryId/organigrama`; the chart as nested lists
(ordered, readable in sequence, no colour as the only cue); the link "Ver organigrama" on each
community page; the BOE attribution on the State's page; texts in `src/i18n/es.ts`.

## Decisions

1. **Where the code lives (to confirm).** A new module `organization` (recommended) or inside
   `governments`. The module keeps the competence table and the government terms untouched and
   stays small; inside `governments` it would share a loader but grow a module that is already a core
   zone.
2. **Posts (to confirm).** The head post of a body is implicit: one `holder` row per period with its
   `post_title` as text ("Vicepresidente primero y Ministro de Hacienda"), recommended; or a `posts`
   table. With depth limited to the president and the consejeros, a posts table adds a join and a
   concept for nothing; it can come with the second level.
3. **History (to confirm).** The CSV holds the history and the database mirrors it with a replace
   (recommended, as `governments`), or an append-only database history like the observations. The
   observations are append-only because they come from downloads that get revised; these rows are
   curated by hand and git already keeps every version.
4. **Parliaments and the TSJ in a community's chart (to confirm).** One box per community with its
   official name and its own article (statute, LOPJ), recommended for the three pilot communities
   (names from DIR3: "Parlament de Catalunya" appears under the Generalitat), or one generic box
   shared by all with a generic text. The first is more work per community and says exactly what
   the law says for it; the second is shorter and hides the differences.
5. **Competences and sectors.** A `\|`-separated column `sector_ids` in the CSV (easy to curate by
   hand), validated by the loader against the sectors and stored in a join table with real foreign
   keys.
6. **Order.** The president first, then alphabetical by the body's name, in the domain and tested; never
   by importance or by the order of a decree.
7. **Today.** The Spanish day from the `Clock`, as everywhere else.

## Verification

- Hand-computed cases for `holder_on` (day of the change belongs to the new holder, `[)`) and for
  completeness (one department without a holder makes the whole executive `no_data`).
- The same data for two communities gives the same chart shape (neutrality, one path of code).
- Migration constraints on PostgreSQL: overlap, a holder on a body that cannot have one, a level and
  territory that do not fit.
- Real-data check: Madrid's nine consejerías against DIR3's names and its government page.

## Risks and what is not verified

- The State's ministers change after 2026-11-29: a new batch within days of the appointments.
- The Real Decreto that names the ministers and the one that sets their structure are not
  identified yet; they are the first thing to locate when the State's batch starts.
- Canarias and Cataluña: the names of their consejeros come from the author; the structure decree of
  Canarias was not found.
- DIR3 states no reuse terms: only official names and codes are taken, with the source named.
