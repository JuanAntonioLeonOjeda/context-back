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
- **Party membership** of presidents and ministers is not stated in official decrees; the
  cited decree proves the appointment, membership is public record.

## Batches

| Batch | Territories | Status |
|---|---|---|
| 1 | State (`es`) | reviewed by the author, 2026-10-13 |
| 2–5 | communities, five at a time | pending |

## Known limits

- The State term from 2019-11-10 (caretaker, PSOE) lists no external support: it came from
  the 2018 motion of no confidence, outside the dataset window.
- Withdrawals of support during a legislature are not modelled.
- `colour_hex` is a provisional grey for every party until the web app chooses colours
  (contrast and neutrality checks).
