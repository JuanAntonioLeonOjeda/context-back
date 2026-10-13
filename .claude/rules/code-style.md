---
description: Python code style — language, typing strictness, lint/format, validation at the edges, errors, logging, configuration and comments.
---

# Code style

Complements `naming-conventions.md` and `atomic-functions-solid.md`; what is there is not
repeated here.

## Language

Code, identifiers, comments, log messages, commits, ADRs and specs in **English**.

## Python

- Python 3.12+. Dependencies managed with `uv`; `pyproject.toml` is the single config
  file (ruff, mypy, pytest).
- `mypy --strict`. No `Any` except at a typed boundary with a comment; no `# type: ignore`
  without the error code and a reason.
- Type hints on every function. Prefer `dataclass(frozen=True, slots=True)` for domain
  values; no mutation of inputs.
- `typing.Protocol` for ports. Exhaustive `match` over enums and unions with
  `assert_never`.
- Prefer `enum.StrEnum` for closed sets (sectors, government levels, link types).

## Format and lint

- `ruff format` and `ruff check` (rule sets `E,F,I,B,UP,SIM,RUF,ANN,S`). Code is delivered
  formatted and with zero warnings.
- No `# noqa` without the code and a justification in the same comment.

## Validation at the edges

- Everything that enters from outside (feeds, statistics files, LLM output, HTTP bodies,
  env vars) is parsed with Pydantic models. Our own domain objects are not Pydantic; the
  adapter converts.
- LLM output is requested as structured JSON and validated against a schema. An invalid
  answer is logged with the article id and retried at most once; it never produces a
  half-filled label.
- An invalid feed item is **logged and dropped**. It never crashes the job.

## Errors

- Expected failures are typed (`class FeedUnavailableError(Exception)`) or returned as
  results; unexpected ones propagate to the job runner.
- Adapters translate library errors (httpx, psycopg, SDK) into the app's own errors.
- Never a bare `except:` and never `except Exception: pass`.

## Logging

- `structlog`, structured. One logger per module with context (`outlet`, `article_id`).
- Log events, not prose: `log.warning("invalid_feed_item_dropped", outlet=o, reason=r)`.
- Never log secrets, API keys or article bodies.

## Configuration

- Read env vars **once**, at startup, through a Pydantic `Settings` class in `config.py`.
  No `os.environ` outside it.
- Every variable appears in `.env.example` with a comment.

## Comments

- Comment the **why**, never the what: non-obvious decisions, source quirks, links to
  ADRs (`# See ADR-0006: threshold chosen on the 200-article test set`).
- Docstrings on ports, use cases and public functions.
- No commented-out code. `TODO` only with enough context to resume it.
