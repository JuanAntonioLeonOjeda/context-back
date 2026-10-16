# Rules classifier data

The terms the rules classifier (`src/datos/classification/`) uses to label an article's
communities, government levels and sectors from its headline and lead (ADR-0015). Rules are
data: a new term is a row, not code. The outlet is never an input, and no file names a party
or a politician.

Written on 2026-10-14 (task 5 of `specs/news-live/tasks.md`), to be reviewed by the author and
measured on the blind test set when it exists. Until then nothing here is a measured claim.

## Files

| File | Row | Gives |
|---|---|---|
| `places.csv` | `term, territory_id, level, kind, language` | a community; institutions (`kind = institution`) also give the level `ccaa`, parliaments (`kind = parliament`) do not |
| `levels.csv` | `term, level, language` | a government level only: `state`, `ccaa` or `local` |
| `sectors.csv` | `term, sector_id, language` | a sector: `education`, `health` or `housing` |
| `exclusions.csv` | `phrase, reason` | text removed before matching |

## How terms match

1. **Exclusions first.** Each phrase in `exclusions.csv` is removed from the text before anything
   else matches. Every exclusion has a reason, from an error seen in real headlines ("Banco
   Santander" is not Cantabria; "León XIV" is the Pope, not the province of León).
2. **Case.** A term that starts with a capital letter ("Santander", "Gobierno", "Junta") matches
   only with that capital, so a proper noun does not match a common word. A term in lower case
   ("hospital", "ayuntamiento") matches in any case.
3. **Whole words.** A term matches only on word boundaries ("CAP" is not the start of "capital").
4. **The longest term wins.** "Gobierno de Canarias" (Canarias, regional level) wins over
   "Gobierno" (State level); "Consell de Mallorca" (local) wins over "Consell" (regional).
   Overlapping shorter matches are ignored.

## Conventions, to be measured on the test set

- **An ambiguous name gives the level only, never a community.** "Junta" (four communities),
  "Generalitat" (two), "Govern" (two) and "Consell" are in `levels.csv`; the community comes from
  their longer forms in `places.csv` ("Junta de Andalucía", "Generalitat de Catalunya").
- **"Gobierno" alone is the State**, as Spanish press uses it; the regional governments appear
  with their name ("Gobierno de Canarias", "Gobierno vasco") and win as longer terms.
- **A parliament is not its government** (decided by the author, 2026-10-14). A regional
  parliament gives its community but no level, and the Cortes Generales give nothing: "el
  Parlamento rechaza la ley del PSOE" is the chamber's vote, and attributing it to the governing
  parties would be wrong. Seen in a real RTVC headline during task 10.
- **A community's name is a place, not its government.** "Comunidad de Madrid" gives the
  community but no level: "la Comunidad de Madrid aprueba" (the government) and "vivir en la
  Comunidad de Madrid" (the place) cannot be told apart by a term.
- **Cities and islands** point to their community. Only provinces (from the INE names), the
  capitals whose name differs from their province and a few large cities are listed.
- **Sector terms follow the labelling guide's boundaries** (`docs/labelling-guide.md`), in
  Spanish and Catalan. Private-market words with no public measure ("hipoteca") are left out.
  Terms that also appear in non-policy news ("hospital", "farmacia", "alquiler") are kept for
  recall: precision is the known weakness of the rules and the reason for the own model.

## Sources

- Communities and provinces: `data/territories/territories.csv` (INE), with their co-official
  forms.
- Regional institutions and public health services: the names used by each Statute of Autonomy
  and each service's own name.

## Coverage on 2026-10-14 (not an evaluation)

Run on the 2,648 articles collected by then (`python -m datos.classification classify-new`,
version `d74a59205b94`, the one after parliaments stopped giving a government level):

- A **community** is found in 36 % of the articles (964), a **government level** in 17 % (447)
  and **any sector** in 13 % (340): housing 148, education 106 and health 100.
- **153 articles have a sector and a community** and **76 a sector and a level**. Those are the
  articles the news page could place, and the attribution (ADR-0014) can be "high" only for the
  76 that name a level: the rest will read "not determined".
- Communities most named: Comunidad de Madrid (197), Canarias (173), Ceuta (163), Cataluña (155).
- Per outlet, a community is found in 22 % to 67 % of its articles and a sector in 6 % to 27 %.
  The community share is highest in the regional outlets (RTVC, Diario de Avisos, Telemadrid),
  as expected. The sector share varies for other reasons we have not looked into: the highest,
  27 %, is of an outlet with 44 articles, so it may be noise. Counts per outlet go from 44 to 569
  articles.

**Known limitation (noticed in use, 2026-10-15).** A community is assigned when the text *names* it, not
when the article is *about* it, while the labelling guide defines the community as the one affected.
An article that names a place only in passing (a comparison, a club called "Las Palmas" playing
elsewhere) gets that community as well. It is measured per community on the blind test set; if it
proves frequent, ADR-0016 already provides for the model taking communities over. Do not fix it by
adding terms after looking at test-set errors.

These numbers say how much the rules fire, not how often they are right: a sample of the sector
matches showed clear policy news next to clear noise (an illness at a wedding, news from
Hungary), the expected weakness of keywords. Precision and recall are measured on the blind test
set when it exists, overall, per outlet and per party.

## `tag-stoplist.csv`: tags the model never reads

Not part of the rules: the rules' version is a hash of the four files above and this one does not
change it. It lists the tags an outlet publishes with an article (`tags`, ADR-0019) that the model
must not read, because they say nothing about the topic and give away who published it:

- `outlet_marker`: the outlet or its section, not the topic (`Home La Razón`, `OKD`, `NLPremium`,
  `Cool`, `Actualidad`, `A fondo`, `Portada…`).
- `byline`: the author (`Artículos Manuel Marraco`, from El Mundo). A new author appears with a new
  tag, so it is one `prefix` row, not one row per author.

`tag` is in key form (lower case, single spaces: the form the database stores), and the loader
rejects any row that is not. `match` is `exact` (the whole tag) or `prefix` (the tag, or the tag
followed by more words: `portada` matches `portada local`, not `portadas`). A tag is compared by its
key, so `Home La Razón` and `home  la razón` are the same entry.

The tags themselves are stored as the outlet wrote them: the list is applied when the text for the
model is built, so changing it never needs a new collection. Its version is a hash of the file; a
model's card and a labelling sample record the one they used.

Written on 2026-10-16 from the 1,210 tags stored that day: each entry above appears in a single
outlet. It is a judgement, not a measurement; the author reviews it before it is used.
