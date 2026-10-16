# ADR-0019: The outlet's tags as part of what the model reads; the article body only where the site allows it

- **Status:** Accepted
- **Date:** 2026-10-16
- **Phase:** news-live

## Context

ADR-0016 gives the own model the headline and the lead. While preparing the training sample the
author found that this is often not enough to tell what a news item is about and who is involved: a
headline names a person or a place, and the lead is short or cut. The model has to classify the
item, and to do it well it has to understand the subject and the actors.

What can be added is limited by what the project may take from an outlet (`docs/sources-audit.md`,
section 7): only the headline and the link are published; the lead is processed under the
text-and-data-mining exception and never shown; article bodies are never stored. Besides the text,
outlets publish **tags** with each article (RSS categories, feed keywords): data about the item, not
the item itself.

Constraints that shape it:

- **The encoder reads 128 tokens** (ADR-0016). Whatever is added competes with the headline and the
  lead for that window.
- **The model never sees the outlet** (ADR-0015). A tag such as "Home La Razón" says nothing about
  the topic and tells the model who published the item.
- **Coverage is uneven.** On 2026-10-16, 7 of the 14 outlets publish tags in their feeds and 7 do not.
- **The training sample is drawn soon** (ADR-0016), so tags are useful only if they are stored before
  it.

## Options considered

### What extra context the model gets
- **A. Nothing: headline and lead only** (ADR-0016 as it was).
  - Pros: no new data, no new risk.
  - Cons: the problem the author saw stays.
- **B. The tags the outlet publishes with the article.**
  - Pros: already in the feeds the collector reads; data about the article, not its text; often name
    the subject and the actors ("Crisis migratoria", "Ceuta", "Pedro Sánchez").
  - Cons: 7 outlets give none; some tags are noise or give away the outlet.
- **C. The article body**, read to extract keywords and never stored.
  - Pros: the most context, and it reaches the outlets without tags.
  - Cons: one request per article, more traffic; it is a reproduction of the text, legal only where
    the outlet has not reserved mining; the 128-token window caps how much of it can be read anyway.

### When the noise is removed
- **A. Store the tags as the outlet wrote them, filter when the model's text is built.**
  - Pros: changing the list never needs a new collection (feeds only list recent items, so what was
    not stored cannot be fetched again).
  - Cons: a join and a filter each time a text is built.
- **B. Filter before storing.**
  - Pros: smaller tables, simpler reads.
  - Cons: a tag dropped by mistake is lost for good.

### How the noise is decided
- **A. A list kept by the author** (a CSV of exact and prefix entries, versioned by its hash).
  - Pros: written down, reviewable, reproducible.
  - Cons: a judgement; needs revisiting as outlets change their tags.
- **B. An automatic rule** (drop what comes 90 % or more from one outlet).
  - Pros: adapts by itself.
  - Cons: drops topical tags that only one outlet happens to use ("Partidos políticos", only from El
    País) and changes with the data.

## Decision

**B, then C where the site allows it.** The model reads the outlet's tags, and later keywords read
from the body, because, in the author's words, it needs more context to classify the news item
correctly, to understand what it is about and the actors involved, and the tags are what is at hand
when the article itself cannot be read.

- **Storage.** Tags are stored once each (`tags`, keyed by a normalised form) and linked to their
  articles with their source (`feed` or `body`) and their place in the article (`article_tags`,
  migrations 0008 and 0009). They are stored as the outlet wrote them and **filtered when the text is
  built**: the author left the choice to what is most efficient, and filtering on read is what keeps
  a change of list free.
- **The list of what the model never reads** (`data/classification/tag-stoplist.csv`) is decided by
  **common sense**, the author's criterion: a tag like "Portada" does not help to classify the item.
  An entry is there because the tag says nothing about the topic, and only for that: it marks the
  outlet or its section (`outlet_marker`) or names the author (`byline`). **No tag is removed for
  what it says about a party, a government or an outlet's line**: the author wants no value
  judgements, only the data, as true to the source as possible. The list is versioned by its hash,
  which the model card, the learning curve and every labelling sample record.
- **The text the model reads** is the headline, then `Etiquetas: a, b.` with at most 8 tags in the
  feed's order, then the lead: if the 128-token window cuts something, it is the end of the lead,
  never the headline. The author sees the same line in Label Studio.
- **The body** is read only **where the site allows it**, and otherwise not at all: the model uses
  what there is. The author's position is that this is a personal, non-commercial project, done as
  well as possible within what each site permits. "Allows" means, for an outlet: its `robots.txt`
  lets our user agent fetch the page, it does not block known AI crawlers, and its pages carry no
  machine-readable mining reservation. The author kept the second condition on purpose: if a site's
  `robots.txt` says no, we stay out, even though our collector is not an AI crawler. Of the 14
  outlets, 8 pass today (erratum below: 7) (`docs/sources-audit.md`,
  section 7). From the body, only keywords are kept (YAKE, a dependency approved by the author on
  2026-10-16); the text is never stored. This part is decided here and not built yet.

## Consequences

- **What gets easier:** the model gets the subject and the actors of many items from data the
  collector already reads; the list can change without losing anything; the author labels from the
  same input the model reads.
- **What gets harder / what we accept:**
  - Uneven input: the model sees tags for some outlets and not for others, and the outlets without
    them are partly the ones whose bodies cannot be read either. The per-outlet promotion criterion of
    ADR-0016 (no outlet more than 2 articles worse than the rules) is what would show the damage.
  - Tags can still hint at the outlet beyond the list. The list is a judgement, revisited when
    new tags appear; "Actualidad" (85 % of one outlet) is its doubtful entry.
  - Articles collected before 2026-10-16 have tags only if their feed still listed them (6 % of them);
    the rest stay without.
  - Reading bodies adds one request per article for the outlets that allow it.
  - The project will not seek a legal review. The reading rule above is the line: what a site does not
    allow is not read.
- **What would make us revisit this:** a better-performing model needing other input; an outlet
  changing what its site allows (its `robots.txt`, a reservation, its feeds or its tags).

## Verification

- Feeds (2026-10-16): El País, El Mundo, La Razón, La Vanguardia, OKDiario and Diario de Avisos put
  categories in their RSS; El Español puts `media:keywords`, which `feedparser` merges into the same
  list (checked on the fixtures in `tests/fixtures/feeds/`). The news sitemap of Telemadrid has a
  `news:keywords` element that is always empty, so nothing is read from it.
- Stored data (2026-10-16): 1,210 distinct tags; in the 7 outlets that publish tags, about 95 % of the
  articles collected since the collector stored them carry at least one. Every entry of the stoplist
  came from a single outlet in that data.
- Body reading rule: which outlets block AI crawlers or reserve mining, from `docs/sources-audit.md`,
  section 7 (checked 2026-10-13). To be checked again for each outlet when the body reading is built.
- Not measured: whether the tags improve the model. The blind test set (ADR-0016) will say it, per
  outlet.

## Amendment (2026-10-16): the page's own tags first, no keyword extraction

Written when the body reading was about to be built, after checking the real pages.

- **Erratum.** Seven outlets pass the reading rule, not eight: ABC and Canarias7 also block AI
  crawlers (they group the crawlers in one `robots.txt` block, which a first check missed). The seven
  that block are exactly the outlets marked `external_llm_allowed = false` in `outlets.csv`. The seven
  that pass are El Español, OKdiario, Diario de Avisos, RTVE, RTVC, Telemadrid and 3Cat; on a sample
  page of each, nothing reserves mining.
- **The pages of RTVE, 3Cat and Telemadrid already publish the outlet's own tags** as
  `<meta property="article:tag">`, in every one of 40 pages sampled for 3Cat and for Telemadrid. They
  are the outlet's tags, as the feed's are, and better than any extraction. The page is already read
  for the lead, so reading them adds no request. These three outlets are the ones that had no tags.
  They are stored as the outlet published them (`source = 'feed'`: the source means "published with
  the article", whether in its feed or in its page). RTVC has none in its pages.
- **No keyword extraction (YAKE).** Only RTVC would have needed it; the author decided not to add a
  dependency (numpy, networkx, an LGPL licence) and mediocre keywords for one outlet. The `body`
  source stays in the schema, unused. If a later change reads bodies, it will need its own decision.
- **The rule is checked on every run, not once** (`ReadPolicy`): robots.txt for our collector and
  for the known AI crawlers, and a `tdm-reservation` in the page. An outlet that changes what its
  site allows stops being read with no change in the code. The tags of pages already stored for
  an outlet are not removed when it stops allowing.
- The articles of the three outlets collected before this change were given their tags by one run
  of `python -m datos.news backfill-page-tags` (316 pages, one per second).
