# Architecture Decision Records

Each significant architecture decision of this project (backend and web app) is recorded
here: the context, the options considered, what was chosen and why. Template:
[`template.md`](template.md). Process: `.claude/workflows/architecture-decision.md`.

All entries below were drafted from the 2026-10-13 design conversation, reviewed by the
author on 2026-10-13 and accepted when `feature/foundation` was merged.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-context-first-approach.md) | Context first, verification later | Accepted |
| [0002](0002-history-sources.md) | Five-year history from outlet archives first, GDELT as a complement | Accepted |
| [0003](0003-backend-stack.md) | Backend stack: Python, FastAPI, PostgreSQL | Accepted |
| [0004](0004-frontend-stack.md) | Frontend: React with React Router v7 | Accepted |
| [0005](0005-responsible-party-attribution.md) | Responsible party from competences and government in force | Accepted |
| [0006](0006-voter-profiles-method.md) | Voter profiles from results, INE data and CIS | Accepted |
| [0007](0007-sectors-as-data.md) | Sectors as data, three at launch | Accepted |
| [0008](0008-classification-strategy.md) | Classification with rules, embeddings and an own model from the start; no LLM | Accepted |
| [0009](0009-labelling-tool.md) | Label Studio for labelling | Accepted |
| [0010](0010-migration-tool.md) | Alembic for database migrations | Accepted |

Pending decision with no ADR yet: how the common summary of a story is produced
(extractive first vs. LLM with mandatory citations). Needed before `story-contrast`.
