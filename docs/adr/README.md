# Architecture Decision Records

Each significant architecture decision of this project (backend and web app) is recorded
here: the context, the options considered, what was chosen and why. Template:
[`template.md`](template.md). Process: `.claude/workflows/architecture-decision.md`.

All entries below are drafts written from the 2026-10-13 design conversation. The author
reviews each one and rewrites the reasoning in their own words before it is `Accepted`.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-context-first-approach.md) | Context first, verification later | Proposed |
| [0002](0002-history-sources.md) | Five-year history from GDELT and sitemaps | Proposed |
| [0003](0003-backend-stack.md) | Backend stack: Python, FastAPI, PostgreSQL | Proposed |
| [0004](0004-frontend-stack.md) | Frontend: React with React Router v7 | Proposed |
| [0005](0005-responsible-party-attribution.md) | Responsible party from competences and government in force | Proposed |
| [0006](0006-voter-profiles-method.md) | Voter profiles from results, INE data and CIS | Proposed |
| [0007](0007-sectors-as-data.md) | Sectors as data, three at launch | Proposed |
| [0008](0008-classification-strategy.md) | Classification: rules and embeddings, LLM proposes, author validates, own model later | Proposed |
| [0009](0009-labelling-tool.md) | Label Studio for labelling | Proposed |

Pending decision with no ADR yet: how the common summary of a story is produced
(extractive first vs. LLM with mandatory citations). Needed before `story-contrast`.
