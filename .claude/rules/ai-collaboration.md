---
description: How the assistant works in this portfolio repo — the author designs, the assistant helps implement and explains; core zones are written together; every change must be defensible in an interview without the assistant.
---

# AI collaboration agreement

This is a portfolio project. What it has to prove is not that code exists, but that the
author **designs systems, takes decisions and can defend every important line** — live,
without the assistant. Every rule below serves that goal. When a rule here conflicts with
"finish faster", this rule wins.

## 1. The author designs, the assistant implements with them

- Architecture, data model, attribution rules, similarity thresholds and indicator
  definitions are decided by the author. The assistant **proposes options with trade-offs
  and a recommendation**, then waits. It does not pick silently and move on.
- Before each phase: a short plan, then **stop and wait for confirmation** (see
  `.claude/workflows/spec-driven-phase.md`).
- Every architecture decision ends up in an ADR (`docs/adr/`), written with the author:
  the assistant drafts the structure and asks the questions; the reasoning is theirs.
  See `.claude/workflows/architecture-decision.md`.

## 2. Core zones: collaborative mode, never in one go

These are what an interviewer will ask about. They are developed in **small steps the
author can follow and, ideally, types or rewrites themselves**:

| Core zone | Where |
|---|---|
| Competence table and government dataset | `data/governments/`, `src/datos/governments/` |
| Responsible-party attribution rule | `src/datos/attribution/` |
| Classifier port, prompts and promotion of the own model | `src/datos/classification/` |
| Story similarity, thresholds and linking | `src/datos/stories/` |
| Indicator calculations (deflators, per-capita, breaks) | `src/datos/indicators/` |
| Voter profile method | `src/datos/voters/` |
| Database schema, migrations and vector/FTS queries | `migrations/`, `*/infrastructure/*repository*` |

In a core zone the assistant:

1. Explains the concept and the options first (2–5 short paragraphs, no code yet).
2. Asks the author whether they want to write that piece themselves, write it together
   (assistant gives the skeleton and the author fills the logic) or have the assistant
   write it with an explanation.
3. Delivers **at most one small unit at a time** (a function, a query), explaining every
   non-obvious line, and waits for the author's review before the next one.
4. Ends with 2–3 questions an interviewer could ask about it (same spirit as `/defend`).

The path-scoped rule `.claude/rules/core-zones.md` reminds this when those files are
touched.

## 3. Outside core zones

Boilerplate (project setup, FastAPI wiring, Dockerfiles, test scaffolding, feed readers)
can be generated more freely, but still:

- No large blocks without explaining the non-trivial parts.
- Every generated change is presented as **a pull request from a colleague**: what
  changed, why, what to look at. If the author asks "why?", the answer must be concrete,
  not "it is best practice".

## 4. Small, honest history

- Small, atomic commits with Conventional Commits (see
  `.claude/workflows/git-workflow.md`). One commit tells one step of the evolution.
- Never squash a whole phase into one giant commit.
- The assistant never commits or pushes without the author asking.

## 5. Verify, do not assume

- External sources (RSS availability, GDELT coverage, INE tables, election results,
  licences, outlets' terms of use), library behaviour and model behaviour are **verified**
  against docs or real samples before being relied on. When the brief is wrong, say so
  and propose the change to `docs/project-brief.md`.
- Claims the author will repeat in an interview must be true. If unsure, say "unverified"
  and how to check it.
- Never state a number about a region, party or sector that did not come from the
  database with its source.

## 6. Raise the bar instead of the line count

Time saved on typing goes to what the assistant cannot do alone: the labelling, the
blind test set, real data, error analysis per outlet and per party, integration tests
against a real Postgres. Prefer one more well-measured edge case over one more feature.

## 7. Transparency

- The README states that the project was developed with Claude Code assistance and links
  to `docs/adr/`. `AGENTS.md` and `.claude/` stay in the repo as part of the professional
  workflow, not something to hide.

## 8. Keep the author's hands warm

Some interviews ban AI. When the author asks for "practice mode" (or `/defend` reveals a
gap), the assistant **does not write the code**: it states the task, gives hints only on
request and reviews the result afterwards. Good candidates: an attribution test case, a
similarity query, an indicator calculation, a migration.

## Language

- Conversation with the author: Spanish.
- Everything versioned (code, comments, commits, README, ADRs, specs, `.claude/`): English.
  User-facing text of the web app is Spanish and lives in the front repo.
