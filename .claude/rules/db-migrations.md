---
paths:
  - "migrations/**"
  - "src/datos/**/infrastructure/**"
---

# Rules when editing the database layer

- A migration that has been merged into `develop` is **immutable**: fix forward with a
  new migration.
- Every migration runs on an empty database and on top of the previous one; the
  integration tests apply all of them from scratch.
- Statistical observations and classification results are append-only: a revision is a
  new row, never an `UPDATE` of the value.
- Writes that can repeat (feeds are re-read) are idempotent: unique key on
  `(outlet_id, url)` or a content hash, `ON CONFLICT DO NOTHING`.
- SQL is parameterised; never string-interpolated values.
- A new query on articles or embeddings comes with its `EXPLAIN` checked on realistic
  volume (hundreds of thousands of rows).
