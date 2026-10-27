# Phase 4 — history-trace: spec

## What it solves

A story (phase 3) says "these outlets cover the same event". It does not say how events connect:
a ruling, the appeal before it and the reaction after it are three stories about one matter. This
phase links each story to the earlier story it continues, so a reader can follow a matter over
time as a **tree of stories**, left to right in chronological order.

Priority is the project's: neutrality and traceability over features. A link is a claim ("this
story is related to that earlier one"), so each one records how it was made and how strong it is.
It never says *why* they are related (no "cause", no "consequence").

## Out of scope

- Typed links (antecedent, consequence, continuation) from the brief: here a link only says
  "related and later". Types need hand-labelled pairs.
- Stories of one article only. A node is a story of phase 3 (two outlets at least), so an article
  with no story has no tree.
- A link threshold fixed on hand-labelled pairs: provisional, chosen by reading real trees.
- History beyond the 60 days that are embedded.
- Anything that ranks stories or outlets by engagement.

## Decisions (2026-10-27, the author)

1. **One parent per story**: the result is a forest, never a graph.
2. **Only connected stories**: a tree is shown only when it has at least two stories. Unrelated
   stories are not shown apart.
3. **A separate view**: each news item keeps its "ver fuente" link to the outlet and gets a "ver
   árbol" button to the tree of its story, shown only when that tree exists.
4. **Horizontal**: time runs left to right.

## Acceptance criteria

**AC1 — links.**
Given the stories of a grouping run, when the linking job runs, then each story gets at most one
parent: an earlier story (by its first article) that is similar enough and not too far back. When
several qualify, the most similar wins (ties: the earlier, then the lower id). A parent is always
strictly earlier, so a tree has no cycle. The job is deterministic.

**AC2 — traceability.**
Given a link, when it is stored, then the run records the grouping run, the threshold and the
window it used, and each link its similarity. Nothing is overwritten: a new run writes new rows
and the reader uses the latest.

**AC3 — tree read side.**
Given a story, when a client asks for its tree, then it gets every story connected to it through
parents and children, each with its articles (outlet, headline, link, date), its first date and
its parent; stories ordered by first date. 404 when the story has no relations. Never a lead, a
vector or a party.

**AC4 — news items.**
Given the news of a community, when an item belongs to a story with a tree, then it says which
story ("tree_story_id"); otherwise it is null.

**AC5 — web.**
Given a news item with a tree, when the user presses "ver árbol", then a separate page shows the
tree horizontally, oldest at the left, each node with every outlet's own headline linking out,
readable by keyboard and screen reader (nested lists). Items without a tree show no button.

**AC6 — neutrality.**
No node is highlighted by outlet, size or line; the order inside a node is by outlet id, and
between siblings by first date. No party appears.

## Open questions

1. Link threshold and window: provisional; chosen by reading real trees with the author.
