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
| 2 | Andalucía, Aragón, Asturias, Illes Balears, Canarias (`ccaa-01`…`ccaa-05`) | reviewed by the author, 2026-10-13 |
| 3 | Cantabria, Castilla y León, Castilla-La Mancha, Cataluña, Comunitat Valenciana (`ccaa-06`…`ccaa-10`) | reviewed by the author, 2026-10-13 |
| 4 | Extremadura, Galicia, Comunidad de Madrid, Región de Murcia, Navarra (`ccaa-11`…`ccaa-15`) | reviewed by the author, 2026-10-13 |
| 5 | País Vasco, La Rioja, Ceuta, Melilla (`ccaa-16`…`ccaa-19`) | pending |

## Known limits

- **General election of 29 Nov 2026** (Real Decreto 806/2026): the State term in force
  ends that day and a caretaker term must be added after it.
- **Caretaker rule checked** in the State (CE art. 101) and Illes Balears (Ley 1/2019,
  art. 5); still to check in the other statutes or government laws.
- **Caretaker without an election** (validated by the author): a government also becomes caretaker
  when its president ceases for another reason (resignation, disqualification) until the
  successor is appointed: Cataluña 2020 (Aragonès substituting Torra), Comunitat
  Valenciana 2025 (after Mazón's resignation).
- **Dates taken from the press because the bulletin decree was not located:** Cataluña
  2020-09-30 and 2022-10-07, Castilla y León 2024-07-12, Comunitat Valenciana 2024-07-11,
  Extremadura and Región de Murcia 2024-07-12 (Vox leaving), Galicia election 2024-02-18.
- **Independents in government are not modelled** (validated by the author): Región de Murcia from
  2021-03-10 had ex-Cs (expelled) and ex-Vox ministers; only the PP is listed as governing.
  Castilla y León 2021-12-21 uses the BOE date of the dissolution decree for the dismissal
  of the Cs ministers the day before.
- Changes after 2023 have no IDP report yet: they cite the regional bulletin (BOA), the
  official government directory (Aragón) or the official portal (Andalucía 2026), not the
  appointment decree itself.

- The State term from 2019-11-10 (caretaker, PSOE) lists no external support: it came from
  the 2018 motion of no confidence, outside the dataset window.
- Withdrawals of support during a legislature are not modelled.
- `colour_hex` is a provisional grey for every party until the web app chooses colours
  (contrast and neutrality checks).
