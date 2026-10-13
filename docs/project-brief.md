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
3. The LLM labels and proposes; facts come from the database; a human validates.
4. Reproducibility: stored results carry model and prompt versions; nothing is silently
   recomputed.
5. Publish metadata and short citations with links, never article bodies.

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
| `competence` | sector, activity, level (state, region, local, shared) | attribution rule input |
| `outlet`, `article` | outlet, URL, published_at, headline, lead, territory, sector, keywords, embedding | news metadata |
| `classification` | article, labels, confidence, model_id, prompt_version, validated_by | stored proposals and validations |
| `story`, `story_link` | grouped articles; link type (antecedent, consequence, continuation), confidence, origin | contrast and traceability |
| `indicator`, `observation` | versioned definition; values by territory and period with source | context data |
| `election`, `result` | votes by party and municipality | voter profiles |

## 5. Phases

See `.claude/rules/project-policies.md` ("Phases"). Pilot for phases 2–4: two or three
communities with governments of different colours (including a coalition) and the three
launch sectors; scale to all 19 once the method holds.

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

## 7. Risks

| Risk | Mitigation |
|---|---|
| Perceived bias in outlet selection | published criterion, all covering outlets shown, stable order |
| Wrong responsible party | competence table, visible confidence, error report |
| Invented links between stories | origin and confidence on every link; threshold chosen on the test set |
| Labeller bias inherited from the LLM | blind test set labelled by hand before any proposal is seen; sampled review |
| Copyright | metadata and short quotes only |
| Ecological fallacy in voter profiles | method note; wording about areas, not individuals |
| LLM cost on the five-year history | cheap model for ambiguous cases, batch processing, measure on a sample first |
