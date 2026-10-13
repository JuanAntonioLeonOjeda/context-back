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
| 5 | País Vasco, La Rioja, Ceuta, Melilla (`ccaa-16`…`ccaa-19`) | reviewed by the author, 2026-10-13 |

## Caretaker rule by territory

Checked on 2026-10-13 against the current consolidated text of each statute or government
law. **Convention (decided with the author):** a caretaker term starts on election day in
every territory, so terms are comparable. Five norms word it differently; for them the
convention is an approximation, documented here. Attribution is unaffected: the parties
of a caretaker government do not change.

| Territory | Norm (current version) | The government ceases… |
|---|---|---|
| es | [CE art. 101; Ley 50/1997 del Gobierno art. 21](https://www.boe.es/buscar/act.php?id=BOE-A-1978-31229) | after the election |
| ccaa-01 Andalucía | [Estatuto (LO 2/2007)](https://www.boe.es/buscar/act.php?id=BOE-A-2007-5825) | after the election |
| ccaa-02 Aragón | [Ley 2/2009 del Presidente y del Gobierno](https://www.boe.es/buscar/act.php?id=BOE-A-2009-9390) | after the election |
| ccaa-03 Asturias | [Ley 6/1984 del Presidente y del Consejo de Gobierno](https://www.boe.es/buscar/act.php?id=BOE-A-1984-19762) | renewal of the Junta as a consequence of the election (ambiguous) |
| ccaa-04 Illes Balears | Ley 1/2019 del Gobierno, art. 5 (BOIB 83/2023 quotes it) | after the election |
| ccaa-05 Canarias | [Estatuto (LO 1/2018)](https://www.boe.es/buscar/act.php?id=BOE-A-2018-15138) | after the election |
| ccaa-06 Cantabria | [Estatuto (LO 8/1981)](https://www.boe.es/buscar/act.php?id=BOE-A-1982-635) | after the election |
| ccaa-07 Castilla y León | [Estatuto (LO 14/2007)](https://www.boe.es/buscar/act.php?id=BOE-A-2007-20635) | after the election |
| ccaa-08 Castilla-La Mancha | [Estatuto (LO 9/1982)](https://www.boe.es/buscar/act.php?id=BOE-A-1982-20820) | after the election |
| ccaa-09 Cataluña | [Ley 13/2008 de la presidencia y del Gobierno](https://www.boe.es/buscar/act.php?id=BOE-A-2008-19526) | change of legislature as a consequence of the election (ambiguous) |
| ccaa-10 C. Valenciana | [Ley 5/1983 del Consell](https://www.boe.es/buscar/act.php?id=BOE-A-1984-3460) | renewal of Les Corts as a consequence of the election (ambiguous) |
| ccaa-11 Extremadura | [Estatuto (LO 1/2011), which prevails over Ley 1/2002](https://www.boe.es/buscar/act.php?id=BOE-A-2011-1638) | after the election |
| ccaa-12 Galicia | [Estatuto (LO 1/1981)](https://www.boe.es/buscar/act.php?id=BOE-A-1981-9564) | after the election |
| ccaa-13 Madrid | [Estatuto (LO 3/1983)](https://www.boe.es/buscar/act.php?id=BOE-A-1983-6317) | after the election |
| ccaa-14 Región de Murcia | [Estatuto (LO 4/1982): end of the Assembly's period; Ley 6/2004: dissolution of the Assembly](https://www.boe.es/buscar/act.php?id=BOE-A-2005-14442) | dissolution / end of period (differs) |
| ccaa-15 Navarra | [LORAFNA (LO 13/1982)](https://www.boe.es/buscar/act.php?id=BOE-A-1982-20824) | after the election |
| ccaa-16 País Vasco | [Estatuto (LO 3/1979)](https://www.boe.es/buscar/act.php?id=BOE-A-1979-30177) | after the election |
| ccaa-17 La Rioja | [Estatuto (LO 3/1982)](https://www.boe.es/buscar/act.php?id=BOE-A-1982-15030) | dissolution of the Parliament (differs) |
| ccaa-18 Ceuta | [Estatuto (LO 1/1995)](https://www.boe.es/buscar/act.php?id=BOE-A-1995-6358) | after the election |
| ccaa-19 Melilla | [Estatuto (LO 2/1995)](https://www.boe.es/buscar/act.php?id=BOE-A-1995-6359) | after the election |

## Known limits

- **General election of 29 Nov 2026** (Real Decreto 806/2026): the State term in force
  ends that day and a caretaker term must be added after it.
- **Caretaker without an election** (validated by the author): a government also becomes caretaker
  when its president ceases for another reason (resignation, disqualification) until the
  successor is appointed: Cataluña 2020 (Aragonès substituting Torra), Comunitat
  Valenciana 2025 (after Mazón's resignation).
- **Dates taken from the press because the bulletin decree was not located:** Cataluña
  2020-09-30 and 2022-10-07, Castilla y León 2024-07-12, Comunitat Valenciana 2024-07-11,
  Extremadura and Región de Murcia 2024-07-12 (Vox leaving), Galicia election 2024-02-18.
- **Independents in government are not modelled** (validated by the author): Región de Murcia from
  2021-03-10 (ex-Cs and ex-Vox ministers), La Rioja from 2022-04-04 (minister expelled from
  Podemos), Melilla from 2021-04-02 (president expelled from Cs).
- **Ceuta and Melilla** elect as president the head of the most voted list when nobody has
  an absolute majority, so there may be no investiture vote to derive external support from.
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
