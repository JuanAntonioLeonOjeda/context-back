# Governments

Who governed the State and each community since 2020-01-01. Rules: `specs/foundation/plan.md`,
"Governments dataset rules". Built in batches reviewed by the author.

| File | One row per |
|---|---|
| `parties.csv` | party, as the brand that appears in government |
| `government_terms.csv` | term: territory, period `[valid_from, valid_to)`, president, caretaker flag, source |
| `government_term_parties.csv` | party of a term (key: `territory_id` + `valid_from`), its role and the source of that role |

## How each fact is sourced

- **Term start:** BOE decree appointing the president (or regional bulletin decree that
  changes the composition).
- **Caretaker term:** starts on election day (State: CE art. 101); the source is the decree
  that dissolves the chamber and calls the election, which fixes that date. A caretaker term
  keeps the parties and supporters of the term it continues.
- **Coalition partner:** the decree appointing that party's leader as vice-president.
- **External support:** the investiture vote in the parliament's session diary (roll call).
  Per-party counts are taken from press reports and checked against the official totals.
- **Communities:** parties and supporters come from the Instituto de Derecho Público's
  "Informe Comunidades Autónomas" of that community and year; the BOE decree still dates
  the term. Without a published report (current year), the regional bulletin or the
  parliament's record is cited.
- A party that leaves a government is not its external support; abstaining is not
  supporting; PSOE federations are `psoe`, the PSC is separate.
- **Party membership** of presidents and ministers is not stated in official decrees; the
  cited decree proves the appointment, membership is public record.

## Batches

| Batch | Territories | Status |
|---|---|---|
| 1 | State (`es`) | reviewed by the author, 2026-10-13 |
| 2 | Andalucía, Aragón, Asturias, Illes Balears, Canarias (`ccaa-01`…`ccaa-05`) | in review |
| 3–5 | the other communities, five at a time | pending |

## Known limits

- **General election of 29 Nov 2026** (Real Decreto 806/2026): the State term in force
  ends that day and a caretaker term must be added after it.
- **Caretaker rule checked** in the State (CE art. 101) and Illes Balears (Ley 1/2019,
  art. 5); still to check in the other statutes or government laws.
- Changes after 2023 have no IDP report yet: they cite the regional bulletin (BOA), the
  official government directory (Aragón) or the official portal (Andalucía 2026), not the
  appointment decree itself.

- The State term from 2019-11-10 (caretaker, PSOE) lists no external support: it came from
  the 2018 motion of no confidence, outside the dataset window.
- Withdrawals of support during a legislature are not modelled.
- `colour_hex` is a provisional grey for every party until the web app chooses colours
  (contrast and neutrality checks).
