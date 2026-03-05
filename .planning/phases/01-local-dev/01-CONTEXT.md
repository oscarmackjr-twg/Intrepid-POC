# Phase 1: Local Dev - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A developer can run the full stack locally — FastAPI backend (`uvicorn`), React frontend (`npm run dev`), and Postgres database — using only documented env config. No hardcoded paths, no Windows artifacts. Alembic migrations apply cleanly and the core loan pipeline runs end-to-end with local storage. Docker and cloud are subsequent phases.

</domain>

<decisions>
## Implementation Decisions

### env file design
- Single `backend/.env` with clearly separated sections: `## LOCAL DEV` at top (active), `## S3 / PRODUCTION` below (commented out)
- `STORAGE_TYPE=local` is the active default in the cleaned-up `.env`
- `DEV_INPUT`, `DEV_OUTPUT`, `DEV_OUTPUT_SHARED` left unset with explanatory comments (e.g., `# Optional: point to your local files_required dir. Defaults to backend/data/inputs/`)
- `backend/.env` is gitignored — verify `.gitignore` enforces this; only `.env.example` is committed
- `.env.example` includes S3 vars as commented-out block so developers understand what to set for staging/production

### Local dev data
- Commit a minimal sample dataset under `backend/data/sample/` (small set of loan files — enough for pipeline to complete)
- `backend/data/` is gitignored; `backend/data/sample/` is excepted and committed
- `.env.example` points `DEV_INPUT` at `./data/sample/files_required` so a new developer can run the pipeline immediately without external files
- LOCAL-06 is satisfied when the pipeline completes end-to-end on the sample data locally

### Dev setup experience
- Create a `Makefile` at project root with targets: `make setup`, `make run-backend`, `make run-frontend`, `make migrate`
- Create `DEVELOPMENT.md` at project root covering: prerequisites, venv setup, `.env` config, running locally, running tests
- `requirements.txt` stays as a single file — no split into dev/prod for Phase 1

### Database
- Target: developer-installed Postgres running on host (no Docker in Phase 1)
- Database name: `intrepid_poc` everywhere — update `docker-compose.yml` to match in Phase 2
- `.env.example` default: `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/intrepid_poc`
- Generate initial Alembic migration via `alembic revision --autogenerate` from existing SQLAlchemy models; `alembic upgrade head` must apply cleanly (satisfies LOCAL-05)

### Claude's Discretion
- Exact Makefile target implementation details and flags
- DEVELOPMENT.md prose and formatting
- Whether to add a `make check` or `make test` target
- How to handle the `alembic.ini` `sqlalchemy.url` line (currently set via env; keep as-is)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/config/settings.py`: Pydantic-settings with full `DEV_INPUT`/`DEV_OUTPUT`/`DEV_OUTPUT_SHARED` override support already wired in — no model changes needed, only `.env` cleanup
- `backend/storage/`: Full abstraction layer (`local.py`, `s3.py`, `factory.py`) — `STORAGE_TYPE=local` switch already works
- `backend/migrations/env.py`: Already reads `settings.DATABASE_URL` — migration tooling is wired correctly, just needs the first revision file generated
- `frontend/vite.config.ts`: Port 5173, `/api` proxied to `:8000` — no changes needed for local dev

### Established Patterns
- `settings.py` uses `extra="ignore"` — safe to have extra env vars in `.env` without breaking startup
- `DATABASE_URL` can be set as a full connection string OR as individual `DATABASE_HOST`, `DATABASE_USER`, etc. components — use full URL in `.env.example` for simplicity

### Integration Points
- `backend/.env` → `settings.py` → all app modules: cleaning up `.env` is the primary integration point
- `.gitignore` at root: must confirm `backend/.env` is excluded
- `deploy/docker-compose.yml`: has hardcoded `loan_engine` DB name and Windows volume path — leave for Phase 2, but note the discrepancy

</code_context>

<specifics>
## Specific Ideas

- Sample data under `backend/data/sample/` — small enough to commit, real enough to run the pipeline
- `.env.example` should be self-documenting: every variable gets a comment explaining what it does and when it's needed

</specifics>

<deferred>
## Deferred Ideas

- Docker Compose volume mount fix (hardcoded Windows path in `docker-compose.yml`) — Phase 2
- `requirements.txt` split into prod/dev — future cleanup, not Phase 1
- `make test` / CI test target — can be added but not required for Phase 1 success

</deferred>

---

*Phase: 01-local-dev*
*Context gathered: 2026-03-05*
