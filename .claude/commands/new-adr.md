---
description: Create a new Architecture Decision Record together with the author — the assistant structures and asks, the author decides
argument-hint: <decision title>
allowed-tools: Read, Write, Edit, Glob, Bash(ls:*)
---

# New ADR: $ARGUMENTS

Follow `.claude/workflows/architecture-decision.md`.

1. Find the next number in `docs/adr/` (`NNNN`, zero-padded) and the kebab-case file name
   from the title.
2. Before writing anything, ask the author, one block at a time:
   - **Context**: what problem forces a decision now? What constraints matter (brief,
     phase, hardware, cost)?
   - **Options**: which options do they see? Add the ones they missed, each with
     verifiable pros and cons. Mark unverified claims as such.
   - **Decision**: which one and why — in their words. Do not choose for them; if they
     ask for a recommendation, give one with its reasoning, then let them decide.
   - **Consequences**: what gets easier, what gets harder, what would make us revisit it.
3. Write `docs/adr/NNNN-<title>.md` from `docs/adr/template.md` with their answers,
   keeping their reasoning (tidy the English, do not replace the argument).
4. Add it to the index in `docs/adr/README.md`.
5. If it supersedes another ADR, mark the old one `Superseded by ADR-NNNN`.
6. Suggest a commit: `docs(adr): add ADR-NNNN <title>` — do not commit unless asked.
