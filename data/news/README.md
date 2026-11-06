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
  current feed); title, date and lead come from the article page's metadata. Which links
  are articles is the `article_url_pattern` column (a regex the absolute link must fully
  match), so a new outlet is a new row, not new code.
- Article pages are read only for URLs not stored yet, at most 30 per feed and run, one
  request per second. Only `<head>` metadata is read (`og:title`, `og:description`,
  `article:published_time`); bodies are never stored.
- RTVE's `og:description` often repeats the headline, so its articles carry little lead.

## Tags from the page (`tags_in_page`, ADR-0019)

Some outlets publish the tags of an article in its RSS feed; RTVE, 3Cat and Telemadrid do not, but
their article pages carry them as `<meta property="article:tag">`: one per tag (RTVE, 3Cat) or all
in one separated by commas (Telemadrid). `tags_in_page` in `feeds.csv` marks those feeds. The page
of a new article is already read for its lead, so the tags cost no request; `python -m datos.news
backfill-page-tags` reads the pages of the articles collected before (one request per second, at
most `--limit` per outlet, in the last `--days`). `keywords` and `news_keywords` are never read:
Telemadrid fills them with search-engine phrases. RTVC has no tags in its pages and is not marked.

The tags of a page are read **only where the site allows it, checked on every run**
(`infrastructure/read_policy.py`): its `robots.txt` lets our collector fetch the page and blocks no
known AI crawler, and the page carries no `tdm-reservation`. A `robots.txt` that cannot be read means
no. The lead is read as before. A test fails if an outlet that blocks AI crawlers
(`external_llm_allowed = false`) is marked `tags_in_page`.

Checked on 2026-10-16 against the real `robots.txt`: 7 of the 14 outlets block AI crawlers (El Mundo,
El País, ABC, El Confidencial, La Razón, La Vanguardia, Canarias7: exactly the `false` ones) and 7 do
not (El Español, OKdiario, Diario de Avisos, RTVE, RTVC, Telemadrid, 3Cat), with no reservation in the
page and no `tdmrep.json` on a sample page of each.
