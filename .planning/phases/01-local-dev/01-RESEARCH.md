# Phase 1: Local Dev - Research

**Researched:** 2026-03-05
**Domain:** Python/FastAPI local dev setup, Alembic migrations, env config, Makefile, sample data
**Confidence:** HIGH

## Summary

Phase 1 is primarily a cleanup and scaffolding exercise on an already-working codebase. The backend (FastAPI + SQLAlchemy + Alembic), frontend (React + Vite), and storage abstraction layer are all implemented and functional. The core problem is that the current `backend/.env` contains hardcoded Windows absolute paths and a mixed-mode config (local dev vars active alongside S3 vars) that breaks cross-platform onboarding.

The work breaks into five concrete buckets: (1) clean up `backend/.env` and create `backend/.env.example`, (2) commit a minimal sample dataset to `backend/data/sample/` with a matching `.gitignore` exception, (3) generate the first Alembic migration from existing SQLAlchemy models and verify `alembic upgrade head` runs cleanly, (4) create a root-level `Makefile` with standard targets, and (5) write `DEVELOPMENT.md` covering the full onboarding flow.

No new libraries are needed. All tooling — pydantic-settings, Alembic, uvicorn, Vite — is already installed and wired. The migrations `env.py` already reads `settings.DATABASE_URL` and the storage factory already switches on `STORAGE_TYPE`. This phase is configuration correction and scaffolding, not feature development.

**Primary recommendation:** Fix `backend/.env` and generate the Alembic initial migration first — those two artifacts block everything else. Then layer in sample data, Makefile, and DEVELOPMENT.md.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**env file design**
- Single `backend/.env` with clearly separated sections: `## LOCAL DEV` at top (active), `## S3 / PRODUCTION` below (commented out)
- `STORAGE_TYPE=local` is the active default in the cleaned-up `.env`
- `DEV_INPUT`, `DEV_OUTPUT`, `DEV_OUTPUT_SHARED` left unset with explanatory comments (e.g., `# Optional: point to your local files_required dir. Defaults to backend/data/inputs/`)
- `backend/.env` is gitignored — verify `.gitignore` enforces this; only `.env.example` is committed
- `.env.example` includes S3 vars as commented-out block so developers understand what to set for staging/production

**Local dev data**
- Commit a minimal sample dataset under `backend/data/sample/` (small set of loan files — enough for pipeline to complete)
- `backend/data/` is gitignored; `backend/data/sample/` is excepted and committed
- `.env.example` points `DEV_INPUT` at `./data/sample/files_required` so a new developer can run the pipeline immediately without external files
- LOCAL-06 is satisfied when the pipeline completes end-to-end on the sample data locally

**Dev setup experience**
- Create a `Makefile` at project root with targets: `make setup`, `make run-backend`, `make run-frontend`, `make migrate`
- Create `DEVELOPMENT.md` at project root covering: prerequisites, venv setup, `.env` config, running locally, running tests
- `requirements.txt` stays as a single file — no split into dev/prod for Phase 1

**Database**
- Target: developer-installed Postgres running on host (no Docker in Phase 1)
- Database name: `intrepid_poc` everywhere — update `docker-compose.yml` to match in Phase 2
- `.env.example` default: `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/intrepid_poc`
- Generate initial Alembic migration via `alembic revision --autogenerate` from existing SQLAlchemy models; `alembic upgrade head` must apply cleanly (satisfies LOCAL-05)

### Claude's Discretion
- Exact Makefile target implementation details and flags
- DEVELOPMENT.md prose and formatting
- Whether to add a `make check` or `make test` target
- How to handle the `alembic.ini` `sqlalchemy.url` line (currently set via env; keep as-is)

### Deferred Ideas (OUT OF SCOPE)
- Docker Compose volume mount fix (hardcoded Windows path in `docker-compose.yml`) — Phase 2
- `requirements.txt` split into prod/dev — future cleanup, not Phase 1
- `make test` / CI test target — can be added but not required for Phase 1 success
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LOCAL-01 | Developer can run backend locally with `uvicorn` against local Postgres | `uvicorn` is in `requirements.txt`; `settings.py` already builds `DATABASE_URL`; cleaned `.env` with `DATABASE_URL` + `STORAGE_TYPE=local` is sufficient |
| LOCAL-02 | React frontend runs locally with `npm run dev` (hot reload) | `vite.config.ts` already has port 5173 and `/api` proxy to `:8000`; no changes needed |
| LOCAL-03 | `backend/.env` config separates local vs S3 mode cleanly (no hardcoded Windows paths) | Current `.env` has `DEV_INPUT=C:\Users\omack\...` — must be removed; `STORAGE_TYPE=s3` active — must be changed to `local` |
| LOCAL-04 | `.env.example` template exists so any developer can onboard | Does not exist yet — must be created with self-documenting comments and correct defaults |
| LOCAL-05 | Alembic migrations run cleanly against local Postgres | `migrations/env.py` reads `settings.DATABASE_URL`; `alembic.ini` has no hardcoded URL; `migrations/versions/` is empty — initial revision must be generated |
| LOCAL-06 | Core loan pipeline executes end-to-end locally (upload → suitability → cashflow) | Pipeline requires specific files under `files_required/`; sample data matching expected file naming conventions must be committed to `backend/data/sample/files_required/` |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uvicorn[standard] | >=0.27.0 | ASGI server for FastAPI | Standard FastAPI dev server with auto-reload |
| FastAPI | >=0.109.0,<0.130 | Web framework | Already chosen, already working |
| pydantic-settings | 2.5.2 | Env var loading from `.env` | Already wired in `settings.py` |
| SQLAlchemy | 2.0.36 | ORM | Already wired; models defined |
| alembic | 1.14.0 | DB migration management | Already installed; `env.py` wired |
| psycopg2-binary | 2.9.10 | Postgres driver | Already installed |
| Vite | (in package.json) | Frontend dev server with HMR | Already configured at port 5173 |

### Not Needed
No new libraries are required for Phase 1. All tooling is already installed.

**Installation:** None. Dependencies are already in `requirements.txt` and `package.json`.

---

## Architecture Patterns

### Existing Project Structure (relevant to Phase 1)
```
intrepid-poc/
├── Makefile                    # CREATE: make setup / run-backend / run-frontend / migrate
├── DEVELOPMENT.md              # CREATE: onboarding guide
├── backend/
│   ├── .env                    # MODIFY: clean up Windows paths, set STORAGE_TYPE=local
│   ├── .env.example            # CREATE: self-documenting template
│   ├── .gitignore              # VERIFY: .env is excluded (already is via line 37)
│   ├── alembic.ini             # KEEP AS-IS: sqlalchemy.url not set; env.py overrides it
│   ├── config/settings.py      # NO CHANGE NEEDED
│   ├── migrations/
│   │   ├── env.py              # NO CHANGE NEEDED: reads settings.DATABASE_URL
│   │   └── versions/           # EMPTY: generate initial revision here
│   ├── data/
│   │   ├── sample/             # CREATE: commit sample files_required here
│   │   │   └── files_required/ # Required pipeline input files (small/synthetic)
│   │   ├── inputs/             # gitignored
│   │   └── outputs/            # gitignored
│   └── storage/
│       └── factory.py          # NO CHANGE NEEDED: STORAGE_TYPE=local already works
└── frontend/
    └── vite.config.ts          # NO CHANGE NEEDED: port 5173, proxy to :8000
```

### Pattern 1: env File Sectioning
**What:** Single `.env` with `## LOCAL DEV` section at top (active) and `## S3 / PRODUCTION` section below (commented out).
**When to use:** Always — this is the locked decision for Phase 1.
**Example:**
```bash
# backend/.env (gitignored — do not commit)
# Copy from .env.example and fill in your values.

## LOCAL DEV
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/intrepid_poc
STORAGE_TYPE=local
SECRET_KEY=local-dev-secret-key-change-in-production

# Optional: point at a specific local files_required directory.
# Defaults to backend/data/inputs/ when unset.
# DEV_INPUT=
# DEV_OUTPUT=
# DEV_OUTPUT_SHARED=

## S3 / PRODUCTION (comment these back in when using S3)
# STORAGE_TYPE=s3
# S3_BUCKET_NAME=
# S3_REGION=us-east-1
# S3_INPUT=input/files_required
# S3_OUTPUT=outputs
# S3_OUTPUT_SHARED=output_share
# AWS_PROFILE=
```

### Pattern 2: .gitignore Exception for Sample Data
**What:** `backend/.gitignore` currently excludes `data/` and all `.xlsx`/`.csv` files. The sample data directory must be carved out as an exception.
**When to use:** Required for LOCAL-06 — sample data must be committable.

The backend `.gitignore` (line 51-54) currently excludes:
```
data/
*.xlsx
*.csv
```

To commit `backend/data/sample/`, add negation rules:
```gitignore
# Data directories — keep large/real data out
data/
*.xlsx
*.csv
!**/test/**/*.csv
!**/test/**/*.xlsx

# Exception: commit sample data for local dev onboarding
!data/sample/
!data/sample/**
!data/sample/**/*.xlsx
!data/sample/**/*.csv
```

**Critical git gotcha:** You cannot un-ignore a file inside an ignored directory without first un-ignoring the directory. The `!data/sample/` rule must appear AFTER the `data/` exclusion rule. Both the directory and file extensions need explicit negations.

### Pattern 3: Alembic Initial Migration
**What:** Generate the first migration from existing SQLAlchemy models using `--autogenerate`.
**When to use:** One-time setup — `migrations/versions/` is currently empty.

```bash
# Run from backend/ directory with virtual env active and .env populated:
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

The `migrations/env.py` already overrides `sqlalchemy.url` with `settings.DATABASE_URL`. The `alembic.ini` does NOT hardcode the URL. This is correct — leave it as-is.

Models to be included in initial migration (all in `db/models.py`):
- `users` — User model with role enum
- `sales_teams` — SalesTeam model
- `pipeline_runs` — PipelineRun with status enum
- `loan_exceptions` — LoanException with JSON columns
- `loan_facts` — LoanFact with JSON columns
- `holidays` — Holiday calendar

**Watch for:** SQLAlchemy `Enum` types defined with `values_callable`. Alembic autogenerate handles these correctly, but the generated migration will include `CREATE TYPE` statements for `userrole` and `runstatus` enums in Postgres. These must run before the table creation DDL in the migration, which autogenerate handles automatically.

### Pattern 4: Makefile Targets
**What:** Root-level Makefile providing standard developer commands.
**When to use:** Always via `make <target>` from project root.

```makefile
.PHONY: setup run-backend run-frontend migrate

# Install backend and frontend dependencies
setup:
	cd backend && python -m venv venv
	cd backend && venv/bin/pip install -r requirements.txt
	cd frontend && npm install

# Start FastAPI backend with auto-reload
run-backend:
	cd backend && venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start Vite frontend dev server
run-frontend:
	cd frontend && npm run dev

# Apply Alembic migrations
migrate:
	cd backend && venv/bin/alembic upgrade head
```

**Discretion note:** The exact FastAPI app module path must be verified. Check `api/main.py` — the app object is likely `app` in `backend/api/main.py`, making the uvicorn target `api.main:app`. Confirm before writing the Makefile.

### Pattern 5: Sample Data Structure
**What:** Minimal committed dataset at `backend/data/sample/files_required/` that the pipeline can process end-to-end.
**When to use:** Required for LOCAL-06 and for `.env.example` `DEV_INPUT` default.

The pipeline's `load_reference_data()` expects these files under `{folder}/files_required/`:
- `MASTER_SHEET.xlsx`
- `MASTER_SHEET - Notes.xlsx`
- `current_assets.csv`
- `Underwriting_Grids_COMAP.xlsx` (with sheets: SFY, Prime, SFY - Notes, Prime - Notes, SFY COMAP, SFY COMAP2, Prime COMAP, Notes CoMAP, SFY COMAP-Oct25, SFY COMAP-Oct25-2, Prime CoMAP-Oct25, Prime CoMAP-Oct25-2, Prime CoMAP - New)

The pipeline's `load_input_files()` expects date-stamped files (discovered by `discover_input_files`):
- `Tape20Loans_{yesterday}.csv`
- `SFY_{yesterday}_ExhibitAtoFormofSaleNotice - Pre-Funding.xlsx`
- `PRIME_{yesterday}_ExhibitAtoFormofSaleNotice - Pre-Funding.xlsx`

**Critical insight about sample data and dates:** The existing `files_required/` at `backend/files_required/` has real loan files dated `02-19-2026`. The pipeline's date-based file discovery uses `yesterday` derived from `pdate`. If sample data has hardcoded dates (e.g., `Tape20Loans_02-18-2026.csv`), running the pipeline without specifying `--pdate` will fail file discovery.

**Options (in order of preference):**
1. Strip dates from sample filenames and update `discover_input_files()` to fall back to undated filenames — this is the cleanest long-term approach but modifies application code.
2. Use the pipeline's `--pdate` flag when running locally: `python main.py --pdate 2026-02-19` — simplest, no code changes, but requires documentation.
3. Create a script that copies and renames sample files to `yesterday`'s date before running.

**Recommendation:** Option 2 is safest for Phase 1. The `DEVELOPMENT.md` documents that sample data is dated `2026-02-19` and instructs developers to run with `--pdate 2026-02-19` or use the `DEV_INPUT` env var to point at any real files_required directory.

**Real data in repo:** The existing `backend/files_required/` contains production loan data (Excel/CSV files, PDFs, FICO/DTI data). These must NOT be committed to `backend/data/sample/`. Synthetic/minimal test data is required. The existing test `conftest.py` fixtures show the minimum data structure needed — these can be the basis for generating synthetic sample files.

### Anti-Patterns to Avoid
- **Hardcoded absolute paths in any committed file:** Any path starting with `C:\` or `/home/user/` in `.env.example`, `Makefile`, or `DEVELOPMENT.md` will break other developers.
- **Committing real loan data as sample data:** The existing `backend/files_required/` has PII-adjacent financial data. Create synthetic sample files instead.
- **Setting `STORAGE_TYPE=s3` with no S3 credentials:** The current `.env` has `STORAGE_TYPE=s3` as the active setting. The cleaned `.env` must have `STORAGE_TYPE=local` as the active line.
- **Leaving `sqlalchemy.url` blank in `alembic.ini`:** It is currently blank (`sqlalchemy.url =` is not even present in `alembic.ini`). This is correct — `env.py` injects it. Do not add a `sqlalchemy.url =` line to `alembic.ini`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var loading | Custom `.env` parser | pydantic-settings (already used) | Handles type coercion, validation, `extra="ignore"`, multi-source |
| DB migrations | Hand-written DDL | Alembic autogenerate (already wired) | Handles Postgres enum types, foreign keys, index tracking |
| Dev server reload | Custom file watcher | `uvicorn --reload` flag | Built into uvicorn standard install |
| Frontend proxy | Custom reverse proxy | Vite dev server proxy (already configured) | `/api` → `:8000` proxy already in `vite.config.ts` |

**Key insight:** Every "could hand-roll" problem in this phase already has a solution wired into the codebase. The work is configuration, not implementation.

---

## Common Pitfalls

### Pitfall 1: Windows Path Separator in S3 Keys
**What goes wrong:** `S3_INPUT=input\files_required` in `.env` passes backslash-separated paths to boto3 S3 key prefix, breaking S3 access.
**Why it happens:** Developer copied Windows path directly into env var.
**How to avoid:** `.env.example` uses forward slashes: `S3_INPUT=input/files_required`. Note: `storage/factory.py` already normalizes backslashes to forward slashes (`_norm()` function) for S3, but the `.env.example` should model correct behavior.
**Warning signs:** S3 key 404 errors with paths containing `\`.

### Pitfall 2: Alembic Autogenerate Misses Enum Type Changes
**What goes wrong:** If `alembic revision --autogenerate` is run, and later the `UserRole` or `RunStatus` Python enum is changed, Alembic may not detect the Postgres `TYPE` change.
**Why it happens:** Alembic does not compare server-side Postgres enum values to Python enum values by default.
**How to avoid:** For Phase 1 (initial migration only) this is not an issue. Document in `DEVELOPMENT.md` that enum changes require manual migration steps.
**Warning signs:** `alembic upgrade head` succeeds but app crashes on enum assignment.

### Pitfall 3: .gitignore Negation Order
**What goes wrong:** Adding `!data/sample/` to `.gitignore` after `data/` does not un-ignore the sample directory — git shows sample files as untracked but won't stage them.
**Why it happens:** git ignores entire directories; you cannot un-ignore files inside an already-ignored directory without also un-ignoring the parent path.
**How to avoid:** The negation pattern must un-ignore both the directory AND the files: `!data/sample/`, `!data/sample/**`, `!data/sample/**/*.xlsx`, `!data/sample/**/*.csv`.
**Warning signs:** `git status` shows sample files as untracked even after adding negation rule; `git add backend/data/sample/` fails silently.

### Pitfall 4: uvicorn App Module Path
**What goes wrong:** `uvicorn api.main:app` fails with `ModuleNotFoundError` if run from the wrong directory.
**Why it happens:** Python module resolution is relative to the working directory. `uvicorn` must be invoked from `backend/` for `api.main` to resolve.
**How to avoid:** Makefile target: `cd backend && venv/bin/uvicorn api.main:app --reload`. Always `cd backend` first.
**Warning signs:** `ModuleNotFoundError: No module named 'api'` on startup.

### Pitfall 5: pydantic-settings .env File Path
**What goes wrong:** When running `uvicorn` from project root (not `backend/`), pydantic-settings cannot find `backend/.env` because `env_file=".env"` resolves relative to cwd.
**Why it happens:** `settings.py` uses `env_file=".env"` — a relative path. pydantic-settings resolves this against the current working directory at import time.
**How to avoid:** Always run backend commands from `backend/` directory. Document this in `DEVELOPMENT.md`.
**Warning signs:** App starts but uses default values (e.g., `STORAGE_TYPE=local` from Settings default instead of from .env), or `DATABASE_URL` is built from individual components instead of the full URL string.

### Pitfall 6: Sample Data Date-Based File Discovery
**What goes wrong:** Pipeline fails with `FileNotFoundError: Tape20Loans file not found` when running against sample data without `--pdate` matching the sample file dates.
**Why it happens:** `discover_input_files()` uses `yesterday` (derived from `pdate`) to pattern-match filenames like `Tape20Loans_{yesterday}.csv`.
**How to avoid:** Document in `DEVELOPMENT.md` that the sample data is dated to a specific reference date. Run with `--pdate <sample_date>` via the API or CLI, or set via the UI.
**Warning signs:** FileNotFoundError mentioning `Tape20Loans_` or `ExhibitAtoFormofSaleNotice`.

---

## Code Examples

Verified patterns from existing codebase:

### Settings Loading (pydantic-settings)
```python
# Source: backend/config/settings.py (existing)
# pydantic-settings auto-loads from backend/.env when cwd=backend/
# extra="ignore" means unknown env vars (like AWS_PROFILE) don't cause errors
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=True,
    env_ignore_empty=True,
    extra="ignore",
)
```

### Alembic Migration Generation
```bash
# Source: Alembic official docs — run from backend/ directory
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Storage Factory Switch
```python
# Source: backend/storage/factory.py (existing)
# STORAGE_TYPE=local → LocalStorageBackend
# STORAGE_TYPE=s3   → S3StorageBackend (requires S3_BUCKET_NAME)
storage = get_storage_backend(area="inputs")   # uses settings.STORAGE_TYPE
storage = get_storage_backend(area="outputs")  # same
```

### DEV_INPUT Path Handling (settings.py model_validator)
```python
# Source: backend/config/settings.py (existing)
# DEV_INPUT points at the files_required directory itself.
# apply_dev_paths() derives INPUT_DIR as the parent of DEV_INPUT.
# So DEV_INPUT=./data/sample/files_required → INPUT_DIR=./data/sample
# Pipeline then reads: {INPUT_DIR}/files_required/MASTER_SHEET.xlsx
if self.DEV_INPUT:
    dev_input = self.DEV_INPUT.rstrip("\\/")
    parent = os.path.dirname(dev_input) or dev_input
    self.INPUT_DIR = parent
```

**Critical:** `.env.example` must set `DEV_INPUT=./data/sample/files_required` (not `./data/sample`). The settings validator strips the `files_required` suffix to derive `INPUT_DIR`. The pipeline then appends `files_required/` back when loading files. If `DEV_INPUT` is set to `./data/sample` (without `files_required`), `INPUT_DIR` becomes `./data` and the pipeline looks in `./data/files_required/` — which doesn't exist.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `python-dotenv` | `pydantic-settings` | Already in use; handles type coercion, validation |
| Direct `os.environ` reads | `Settings` dataclass via pydantic | Already in use; no migration needed |

**Deprecated/outdated in this codebase:**
- `backend/.env` currently: `STORAGE_TYPE=s3` active, `DEV_INPUT` set to Windows absolute path — this is the artifact to remove.

---

## Open Questions

1. **FastAPI app module path for uvicorn**
   - What we know: `backend/api/main.py` exists; the ASGI app object name is presumed to be `app`
   - What's unclear: Exact import path (`api.main:app` vs `backend.api.main:app`)
   - Recommendation: Verify by checking `backend/api/main.py` before writing the Makefile. Run from `backend/` directory so `api.main:app` should be correct.

2. **Synthetic sample data creation**
   - What we know: The pipeline needs 3+ Excel files with specific sheet names and a CSV tape file; the `conftest.py` has Python fixtures that model the required structure
   - What's unclear: Whether to create truly minimal synthetic files (tiny datasets) or to use anonymized/modified versions of existing files
   - Recommendation: Create synthetic files programmatically using pandas (as `conftest.py` does) — this avoids any PII concerns and keeps sample data small enough to commit.

3. **`alembic upgrade head` against an existing (non-empty) database**
   - What we know: If a developer has an older local Postgres instance with existing tables (from running `Base.metadata.create_all()` manually in the past), `alembic upgrade head` may fail with constraint conflicts
   - What's unclear: Whether any existing instances have pre-migration tables
   - Recommendation: Document in `DEVELOPMENT.md`: "If you have an existing `intrepid_poc` database, drop and recreate it before running `make migrate`." Include: `psql -U postgres -c "DROP DATABASE IF EXISTS intrepid_poc; CREATE DATABASE intrepid_poc;"`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.3 |
| Config file | `backend/pytest.ini` (exists) |
| Quick run command | `cd backend && venv/bin/pytest tests/ -x --tb=short -q` |
| Full suite command | `cd backend && venv/bin/pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOCAL-01 | Backend starts, connects to Postgres | smoke | `cd backend && venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000` (start + curl /api/health) | manual-only — no automated startup test |
| LOCAL-02 | Frontend starts with HMR at port 5173 | smoke | `cd frontend && npm run dev` (visual verify) | manual-only |
| LOCAL-03 | `.env` has no Windows paths, `STORAGE_TYPE=local` | manual inspect | `grep -n "C:\\\\" backend/.env` should return nothing | manual inspect |
| LOCAL-04 | `.env.example` covers all required vars | manual inspect | `diff <(grep -v '^#' backend/.env.example \| grep -v '^$' \| cut -d= -f1) <(expected list)` | ❌ Wave 0: `.env.example` does not exist yet |
| LOCAL-05 | Alembic migrations apply cleanly | integration | `cd backend && venv/bin/alembic upgrade head` (exit 0) | ❌ Wave 0: no migration version files exist yet |
| LOCAL-06 | Pipeline completes end-to-end on sample data | integration | `cd backend && venv/bin/python main.py --pdate <sample_date>` (exit 0) | ❌ Wave 0: `backend/data/sample/` does not exist yet |

### Sampling Rate
- **Per task commit:** `cd backend && venv/bin/pytest tests/ -x -q` (unit tests only, ~30s, no DB required — uses SQLite in-memory)
- **Per wave merge:** `cd backend && venv/bin/pytest tests/ -v`
- **Phase gate:** All 6 LOCAL requirements verified manually before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/data/sample/files_required/` — sample data directory with pipeline input files (covers LOCAL-06)
- [ ] `backend/.env.example` — committed env template (covers LOCAL-04)
- [ ] `backend/migrations/versions/<hash>_initial_schema.py` — generated via `alembic revision --autogenerate` (covers LOCAL-05)
- [ ] `Makefile` — root-level with setup/run-backend/run-frontend/migrate targets
- [ ] `DEVELOPMENT.md` — root-level onboarding guide

*(Existing test infrastructure in `backend/tests/` covers unit testing with SQLite in-memory; no new test files needed for Phase 1 — the phase requirements are validated via manual smoke testing and CLI/migration verification.)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `backend/config/settings.py`, `backend/migrations/env.py`, `backend/alembic.ini`, `backend/.gitignore`, `backend/.env` (current state)
- `backend/orchestration/pipeline.py` — pipeline file loading requirements
- `backend/tests/conftest.py` — sample data structure reference
- `backend/storage/factory.py` — storage abstraction switch behavior

### Secondary (MEDIUM confidence)
- Alembic documentation (standard `--autogenerate` workflow)
- pydantic-settings documentation (env_file path resolution behavior)
- git documentation (`.gitignore` negation pattern ordering)

### Tertiary (LOW confidence)
- None — all findings are from direct codebase inspection or well-established tool documentation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — inspected `requirements.txt`, `package.json`, all relevant source files directly
- Architecture: HIGH — all patterns derived from existing working code; no guesswork
- Pitfalls: HIGH (path/module pitfalls) / MEDIUM (Alembic enum caveat) — based on known pydantic-settings and git behavior

**Research date:** 2026-03-05
**Valid until:** 2026-06-05 (stable tools; no fast-moving dependencies in this phase)
