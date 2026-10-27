# Architecture Decision Records

Each significant architecture decision of this project (backend and web app) is recorded
here: the context, the options considered, what was chosen and why. Template:
[`template.md`](template.md). Process: `.claude/workflows/architecture-decision.md`.

All entries below were drafted from the 2026-10-13 design conversation, reviewed by the
author on 2026-10-13 and accepted when `feature/foundation` was merged. ADR-0014 and ADR-0015
were drafted in the `news-live` phase and accepted by the author on 2026-10-14, after the phase's
web and API were merged.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-context-first-approach.md) | Context first, verification later | Accepted |
| [0002](0002-history-sources.md) | Five-year history from outlet archives first, GDELT as a complement | Accepted |
| [0003](0003-backend-stack.md) | Backend stack: Python, FastAPI, PostgreSQL | Accepted |
| [0004](0004-frontend-stack.md) | Frontend: React with React Router v7 | Accepted |
| [0005](0005-responsible-party-attribution.md) | Responsible party from competences and government in force | Superseded by 0018 |
| [0006](0006-voter-profiles-method.md) | Voter profiles from results, INE data and CIS | Accepted |
| [0007](0007-sectors-as-data.md) | Sectors as data, three at launch | Accepted |
| [0008](0008-classification-strategy.md) | Classification with rules, embeddings and an own model from the start; no LLM | Accepted |
| [0009](0009-labelling-tool.md) | Label Studio for labelling | Accepted |
| [0010](0010-migration-tool.md) | Alembic for database migrations | Accepted |
| [0011](0011-reference-data-model.md) | Reference data model for territories, governments and competences | Accepted |
| [0012](0012-indicator-observations.md) | Indicators as append-only observations of what the INE published | Accepted |
| [0013](../../../front/docs/adr/0013-svg-map.md) | The map is an SVG drawn with d3-geo, one link per community (front repo) | Accepted |
| [0014](0014-attribution-on-read.md) | Attribution computed on read, with a three-value confidence | Superseded by 0018 |
| [0015](0015-article-classifier.md) | One classifier port, rules as data, classifications append-only | Accepted |
| [0016](0016-own-classifier-model.md) | The own classifier: SetFit on a multilingual encoder, sectors and levels, promotion set before training | Accepted |
| [0017](0017-deployment.md) | Deployment: Docker Compose on a single host, no Kubernetes | Accepted |
| [0018](0018-no-responsible-party.md) | No responsible party per news item; laws and votes instead | Accepted |
| [0019](0019-article-tags-as-model-input.md) | The outlet's tags as part of what the model reads; the article body only where the site allows it | Accepted |
| [0020](0020-story-grouping.md) | Grouping the articles of the same story with embeddings, a threshold and a window | Proposed |
| [0021](0021-story-links.md) | Linking each story to the earlier story it continues, one parent per story | Proposed |

Pending decision with no ADR yet: how the common summary of a story is produced
(extractive first vs. LLM with mandatory citations). Needed before `story-contrast`.
