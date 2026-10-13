---
name: architecture-decision
description: When an Architecture Decision Record is needed and how to write it with the author, so the reasoning in docs/adr/ is genuinely theirs. Use it when a plan step, review or /defend reveals a decision, or via /new-adr.
---

# Architecture decisions (ADRs)

ADRs are the strongest evidence in this repo that the author has judgement. They are
short, honest and written in the author's reasoning. ADRs for the whole project (back and
front) live here, in `docs/adr/`; the front repo links to them.

## When an ADR is needed

Write one when a choice:
- is hard to reverse later (data model, similarity threshold semantics, attribution
  rule), or
- has a real alternative a reviewer might prefer (own model vs. LLM, extractive vs.
  generated summaries), or
- sets a behaviour users notice (how a party is attributed, which outlets appear), or
- deviates from the brief.

Not for: naming, folder tweaks, a library patch version.

## Already identified — to be written as each phase reaches them

| Topic | Phase |
|---|---|
| Migration tool, ORM or query layer, test layout | foundation |
| Taxonomy of sectors and how a new sector is added | foundation |
| How a government (coalitions, minority with support, caretaker) is modelled | map-governments |
| Source selection criteria and the published outlet list | news-live |
| Classifier port, LLM proposal flow and promotion criteria for the own model | news-live |
| Similarity model, fixed version, thresholds and window for "same story" | story-contrast |
| Link types between stories and the minimum confidence shown | history-trace |
| Indicator definitions, deflators and how breaks in series are shown | context-voters |
| Voter profile method and its wording (ecological inference) | context-voters |
| Verdict scale and the human review rule | verification |

## How to write it together

1. The assistant explains the problem and lists options with verifiable pros/cons
   (marking unverified claims).
2. The author decides and states why, in their own words — in Spanish in the chat is
   fine.
3. The assistant writes it in English from `docs/adr/template.md`, preserving the
   author's argument, and adds it to `docs/adr/README.md`.
4. Status: `Proposed` while the phase is open, `Accepted` when merged. Never rewrite an
   accepted ADR's decision: supersede it with a new one.

Shortcut: `/new-adr <title>`.
