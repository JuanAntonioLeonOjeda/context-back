# ADR-0023: Public deploy on a Hugging Face Space, fed by a daily snapshot

- **Status:** Proposed
- **Date:** 2026-11-06 (options chosen by the author the same day; to be accepted by the author)
- **Phase:** news-live (first public deploy)
- **Amends:** ADR-0017 (where the public copy runs; the local Compose setup is unchanged)

## Context

The site needs a public address. ADR-0017 chose Docker Compose on a single host and left open
where the host is, TLS and backups. The author asked for the same setup as their master's thesis
demo (`JuanAntonioLeonOjeda/TFM`): a Docker Space on Hugging Face with the API and the web app in
one container, deployed by a GitHub workflow on every push to `main`.

What makes this project different from that demo:

- **It has state.** The web app needs PostgreSQL with the articles, the classifications, the
  stories and the reference data. A free Space has no persistent disk: every restart starts empty.
- **The writers live on the author's Mac.** The collector runs in the local Compose stack and the
  promoted model classifies there every hour (ADR-0022): it needs the `ml` group, which never goes
  into a served image.
- **The lead must never be published** (project policies, LPI art. 129 bis). The local database
  holds it for classification; a public copy must not.
- **Two repositories.** The Space is built from `context-back` and `context-front`.

## Options considered

### Option A — PostgreSQL in the container, restored from a daily private snapshot (chosen)
On start the Space downloads the latest dump from a private Hugging Face dataset and restores it
into a fresh PostgreSQL. The Mac writes the dump every day, with the leads removed and without the
embeddings, uploads it and restarts the Space.
- Pros: no new account or service; the public copy can never hold a lead; the collector and the
  model stay where they run today; a restart is a clean, reproducible state.
- Cons: the news is up to a day old; the daily restart takes the site down for a minute or two; if
  the Mac is off, the snapshot is not refreshed.

### Option B — A managed PostgreSQL (Neon, free plan of 0.5 GB)
- Pros: always current; the Space only serves.
- Cons: someone has to write to it: the collector in the Space and the model's classification from
  the Mac means two databases to keep in step, or moving local work onto the remote one; a lead
  would sit in a third-party service unless the writers strip it.

### Option C — A fixed snapshot in every deploy
- Pros: the simplest.
- Cons: the news is frozen between deploys.

## Decision

Option A, chosen by the author on 2026-11-06. The Space is `Juanan237/incontext` and the snapshot
dataset `Juanan237/incontext-data` (private).

- **Image** (`deploy/huggingface/Dockerfile`): the web app built with pnpm, then Debian trixie with
  PostgreSQL 17, pgvector and nginx, and the API with the same `uv sync` as the API image. Port 7860,
  uid 1000, as Spaces require.
- **Start** (`deploy/huggingface/start.sh`): new cluster, snapshot restored (read with the Space
  secret `HF_TOKEN`), then the same steps as `docker/entrypoint.sh` (migrations and CSV data of the
  deployed commit), then the API on 127.0.0.1:8000 and nginx in front, with the web app's routing
  (`/api` forwarded, the rest the single-page app). With no snapshot the site starts with the
  reference data only.
- **Snapshot** (`scripts/publish-snapshot.sh`, daily at 07:30 through launchd): dump, restored into a
  scratch database where `articles.lead` is set to null, dumped again, uploaded, Space restarted.
- **Deploy** (`.github/workflows/deploy-space.yml`): on a push to `main` of the backend, or when the
  web app's workflow asks for it after a push to its `main`, both `main` branches are assembled
  (`deploy/huggingface/build_space.sh`) and uploaded with `hf upload`; the job waits until the Space
  runs. A daily ping (`keep-space-awake.yml`) keeps the free Space from sleeping when no snapshot
  arrives.

## Consequences

- What gets easier: a public address with TLS, given by Hugging Face; a deploy is a merge to `main`.
- What we accept: news up to a day old and a short daily restart; the public copy depends on the
  Mac being on; `main` must be kept deployable (today it is behind `develop`).
- Not solved here: backups. The snapshot has no leads and no embeddings, so it is not a backup of
  the local database.
- What would make us revisit this: the need for fresher news, or moving the collector and the model
  off the Mac; then option B.

## Verification

- 2026-11-06: the image was built and run locally as uid 1000 with that day's snapshot (5.0 MB):
  29,561 articles, 142,997 classifications, 0 leads; `/api/health`, the news and map endpoints, the
  web app and a client-side route answered through nginx. Without a snapshot it started with the
  reference data.
- Debian trixie packages checked the same day: postgresql-17 17.11, postgresql-17-pgvector 0.8.0,
  nginx 1.26.3.
- The read-side queries of the API do not read `articles.lead` (checked in `src/datos/news`).
- Not verified yet: the workflows on GitHub, the Space build on Hugging Face and the upload from the
  Mac (they need the Space, the dataset and the tokens).
