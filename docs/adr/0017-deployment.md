# ADR-0017: Deployment: Docker Compose on a single host, no Kubernetes

- **Status:** Accepted
- **Date:** 2026-10-15 (accepted by the author the same day)
- **Phase:** news-live

## Context

The project already runs as containers: `docker-compose.yml` has PostgreSQL with pgvector, the API
(`back-main`), the collector (the same image running `collector.sh` every `COLLECT_INTERVAL_MIN`
minutes, 180 by default) and the web app (`front`, built from `../front`), the last three under the
profile `app`. A Compose file is also what the collector replaced launchd with
(2026-10-14). The question that came up is whether production should stay on Compose or move to an
orchestrator such as Kubernetes, and the decision is worth recording before the first public
deployment, because it shapes how the later phases are packaged.

What is true of the system today, from the repository:

- **One database, one writer.** A single PostgreSQL holds everything; the API is read-only
  (`.claude/rules/architecture.md`); the writes come from the collector and the jobs.
- **Load is small and predictable.** The API serves a few endpoints per community from the
  database; collection runs every three hours. Nothing in the design calls for horizontal scaling.
- **Heavy jobs are not part of serving.** Training and, after task 18, batch classification with the
  own model run as jobs on the author's machine, never in the API image (ADR-0016). That image has
  no torch (452 MB, measured on 2026-10-15).
- **A portfolio project run by one person.** The project's weight is in data, neutrality and
  traceability, not in infrastructure.

Not decided, and not part of this ADR: where the host is (a VPS, a home server, a managed Docker
service), the domain and TLS, and the backups.

## Options considered

### Option A — Docker Compose on a single host (chosen)
The same Compose file, with the profile `app`, on one machine, behind a reverse proxy for TLS.
- Pros: what is deployed is what is developed and tested; one file to read and defend; nothing to
  operate beyond Docker; a restart policy and the healthchecks already cover the failures that
  matter at this size; cheap.
- Cons: one host is a single point of failure; no rolling updates (a deploy restarts the services
  for a few seconds); scaling means a bigger host, not more of them.

### Option B — Kubernetes (managed, or a light distribution on one or more nodes)
- Pros: rolling updates, self-healing across nodes, a standard way to run jobs on a schedule
  (`CronJob`), and a skill many teams ask for.
- Cons: a cluster, an ingress, secrets, volumes for PostgreSQL and upgrades to operate, for a system
  that has one database and a handful of containers; the database would still be the one stateful
  piece that does not benefit from it; far more to explain than the project needs.

### Option C — A managed platform (PaaS) that builds from the repository
- Pros: no host to administer; TLS and deploys are provided.
- Cons: the platforms differ in how they run a scheduled job and a PostgreSQL with the `pgvector`
  extension, and none of that was checked; it adds a dependency on a provider's model of how an
  app is packaged, away from the Compose file already in use.

## Decision

The project is deployed with **Docker Compose on a single host** (option A). The profile `app`
of the existing Compose file is the deployment: the API, the collector and the web app, with
PostgreSQL, behind a reverse proxy that terminates TLS. Kubernetes is not used.

The reason is proportion. The system has one database, a read-only API and a collector every three
hours; the failures that matter (a crashed process, a slow start, a database not ready) are already
handled by `restart: unless-stopped`, the healthchecks and `depends_on`. An orchestrator would add
operations work and concepts without removing the single point that counts, the database. What an
interviewer should be able to hear is that the choice was made against a stated load and a stated
cost, not out of habit in either direction.

## Consequences

- What gets easier: one artifact to build, run and reason about; the local setup and production
  are the same file; the collector, the API and the migrations on start (`entrypoint.sh`) keep their
  current behaviour.
- What gets harder / what we accept:
  - A deploy restarts the services; there is a few seconds of downtime, accepted.
  - The host is a single point of failure. Backups of the `db-data` volume (a scheduled
    `pg_dump` kept off the host) and the restore procedure are needed before the first public
    deployment and are **not yet written**.
  - The API port is bound to `127.0.0.1` and the web port to every interface in the current file:
    the production file needs the reverse proxy and the exposure of each port decided.
  - Credentials: the Compose defaults (`datos`/`datos`) are for development; production reads them
    from environment variables that are never committed.
- What would make us revisit this: traffic or availability needs that one host cannot meet; the need
  for deploys without downtime; a second environment that has to be reproduced exactly; or the
  own model's batch classification outgrowing a job on one machine (ADR-0016 already plans a
  separate image for it, which Compose can run as another service).

## Verification

- The services, profiles, ports, healthchecks and the collector's restart policy and interval:
  `docker-compose.yml`, read on 2026-10-15.
- The image has no torch and is 452 MB: measured on 2026-10-15 when the `ml` group was added
  (ADR-0016), by building the image and checking its contents.
- Not checked: hosting options, prices, and how any managed platform runs scheduled jobs or the
  `pgvector` extension. Option C is described by what is general, not by a provider.
