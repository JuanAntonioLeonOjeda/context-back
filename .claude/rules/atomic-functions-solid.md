---
description: Atomic functions and the practical SOLID that applies to this Python data/API project.
---

# Atomic functions and SOLID

## Atomic functions

- A function does **one** thing. If its description needs an "and"
  (`classify_and_store()`), it is two functions.
- No hidden side effects: a function that computes something does not also write to the
  database, call the LLM or log business events. Split into a pure function that decides
  and a thin one that applies the decision. Classification rules, similarity
  scoring and indicator calculations **must** be pure.
- Practical limit: past ~25 lines or 2–3 levels of nesting, extract sub-functions whose
  names explain each step. The name replaces the comment you were about to write.
- More than 3 positional parameters → keyword-only arguments or a small dataclass.

## SOLID, only what is actionable here

**S — single responsibility.** The feed reader fetches and parses items; the classifier
labels one article; the story linker decides whether two articles belong together. None
does the others' job.

**O — open/closed.** A new sector is a new entry in the sector taxonomy plus its
indicators, not another `if sector == ...` in the classifier. A new news source is a new
feed adapter registered in the source list.

**L — Liskov.** Any `ArticleClassifier` (LLM-backed, own model, rules, in-memory fake)
honours the same contract: same output schema, same confidence semantics, same errors.

**I — interface segregation.** A use case that only reads governments gets a read-only
port, not the full repository.

**D — dependency inversion.** Use cases depend on ports (`typing.Protocol`); the
composition root binds adapters. Time is a dependency too (`Clock`), so "articles from
the last 7 days" is testable.

## When NOT to apply this literally

SOLID is a guide, not a checklist for every 10-line file. Do not add a port, a factory or
a strategy for something with one implementation and no test need. Over-engineering is as
hard to defend in an interview as messy code.
