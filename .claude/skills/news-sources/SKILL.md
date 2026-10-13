---
name: news-sources
description: Verified facts about the news outlets and data sources of this project - which outlets are collected and how (RSS, news sitemaps, section pages), what may be published or processed under Spanish IP law, which outlets must never reach an external LLM, GDELT's coverage bias, and the INE and election data sources. Use it before writing or changing any collector, classifier input, or anything that displays news content.
---

# News sources

Everything here was checked on 2026-10-13 and is recorded with evidence in
`docs/sources-audit.md`. Unverified points are marked. Re-check before relying on a fact
older than a few months: feeds and `robots.txt` change without notice.

## Outlets and how to collect them

- The list is `data/news/outlets.csv`; the collection paths are `data/news/feeds.csv`
  (`rss`, `news_sitemap`, `html_section`). Selection rule: `specs/foundation/plan.md`.
- RSS with date and lead: El Español, El Mundo, El País, ABC, El Confidencial, OKdiario,
  La Razón, La Vanguardia, Canarias7, Diario de Avisos.
- News sitemap (title and date, no lead): RTVC, Telemadrid. Lead = the article page's
  `og:description`.
- Section pages only: RTVE (date in the URL), 3Cat (date from the article page).
- Use an honest user agent. Never bypass bot protection: El Periódico, El Economista and
  El Día answer 403/406 to automated clients and are excluded for that reason.

## What may be published and processed (not legal advice)

- Publish **headline and link only** (LPI art. 129 bis: hyperlinks and very short extracts
  are free; a full lead probably is not). Never display leads; never store bodies.
- Store and process leads only under the mining exception (RDL 24/2021 art. 67), which
  does not apply when the outlet reserved it by machine-readable means.
- 20 Minutos reserves mining (`tdm-reservation = 1`): excluded.
- `external_llm_allowed = false` (outlets blocking AI crawlers in `robots.txt`): their text
  goes only to rules and local models, never to an external LLM. Check this flag in any
  code path that calls an LLM.

## History

- GDELT's Translingual stream has Spanish news but very uneven coverage (several pilot
  outlets absent); using it alone biases the history. Use per-outlet sitemap archives
  first, GDELT as a complement. The DOC API throttles to one request every 5 s.

## Statistics and elections

- INE Tempus API: `https://servicios.ine.es/wstempus/js/ES/`. Tables by community:
  population 56940, poverty 29282, AROPE 60264, education level 66104, unemployment 14506,
  housing prices 80270 (quarterly), rents 59056. Income by municipality: ADRH, one table
  per province.
- Elections by municipality: Ministerio del Interior, Infoelectoral download area.
  Regional results of the pilot: not located yet (unverified).
