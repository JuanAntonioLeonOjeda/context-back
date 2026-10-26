# Phase 3 — story-contrast: spec

## What it solves

The portal lists the latest news of a community and sector, one article after another. Several
outlets usually cover the same event, and today nothing says so. This phase groups the articles
that tell the same story, so the web app can show "this story, covered by these outlets" with
each outlet's own headline side by side.

Priority is the one of the whole project: neutrality and traceability over features. A group is
a claim ("these articles are about the same event"), so each one records how it was made and
how confident the match is.

This is an MVP of the idea: a basic grouper, no summary, and a provisional threshold.

## Out of scope

- The common summary of a story (D10: extractive or LLM). The group shows each outlet's own
  headline and nothing written by us.
- Links between stories over time (antecedent, consequence, continuation): phase 4
  `history-trace`.
- A threshold fixed on hand-labelled pairs. This phase uses a provisional one, shown as such in
  the code and in the spec; fixing it on labelled pairs comes later.
- Wiring the own classification model into live classification (left from `news-live`).
- Any ranking of outlets or stories by engagement.

## Acceptance criteria

**AC1 — embeddings.**
Given stored articles, when the embedding job runs, then every article gets one vector computed
from its headline, its tags and its lead (the same text the classifier reads), stored with the
name and version of the encoder that produced it. Running it again computes only what is
missing. Vectors are never exposed by the API.

**AC2 — grouping.**
Given the embeddings, when the grouping job runs, then articles from different outlets whose
vectors are closer than the threshold and whose publication dates are within the window are put
in the same story. A story has at least two articles from at least two different outlets; an
article with no match belongs to no story. The job is deterministic: the same data, threshold
and window give the same stories.

**AC3 — traceability.**
Given a story, when it is stored, then it records the encoder version, the threshold, the
window and, for each article, its similarity to the story. Nothing is overwritten: a new run
writes new stories and the reader uses the latest run.

**AC4 — read side.**
Given stories, when a client asks `GET /communities/{id}/stories`, optionally with `sector` and
a window, then it gets the stories whose articles are classified in that community (and sector),
each with its articles (outlet, headline, link, date) in a stable order that does not depend on
engagement, ranking or outlet size (by outlet id). The response never contains a lead or a vector.

**AC5 — neutrality.**
Given two outlets, when the same story is covered by both, then both appear, in the same
position rules, and no field says which outlet is "better" or "first to publish" as a ranking.
No party appears in a story: ADR-0018 holds.

**AC6 — web.**
Given the API, when a user opens a community, then the news list shows grouped stories with the
outlets that cover each one and a link to each article; articles with no story keep appearing
as today.

## Decisions (2026-10-27, the author)

1. Threshold and window: provisional. The window starts at 3 days between two articles; the threshold is
   chosen by looking at real groups and marked as provisional until pairs are labelled.
2. The community and sector of a story come from the stored classification of its articles
   (today the rules'), by majority.
3. Only the articles of the last 60 days are embedded (17,174 on 2026-10-27, almost all of the table).
