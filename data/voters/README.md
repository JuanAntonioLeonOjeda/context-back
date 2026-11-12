# Voters data

## `candidature-parties.csv`

Which party of `data/governments/parties.csv` a candidature of an election counts as, so a voter
profile names and colours votes the way the rest of the site does (phase `context-voters`, spec
decision 6). One row per election and **candidature**, by the code the Ministerio del Interior's
file gives it (file `03`, positions 9–14).

The rule (decided by the author on 2026-11-12; before, the table followed the file's national
accumulation head, which made PSC count as PSOE):

- **A candidature gets a row only when it is a party of the party table.** The same party under
  another code is that party: the PP's lists in Cataluña and the Illes Balears, Sumar's lists
  named Sumar (Andalucía, Aragón, Canarias, Galicia). `SUMAR ARAGÓN` counts as Sumar by its name
  (author's decision, 2026-11-12); who made up that list was not checked.
- **A party with its own row in the party table is itself**, whatever the file adds it up to:
  PSC is `psc`, not `psoe`.
- **A territorial federation counts as its party**: PSdeG-PSOE, PSE-EE (PSOE), PSN-PSOE and
  PSIB-PSOE are `psoe`, as in the governments dataset.
- **A coalition has no row**, even when it is named after its main party: `SUMAR - ECP`,
  `SUMAR - COMPROMÍS`, `MÉS PER MALLORCA-MÉS PER MENORCA-SUMAR`, `CUP-PR`, `NC-bc`, `EXISTE`
  (both Aragón Existe and Teruel Existe ran as "Coalición Existe").
- **A candidature without a row** is shown with its acronym from the file and a neutral colour
  when it reaches the 3 % threshold in a community (in 2023, for example, UPN in Navarra and
  `SUMAR - ECP` in Cataluña), and adds up to "Otras" otherwise. No party colour is invented for it.

- **Source**: the Infoelectoral file of the election (`02202307_MUNI.zip` for the July 2023
  Congreso), downloaded by hand (`docs/sources-audit.md`, section 10). `acronym_in_file` is the
  acronym as the file writes it, to check a row against the file; the code does not read it.
- The reader refuses a row that does not validate and a candidature written twice, with the line.
- The 2023 rows cover the candidatures with 92.6 % of the valid votes (blank votes count as
  valid). The election of 29 November 2026 needs its own rows: candidature codes change from one
  election to the next.
