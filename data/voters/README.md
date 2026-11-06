# Voters data

## `candidature-parties.csv`

Which party of `data/governments/parties.csv` each candidature of an election belongs to, so a
voter profile names and colours votes the way the rest of the site does (phase `context-voters`,
spec decision 6). One row per election and **national accumulation head**: the candidature that
the Ministerio del Interior's own file (file `03`, positions 227–232) says a list adds up to
nationally. So PSC, PSdeG-PSOE and PSE-EE count as PSOE, and Sumar's lists in each community
(Sumar-ECP, Sumar-Compromís…) as Sumar, without a row each.

- **Source**: the Infoelectoral file of the election (`02202307_MUNI.zip` for the July 2023
  Congreso), downloaded by hand (`docs/sources-audit.md`, section 10). `acronym_in_file` is the
  acronym as the file writes it, to check a row against the file.
- **Curated by hand, 2026-11-06**: a head gets a row only when it is the same party as a row of
  the party table. Two are coalitions named after their main party: `CUP-PR` (CUP's list "per la
  ruptura") as CUP, and `NC-bc` (Nueva Canarias–Bloque Canarista) as Nueva Canarias.
- **Left out on purpose**: `EXISTE` (Aragón Existe–Coalición Existe) is not the same list as
  Teruel Existe of the party table.
- **A candidature without a row** is shown with its acronym from the file and a neutral colour
  when it reaches the 3 % threshold in a community (amendment of 2026-11-06 to decision 6: in
  2023 that is UPN in Navarra, 15.3 %), and adds up to "Otras" otherwise. No party colour is
  invented for it.
- The 2023 rows cover the heads with 97.2 % of the valid votes (blank votes count as valid). The election of 29 November 2026
  needs its own rows: candidature codes change from one election to the next.
