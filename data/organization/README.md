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

A community's executive is shown only if its head and **every** department listed here have a
holder in force that day; otherwise the page says "sin datos todavía".

## `competences.csv`

One row per competence of a body: `body_id`, `summary` (in our words), `legal_basis` (the article),
`sector_ids` (one or more ids of `data/governments/sectors.csv`, separated by `|`) and `source_url`
(a link to the text). It states what the law gives a body, never who is responsible for what a news
item says (ADR-0025).
