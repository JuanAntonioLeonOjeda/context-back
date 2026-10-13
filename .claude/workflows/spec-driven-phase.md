---
name: spec-driven-phase
description: Full process for each project phase (or any non-trivial change) — branch, short plan and wait, spec, plan, tasks, implementation in small commits, tests, review, ADRs and a defend check. Use it when starting a phase from the brief or a substantial change to an existing one.
---

# Spec-driven phase workflow

Code is not written directly from a request. Each phase of the brief
(`.claude/rules/project-policies.md`, "Phases") goes through `specs/<phase>/` first.

## Steps

0. **Branch.** `feature/<phase>` from an up-to-date `develop`
   (`.claude/workflows/git-workflow.md`), before touching the spec.

1. **Short plan, then stop.** In the conversation (not a file yet): goal of the phase,
   what will be built, the decisions that need the author, the risks and what must be
   verified first. **Wait for the author's confirmation.**

2. **Spec.** `specs/<phase>/spec.md`: what it solves, out of scope, acceptance criteria
   as given/when/then, open questions. Do not continue while open questions remain.

3. **Plan.** `specs/<phase>/plan.md`: modules, ports, adapters, schemas, migrations,
   config variables, and every non-obvious technical decision with its why. Each
   architecture decision → an ADR draft (`.claude/workflows/architecture-decision.md`),
   decided by the author.

4. **Tasks.** `specs/<phase>/tasks.md`: ordered checklist, small enough that **each task
   is one or a few commits**. Mark core-zone tasks with `[core]`: those follow the
   collaborative mode of `ai-collaboration.md`. End the file with a "Defend" section
   (step 8).

5. **Implement task by task**, committing as you go (Conventional Commits, small). If
   something the plan did not foresee appears, update `plan.md` (or `spec.md`) first —
   no architecture improvised in code. When a task touches a domain, follow its skill.

6. **Tests** per `.claude/rules/testing-conventions.md`. A task is not done while ruff,
   mypy or pytest fail.

7. **Review.** Run `py-reviewer`; `neutrality-reviewer` whenever the diff touches
   attribution, ranking, summaries, labels shown to users or the source list;
   `code-reviewer` for a general security/correctness pass when the diff is large. Fix
   or explicitly accept each finding.

8. **Defend.** Run `/defend <phase>`. Record in the "Defend" section of `tasks.md` the
   date, the result and the gaps. A phase is closed when the author can explain its core
   decisions without the assistant. Update `AGENTS.md` statuses.

9. **PR** with `/create-pr` into `develop`.

## Phase-specific notes

- **foundation**: decisions here are many and cheap to make now (migration tool, test
  layout, lint setup, package name): one ADR each only when it is a real trade-off. It
  also produces the hand-labelled test set (200 articles, labelled blind) and verifies
  the source catalogue (`docs/project-brief.md`, "Sources to verify").
- **news-live**: the LLM only proposes labels behind the `ArticleClassifier` port; the
  author validates them. Metrics are always reported per outlet and per party.
- **polish**: README (description, screenshots, diagram, how to run, ADR links, known
  limitations, data attributions, Claude Code note) and a final `/defend` over the whole
  system.

## When to skip steps

A trivial change (typo, copy, a log message, a dependency patch bump) does not need
spec/plan/tasks — it still needs a branch, a small commit and green CI.
