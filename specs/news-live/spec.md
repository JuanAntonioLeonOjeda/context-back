# Phase 2 — news-live: spec

> **Amendment, 2026-10-15 (ADR-0018).** The author decided that no news item is attributed to a
> party. The attribution described below (AC1, and the attribution in the API and the web) was
> built, reviewed and then removed; this spec keeps it as the record of what the phase did. The
> promotion of the own model drops its per-party criterion. Who governs is still shown (map and
> panel); laws and votes come in phase 7.

## What it solves

The collector already stores the headline, link, date and a short lead of every article of
the 14 approved outlets, every three hours. Nothing reads them yet. This phase turns them into
what the portal promises: for each community and sector (education, health, housing), the
latest news of each outlet, and for each piece of news the party responsible for what it
describes, with the basis of that attribution and its confidence.

Two things decide whether that is trustworthy, and both are measured, not assumed:

- **Classification** (community, sector, government level of each article): rules first, then
  the author's own model (ADR-0008), trained on hand labels and promoted only if it beats the
  rules on the blind test set, overall, per outlet and per party.
- **Attribution** (who is responsible): never typed by hand and never guessed by a model; derived
  by one rule from the competence table and the government in force on the article's date
  (ADR-0005). When the rule cannot decide, the article says so.

Decided with the author on 2026-10-14 (plan step): attribution, rules, API and web first; the
model when the blind test set exists (early November); a training set of 400 to start, in
sessions of 100, grown only if the learning curve still rises; SetFit on a multilingual encoder
(Spanish and Catalan) in a separate dependency group; low-confidence attributions shown as "not
determined", never hidden; collection moved into Docker.

## Out of scope

- Grouping the same story across outlets (phase `story-contrast`) and the five-year history
  (phase `history-trace`).
- Municipal and island governments (cabildos, consells, councils): an article whose level is
  local is shown with its responsible "not determined (local government not modelled yet)".
- Any LLM in classification (ADR-0008).
- The article body: only headline, link and date are published; the lead is processed, never
  shown (`docs/sources-audit.md`, section 7).
- Drawing the provinces inside a community on the map (noted as an optional improvement).

## Acceptance criteria

**AC1 — attribution.**
Given an article with a community, a sector, the government levels it names and its date,
when the attribution rule runs, then it returns for each responsible government: the level,
the territory, the governing parties on that date, the competence that makes that level
responsible (activity and function, with its legal basis) and a confidence. When no level is
named, the levels come from the competence table for that sector and community (with the
per-territory rows, e.g. the State for health in Ceuta). When the rule cannot decide (a local
level, no government on that date, no competence for that sector), the result is "not
determined" with the reason. Every case of the competence table has a test, and so do a
government change on the exact article date, a coalition and a caretaker term.

**AC2 — rules classifier.**
Given a new article, when classification runs after each collection, then the rules assign
communities (from a gazetteer of communities, provinces, capitals and regional institutions),
sectors (from per-sector dictionaries) and government levels (from the institutions named),
store the result append-only with its `model_id` and version, and the rules never read the
outlet or a party to decide.

**AC3 — training set.**
Given the labelling guide and a Label Studio project with no proposals loaded, when the author
labels the training sample in sessions of 100, then `data/train/train-set-v1.jsonl` holds the
ids, URLs and labels only, and a test fails if any of its articles is in the blind test set.

**AC4 — own model.**
Given the training set, when the SetFit model is trained with fixed seeds, then it is evaluated
on the blind test set overall, per outlet and per party, next to the rules; it replaces the
rules for a label only if it meets criteria the author sets before training; the model is
identified by a version stored with every classification it makes, and its weights stay out of
git.

**AC5 — news API.**
Given classified and attributed articles, when a client asks
`GET /communities/{id}/news?sector=...`, then it gets the recent articles of that community and
sector with outlet, headline, link and date (never the lead), each with its attribution
(responsible parties, basis and confidence, or "not determined" with the reason), in an order
that does not depend on outlet size or political line, documented in the API.

**AC6 — web.**
Given the API, when a visitor opens a community card and chooses a sector, then the latest news
are listed with outlet, date and headline linking to the outlet, and each shows who is
responsible, why (level and competence) and with what confidence, in text; an empty sector says
so. Tests with Testing Library and axe in both themes.

**AC7 — collection in Docker.**
Given `docker compose --profile app up -d`, when three hours pass, then a `collector` service
has collected all feeds once, with the same politeness limits as today, logging in JSON, and the
launchd agent is retired.

**AC8 — neutrality.**
Given the phase's diff, when the neutrality review runs, then classification and attribution
take the same path for every party and outlet, metrics are reported per outlet and per party,
outlets are never re-ranked, and no text evaluates a party or a government.

**AC9 — quality gates.**
CI green in both repos; ADRs for the decisions of the phase; `AGENTS.md` and data READMEs
updated.

## Open questions

Blocking, to be settled in `plan.md`:

1. **Confidence scale.** Proposal: three values (named and competent: high; derived from the
   competence table with a single responsible level: medium; anything else: not determined),
   and their exact words in the web app.
2. **News window.** How recent "latest" is (for example the last 30 days) and how many per
   outlet and sector.
3. **Promotion criteria for the own model** (AC4): the author sets them before training.

Not blocking:

- The rules are measured on the blind test set only when it exists (tasks 20 and 21 of
  `foundation`, early November); until then they run unmeasured, and the web app says how
  articles are classified.
