---
paths:
  - "data/governments/**"
  - "src/datos/governments/**"
  - "src/datos/classification/**"
  - "src/datos/stories/**"
  - "src/datos/indicators/**"
  - "src/datos/voters/**"
  - "migrations/**"
  - "src/datos/**/infrastructure/*repository*"
---

# You are in a core zone

These files are what an interviewer will ask the author to explain or change live.
Follow `.claude/rules/ai-collaboration.md`, section 2:

1. Explain the concept and the options first, without code.
2. Ask: does the author write it, write it together, or want it written with an
   explanation?
3. One small unit at a time, every non-obvious line explained, wait for review.
4. Close with 2–3 interview questions about what was just built.

Also:

- If the change embodies a decision (a threshold, a competence assignment, a deflator,
  an index), check that an ADR covers it; if not, propose `/new-adr`.
- Changes to the competence table or the governments dataset cite their source (BOE,
  parliament, official results) in the file.
- Never mark a task in a core zone as done while its tests fail.
