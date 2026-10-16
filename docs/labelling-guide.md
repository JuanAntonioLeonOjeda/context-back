# Labelling guide — blind test set v1

How to label the 200 articles of `data/eval/test-set-v1.jsonl`. The test set measures every
classifier (rules, LLM, own model). Its labels must say **what the text is about**, not
what we believe about who is responsible. The site attributes no news item to a party
(ADR-0018); the levels say which government acts, and in phase 7 which parliament's laws apply.

Status: draft, pending the author's review (task 19).

## What you see and what you label

- Label **only from the headline, the tags and the lead**, the same input the classifiers get.
  The tags are the ones the outlet published with the article, already filtered (`Etiquetas: …`,
  at most eight; none when the outlet gives none). Do not open the link. If what you see is not
  enough, the right answer is the one it supports, even if the full article says more.
- No model proposal is shown. Label each article on its own, in the order given.
- Articles in Catalan follow exactly the same rules.
- If you hesitate for more than a minute, pick the best answer **and** tick `unsure`. Those
  articles get a second pass at the end of the session. Do not leave fields empty to
  signal doubt.

## The three labels

Each article gets three labels. Each one can have several values or none.

| Label | Values | Empty means |
|---|---|---|
| `communities` | ids `ccaa-01` … `ccaa-19` (appendix) | no specific community is affected |
| `sectors` | `education`, `health`, `housing` | `none`: not about public policy in these sectors |
| `government_levels` | `state`, `ccaa`, `local` | no government acts and none is addressed |

The three labels are independent. An article about an investiture debate with no sector
still gets its community and level. An article that is out of every sector is still a
valid, useful example: it is a negative.

### 1. Sector: public policy only

An article belongs to a sector when its subject is **public action in that sector**:

- a norm, decision, plan, budget or appointment of a public administration;
- how a public service performs (waiting lists, school places, public housing stock);
- a demand, proposal or criticism addressed to a government, from a party, union,
  association or court;
- a court ruling on a public norm or decision of the sector.

It does **not** belong to a sector when the sector is only the setting or a market:

- an event that happens in a hospital or a school (an illness, a crime, a celebrity);
- private market news with no public measure (mortgage offers, prices, a private
  clinic's business);
- personal stories with no policy in them.

Sector boundaries:

- **education**: from infant school to university, vocational training, scholarships,
  teachers, school buildings, curricula.
- **health**: public health care, primary care, hospitals, waiting lists, public health,
  medicines policy, health staff.
- **housing**: public and protected housing, rent regulation and stressed areas, evictions
  policy, housing aid, land for housing.

An article can have more than one sector (a plan for housing for health workers is
`housing` and `health`).

### 2. Community: the one affected

Label the communities **where the measure applies or the event happens**, whether or not
they are named.

- A city, province or island implies its community (Lanzarote → `ccaa-05`).
- A measure for the whole country has **no** community: its scope is national.
- An article about all communities as a group (a national ranking) has no community.
  Label a community only when it is a subject of the article, not one entry in a list.
- A politician from one community speaking about another: label the community the
  statement is about.

### 3. Government level: those who act or are addressed

Label every level of government that **acts** in the article or to which a **demand is
addressed**:

- `state`: the Government of Spain, ministries, state agencies (including INGESA and the
  Ministry of Education in Ceuta and Melilla), the Cortes when legislating.
- `ccaa`: regional governments and parliaments (Junta, Generalitat, Xunta, Gobierno
  Vasco, Comunidad…). Cabildos and consells insulars are not here: they are `local`.
- `local`: city councils, provincial councils (diputaciones), island councils (cabildos,
  consells insulars).

Rules:

- Parties are not governments. A party's internal life (lists, primaries) has no level.
  A party's demand to a government gets the level of that government.
- Label what the text says, not what the competence table says. If a protest asks for
  "more housing" and names no government, the level is empty. Who is competent is not
  a label.
- Courts are not a level. A ruling on a regional decree gets `ccaa`.

## Edge cases

Every example is **invented** to show a rule; none is a real headline. Each pattern is
shown with governments and parties of different colours, so no rule depends on who
governs.

| # | Invented headline + lead | communities | sectors | levels | Rule |
|---|---|---|---|---|---|
| 1 | "A footballer is admitted to a hospital in Seville after a fall" | — | none | — | sector as setting |
| 2 | "Banks offer 100% mortgages again" | — | none | — | private market |
| 3 | "The Government approves a decree to cap rent rises across Spain" | — | housing | state | national scope |
| 4 | "The PP asks the Government to withdraw the rent decree" | — | housing | state | demand to a government |
| 5 | "The Generalitat (PSC) declares 40 new stressed areas" | ccaa-09 | housing | ccaa | regional measure |
| 6 | "The Comunidad de Madrid (PP) opens a call for protected rental housing" | ccaa-13 | housing | ccaa | same pattern, other colour |
| 7 | "Más Madrid accuses the Comunidad of underfunding primary care" | ccaa-13 | health | ccaa | opposition demand |
| 8 | "The PP demands that the Gobierno de Navarra (PSOE–Geroa Bai–Contigo-Zurekin) cut waiting lists" | ccaa-15 | health | ccaa | same pattern, other party |
| 9 | "The Junta de Castilla-La Mancha (PSOE) blames the ministry for the shortage of doctors" | ccaa-08 | health | ccaa, state | both act |
| 10 | "The Xunta (PP) and the ministry clash over the funding of the MIR places" | ccaa-12 | health | ccaa, state | both act |
| 11 | "The Supreme Court annuls a state decree on new universities" | — | education | state | court ruling |
| 12 | "The TSJ annuls the Junta de Castilla-La Mancha's (PSOE) school calendar decree; the PP celebrates" | ccaa-08 | education | ccaa | court ruling, regional |
| 13 | "Teachers strike against the Gobierno de Navarra (PSOE–Geroa Bai–Contigo-Zurekin) for smaller classes" | ccaa-15 | education | ccaa | demand implied by the strike, government named |
| 14 | "Thousands march in Barcelona for the right to housing" | ccaa-09 | housing | — | no government named |
| 15 | "Teachers at a private school investigated for mistreating children" | community of the school | none | — | crime, not policy |
| 16 | "The Cabildo de Lanzarote (CC) builds 200 public flats" | ccaa-05 | housing | local | island council is local |
| 17 | "Barcelona City Council (PSC) and ERC agree on a tax on empty flats" | ccaa-09 | housing | local | city council |
| 18 | "The Basque Government (PNV–PSOE) and EH Bildu agree on Osakidetza's new staff plan" | ccaa-16 | health | ccaa | regional health service |
| 19 | "The BNG asks the Xunta (PP) for more public nursery places" | ccaa-12 | education | ccaa | demand to a government |
| 20 | "Junts and the PP vote down the Government's housing bill in Congress" | — | housing | state | Cortes legislating |
| 21 | "Sumar proposes a public housing company for the whole State" | — | housing | state | proposal for the state level |
| 22 | "Podemos and IU ask the Gobierno de Aragón (PP–Vox) for free university fees" | ccaa-02 | education | ccaa | demand to a government |
| 23 | "Coalición por Melilla asks INGESA to hire doctors for the Melilla hospital" | ccaa-19 | health | state | Ceuta/Melilla: State manages health |
| 24 | "The Ministry of Education opens 3 new schools in Ceuta" | ccaa-18 | education | state | Ceuta/Melilla: State manages education |
| 25 | "The PSOE presents its candidate in Valencia for the general election" | ccaa-10 | none | — | party life, no government |
| 26 | "The Canarian Government (CC–PP) and the State sign the housing aid agreement" | ccaa-05 | housing | ccaa, state | agreement between levels |
| 27 | "The Ajuntament de Girona (Junts) closes a health centre for repairs" | ccaa-09 | health | local | local acts, even outside its competence |
| 28 | "Opinion: why rent caps will not lower prices" | — | housing | state if the text refers to the state rule; else — | opinion pieces follow the same rules |
| 29 | "Comparison of waiting lists in all 17 communities" | — | health | — | all communities as a group |
| 30 | "The Pope undergoes surgery in a Rome hospital" | — | none | — | foreign, setting |

Rows 27 and 13 matter for neutrality: the label follows the text even when the acting
government is not the one with the competence, or the text implies the addressee. Row 13
labels `ccaa` because the strike is called against the named government, row 14 does not
because no government is named.

### Party coverage

The examples name parties in government and in opposition, at every level: PSOE, PSC,
PP, Vox, Sumar, Podemos, IU, Más Madrid, ERC, Junts, PNV, EH Bildu, CC, BNG, Compromís,
Geroa Bai, Contigo-Zurekin, Coalición por Melilla. Party labels in brackets match the governments in
force in `data/governments/` on the date of this guide. Smaller parties are not listed
one by one because no rule refers to a party: swapping the parties in any row must not
change its labels. The neutrality reviewer checks exactly that.

## Session protocol

- Two sessions of 100 articles, on different days, to limit fatigue.
- At the end of each session, review the `unsure` articles once more. Then the labels are
  final.
- After the second session, relabel 20 random articles from the first session without
  looking at the previous labels. The agreement with yourself is reported with the test
  set; disagreements point to rules this guide must make clearer (a new guide version,
  not a silent edit of v1).
- Any rule added during labelling is written here with the date, and the articles already
  labelled are checked against it.

## Appendix: community ids

| id | Community | id | Community |
|---|---|---|---|
| ccaa-01 | Andalucía | ccaa-11 | Extremadura |
| ccaa-02 | Aragón | ccaa-12 | Galicia |
| ccaa-03 | Principado de Asturias | ccaa-13 | Comunidad de Madrid |
| ccaa-04 | Illes Balears | ccaa-14 | Región de Murcia |
| ccaa-05 | Canarias | ccaa-15 | Comunidad Foral de Navarra |
| ccaa-06 | Cantabria | ccaa-16 | País Vasco |
| ccaa-07 | Castilla y León | ccaa-17 | La Rioja |
| ccaa-08 | Castilla-La Mancha | ccaa-18 | Ceuta |
| ccaa-09 | Cataluña | ccaa-19 | Melilla |
| ccaa-10 | Comunitat Valenciana | | |
