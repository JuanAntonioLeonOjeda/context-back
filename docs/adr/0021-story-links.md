# ADR-0021: Linking each story to the earlier story it continues, one parent per story

- **Status:** Accepted (by the author, 2026-10-27)
- **Date:** 2026-10-27
- **Phase:** history-trace

## Context

A story says "these outlets cover the same event" (ADR-0020). It does not say how events connect:
the appeal, the ruling and the reaction are three stories about one matter. The author wants to show
that as a tree of stories in chronological order, in a view of its own.

Constraints that shape it:

- **A link is a claim.** It must carry how it was made and how strong it is.
- **No causes.** Nothing in the data says why two stories are related, and the project does not
  invent it (ADR-0018 spirit): a link only says "related and later".
- **The author's decisions (2026-10-27):** one parent per story; only connected stories are shown;
  a separate view, horizontal.

## Options considered

### The shape
- **A. A graph:** a story may have several parents. Pros: truer to matters that merge. Cons:
  unreadable as a tree; cycles must be ruled out.
- **B. A forest, one parent per story** (chosen). Pros: a tree is readable; no cycles because the
  parent is always strictly earlier. Cons: a story that continues two matters shows only one.

### How two stories are compared
- **The cosine of the centroids** (the mean of the vectors of their articles) (chosen): one number
  per pair, cheap (509 stories, under 0.1 s).
- The strongest pair of articles between the stories: favours long stories.

### Which earlier story is the parent
- The most similar earlier story inside the window (chosen); ties go to the earlier story, then to the
  lower id. The most recent or the first one above the threshold depend on the order of the data.

## Decision

A forest. For each story, the parent is the most similar story that started strictly earlier, within
**14 days** and with a centroid cosine of at least **0.75** (provisional). Only stories of two outlets
or more are nodes. A tree is shown only when it has two stories or more. Runs are immutable and store
the grouping run, the threshold and the window; each link stores its similarity.

## Consequences

- What gets easier: a tree is a plain read of rows; the order is chronological by construction.
- What we accept: **few news have a tree**, because nodes are only the grouped stories; a story with
  two possible matters keeps one; a card is represented by the headline of its first article
  published, which is an objective rule and still a choice the page states.
- What would make us revisit this: typed links (antecedent, consequence), which need hand-labelled
  pairs; a second parent per story; a threshold fixed on labelled data.

## Verification

Measured on 2026-10-27 over the 509 stories of the first grouping run, window 14 days:

| Threshold | Links | Trees | Largest | Reading |
|---|---|---|---|---|
| 0.75 | 121 | 66 | 11 | the Pope's surgery to his return (11 stories) reads whole; the "ley de nietos" tree carries two court stories of another matter |
| 0.78 | 91 | 62 | 6 | the "ley de nietos" tree is clean; the Pope's tree loses the diagnosis (a link at 0.77) |
| 0.80 | 70 | 52 | 6 | cleaner, but many trees of two or three stories |

Tests: unit tests of the parent rule (chronology, window and threshold edges, ties, order
independence, the tree of a story), integration tests of the pair query, the constraints of
migration 0011 and the news field that names the story of a tree.
