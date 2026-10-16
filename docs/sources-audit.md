# Sources audit (phase `foundation`, task 15)

What the brief assumed about each source, what was checked, on which date and with which
result. Only checked facts go to the `news-sources` skill. Downloads were made with an
honest user agent (`datos-portfolio-audit/0.1; research`); no bot protection was bypassed.

## 1. Outlet feeds (checked 2026-10-13)

| Outlet | Access | Feed or sitemap used | Items | Date | Lead | Notes |
|---|---|---|---|---|---|---|
| El Español | RSS | `/rss/`, `/rss/espana/` | 30 each | yes | yes | España ~21/day |
| El Mundo | RSS | `e00-elmundo.uecdn.es/elmundo/rss/portada.xml`, `espana.xml` | 25 / 45 | yes | yes | España ~15/day |
| El País | RSS | `feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada`, `/section/espana/portada` | 150 / 19 | yes | yes | home page returns 403 to automated clients; feeds work |
| ABC | RSS | `/rss/2.0/portada/`, `/rss/2.0/espana/` | 25 each | yes | yes | short window (feed refreshes fast) |
| El Confidencial | RSS | `rss.elconfidencial.com/espana/` | 15 | yes | yes | |
| OKdiario | RSS | `/feed`, `/espana/feed` | 50 each | yes | yes | España ~47/day |
| 20 Minutos | RSS | `/rss/`, `/rss/nacional/` | 190 / 34 | yes | yes | |
| La Razón | RSS | `/?outputType=xml`, `/espana/?outputType=xml` | 195 / 15 | yes | yes | |
| La Vanguardia | RSS | `/rss/home.xml`, `/rss/politica.xml` | 138 / 100 | yes | yes | Política ~25/day |
| El Periódico | **blocked** | — | — | — | — | feeds and `robots.txt` answer 406 to automated clients |
| El Economista | **blocked** | — | — | — | — | feeds and `robots.txt` answer 403 to automated clients |
| RTVE | **none current** | — | — | — | — | classic RSS (`api2.rtve.es/rss/…`) last item 2022; news sitemap mixes years (newest 2026-09-14); `sitemaps/noticias/sitemap.xml` is an archive capped at 50,000 URLs ending 2025-03-17 |
| RTVC | news sitemap | `rtvc.es/sitemap-news.xml` | 72 | yes | **no** | `robots.txt` disallows `/feed`; sitemap allowed |
| Telemadrid | news sitemap | `/sitemap_google_news.xml` | 30 | yes | **no** | |
| 3Cat | **none found** | — | — | — | — | no feed or sitemap found; `robots.txt` declares none |

## 2. robots.txt (checked 2026-10-13)

- No outlet disallows crawling for `User-agent: *`.
- Feed paths are allowed everywhere except RTVC (`/feed` disallowed) and ABC's widget feeds
  (`/comunabc/Widgets/rss/`, not used).
- El Periódico and El Economista do not serve `robots.txt` to automated clients.
- Terms of use have not been read outlet by outlet yet (pending, see section 7).

## 3. Measured diversity (step 3 of the outlet criterion, checked 2026-10-13)

- CIS barometer of May 2026 (study 3562, tabulations by ideology): no question on
  specific outlets.
- Reuters Institute Digital News Report España 2026 (University of Navarra): ideology is
  reported for trust and attitudes, not per outlet audience.
- Closest per-outlet measure found: EsadeEcPol Insight 41 (2022), based on DNR 2022 data.
- **Result:** no current, per-outlet measure of audience ideology was found.

## 4. GDELT (checked 2026-10-13)

- DOC 2.0 API: returns articles from 2021 (El Mundo, March 2021), 250 records per query,
  and throttles hard (one request every 5 s; repeated refusals even at 15 s).
- Raw files: the main GKG stream barely contains Spanish outlets; Spanish-language news is
  in the **Translingual** stream (`*.translation.gkg.csv.zip`).
- Coverage sample (12 of 96 Translingual files of one day):

| Outlet | 2026-10-12 | 2021-03-10 |
|---|---|---|
| La Razón | 75 | 3 |
| ABC | 51 | 5 |
| El Confidencial | 37 | 6 |
| 20 Minutos | 21 | 83 |
| El País | 17 | 16 |
| El Mundo | 2 | 16 |
| La Vanguardia | 0 | 25 |
| El Español, OKdiario | 0 | 0 |
| RTVE | 2 | 0 |
| Canarias7 | 7 | 8 |
| 3Cat / CCMA | 8 | 7 |
| Telemadrid, RTVC, El Día, Diario de Avisos, La Provincia | 0 | 0 |

- **Result:** coverage is partial and very uneven between outlets and years. A history built
  only from GDELT would over-represent some outlets: a coverage bias. ADR-0002 must be
  revisited (task 22): per-outlet sitemap archives as the main source, GDELT as a
  complement.

## 5. INE (checked 2026-10-13, Tempus API `servicios.ine.es/wstempus/js/ES/`)

| Indicator | Operation | Table | Notes |
|---|---|---|---|
| Population by community | ECP (Estadística Continua de Población) | 56940 | 56934 is national only |
| At-risk-of-poverty rate by community | ECV | 29282 | |
| AROPE (poverty or social exclusion) by community | ECV | 60264 | |
| Education level attained by community | EPA | 66104 | |
| Unemployment rate by community | EPA | 14506 | |
| Housing price index by community (quarterly) | IPV | 80270 | live value read: Q2 2026, +12.2 % year on year (national) |
| Rent price index by community | IPVA | 59056 | |
| Income by municipality (voter profiles) | ADRH | one table per province ("Indicadores de renta media y mediana") | |

- Mean income per person by community (ECV) not identified by table name yet; choose in
  phase `map-governments`.

## 6. Election results (checked 2026-10-13)

- General, municipal and European elections by municipality: Ministerio del Interior,
  Infoelectoral download area; open tooling exists (rOpenSpain `infoelectoral`).
- Regional elections of the pilot (Canarias, Madrid, Cataluña) by municipality: not
  located yet; needed only in phase `context-voters`.

## 7. Intellectual property and text and data mining (checked 2026-10-13)

Not legal advice, and none will be sought: a personal, non-commercial project that stays within what
each site allows (ADR-0019). Where a site does not allow something, it is not done.

- **LPI art. 129 bis** (press publishers' right): exclusive right over reproduction and
  making available online of press publications. Free uses include **hyperlinks** and
  **"palabras sueltas o extractos muy breves o poco significativos"** that do not harm the
  publisher's investment. A full lead is unlikely to qualify as a very short extract.
- **LPI art. 32.2:** news aggregators need the right holders' authorisation for texts or
  fragments of press publications.
- **RDL 24/2021 art. 67** (text and data mining): reproductions of lawfully accessible works
  for mining need no authorisation and may be kept as long as needed, **unless the right
  holder reserved them expressly by machine-readable means**.
- Reservations found:
  - **20 Minutos:** `<meta name="tdm-reservation" content="1">` with a `tdm-policy` link:
    an express machine-readable reservation.
  - El Mundo, El País, ABC, El Confidencial, 20 Minutos, La Razón and La Vanguardia block
    known AI crawlers (GPTBot, ClaudeBot, CCBot…) in `robots.txt`. Whether that counts as
    a reservation under art. 67.3 is a legal question.
  - No outlet publishes `/.well-known/tdmrep.json`.

## 8. Most-read private regional outlets in the pilot (checked 2026-10-13)

- Official GfK DAM regional figures are not public; outlets publish their own releases.
- Canarias, audience within Canarias (Canarias7 release citing GfK DAM, April 2026):
  Canarias7 (Las Palmas) first, El Día (Santa Cruz) second. Diario de Avisos reports
  total audience instead, with itself first.
- Cataluña: no within-community GfK DAM figure found; a Catalan-language ranking
  (comunicació21, February 2026) puts ElNacional.cat first.

## 9. Congreso votes (checked 2026-10-15, for phase `parliament-votes`)

- Source: `https://www.congreso.es/es/opendata/votaciones`, one page per plenary session with a
  ZIP of the session and, per vote, PDF, XML and JSON. Legislatures X to XV listed.
- Path: `/webpublica/opendata/votaciones/Leg15/Sesion{n}/{yyyymmdd}/Votacion{nnn}/VOT_{timestamp}.json`.
  The timestamp differs per file, so the file names are read from the session page, not built.
- Contents, checked on session 202, vote 1 (2026-09-30): `informacion` (session, number, date,
  title, the initiative's text), `totales` (present, yes, no, abstentions, not voting) and
  `votaciones`, one row per deputy with seat, name, group code (`GP`, `GS`, `GVOX`, `GMx`…) and
  vote (`Sí`, `No`, `Abstención`, `No vota`). 350 rows; the Grupo Mixto split 6 / 2 / 1.
- Reuse conditions (Congreso legal notice, "Reutilización de información"): the content is not
  altered, its meaning is not distorted, the source is cited and the date of the last update is
  stated.
- elcongresoentumano.es (independent, donation-funded) republishes these votes with its own API;
  its summaries and "popular names" are its own, under CC BY 4.0, and it states they are
  unchecked automatic interpretation. Not used as a source: the project reads the Congreso.
- Regional parliaments: not checked yet.

## Decisions taken with the author (2026-10-13)

- El Periódico and El Economista are excluded (no usable access; protection not bypassed).
- RTVE and 3Cat are collected from section pages allowed by their `robots.txt` (RTVE's
  list dates in the URL; 3Cat needs the article page for the date).
- RTVC and Telemadrid: the lead is the article page's `og:description` (public metadata).
- Measured diversity: fallback of the criterion (audience plus RTVE, figures published).
- Collection paths per outlet: `data/news/feeds.csv`.
- **Published:** headline and link only; the lead is processed internally under the mining
  exception and never shown.
- **20 Minutos excluded** (express mining reservation).
- **Outlets blocking AI crawlers** (El Mundo, El País, ABC, El Confidencial, La Razón, La
  Vanguardia, Canarias7) are processed only by rules and local models, never by an
  external LLM (`external_llm_allowed = false`).
- **Canarias:** Canarias7 (Las Palmas) and Diario de Avisos (Santa Cruz; El Día answers
  406). Both feeds checked: Canarias7 100 items with leads, Diario de Avisos 20 items
  (~33/day). **Cataluña:** private outlet pending a within-community audience figure.
- **GDELT** is a complement, not the main history source (to revise in ADR-0002).

