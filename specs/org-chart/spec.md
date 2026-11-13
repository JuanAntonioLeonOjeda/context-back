# Phase 8 — org-chart: spec

## What it solves

The site says who governs (the parties, from the BOE) and shows the community's news and figures.
It does not say **which bodies exist, who holds the posts of the executive, or what competences
each body has by law**. This phase adds an organisation chart for each community and a general one
(State, community, local), with a link "Ver organigrama" on each community page.

It states facts about **bodies and posts**, each with its source. It says nothing about who is
responsible for anything, and never puts a party next to a person.

## Out of scope

- Using the competences to decide the level of responsibility of a news item (it would reopen
  ADR-0018 and needs its own ADR).
- A second level (secretarios generales, directores generales), history before today and any person
  who is not the president or a consejero/ministro.
- Names for parliaments, the judiciary and local bodies (generic boxes only; an optional later batch
  may add the presidents of the parliaments, the TSJ and the CGPJ).
- The party of a post holder, anywhere.
- The sixteen communities outside the pilot.
- Reading regional gazettes or government pages automatically (`docs/sources-audit.md`, section 11).

## Decisions (2026-11-12 and 2026-11-13, the author)

1. Phase 5 closes first (done); this phase opens afterwards.
2. Depth: president and consejeros (ministers for the State).
3. Only the current composition, each holder with `valid_from` / `valid_to`, so the history grows
   from now.
4. Competences: a short summary in our words, the article and a link, each body mapped to the 12
   sectors.
5. Local level generic only (LRBRL: ayuntamiento, diputación, cabildo, consell), no names.
6. The general chart and each community's: the executive plus parliaments and the judiciary as
   generic boxes with competences and without names. The judiciary is one for the whole State: the
   TSJ is a separate box, not under the regional government.
7. **Pilot**: the State and Canarias, Madrid and Cataluña. The sixteen others show "sin datos
   todavía" until their batch is loaded.
8. A new ADR (not an amendment of ADR-0018): competences are shown again as facts of a body.
9. Hand-curated CSVs with one source URL per row; the BOE API only for the State; DIR3 as a
   cross-check and the source of each body's code. Names for Canarias and Cataluña are given by the
   author.

## Acceptance criteria

1. **General chart.** Given the page `/organigrama`, when it opens, then it shows the State's
   executive (president and ministers, with the date each holds the post and its source), the
   parliament and the judiciary as boxes with their competences and no names, and the community
   and local levels as generic boxes with their competences.
2. **A community's chart.** Given a pilot community, when `/comunidades/{id}/organigrama` opens, then
   it shows its president and consejeros with the official name of each consejería, the parliament
   box, the State's judiciary box with the TSJ apart, and the generic local boxes.
3. **Competences.** Given any body, then its competences appear as a summary, the legal basis (article)
   and a link, and the sectors it relates to.
4. **A community outside the pilot** shows the same page with "sin datos todavía" and no invented
   content.
5. **A community is shown only complete.** If any consejero of a pilot community has no loaded row, the
   whole executive of that community shows "sin datos todavía" (never half a government).
6. **Current only.** Given a post whose row has `valid_to` in the past, then it is not shown. A new
   holder is a new row; nothing is edited in place.
7. **Source on every row.** The loader refuses a post, a holder or a competence without a source URL,
   with the file and the line.
8. **Neutrality.** The same code path for every body; no party next to any holder; the president first
   and then the rest in alphabetical order of the body's name (never by importance); wording with no
   evaluative word.
9. **Attribution.** The State's page carries the BOE's attribution for data taken from it.
10. **Link and access.** Each community page has the "Ver organigrama" link; the chart is a nested list
    that is read in order, usable with the keyboard and without colour, and passes axe in both
    themes.
11. **Change of government.** Given the general election of 2026-11-29, when new ministers are
    appointed, then loading them closes the old rows (`valid_to`) and adds new ones, and the chart
    shows only the new ones.

## Risks

- The State's ministers change after the election of 2026-11-29: the data needs a new batch within
  days of the appointments.
- Curating about 40 posts and the competences of each body by hand is long: batches reviewed by the
  author, as the laws' topics were.
- A chart per community is where unequal treatment would show first: one path of code for all, and a
  test with the same data for two communities.
- DIR3 states no reuse terms: only official names and codes are taken, with the source named.

## Open questions

None for the pilot. For later: the TSJ and parliament presidents (optional batch) and the sixteen
other communities.
