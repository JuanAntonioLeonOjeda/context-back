---
description: Create a pull request into develop with conventional commits, local checks and a generated description
allowed-tools: Bash, Read
---

# Create PR

Create a pull request with `gh` from the current branch into `develop` (never into
`main`, except the `develop → main` release PR).

## Workflow

1. Ask: "Do you want to reference an issue, or a phase task in `specs/<phase>/tasks.md`?"
2. Check the branch name follows `.claude/workflows/git-workflow.md`.
3. Run the local checks and stop if any fails: `uv run ruff check .`, `uv run ruff format --check .`,
   `uv run mypy`, `uv run pytest` (and `uv run pytest -m integration` if the diff touches
   migrations, repositories or ingestion and Docker is available). Report the exact output of failures.
4. Analyse the commits on the branch (`git log develop..HEAD`) and the diff
   (`git diff develop...HEAD`). If there are uncommitted changes, ask before committing
   them, and propose a Conventional Commit message `<type>(<scope>): <subject>`
   (types: feat, fix, docs, refactor, test, chore, ci, build; scope = module or area:
   `api`, `news`, `classification`, `stories`, `governments`, `indicators`, `voters`,
   `db`, `adr`).
5. Generate the title and description:
   - **Context**: which phase/task and why.
   - **Changes**: grouped by module.
   - **Decisions**: ADRs added or updated (links). If the change contains a decision
     without an ADR, say so.
   - **How to verify**: commands and, for runtime behaviour, the manual check.
   - **Checklist** (below).
6. Show title and description and **wait for confirmation** before publishing.
7. `gh pr create --base develop --title ... --body ...`.

## PR checklist

- [ ] Commits are small and follow Conventional Commits
- [ ] Lint, typecheck and tests pass locally
- [ ] Decisions are recorded in `docs/adr/`
- [ ] Core-zone changes are understood and can be explained without the assistant
- [ ] `AGENTS.md` route map updated if paths were created or finished
- [ ] No secrets, `.env`, password files or private keys in the diff
