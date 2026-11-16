# ADR-0025: Organisation charts: bodies, posts and competences as facts of a body

- **Status:** Proposed
- **Date:** 2026-11-13 (draft; the decisions are the author's)
- **Phase:** org-chart
- **Relates to:** ADR-0018 (not amended: nothing here attributes anything to a party or a person)

## Context

ADR-0018 removed the "responsible party" of each news item: a chain of readings ended in a
statement about a party that the reader could not check. The competence table stayed as data. The
site now wants to show the organisation of the State and of each community: which bodies exist, who
holds the head post of the executive, and what competences each body has by law. The risk of
bringing the competences back is that they end up read as "this body, and so this party, is
responsible for what the news says". This phase states facts about bodies and posts, each with its
source, and stops there.

Sources (`docs/sources-audit.md`, section 11): the BOE has an open API; DIR3 gives official names
and codes but not the posts or which bodies are current; each community publishes its government and
its structure decrees in its own way, and two of the three pilot communities do not allow or do not
offer an automatic reading.

## Options considered

### How the data is obtained
- **A — Curated by hand in CSV, one source URL per row** (proposed). Pros: works with every source
  whatever its `robots.txt`; each row can be checked against its page; the same method as the
  governments dataset. Cons: manual work and a batch after every change of government.
- **B — Automatic readers of the gazettes.** Pros: always up to date. Cons: 19 different formats,
  `robots.txt` that close the site, reuse terms that reserve reproduction; the structure decrees are
  prose.
- **C — DIR3 as the list of bodies.** Pros: official names and codes, one file. Cons: it lists
  everything under a community (companies, foundations, old departments) all as "in force", no post
  holders, and states no reuse terms.

### What the chart says about responsibility
- **A — Bodies, posts and competences, as stated by the law, with no link to news and no party**
  (proposed).
- **B — Also link news to the body that holds the competence.** It would reopen ADR-0018: out of
  scope, it needs its own ADR.

## Decision

_Pending: the author decides and writes the reasons._ Proposed: option A in both questions, a new
`organization` module, the head post implicit in a holder row, the history kept in the CSV and
mirrored by the database, and a box per community for each parliament and TSJ (`specs/org-chart/plan.md`,
decisions 1 to 4).

_The reasons in the author's words: not written yet._

## Consequences

- What gets easier: every body, holder and competence has a source a reader can open; the chart can
  be rebuilt from the CSV files at any time.
- What gets harder / what we accept: the data is curated by hand; the State's page needs a batch
  after each change of government (the next one after 2026-11-29); communities outside the pilot
  show "sin datos todavía".
- What would make us revisit this: a community that publishes its government as open data; the wish
  to link news to bodies (a new ADR).

## Verification

- The loader refuses a row without a source and reports every problem with file and line.
- The same code path for every body and community; order by name, never by importance.
- Sources: `docs/sources-audit.md`, section 11.
