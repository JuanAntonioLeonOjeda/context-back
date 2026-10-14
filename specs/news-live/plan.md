# Phase 2 — news-live: plan

## Decided with the author

- **2026-10-14, plan step (D1–D5):** attribution, rules, API and web first, the own model when
  the blind test set exists; a training set of 400 to start, in sessions of 100; SetFit on a
  multilingual encoder in a separate `ml` dependency group; low-confidence attributions shown as
  "not determined", never hidden; collection moved into Docker.
- **2026-10-14, spec questions:** confidence in three values (high, medium, not determined); the
  latest news are those of the last 30 days, at most 5 per outlet and sector.
- **2026-10-14, D6 = A:** at sector level every function is shared, so an article that names no
  government is not determined; "medium" stays unused until the activity is classified or a
  managing level is curated (options B and C below, for a later phase).

## The attribution rule (core zone, ADR-0005; ADR-0014 to write)

Input: an article's community, sector, the government levels it names and its date. Output:
one entry per responsible government (level, territory, governing parties on that date, the
competences that make that level responsible) or "not determined" with a reason.

1. **Levels named in the article.** For each named level: the territory is the community
   (`ccaa`), the State (`state`) or not modelled (`local`, reason "local government not modelled
   yet"). If that level holds at least one competence of the sector in that community (applying
   the per-territory rows), the entry is **high**. If it holds none, the entry is **not
   determined**, reason "the article names a government with no competence in this sector": the
   label follows the text (labelling guide, row 27), the responsibility does not.
2. **No level named.** Not determined, reason "the article names no government, and the sector's
   competences are shared by several levels" (D6-A).
3. **Government on the date:** the term in force on the article's publication date in Spain
   (`in_force_on`), its governing parties only; no term → not determined, reason "no government
   in the dataset on that date". Parties that only supported the investiture are never responsible.

**Computed on read, not stored.** Attribution is a pure function of the stored classification,
the competence table and the governments dataset. Computing it when the API reads keeps it
consistent when the curated data is corrected (a stored attribution would go stale silently),
and it is cheap (a page shows tens of articles). Classifications, which are costly and come from
versioned models, are stored. To argue in ADR-0014.

### D6 — what "medium" means (decided: A)

At sector level every function is shared: in education, health and housing the execution is
state, regional and local at once, also in Ceuta and Melilla. So "a single responsible level
from the table" never happens, and every article that names no government would be not
determined.

| Option | What it means | Cost |
|---|---|---|
| **A — keep it strict** (recommended now) | No level named → not determined. "Medium" is reserved for D6-B or C later | None. Honest; the web says why. How many articles end not determined is measured on the test set |
| B — classify the activity too | Curriculum, schools, waiting lists… map to the table's activities, which often have one executing level | A finer label: changes the labelling guide and needs more training labels |
| C — a "managing level" per sector | A curated column in `competences.csv` marks the level that runs the public service (education and health: the community; Ceuta and Melilla: the State) | An editorial choice to defend with sources; simple to compute |

## Classification

- **Port** `ArticleClassifier` (application): `classify(text) -> Labels` (communities, sectors,
  levels, each with a score); adapters `RulesClassifier` now, `SetFitClassifier` in the model
  tasks. Same contract for both, one contract test suite (testing conventions).
- **Rules as data, not code** (open/closed): `data/classification/` (built as `places.csv`, `levels.csv`,
  `sectors.csv` and `exclusions.csv`; the files below are the first sketch, see its `README.md`)
  - `gazetteer.csv`: term → territory (communities, provinces and capitals from the INE names;
    regional institutions: "Xunta de Galicia", "Generalitat de Catalunya", "Junta de
    Andalucía"…). A term that names more than one community ("Junta", "Generalitat") gives the
    level only, never a community.
  - `institutions.csv`: term → level ("Gobierno de España", "Consejo de Ministros", "ministerio"
    → state; regional governments and parliaments → ccaa; "ayuntamiento", "cabildo", "consell
    insular", "diputación" → local), in Spanish and Catalan.
  - `sectors.csv`: term → sector, curated from the labelling guide's boundaries, in Spanish and
    Catalan.
  Text: headline plus lead, case-folded, matched on word boundaries; the outlet is never an input.
- **Stored append-only:** `classifications(article_id, model_id, model_version, communities[],
  sectors[], levels[], scores, created_at)`, one row per article and model version (migration
  `0005`, the same trigger as observations). The current classification of an article is the one
  of the active model.
- **When:** after each collection, the new articles are classified (`python -m
  datos.classification classify-new`).

## Own model (after the blind test set, early November)

- `ml` dependency group: `setfit`, `sentence-transformers`, `torch` (CPU build). Never in the API
  image: training and batch classification are jobs.
- Encoder: a multilingual sentence encoder that covers Spanish and Catalan (candidate
  `paraphrase-multilingual-mpnet-base-v2`; to verify its licence and Catalan coverage). Proposal:
  the model takes **sectors and levels**, where keywords are weak; communities stay with the
  gazetteer unless the test set shows otherwise.
- Training sample: 400 articles not in the test set, stratified like it (equal per outlet, half
  random and half enriched), labelled in Label Studio with no proposals; ids, URLs and labels in
  `data/train/train-set-v1.jsonl`. A test fails if any id is also in `data/eval/`.
- Weights in `models/` (out of git), identified by training-set version and seed.
- Promotion criteria: set by the author before training; evaluation on the test set overall, per
  outlet and per party, next to the rules.

## News API (`news` module, interface)

`GET /communities/{id}/news?sector=education|health|housing`

- Articles of the last 30 days (Spain time) classified with that community and sector by the
  active model, at most 5 per outlet.
- Order: publication time, newest first; ties by outlet id. It never depends on outlet size or
  line. Documented in the endpoint.
- Each item: outlet id and name, headline, URL, `published_at`, and the attribution entries
  (level, territory, party ids, competence activities and legal basis, confidence, reason).
  Never the lead.
- Includes how the article was classified (`model_id`, version), so the web app can say it.

## Web (front, `features/community`)

A sector selector in the community card (three links, `?sector=` in the URL), the news list with
outlet, date and headline linking to the outlet, and for each piece of news who is responsible,
why (level and competence) and the confidence in words ("Alta", "Media", "Sin determinar: …").
Empty state per sector. Same tests as the card: Testing Library, axe in both themes.

## Collection in Docker

A `collector` service (profile `app`, the back-main image): every 3 hours runs the collector and
then `classify-new`, logs JSON to stdout, `restart: unless-stopped`. Once it has run, the launchd
agent is unloaded and its plist removed (a change to the author's system, done with their yes).
The Mac still has to be on.

## Schema (migration `0005`)

```
classifications(id PK, article_id FK, model_id text, model_version text, communities text[],
                sectors text[], levels text[], scores jsonb, created_at timestamptz,
                UNIQUE(article_id, model_id, model_version))
-- append-only trigger, as observations; index (model_id, model_version, article_id)
```

## ADRs of the phase

- **ADR-0014:** attribution computed on read, the confidence scale and D6.
- **ADR-0015:** the `ArticleClassifier` port, rules as data, classifications append-only.
- **ADR-0016 (November):** the own model, its encoder and its promotion criteria.

## Risks

- **Sector keywords are noisy** (half of the "hospital" or "vivienda" matches were not policy in
  the guide's sample): the rules will over-assign sectors; the model is the remedy, measured on
  the test set.
- **Ambiguous institution names** ("Junta", "Generalitat", "Gobierno"): they give the level only.
- **Not determined everywhere** if D6-A: visible and explained, measured on the test set.
- **Catalan coverage** of dictionaries and encoder: tested with 3Cat articles.
