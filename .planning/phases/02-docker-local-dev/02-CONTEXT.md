# Phase 2: Docker Local Dev - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

`docker compose up` starts the full local stack — FastAPI backend, Postgres, and React dev server — with data persisting across restarts and Alembic migrations running automatically. No manual steps after first run. No hardcoded Windows paths in any config files.

</domain>

<decisions>
## Implementation Decisions

### React dev server
- Include a `frontend` service in docker-compose.yml running the Vite dev server
- Exposed at port 5173; developer accesses `localhost:5173` for live UI with HMR
- Source mounted as volume: `./frontend:/app/frontend` with an anonymous volume for node_modules (`- /app/frontend/node_modules`) so container-built binaries aren't overwritten by host mount
- Vite proxy target (`http://app:8000`) configured via environment variable in compose — keeps vite.config.ts clean and working both in-Docker and on-host

### Backend hot reload
- No separate Dockerfile.dev — override `command` and `working_dir` directly in docker-compose.yml
- Mount `./backend:/app/backend` only (not `/app` root) so installed pip packages at `/usr/local/lib` are not overwritten
- Override `command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- Override `working_dir: /app/backend` so `api.main` resolves correctly (mirrors local dev invocation)

### DB name fix
- Update docker-compose.yml DB name from `loan_engine` to `intrepid_poc` (decided in Phase 1)
- Update `DATABASE_URL` in the compose environment block to match

### Volume mount fix
- Replace hardcoded Windows absolute path (`C:\\Users\\omack\\...`) with a relative path or env-var-based path
- Sample data available at `./backend/data/sample/` — mount as read-only volume for zero-config dev input

### Claude's Discretion
- Migration automation mechanism: entrypoint shell script (`alembic upgrade head && uvicorn ...`) vs separate `migrate` service — Claude chooses the cleaner approach
- CORS origins update to include `http://localhost:5173` for the new frontend container
- Whether `docker-compose.yml` needs a `healthcheck` update for the frontend service

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/docker-compose.yml`: Already has `app` + `db` services with healthchecks and named volume (`pgdata`). Needs: DB name fix, Windows path fix, migration step, frontend service added, backend override for hot reload.
- `deploy/Dockerfile`: Multi-stage production image (node:20-slim frontend build + python:3.12-slim backend). Packages install to `/usr/local/lib` — safe to mount `./backend:/app/backend` without clobbering packages.
- `frontend/vite.config.ts`: Already proxies `/api` to port 8000. Needs env-var-based proxy target for Docker compatibility.
- `backend/config/settings.py`: Already handles `DEV_INPUT`, `DEV_OUTPUT`, `DEV_OUTPUT_SHARED` overrides — compose can set these to container paths for the sample data mount.

### Established Patterns
- `STORAGE_TYPE=local` + `DEV_INPUT/DEV_OUTPUT` env vars already wired in settings.py — compose sets these as environment vars
- `pgdata` named volume already defined — persists Postgres data across restarts (requirement DOCKER-03 met by existing pattern)
- Healthcheck on db service (`pg_isready`) + `depends_on: condition: service_healthy` already in place for app → db ordering

### Integration Points
- `CORS_ORIGINS` in settings.py must include `http://localhost:5173` for the React dev container to reach the backend
- `DATABASE_URL` in compose environment block: update host from implied localhost to `db` (already done), update DB name from `loan_engine` to `intrepid_poc`
- Migration entry point: `alembic upgrade head` runs from the backend directory — same `working_dir` override applies

</code_context>

<specifics>
## Specific Ideas

- No specific UX references — standard Docker Compose dev pattern
- The frontend container should use `npm run dev -- --host` (Vite `--host` flag) so it binds to `0.0.0.0` and is reachable from outside the container

</specifics>

<deferred>
## Deferred Ideas

- Production Dockerfile optimization (layer caching, multi-platform builds) — Phase 3/4 concern
- `docker-compose.override.yml` for per-developer customization — not needed for Phase 2

</deferred>

---

*Phase: 02-docker-local-dev*
*Context gathered: 2026-03-05*
