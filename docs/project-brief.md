# Project brief — Regional news context portal

Source of truth for scope and architecture. Replaces the decision board used while the
project was being defined (2026-10-13). Original draft: "Portal de verificación de
políticas públicas autonómicas" (2026-10-12), whose fact-checking part becomes phase 6.

## 1. Goal

An interactive map of Spain. Choosing a community (CCAA) and a sector shows:

- the most recent news from several outlets, grouped by story;
- the party or parties governing the community, alone or in coalition, and the party
  responsible for what each piece of news describes;
- a traceable sequence of earlier events (last five years) that led to the story;
- relevant statistics (education level, income, sector indicators) and keywords;
- voter profiles by community.

Sectors at launch: education, health, housing. The design supports N sectors
(candidates: social services and dependency, employment, regional taxation, water and
environment, transport).

## 2. Principles

1. Neutrality by construction: one code path for every party and outlet; rules are data.
2. Traceability: every number has a source; every link between stories has a type, a
   confidence and an origin (rule, model or human).
3. Labels come from rules and the author's own model, trained on hand labels (ADR-0008);
   facts come from the database.
4. Reproducibility: stored results carry model and prompt versions; nothing is silently
   recomputed.
5. Publish headlines and links only; leads are processed internally under the
   text-and-data-mining exception and never shown (see `docs/sources-audit.md`).

## 3. Architecture

See `.claude/rules/architecture.md` for the layout and dependency rules.

```
RSS / GDELT / sitemaps ─► news ─► classification ─► attribution ─► stories ─► PostgreSQL ─► API ─► web
INE / ministries / CIS / elections ─► indicators, voters (ETL) ──────────────────────────┘
curated governments + competences ──────────────────────────────────────────────────────┘
```

Stack (ADR-0003, ADR-0004): Python 3.12, FastAPI, PostgreSQL with pgvector and Spanish
full-text search; React + Vite + React Router v7 in the web app.

## 4. Data model (draft)

| Entity | Main fields | Purpose |
|---|---|---|
| `territory` | INE code, name, level, geometry | CCAA, provinces, municipalities |
| `party` | id, name, colour | single source of party data |
| `government_term` | territory, president, governing and supporting parties, caretaker flag, valid_from/to | who governed when |
| `sector`, `competence` | sector; activity, level (state, ccaa, local) and function (basic legislation, development legislation, execution), one row per level when shared | attribution rule input |
| `outlet`, `article` | outlet, URL, published_at, headline, lead, territory, sector, keywords, embedding | news metadata |
| `classification` | article, labels, confidence, model_id, prompt_version, validated_by | stored proposals and validations |
| `story`, `story_link` | grouped articles; link type (antecedent, consequence, continuation), confidence, origin | contrast and traceability |
| `indicator`, `observation` | versioned definition; values by territory and period with source | context data |
| `election`, `result` | votes by party and municipality | voter profiles |

## 5. Phases

See `.claude/rules/project-policies.md` ("Phases"). Pilot for phases 2–4 (decided 2026-10-13):
Canarias, Comunidad de Madrid and Cataluña, with the three launch sectors. The map,
governments, competences and national outlets cover the whole country from day one;
regional outlets and thorough validation start with the pilot and grow in batches.

Phase 7, `parliament-votes` (decided with the author on 2026-10-15): next to a measure, how each
parliamentary group voted. It starts with the Congreso, whose open data gives every deputy's vote
and group per vote (`docs/sources-audit.md`, section 9), and then tries the regional parliaments,
where most education, health and housing measures are voted, using only what each publishes
officially. Data comes from the parliaments, never from third-party sites or their summaries. A
parliamentary group is not a party (the Grupo Mixto and some groups hold several), so votes are
shown per group, with any mapping to parties curated and dated like the governments dataset. The
official title of the initiative and the kind of vote (amendment, final text, motion) are shown
as published, without wording about what the measure is "for".

How a news item meets a law (decided with the author on 2026-10-15, D16):

- **MVP, by topic.** Next to a news item, the most recent laws approved on the item's topic
  (its sector, now aligned with the 12 topics of D15), each with its final vote per group. It is
  presented as what it is, "latest laws on housing", never as "related to this news item": a
  shared topic is not a link between the two. Which topics a law has is a curated, sourced fact,
  not taken from third-party sites.
- **Later, links with a basis.** "Mentions the law" (its number, official title or a curated
  common name; high confidence, by rules) and "similar" (embeddings of the item against the
  law's title and preamble; medium, with a threshold measured on hand-labelled pairs), shown with
  their basis like the responsible party.
- The vote shown is the final vote of the law's file (`votación de conjunto`), not amendments,
  with its date and a link to the Congreso's data. State laws only until the regional
  parliaments are covered.

## 6. Sources to verify (phase 0)

| Source | Assumption | Status |
|---|---|---|
| RSS of the main outlets | most offer section feeds; some have removed them | unverified |
| GDELT coverage of regional Spanish press | enough to rebuild headlines since 2021 | unverified |
| Outlets' terms and `robots.txt` | metadata and links allowed; bodies not republished | unverified |
| INE API | EPA, ECV, Padrón, housing price and rent indices by CCAA | unverified |
| Election results by municipality | Interior publishes general and European; regional ones vary by CCAA | unverified |
| CIS microdata licence | reusable with attribution | unverified |
| CCAA geometries | IGN/CNIG open licence | unverified |
| Congreso votes | per-deputy votes with group, open data | verified 2026-10-15 (`docs/sources-audit.md`, 9) |
| Regional parliaments' votes | each publishes official per-group or per-deputy votes | unverified, one by one in phase 7 |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Perceived bias in outlet selection | published criterion, all covering outlets shown, stable order |
| Wrong responsible party | competence table, visible confidence, error report |
| Invented links between stories | origin and confidence on every link; threshold chosen on the test set |
| Labeller bias inherited from model proposals | blind test set labelled by hand with no proposals; training labels without proposals (ADR-0008) |
| Copyright | metadata and short quotes only |
| Ecological fallacy in voter profiles | method note; wording about areas, not individuals |
| Labelling effort for the own model | training-set size measured in `news-live`; labelling in short sessions |
