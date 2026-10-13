# Review of the foundation phase (2026-10-13)

Done with the criteria of `py-reviewer` and `neutrality-reviewer` (`.claude/agents/`),
applied as mechanical checks over `src/`, `data/` and `docs/`. A review by the agents
themselves on the merged PR is still a good second opinion before closing the phase.

## py-reviewer

| Check | Result |
|---|---|
| `domain/` imports no I/O library and never calls `now()` / `today()` | pass |
| `application/` imports no adapter; no module imports another's `domain` or `infrastructure` | pass |
| External hosts are requested only by `news/infrastructure` | pass |
| `os.environ` only in `config.py` | pass |
| SQL parameterised; no interpolated values | pass |
| Feed items and file rows validated at the edge, one bad item dropped and counted | pass |
| No party-specific or outlet-specific code in `src/` | pass |
| Gaps and overlaps of government terms tested (and an `EXCLUDE` constraint in the database) | pass |
| `Any` without a comment (`rss_feed_source.py`) | **fixed**: comment added at the boundary |
| `type: ignore` and `noqa` carry a code and a reason | pass |

## neutrality-reviewer

| Check | Result |
|---|---|
| Parties come from one table; colours are one provisional grey until the front chooses them | pass |
| Every role in `government_term_parties.csv` has its own `source_url` | pass (0 rows without) |
| Outlets are data with a published selection criterion; no per-outlet ideology measure exists, so the list is audience-based plus public broadcasters | pass, limit documented |
| Examples of the labelling guide are invented and mirrored across parties | **fixed**: PP governed 9 of the examples and PSOE 4; now 5 and 5 |
| Guide's party list named a party no example used | **fixed** (Coalición por Melilla) |
| Metrics per outlet and per party | not applicable yet (no classifier); required in `news-live` |
| Ordering of outlets in the UI | not applicable yet; to be checked in `story-contrast` |

## Open notes (not blocking)

- State caretaker term from 2026-11-29 (general election) must be added when it happens.
- Cataluña has no private regional outlet yet.
- Fixtures in `tests/fixtures/` come from real outlets; they are excerpts for tests only.
