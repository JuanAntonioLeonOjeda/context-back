# Outlets

`outlets.csv` follows the published selection criterion in `specs/foundation/plan.md`
("Outlet selection criterion"), approved by the author on 2026-10-13.

- **National:** general-news outlets in the GfK DAM monthly top 10 ("News and
  information") of March, April, June, July and August 2026, as reported by CMS MAG
  (May 2026 was not found published). Sports outlets (AS, MARCA) excluded. Plus RTVE.
- **Regional (pilot):** the public broadcaster of each pilot community. The most-read
  private outlet (audience within the community; one per province in Canarias) is added
  after task 15 checks the official GfK DAM regional figures. Madrid has no private
  regional outlet: national outlets cover it.
- **Pending (task 15):** the measured-diversity step and the feeds of every outlet; an
  outlet without usable feeds is replaced by the next one under the same rule.

The `selection` column records why each outlet is in the list.

## Excluded (task 15, decided with the author on 2026-10-13)

- **El Periódico** and **El Economista**: both answer 403/406 to automated clients, for
  their feeds and even their `robots.txt`. Under rule 5 they are out until an access path
  exists; the bot protection is not bypassed. If the GfK DAM ranking beyond position 10
  becomes available, the next outlet is added.
- **20 Minutos**: declares an express text-and-data-mining reservation
  (`<meta name="tdm-reservation" content="1">`), so RDL 24/2021 art. 67 does not cover
  processing its content. Out while the reservation stands.
- **El Día** (Santa Cruz de Tenerife): answers 406 to automated clients; the next outlet by
  audience within Canarias, Diario de Avisos, takes its place.
- **Measured diversity (rule 3):** no current per-outlet measure of audience ideology
  exists (see `docs/sources-audit.md`), so the list is audience-based plus RTVE, and the
  audience figures are published. Outlets are not labelled by hand.

## What is published and what is processed

- **Published:** headline and link only (LPI art. 129 bis allows hyperlinks and very short
  extracts). Leads are never shown.
- **Processed internally:** the lead, for classification, under the text-and-data-mining
  exception (RDL 24/2021 art. 67), only for outlets without an express reservation.
- **`external_llm_allowed = false`:** outlets whose `robots.txt` blocks AI crawlers. Their
  text is processed only by rules and local models (embeddings, own classifier), never sent
  to an external LLM. Decided with the author on 2026-10-13, pending legal review.

## How each outlet is collected (`feeds.csv`)

- `rss`: the outlet's feed (title, date and lead).
- `news_sitemap`: the Google News sitemap (title and date); the lead is the page's
  `og:description`, read with one request per article (`needs_page_fetch`).
- `html_section`: a section page listing article links (RTVE, 3Cat, which publish no
  current feed); date and lead come from the article page's metadata.

