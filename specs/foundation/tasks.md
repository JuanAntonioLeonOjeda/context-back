# Phase 0 — foundation: tasks

Each task is one or a few commits. `[core]` tasks follow the collaborative mode of
`.claude/rules/ai-collaboration.md`.

## Setup

- [x] 1. `pyproject.toml` with uv, ruff, mypy strict and pytest config; empty package `src/datos`
- [x] 2. `config.py` (Pydantic settings), structlog setup, `.env.example`
- [x] 3. Query layer confirmed by the author: SQLAlchemy Core 2.0 + psycopg 3, no ORM (2026-10-13); no ADR needed
- [x] 4. `docker-compose.yml`: PostgreSQL + pgvector and Label Studio, pinned and with healthchecks
- [ ] 5. Alembic setup; ADR-0010 reviewed by the author
- [x] 6. FastAPI app with `/health` (database check) and its tests
- [ ] 7. CI: ruff, mypy, unit and integration tests — workflow written; integration tests pass locally (2026-10-13); still unrun on GitHub (no remote yet)

## Reference data

- [x] 8. [core] First migration: territories, parties, government terms, competences, outlets, articles
- [x] 9. Territories CSV (State, 19 communities, 52 INE provinces) and idempotent loader
- [x] 10. [core] Domain: `GovernmentTerm`, kinds, overlap/gap detection, term in force on a date — tests first
- [x] 11. [core] `data/governments/` CSVs: parties and terms since 2020 for the State and the 19 regional territories, each with source (93 terms, 34 parties; caretaker rule checked per statute). Pending outside the phase: add the State caretaker term on 2026-11-29
- [x] 12. Governments loader and integration test (`uv run python -m datos.governments load`; replaces all terms in one transaction, nothing is written if any rule fails)
- [ ] 13. [core] Competence table for education, health and housing with legal bases; author approval

## Sources

- [ ] 14. Candidate outlet list and selection criterion, approved by the author
- [ ] 15. Sources audit (feeds, GDELT sample, INE table ids, election results, terms) → `docs/sources-audit.md`
- [ ] 16. Skill `news-sources` with the verified facts
- [ ] 17. Pilot communities chosen by the author; brief updated

## Blind test set

- [ ] 18. Minimal RSS collector into `outlets` / `articles` (idempotent), with real-sample tests
- [ ] 19. `docs/labelling-guide.md`, reviewed by the author
- [ ] 20. Stratified sample of 200 and Label Studio project (no proposals loaded)
- [ ] 21. Author labels; export to `data/eval/test-set-v1.jsonl`

## Close

- [ ] 22. ADR-0001 to ADR-0010 reviewed in the author's words → Accepted
- [ ] 23. `AGENTS.md` statuses updated
- [ ] 24. Review: `py-reviewer`, `neutrality-reviewer` (governments data, outlet list, guide)

## Defend

_Date, result and gaps of `/defend foundation`._
