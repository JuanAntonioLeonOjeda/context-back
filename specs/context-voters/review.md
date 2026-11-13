# Review of the context-voters phase (2026-11-12)

Five read-only reviews of `origin/develop...HEAD` on the `feature/context-voters` branch of both
repos, with the criteria of `py-reviewer` and `neutrality-reviewer` (back) and `ts-reviewer`,
`accessibility-reviewer` and `neutrality-reviewer` (front). The accessibility part is static plus
axe in jsdom, and the section was looked at in Chrome at phone width and in the dark theme: that
does not show conformance.

No must-fix finding. The author accepted every recommended fix and decided the open points; this
file lists each finding with what was done. The checks that passed are not listed.

## Back

| Finding | Outcome |
|---|---|
| Migration `0015`: `elections` and `election_candidatures` had no append-only triggers, unlike the other three tables | **fixed** (`99db53e`): the revision is not on `main`, so it was edited; a test covers UPDATE, DELETE and TRUNCATE on the five tables |
| `pg_voters_reader`: the inner joins dropped a municipality with no vote rows, with its census and blank votes | **fixed** (`d4ab116`): left joins; the municipality comes once, without counts |
| `candidature_parties`: the CSV was read without a row model and a repeated national head let the later row win | **fixed** (`ac9d5fa`): each row validated; a bad row, a repeated head or a missing file stop the load with file and line |
| `infoelectoral`: a missing file, a file that is not a zip, a damaged one or bytes that are not cp1252 escaped as plain Python errors, past the command's handler | **fixed** (`0bf4ae7`): all four are `InvalidElectionFileError`; the zip is opened from the bytes that were hashed |
| `load_income`: a year without data stored nothing and exited 0, like a load with nothing new | **fixed** (`5c98c0a`): an answer without any municipality is an error |
| `adrh_source`: income not rounded to the column's two decimals; `profile.band_index`: division by zero when the municipalities with income have no census | **fixed** (`2054931`): cents, half up; no profile without any census. That case is reported as `too_few_municipalities`, which is not exact; it does not happen with real data |
| Tests: no DELETE or TRUNCATE case for `municipal_income`, no row-level case for `municipal_candidature_votes` | **fixed** with the first row (`99db53e`) |
| The 3 % threshold was written in the web app's text and nowhere in the contract | **fixed** (`15714d5`, decided by the author): `shown_from_percent` in the answer |
| The 404 of `GET /communities/{id}/voters` was not declared in the OpenAPI | **fixed** (`15714d5`, decided by the author) |
| `income.source_url` was the loader's request, not a page a reader can open; the web app had the INE page hard-coded | **fixed** (`15714d5`, decided by the author): the API sends the statistic's page; the request stays in `downloads` |
| `kind: "list"` and "a list without a party": UPN is a party | **fixed** (`15714d5`, `5c6d06f`, decided by the author): `"candidature"`, "a candidature that is not in the party table". Group ids keep the `lista:` prefix |
| "The indicator a sector is measured by" read as a measure of performance | **fixed** (`5c6d06f`, `8d392bb`, decided by the author): "the indicator shown next to the sector's news" |
| ADR-0024 "a poor community"; spec "has not governed since 2020" | **fixed** (`5c6d06f`, decided by the author): "a community with lower incomes"; "has neither governed nor given external support" |
| `candidature-parties.csv` had no single rule for coalitions: `CUP-PR` and `NC-bc` counted as their main party, PSC and Sumar's lists followed the Ministerio's national head, `EXISTE` was left out | **fixed** (decided by the author): the table and the reader go by candidature, not by national head. A party of the party table is itself (PSC), a territorial federation counts as its party, a coalition has no row and is shown apart by its acronym from 3 %. The rule is in `data/voters/README.md`, decision 6 of the spec and ADR-0024 |

## Front

| Finding | Outcome |
|---|---|
| `useVoterProfile`: the error check ran before the absent one, so a 404 of the profile plus a failed `/parties` showed an error; retry did not refetch everything | **fixed** (front `294e908`): absent first; retry refetches both; tests for a failing `/parties` and for retry |
| A party missing from the party table was drawn as a grey bar with the API's label | **fixed** (front `294e908`, decided by the author): a data error, like the map's |
| The title "Perfil de voto por renta" read as people voting by their income | **fixed** (front `294e908`, decided by the author): "Cómo votaron los municipios según su renta media" |
| "los partidos" where lists are shown too; no sentence saying the income is the election year's | **fixed** (front `294e908`): "las candidaturas"; the sentence added |
| The method note disappeared when the API sent no income | **fixed** (front `294e908`): always shown, without the year |
| Accessibility: the scrolling table could not take focus; lists styled without markers lost their semantics in Safari; a band's name was announced twice; nested `aside`; "—" cells with no text | **fixed** (front `294e908`): a focusable named region, `role="list"`, bands without `article`, `div role="group"` for the sector's figure, "Sin dato" |
| Literals "—" and " · " outside the texts file; a share of an undeclared group dropped in silence | **fixed** (front `294e908`): in `es.ts`; a zod refinement refuses the answer |
| The 3 % and the INE address written by hand; `municipalities` and `incomeSourceUrl` mapped and not used | **fixed** (front `90d1ed0`, `1d3c679`): both come from the API; the unused field is gone |
| After the coalition rule, in Chrome at 328 px in the dark theme: a long group name (the Illes Balears list with Sumar) took the whole row of its bar and left it 2 px wide | **fixed** (front `72124ba`): every row has the same columns, the name wraps in its own, the bars keep one scale |
