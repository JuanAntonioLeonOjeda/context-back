# Organisation data

The bodies of the State and the communities, who holds the head post of each executive and
department, and what the law gives each body (phase `org-chart`, `specs/org-chart/`, ADR-0025).
Curated **by hand, one source URL per row**: no automatic reader of gazettes, because their
`robots.txt` and terms do not allow it (`docs/sources-audit.md`, section 11).

Load and check with `uv run python -m datos.organization load [--data-dir PATH]`. Every problem is
reported at once and nothing is written unless there is none. The database mirrors the files: what
a file no longer has is removed from the database, and the history stays in the files (a holder
that leaves gets a `valid_to`) and in git.

## `bodies.csv`

One row per box of the chart.

| Column | Meaning |
|---|---|
| `id` | A slug that starts with the territory id (`ccaa-13-sanidad`, `es-hacienda`); `local-…` for a generic local body |
| `kind` | `executive_head`, `department` (a consejería or ministry), `parliament`, `judiciary` or `local` |
| `level` | `state`, `ccaa` or `local`, as in `data/governments/competences.csv` |
| `territory_id` | `es` or `ccaa-NN`; empty only for a generic local body, which appears in every community |
| `name` | The official name |
| `parent_id` | A department's parent: the executive head of its territory |
| `dir3_id` | The code of the body in DIR3, to cross-check the name; empty when it has none |
| `source_url` | Where the body and its name are stated |

A court is a State body that sits in a community (a TSJ: `level` `state`, `territory_id` the
community). A local body that exists in one community only (a cabildo) has that community as
territory.

## `holders.csv`

One row per holder of the head post of an `executive_head` or a `department`, over a period. Only
those two kinds have holders. No party is recorded for a holder (decided 2026-11-13).

`body_id`, `post_title` (as the appointment writes it: "Vicepresidente primero y Ministro de
Hacienda"), `holder_name`, `valid_from`, `valid_to` (empty: in force) and `source_url`. Periods are
half-open `[valid_from, valid_to)`: the day of a change belongs to the new holder. A body's periods
never overlap.

Only the current composition is kept: someone who has left has no row, and the history that
accrues from now is in the periods and in git. `valid_from` is the date of the decree that gave
the holder the post under that title (the person may take office the day after). The source of a
row is that decree; when the title joins a vice-presidency and a ministry, it is the decree of the
vice-presidency. A post that is vacant while someone attends its ordinary business (the BOE says
"asuma el despacho ordinario de los asuntos del Ministerio") has that person as its holder, with
the BOE's words in the title.

A community's executive is shown only if its head and **every** department listed here have a
holder in force that day; otherwise the page says "sin datos todavía".

### Updating the State

After a change of government or a reshuffle: new rows for the new holders with the date of their
decrees, and a `valid_to` (the date of the decree of cese) on the rows of those who leave. The
BOE's open API lists them by day (`/datosabiertos/api/boe/sumario/YYYYMMDD`), and the data of the
BOE is cited as "Fuente de los datos: Agencia Estatal Boletín Oficial del Estado".

## `competences.csv`

One row per competence of a body: `body_id`, `summary` (in our words), `legal_basis` (the article),
`sector_ids` (one or more ids of `data/governments/sectors.csv`, separated by `|`) and `source_url`
(a link to the text). It states what the law gives a body, never who is responsible for what a news
item says (ADR-0025).

### Wording and sectors: one rule for every territory

- **Wording.** A competence is written in Spanish, in our words, and says what the norm gives the
  body: "Tiene atribuidas las competencias en …" for a department; a plain description of the
  article for the other bodies. Official names (`name`, `post_title`) stay in the language of the
  source, so a Catalan department keeps its Catalan name.
- **Granularity.** One row per group of matters of the same sector that the same article of the
  norm assigns to a body. Matters of different sectors are split into different rows, and a row
  never merges matters of different sectors.
- **Sector of a matter** (the same in every file):

| Matter | Sector |
|---|---|
| Education, universities, research, innovation, culture, sport | `education` |
| Health | `health` |
| Housing, urban planning, land | `housing` |
| Environment, water, energy, climate | `environment` |
| Economy, industry, trade, consumers, gambling, tourism, agriculture, transport and public works | `economy` |
| Taxes, budgets, public debt | `taxes` (with `economy` when the row also covers economic policy) |
| Employment, labour relations | `work` |
| Social services, equality, youth, children, democratic memory, human rights | `rights` |
| Migration, asylum, citizenship | `migration` |
| Justice, courts, penitentiary services | `justice` |
| Public administration, civil service, security, civil protection, elections, institutions | `institutional` |
