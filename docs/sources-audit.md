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

## Decisions taken with the author (2026-10-13)

- El Periódico and El Economista are excluded (no usable access; protection not bypassed).
- RTVE and 3Cat are collected from section pages allowed by their `robots.txt` (RTVE's
  list dates in the URL; 3Cat needs the article page for the date).
- RTVC and Telemadrid: the lead is the article page's `og:description` (public metadata).
- Measured diversity: fallback of the criterion (audience plus RTVE, figures published).
- Collection paths per outlet: `data/news/feeds.csv`.

## Pending in this task

4. GDELT coverage of the pilot outlets.
5. INE table ids (population, income, education level, housing prices and rents).
6. Election results by municipality.
7. Terms of use of each outlet.
8. Most-read private regional outlets in the pilot (GfK DAM regional figures).
