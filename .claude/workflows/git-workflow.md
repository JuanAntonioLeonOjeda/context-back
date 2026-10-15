---
description: Permanent branches (main, develop), branch naming, where each branch comes from, Conventional Commits and small atomic commits.
---

# Git workflow

## Permanent branches

| Branch | Purpose |
|---|---|
| `main` | Stable, what a recruiter sees. Only receives merges from `develop`; never direct commits. |
| `develop` | Integration branch. Every work branch starts from it and returns to it. |

```
main ← develop ← feature/<phase>
               ← fix/<short-description>
               ← chore/<short-description>
               ← docs/<short-description>
```

## Naming

| Kind of work | Branch | Example |
|---|---|---|
| Phase or feature (has a `specs/` folder) | `feature/<phase>` | `feature/foundation` |
| Bug fix | `fix/<kebab-description>` | `fix/duplicate-story-links` |
| Config/tooling (`.claude/`, `AGENTS.md`, CI, lint, deps) | `chore/<kebab-description>` | `chore/agent-config` |
| Docs only (README, ADR outside a phase) | `docs/<kebab-description>` | `docs/adr-similarity-threshold` |

The phase name in the branch matches its `specs/<phase>/` folder 1:1.

## Creating a branch

1. `git checkout develop`
2. `git pull` (if there is no upstream: `git branch --set-upstream-to=origin/develop develop`)
3. `git checkout -b <type>/<name>`

If the new work depends on an unmerged branch, wait for the merge or ask the author.

## Commits

- **Conventional Commits**: `<type>(<scope>): <subject>`, imperative, English, ≤ 72
  chars. Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`,
  `perf`. Scopes: `api`, `news`, `classification`, `stories`, `governments`, `indicators`,
  `voters`, `db`, `adr`, `ci`, `repo`.
- **Small and atomic**: one logical step per commit, building and passing tests on its
  own. A phase is many commits that tell how it evolved (schema → test → classifier →
  store → wiring), not one dump.
- Body when the why is not obvious; reference the ADR (`Refs: ADR-0004`).
- The assistant proposes commit messages and commits **only when the author asks**.

## Merging

- `feature/`, `fix/`, `chore/`, `docs/` → PR into `develop` with green CI.
- `develop` → `main` when a phase is closed (tests green, `docker compose up` works on a
  clean checkout). `/defend` is optional and never a merge condition. Prefer merge commits or rebase-merge over squash, so
  the small-commit history stays visible.

## What NOT to do

- No direct commits to `main` or `develop`.
- No work branches from `main`.
- No different phases on the same branch; no unrelated fixes on one fix branch.
- No force-push to `develop` or `main`.
