# Phase 2: Docker Local Dev - Research

**Researched:** 2026-03-05
**Domain:** Docker Compose multi-service local development stack (FastAPI + Postgres + Vite)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**React dev server:**
- Include a `frontend` service in docker-compose.yml running the Vite dev server
- Exposed at port 5173; developer accesses `localhost:5173` for live UI with HMR
- Source mounted as volume: `./frontend:/app/frontend` with an anonymous volume for node_modules (`- /app/frontend/node_modules`) so container-built binaries aren't overwritten by host mount
- Vite proxy target (`http://app:8000`) configured via environment variable in compose — keeps vite.config.ts clean and working both in-Docker and on-host

**Backend hot reload:**
- No separate Dockerfile.dev — override `command` and `working_dir` directly in docker-compose.yml
- Mount `./backend:/app/backend` only (not `/app` root) so installed pip packages at `/usr/local/lib` are not overwritten
- Override `command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- Override `working_dir: /app/backend` so `api.main` resolves correctly (mirrors local dev invocation)

**DB name fix:**
- Update docker-compose.yml DB name from `loan_engine` to `intrepid_poc` (decided in Phase 1)
- Update `DATABASE_URL` in the compose environment block to match

**Volume mount fix:**
- Replace hardcoded Windows absolute path (`C:\\Users\\omack\\...`) with a relative path or env-var-based path
- Sample data available at `./backend/data/sample/` — mount as read-only volume for zero-config dev input

### Claude's Discretion

- Migration automation mechanism: entrypoint shell script (`alembic upgrade head && uvicorn ...`) vs separate `migrate` service — Claude chooses the cleaner approach
- CORS origins update to include `http://localhost:5173` for the new frontend container
- Whether `docker-compose.yml` needs a `healthcheck` update for the frontend service

### Deferred Ideas (OUT OF SCOPE)

- Production Dockerfile optimization (layer caching, multi-platform builds) — Phase 3/4 concern
- `docker-compose.override.yml` for per-developer customization — not needed for Phase 2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCKER-01 | `docker compose -f deploy/docker-compose.yml up` starts app + Postgres successfully | Existing compose file needs DB name + path fixes; migration entrypoint added |
| DOCKER-02 | Docker Compose volume mount is configurable (not hardcoded Windows path) | Replace absolute path with `./backend/data/sample` relative mount |
| DOCKER-03 | App is accessible at `localhost:8000` after compose up | Port 8000 already exposed; migrations must complete before healthcheck passes |
| DOCKER-04 | Migrations run automatically on container start | Entrypoint script pattern: `alembic upgrade head && exec uvicorn ...` from `working_dir: /app/backend` |
</phase_requirements>

---

## Summary

Phase 2 is a targeted configuration-surgery phase: the codebase already has 90% of what's needed. The existing `deploy/docker-compose.yml` has the `app` + `db` services with `pg_isready` healthcheck and `pgdata` named volume. The main blockers are a hardcoded Windows absolute path in the volume mount, the DB name mismatch (`loan_engine` vs `intrepid_poc`), the absence of automatic Alembic migration execution, and the missing Vite dev-server frontend service.

All four DOCKER requirements can be satisfied by editing `deploy/docker-compose.yml` and `frontend/vite.config.ts` — no new Python or TypeScript modules are required. The production `deploy/Dockerfile` is untouched by this phase.

**Primary recommendation:** Use an inline shell entrypoint in docker-compose.yml (`sh -c "alembic upgrade head && exec uvicorn ..."`) for migration automation — simpler than a separate `migrate` service and avoids Dockerfile changes.

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Docker Compose v2 | CLI plugin bundled with Docker Desktop | Orchestrate multi-container local stack | `docker compose` (no hyphen) is the current syntax; `docker-compose` v1 is deprecated |
| postgres | 15-alpine | Already in compose; provides pg_isready | Already chosen; consistent with production RDS target |
| uvicorn | Current in requirements.txt | ASGI server with `--reload` for hot reload | Already in project; `--reload` watches `./` by default |
| alembic | Current in requirements.txt | Database migrations | Already configured with working migrations |
| vite | ^7.2.4 | Frontend dev server with HMR | Already in frontend/package.json; `--host` flag binds to 0.0.0.0 |

### Supporting
| Tool | Purpose | Notes |
|------|---------|-------|
| `sh -c` entrypoint | Run migration then start server | Built into every Linux container image — no extra tooling |
| Anonymous volume for node_modules | Prevent host mount from clobbering container-built binaries | Standard pattern for Node.js Docker dev |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline entrypoint `sh -c` | Separate `migrate` service with `restart: on-failure` | Separate service requires `depends_on` chains and leaves a dead container; inline is simpler for local dev |
| Inline entrypoint `sh -c` | Custom `docker-entrypoint.sh` script file + ENTRYPOINT in Dockerfile | Requires Dockerfile change; context decision says no separate Dockerfile.dev |
| Relative path `./backend/data/sample` | `${DATA_PATH:-./backend/data/sample}` env-var pattern | Env-var pattern provides escape hatch if a developer has data elsewhere; minor complexity increase |

---

## Architecture Patterns

### Recommended Project Structure (no changes — existing layout)
```
deploy/
├── docker-compose.yml      # Only file modified in this phase
├── Dockerfile              # NOT modified in this phase
backend/
├── data/sample/            # Mounted read-only into container at /data/sample
│   └── files_required/     # 9 sample files already present
frontend/
├── vite.config.ts          # VITE_API_TARGET env var branch added
```

### Pattern 1: Inline Migration Entrypoint (RECOMMENDED)

**What:** Override `command` in docker-compose.yml to run migrations before starting uvicorn. Use `exec` so uvicorn becomes PID 1 (receives SIGTERM cleanly).

**When to use:** Local dev — simple, no extra service, no Dockerfile changes.

**Example:**
```yaml
# In docker-compose.yml app service:
command: >
  sh -c "alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
working_dir: /app/backend
```

`alembic upgrade head` reads `DATABASE_URL` from the environment (already set in compose). It uses `migrations/env.py` which calls `settings.DATABASE_URL` — this works correctly because `settings.py` reads environment variables.

**Why `exec`:** Without `exec`, uvicorn is a child of sh. SIGTERM from `docker compose down` goes to sh, which may not forward it, leaving uvicorn zombie. With `exec`, uvicorn replaces sh as PID 1.

### Pattern 2: Vite Proxy with Environment Variable Target

**What:** `vite.config.ts` reads `process.env.VITE_API_TARGET` (or `VITE_API_TARGET`) to set the proxy target, falling back to `http://localhost:8000` for host-native dev.

**When to use:** Always — makes the config work both in-Docker and on-host without modification.

**Example:**
```typescript
// frontend/vite.config.ts
server: {
  port: 5173,
  host: true,  // binds 0.0.0.0 — needed when reading from env in compose
  proxy: {
    '/api': {
      target: process.env.VITE_API_TARGET ?? 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

In docker-compose.yml frontend service:
```yaml
environment:
  VITE_API_TARGET: http://app:8000
```

Note: Vite environment variables with `VITE_` prefix are embedded at build time. For the dev server, `process.env` is available at config-load time (Node.js context). This pattern works for `vite.config.ts` because it runs in Node.js — not in the browser bundle.

### Pattern 3: Node Modules Anonymous Volume

**What:** Declare an anonymous volume for the `node_modules` directory so the container-built binaries (linux-specific Rollup binaries, etc.) are not shadowed by the host volume mount.

**When to use:** Any Node.js service with a source volume mount in Docker.

**Example:**
```yaml
frontend:
  volumes:
    - ./frontend:/app/frontend       # source code (HMR watches this)
    - /app/frontend/node_modules     # anonymous volume — preserves container binaries
```

The existing `deploy/Dockerfile` already handles the linux Rollup binary issue during production builds (`npm install @rollup/rollup-linux-x64-gnu`). The frontend dev container uses `node:20-slim` with `npm ci` in the Dockerfile — for the dev service we need a separate lightweight service definition (not the production multi-stage build).

### Pattern 4: Volume Mount Path — Relative vs Env-Var

**What:** Docker Compose resolves relative paths from the directory containing the compose file. Since compose is at `deploy/docker-compose.yml` and sample data is at `backend/data/sample/`, the relative path from the compose file's directory is `../backend/data/sample`.

**Critical insight:** Compose relative paths are relative to the compose file location, not the working directory of the `docker compose` invocation. Since the instructions say to run `docker compose -f deploy/docker-compose.yml up` from repo root, the compose file is at `deploy/`, so `../backend/data/sample` resolves correctly.

**Example:**
```yaml
# In app service:
volumes:
  - ../backend/data/sample:/data/sample:ro   # read-only; replaces hardcoded Windows path
  - ./backend:/app/backend                   # backend hot reload (from repo root context)
```

Wait — the `context: ..` in the build section confirms the compose file is run from its own directory (`deploy/`). Compose path resolution uses the compose file's directory as base. So:
- `../backend` from `deploy/` = `backend/` at repo root — correct
- `../backend/data/sample` = `backend/data/sample` at repo root — correct

### Anti-Patterns to Avoid

- **Mounting `/app` root instead of `/app/backend`:** Would shadow `/usr/local/lib` (pip packages) inside the container, causing import errors. The context decision explicitly specifies `./backend:/app/backend` only.
- **Hardcoded Windows paths in compose:** Blocks CI/CD and cross-platform use. Replace with relative paths.
- **Running migrations without `exec`:** `sh -c "alembic upgrade head && uvicorn ..."` without `exec` means uvicorn is a child process and won't receive SIGTERM cleanly.
- **Using `VITE_` prefix for server-side config:** `VITE_` vars are embedded at build time into the browser bundle. For dev server proxy config (Node.js context), plain `process.env.VITE_API_TARGET` works, but the variable does NOT need `VITE_` prefix to be usable in `vite.config.ts`. Either naming works; `VITE_API_TARGET` is fine.
- **Starting Vite without `--host`:** Without `--host` (or `host: true` in config), Vite binds to `127.0.0.1` only — unreachable from outside the container. The context decision notes `npm run dev -- --host` or `host: true` in vite.config.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Migration ordering | Custom wait loop checking if DB is ready | `depends_on: condition: service_healthy` (already in compose) + `alembic upgrade head` in entrypoint | Already works; pg_isready healthcheck ensures DB is up before app starts |
| Cross-platform paths | Path translation scripts | Relative paths (`../backend/data/sample`) | Docker Compose handles relative paths natively |
| HMR in container | Custom file-watch daemon | Vite `--host` + source volume mount | Vite's HMR works over WebSocket; `--host` makes it reachable |

---

## Common Pitfalls

### Pitfall 1: Compose Path Resolution from compose file location vs invocation directory

**What goes wrong:** Developer sets `./backend/data/sample` expecting it to resolve from repo root, but compose resolves from the compose file's directory (`deploy/`), so it looks for `deploy/backend/data/sample` which doesn't exist.

**Why it happens:** `docker compose -f deploy/docker-compose.yml` — paths in the compose file are relative to the compose file, not the shell's CWD.

**How to avoid:** Use `../backend/data/sample` (relative to `deploy/`) or verify with `docker compose -f deploy/docker-compose.yml config` which shows resolved absolute paths.

**Warning signs:** `bind source path does not exist` error on `docker compose up`.

### Pitfall 2: Working Directory for Alembic

**What goes wrong:** `alembic upgrade head` fails with `No config file 'alembic.ini' found` or Python import errors.

**Why it happens:** `alembic.ini` is at `backend/alembic.ini` and `script_location = migrations` is relative. If the working dir is `/app` (compose default), alembic looks for `/app/alembic.ini` which doesn't exist.

**How to avoid:** Set `working_dir: /app/backend` in the app service — same directory as on the host where `cd backend && alembic upgrade head` works. This is already required for the `api.main` module resolution.

**Warning signs:** `FAILED: Can't locate revision identified by...` or `ModuleNotFoundError` in alembic output.

### Pitfall 3: node_modules Shadowing by Host Volume

**What goes wrong:** Frontend container crashes with `Cannot find module` or Rollup binary errors because the host `node_modules` (Windows binaries) shadows the container's `node_modules` (Linux binaries).

**Why it happens:** `- ./frontend:/app/frontend` mounts everything including `node_modules` from Windows, overwriting Linux binaries.

**How to avoid:** Add `- /app/frontend/node_modules` anonymous volume after the source mount. Docker evaluates volumes in order; the anonymous volume creates a separate overlay for `node_modules`.

**Warning signs:** `Error: Cannot find module '@rollup/rollup-linux-x64-gnu'` or similar platform binary errors.

### Pitfall 4: Frontend Container Needs Its Own Image

**What goes wrong:** Using the production `deploy/Dockerfile` for the frontend dev service — it produces a static build, not a dev server.

**Why it happens:** The existing Dockerfile is a multi-stage production build that runs `npm run build` and copies static files into the backend image. There's no dev server stage.

**How to avoid:** The frontend service in docker-compose.yml must use `node:20-slim` image directly and run `npm ci && npm run dev -- --host`. This is a simple service definition, not the existing Dockerfile.

**Warning signs:** Frontend container exits immediately after running (because build completes and process exits, rather than staying up as a server).

### Pitfall 5: CORS Missing for Frontend Container Origin

**What goes wrong:** Browser shows CORS errors when the React app at `localhost:5173` calls the backend at `localhost:8000`.

**Why it happens:** `settings.CORS_ORIGINS` defaults already include `http://localhost:5173` (verified in `settings.py` line 103). However, the docker-compose.yml `CORS_ORIGINS` environment override must also include it.

**Current state:** The existing docker-compose.yml already has `CORS_ORIGINS: '["http://localhost:8000","http://localhost:5173"]'` — this is already correct. No change needed for CORS.

### Pitfall 6: DB Name Mismatch Causing Migration Failure

**What goes wrong:** Alembic connects to `loan_engine` (old DB name in compose env) but Postgres created `intrepid_poc` (or vice versa).

**Why it happens:** `POSTGRES_DB: loan_engine` in the db service and `DATABASE_URL: ...5432/loan_engine` in the app service must be changed to `intrepid_poc` to match what Phase 1 established.

**How to avoid:** Update both the `db` service `POSTGRES_DB` and the `app` service `DATABASE_URL` to use `intrepid_poc` atomically in the same commit.

**Warning signs:** `FATAL: database "loan_engine" does not exist` in app container logs.

---

## Code Examples

Verified patterns from codebase inspection:

### Final docker-compose.yml app service structure
```yaml
app:
  build:
    context: ..
    dockerfile: deploy/Dockerfile
  ports:
    - "8000:8000"
  volumes:
    - ../backend:/app/backend           # hot reload; packages safe at /usr/local/lib
    - ../backend/data/sample:/data/sample:ro  # read-only sample data
  working_dir: /app/backend
  command: >
    sh -c "alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
  environment:
    DATABASE_URL: postgresql://postgres:postgres@db:5432/intrepid_poc
    SECRET_KEY: change-me-in-production
    CORS_ORIGINS: '["http://localhost:8000","http://localhost:5173"]'
    STORAGE_TYPE: local
    DEV_INPUT: /data/sample/files_required
    DEV_OUTPUT: /data/sample/output
    DEV_OUTPUT_SHARED: /data/sample/output_share
  depends_on:
    db:
      condition: service_healthy
```

### Final docker-compose.yml db service structure
```yaml
db:
  image: postgres:15-alpine
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: intrepid_poc          # changed from loan_engine
  volumes:
    - pgdata:/var/lib/postgresql/data
  ports:
    - "5432:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 3s
    retries: 5
```

### Frontend service (new)
```yaml
frontend:
  image: node:20-slim
  working_dir: /app/frontend
  volumes:
    - ../frontend:/app/frontend         # source (HMR watches this)
    - /app/frontend/node_modules        # anonymous volume protects Linux binaries
  ports:
    - "5173:5173"
  environment:
    VITE_API_TARGET: http://app:8000
  command: sh -c "npm ci && npm run dev -- --host"
  depends_on:
    - app
```

Note: `npm ci` on every container start is slower but guarantees correct binaries. If startup time becomes painful, the plan can add a named volume for node_modules with a separate install step.

### vite.config.ts proxy update
```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: process.env.VITE_API_TARGET ?? 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

No `host: true` needed in config if `--host` flag is passed in compose command. Either works; `--host` flag is the approach specified in the context decisions.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `docker-compose` (v1, Python) | `docker compose` (v2, Go CLI plugin) | v1 EOL May 2023; use `docker compose` not `docker-compose` |
| Separate `migrate` service + `restart: on-failure` | Inline entrypoint `sh -c "alembic upgrade head && exec ..."` | Simpler for local dev; separate service leaves a dead container |
| `VITE_API_URL` (build-time) | `VITE_API_TARGET` (config-load-time, Node.js) | Config-load-time env works for dev server proxy; no build step needed |

**Deprecated/outdated:**
- `docker-compose` v1 binary: Replaced by `docker compose` plugin. This project's instructions already use `docker compose -f` (correct).

---

## Open Questions

1. **Frontend container startup time with `npm ci` on every start**
   - What we know: `npm ci` re-installs all packages each container start; on first run with cold node_modules cache this may take 30-60 seconds
   - What's unclear: Whether startup time is acceptable for developer workflow
   - Recommendation: Start with `npm ci` on start (simple); note in plan that a named volume for node_modules can be added if startup is too slow

2. **DEV_OUTPUT and DEV_OUTPUT_SHARED pointing to read-only sample mount**
   - What we know: The sample data is mounted read-only at `/data/sample`; settings.py maps DEV_OUTPUT → OUTPUT_DIR; the pipeline may try to write outputs there
   - What's unclear: Whether writing output inside the sample volume causes errors or silently fails
   - Recommendation: Set `DEV_OUTPUT` and `DEV_OUTPUT_SHARED` to writable paths (e.g., `/tmp/dev_output` and `/tmp/dev_output_share`) rather than inside the read-only sample mount. Only `DEV_INPUT` points to the sample data.

3. **healthcheck for frontend service**
   - What we know: Context marks this as "Claude's Discretion"; the backend already has a healthcheck
   - Recommendation: Skip frontend healthcheck for Phase 2. The frontend is a dev convenience; no other service depends on it being healthy. Keeping compose simple is preferable.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini at `backend/pytest.ini`) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_api_routes.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCKER-01 | Compose starts app + db with no errors | smoke | `docker compose -f deploy/docker-compose.yml up -d && docker compose -f deploy/docker-compose.yml ps` | manual-only — requires Docker daemon |
| DOCKER-02 | No hardcoded Windows paths in compose file | static analysis | `grep -v "C:\\\\" deploy/docker-compose.yml` exits 0 | ❌ Wave 0 — simple shell check |
| DOCKER-03 | App accessible at localhost:8000 | smoke | `curl -f http://localhost:8000/health/ready` | manual-only — requires running stack |
| DOCKER-04 | Migrations run automatically | smoke | `docker compose -f deploy/docker-compose.yml logs app | grep "Running upgrade"` | manual-only — requires running stack |

**Note:** DOCKER-01 through DOCKER-04 are fundamentally infrastructure tests that require a running Docker daemon and cannot be fully automated in the existing pytest suite. The existing `tests/test_api_routes.py` provides unit coverage of the API layer but does not validate the compose configuration itself.

### Sampling Rate
- **Per task commit:** `cd /path/to/intrepid-poc/backend && pytest tests/test_api_routes.py -x -q` (validates backend still imports correctly with working_dir change)
- **Per wave merge:** `cd /path/to/intrepid-poc/backend && pytest -x -q`
- **Phase gate:** Full suite green + manual smoke test of `docker compose up` before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] No automated test for compose YAML syntax — manual validation with `docker compose config` is sufficient
- [ ] `deploy/docker-compose.yml` path check: `grep "C:\\\\" deploy/docker-compose.yml` should return no matches after the fix — this is a verification step, not a gap requiring a test file

*(Existing test infrastructure covers all backend unit/integration requirements. Docker-level requirements are verified manually.)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `deploy/docker-compose.yml`, `deploy/Dockerfile`, `frontend/vite.config.ts`, `backend/config/settings.py`, `backend/migrations/env.py`, `backend/alembic.ini`
- All findings derived from reading actual project files, not external sources

### Secondary (MEDIUM confidence)
- Docker Compose v2 relative path behavior — well-established behavior, verified against known Compose v2 semantics
- Vite `process.env` in `vite.config.ts` — standard Vite/Node.js behavior; config file runs in Node.js context

### Tertiary (LOW confidence)
- None — all claims grounded in codebase inspection or well-established Docker/Vite behavior

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in project; no new dependencies
- Architecture: HIGH — patterns derived from existing code; verified against codebase
- Pitfalls: HIGH — path resolution pitfall verified against compose file structure; module clobbering pitfall verified against Dockerfile

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable tooling — Docker Compose, Vite, Alembic)
