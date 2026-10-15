# Fixtures

Real responses captured on 2026-10-13, trimmed to what the tests need. They keep the real
shape of each source and must not be used as content.

- `feeds/`: RSS feeds cut to three items (see `feeds/README.md`).
- `sitemaps/`: Google News sitemaps of RTVC and Telemadrid cut to three `<url>` entries.
- `sections/`: the `<a>` tags of a real RTVE and 3Cat section page (link text replaced by
  `x`): a few non-article links and the first article links, repeated as on the page.
- `pages/`: the `<meta>` tags of one real article page per outlet (`og:title`,
  `og:description`, `og:site_name`, `article:published_time`); the body is a placeholder.
- `geo/`: the IGN GML of the autonomous communities (2026-08-10) cut to three units:
  Ceuta, Melilla and unit 20 (territories outside any community).
