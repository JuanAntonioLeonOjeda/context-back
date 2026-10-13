---
description: Backend layout, module boundaries, ports & adapters, and the dependency rules between layers and modules.
---

# Architecture

## Data flow

```
RSS / GDELT / sitemaps ─► news (ingestion) ─► classification ─► attribution ─► stories ─► PostgreSQL ─► api ─► front
INE / ministries / CIS / election results ─► indicators, voters (ETL) ───────────────────────┘
curated data/governments ─► governments ────────────────────────────────────────────────────┘
```

- **Only ingestion and ETL modules talk to external sources.** Everything downstream reads
  from PostgreSQL. The API never calls an external source or an LLM while serving a
  request.
- **The LLM is an adapter** behind the `ArticleClassifier` port (and, later, a summariser
  port). It is called by background jobs, never by request handlers.
- **The API is read-only** towards the web app. Writes come from jobs and from the
  validation tool.
- **Every number has a source:** observations keep their `source` and `download` ids.

## Layout

```
src/datos/<module>/       # territories, governments, attribution, news, classification,
                          # stories, indicators, voters, api
  domain/          # pure Python: entities, value objects, rules. No I/O, no FastAPI,
                   # no SQLAlchemy, no HTTP, no datetime.now()
  application/     # use cases; ports are typing.Protocol classes declared here
  infrastructure/  # adapters: repositories, feed readers, LLM client, embedding model
  interface/       # FastAPI routers and Pydantic response models
src/datos/main.py  # composition root
src/datos/config.py # settings, read once
```

### Dependency rule

```
interface → application → domain ← infrastructure
```

- `domain/` imports nothing outside itself. An import of `fastapi`, `sqlalchemy`,
  `httpx`, `anthropic` or a call to `datetime.now()` / `date.today()` inside `domain/` is
  a high-priority finding for `py-reviewer`. Time arrives as a parameter or through an
  injected `Clock` port.
- `application/` depends on ports, never on concrete adapters.
- `infrastructure/` implements ports; it is the only layer that touches I/O libraries.
- `interface/` calls use cases; it never queries the database directly.
- A module may use another module's `application` API (a use case or a port it exposes),
  never its `infrastructure` or `domain` internals.

### Naming

- Port: `Protocol` with a role name — `ArticleRepository`, `Clock`, `ArticleClassifier`.
- Adapter: technology + role — `PgArticleRepository`, `SystemClock`,
  `LlmArticleClassifier`, `SetFitArticleClassifier`, `RssFeedReader`.
- Use case: verb phrase — `ClassifyArticle`, `LinkStories`, `AttributeResponsibleParty`.
  Avoid `XxxService` god-classes.

## Reproducibility

- Classification results are stored with `model_id`, `prompt_version` and `created_at`;
  they are never silently recomputed.
- Embedding model name and version are pinned in config; changing them is an ADR.
- Statistical observations are append-only (a new revision is a new row).

## When NOT to apply this literally

- Small modules with no business logic (`territories` lookups, `health`) do not need four
  folders.
- Do not create ports for things that will never have a second implementation **and** do
  not need a fake in tests. Every port must earn its place.
