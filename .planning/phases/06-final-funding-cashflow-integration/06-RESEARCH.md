# Phase 6: Final Funding & Cashflow Integration - Research

**Researched:** 2026-03-09
**Domain:** Python FastAPI backend job-queue pattern, script replacement, storage bridging, React polling UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Real `final_funding_sg.py` and `final_funding_cibc.py` scripts exist in the legacy loan_engine repo (local folder) and already follow the FOLDER env var convention (input from `files_required/`, output to `output/` and `output_share/`). Bundle them directly into `backend/scripts/` — replace the stubs, no env var config required for deployment.
- No wrapper or adapter needed — scripts are convention-compatible with the existing runner.
- Cashflow outputs (from the CashFlow page, stored in the `outputs` S3 prefix / local outputs dir) must be automatically available as Final Funding inputs without Ops manually downloading and re-uploading. Ops triggers cashflow and final funding runs independently — no automatic chaining.
- Final Funding SG and CIBC runs should show status in the UI (RUNNING, COMPLETED, FAILED) — not just a completion alert. Pattern: similar to the CashFlow job queue (cashflow_job table pattern).
- Real scripts produce Excel workbooks in `output/` and `output_share/`. Output browsing via the existing ProgramRuns file manager is sufficient — no dedicated output panel needed for Phase 6. Runner already copies `output/` → outputs storage area under `final_funding_sg/` or `final_funding_cibc/` prefix.
- Tagging, wire instruction PDFs, SES email, and counterparty tagging are NOT part of this phase.

### Claude's Discretion
- Exact DB schema for run tracking (new table vs extending cashflow_job)
- Implementation of cashflow → final funding input bridge mechanism
- UI layout for run status display within Program Runs page

### Deferred Ideas (OUT OF SCOPE)
- Wire instruction PDF generation (WeasyPrint + Jinja2) — v2.0 / BIZ-01
- SES email delivery to counterparties — v2.0 / BIZ-02
- Counterparty tagging stub replacement — separate phase or v2.0
- In-UI PDF preview — v2.0 / BIZ-04
</user_constraints>

---

## Summary

Phase 6 is composed of three tightly related pieces: (1) replace the stub Final Funding SG and CIBC scripts with the real Python workbook scripts from the legacy `loan_engine` repo, (2) add a lightweight job tracking table so Ops can see RUNNING / COMPLETED / FAILED status in the UI instead of waiting for a browser alert, and (3) provide a bridge so cashflow outputs written to the outputs storage area are automatically available as inputs to Final Funding runs without manual download-upload.

The work builds almost entirely on patterns that already exist in this codebase. The `cashflow_job` table in `backend/cashflow/routes.py` is the reference implementation for async job tracking — it defines the exact DB schema, job lifecycle states, orphan detection, progress messages, and polling API. The `final_funding_runner.py` already handles local/S3, temp dirs, script execution, and output upload. The real legacy scripts use hardcoded Windows paths (e.g. `folder = Path(r'C:\Users\omack\Intrepid\...')`) and must be patched to read `folder = Path(os.environ.get("FOLDER"))` before being bundled. The cashflow→final funding bridge is the only design decision with real optionality.

**Primary recommendation:** Add a `final_funding_job` table mirroring `cashflow_job` (with `mode` discriminator distinguishing `sg` / `cibc`), wrap `execute_final_funding_sg/cibc` calls in a background thread that writes status updates to this table, expose `GET /api/program-run/jobs` and `GET /api/program-run/jobs/{job_id}` endpoints, and have ProgramRuns.tsx poll these endpoints for each button. For the cashflow bridge, use a lightweight "copy on trigger" approach: when a Final Funding run starts, the runner copies any matching files from the outputs storage area into the temp `files_required/` before executing the script.

---

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | API router for new job endpoints | Already in use |
| psycopg v3 | current | Direct DB access for job state table | cashflow_job already uses this pattern |
| SQLAlchemy | current | PipelineRun model; not needed for job table | cashflow uses raw psycopg, follow same |
| React + axios | 19 / current | Frontend polling | Identical to cashflow job polling pattern |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading | stdlib | Background job execution | Same as pipeline run background thread |
| subprocess | stdlib | Script execution via `_run_workbook_script` | Already used in final_funding_runner.py |
| storage backends | local | Bridging outputs→inputs areas | Already used for all file operations |

### No New Dependencies Required
All required libraries are already in `requirements.txt`. No new packages needed for Phase 6.

---

## Architecture Patterns

### Recommended File Layout Changes
```
backend/
├── scripts/
│   ├── final_funding_sg.py      # REPLACE stub with real script (FOLDER env patched)
│   └── final_funding_cibc.py    # REPLACE stub with real script (FOLDER env patched)
├── orchestration/
│   └── final_funding_runner.py  # ADD job tracking hooks (status write before/after run)
├── api/
│   └── routes.py                # ADD job create/list/get endpoints; refactor program-run handler
└── cashflow/
    └── routes.py                # REFERENCE ONLY — do not modify
```

```
frontend/src/pages/
└── ProgramRuns.tsx              # ADD job status display per button; replace alert() pattern
```

### Pattern 1: Job Table — Reuse cashflow_job Schema with a Mode Discriminator

**What:** Add a `final_funding_job` table whose DDL is a strict subset of `cashflow_job`. Use a `mode` column with values `'sg'` or `'cibc'` to distinguish SG from CIBC runs. The `_ensure_final_funding_job_table()` function creates it on first use, identical to `_ensure_cashflow_job_table()`.

**When to use:** Any time a new async job type needs status tracking. The discriminator-per-table approach (separate `final_funding_job`) is cleaner than adding to `cashflow_job` because it avoids mode-namespace collisions and keeps cashflow job history independent of final funding job history.

**Recommended schema:**
```sql
CREATE TABLE IF NOT EXISTS final_funding_job (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,          -- QUEUED | RUNNING | COMPLETED | FAILED
  mode TEXT NOT NULL,            -- 'sg' | 'cibc'
  created_at TIMESTAMPTZ NOT NULL,
  started_at TIMESTAMPTZ NULL,
  completed_at TIMESTAMPTZ NULL,
  request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_prefix TEXT NULL,       -- e.g. 'final_funding_sg'
  progress_message TEXT NULL,
  error_detail TEXT NULL,
  owner_instance TEXT NULL,
  worker_pid INTEGER NULL,
  last_heartbeat TIMESTAMPTZ NULL
);
```

Note: `cancel_requested`, `worker_task_arn`, `log_messages_json`, `output_files_json`, and `progress_percent` from `cashflow_job` are all optional — Phase 6 should include at minimum: `status`, `mode`, `created_at`, `started_at`, `completed_at`, `progress_message`, `error_detail`, `output_prefix`, `owner_instance`, `worker_pid`, `last_heartbeat`. Add `log_messages_json` if you want log display; skip `cancel_requested` unless cancellation is in scope.

### Pattern 2: Background Job Execution — Threading Pattern

**What:** The `create_program_run` route currently calls `execute_final_funding_sg/cibc()` synchronously, which blocks until the script finishes (potentially minutes). Replace with a background thread that writes status to `final_funding_job` table.

**Reference:** `_run_pipeline_background` in `backend/api/routes.py` (threading.Thread pattern) and `_run_cashflow_job` in `backend/cashflow/routes.py` (status update pattern).

**Example flow:**
```python
# In create_program_run handler, for final_funding_sg:
job_id = f"ff-sg-{uuid4()}"
# INSERT job row with status=QUEUED
thread = threading.Thread(target=_run_ff_job_background, args=(job_id, "sg", body.folder))
thread.start()
return {"job_id": job_id, "status": "QUEUED", ...}

def _run_ff_job_background(job_id: str, mode: str, folder: Optional[str]) -> None:
    _set_ff_job_state(job_id, status="RUNNING", started_at=now())
    try:
        if mode == "sg":
            output_prefix = execute_final_funding_sg(folder=folder)
        else:
            output_prefix = execute_final_funding_cibc(folder=folder)
        _set_ff_job_state(job_id, status="COMPLETED", output_prefix=output_prefix, completed_at=now())
    except Exception as e:
        _set_ff_job_state(job_id, status="FAILED", error_detail=str(e), completed_at=now())
```

### Pattern 3: Cashflow → Final Funding Input Bridge

**What:** Before executing the Final Funding script in `_execute_final_funding`, scan the `outputs` storage area for any files matching cashflow output naming conventions and copy them into the temp `files_required/` directory alongside other inputs.

**Design decision:** Use "copy on trigger" — at run start, before `_run_workbook_script`, read the outputs storage area and copy any matching cashflow outputs into the temp work dir's `files_required/`. This is the lightest-weight approach: no S3 object copy overhead (because the runner already syncs all inputs to temp), no permanent duplication, no UI action required.

**What the real scripts need from cashflow outputs:** The real scripts read `current_assets.csv` from `files_required/`. The cashflow `current_assets` mode produces this file (named by `req.current_assets_output`). This is the primary bridge candidate. The scripts also read exhibit files (SFY/PRIME), MASTER_SHEET, and FX3/FX4 servicing files — these come from the main inputs area, not cashflow outputs.

**Concrete implementation:**
```python
def _bridge_cashflow_outputs_to_inputs(temp_dir: str, storage_type: str) -> None:
    """Copy cashflow outputs (current_assets.csv) from outputs area into temp files_required/."""
    files_required = Path(temp_dir) / "files_required"
    output_storage = get_storage_backend(area="outputs")
    # current_assets.csv is the primary cashflow output needed by final funding scripts
    for candidate_name in ["current_assets.csv"]:
        if output_storage.file_exists(candidate_name):
            content = output_storage.read_file(candidate_name)
            dest = files_required / candidate_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            logger.info("Bridged cashflow output %s into final funding inputs", candidate_name)
```

Call this inside `_execute_final_funding` after `_prepare_temp_input_from_local/s3` and before `_run_workbook_script`.

**Important:** The bridge does NOT fail if the cashflow output is absent. If `current_assets.csv` is not in the outputs area, it silently skips — the script will fail naturally if it needs the file. This keeps the bridge non-blocking.

### Pattern 4: New API Endpoints

Add to `backend/api/routes.py` (or a new `backend/api/program_run_jobs.py`):

```
POST   /api/program-run/jobs           # Create job, start background thread, return job row
GET    /api/program-run/jobs           # List recent jobs (all modes, last 20)
GET    /api/program-run/jobs/{job_id}  # Poll single job status
```

Keep `POST /api/program-run` as-is for backward compat (pre_funding and tagging paths). Change `final_funding_sg` and `final_funding_cibc` paths to delegate to the new job creation flow.

### Pattern 5: Frontend Polling

Replace `alert()` in `runFinalFundingSG` / `runFinalFundingCIBC` with job-id-based polling identical to the `stdoutRunId` / `fetchStdout` pattern already in `ProgramRuns.tsx` for pre-funding runs.

```typescript
// State additions:
const [finalFundingSGJobId, setFinalFundingSGJobId] = useState<string | null>(null)
const [finalFundingSGStatus, setFinalFundingSGStatus] = useState<string>('')
const [finalFundingCIBCJobId, setFinalFundingCIBCJobId] = useState<string | null>(null)
const [finalFundingCIBCStatus, setFinalFundingCIBCStatus] = useState<string>('')

// In runFinalFundingSG:
const res = await axios.post('/api/program-run/jobs', { mode: 'sg' })
setFinalFundingSGJobId(res.data.job_id)
setFinalFundingSGStatus('QUEUED')

// useEffect polling (3-second interval while status in {QUEUED, RUNNING}):
const poll = async () => {
  const res = await axios.get(`/api/program-run/jobs/${jobId}`)
  setFinalFundingSGStatus(res.data.status)
  if (res.data.status === 'COMPLETED') { loadOutputFiles() }
  if (res.data.status === 'RUNNING' || res.data.status === 'QUEUED') {
    setTimeout(poll, 3000)
  }
}
```

Display status inline beneath each button: `"Status: RUNNING..."` or `"Status: COMPLETED"` or `"Failed: {error_detail}"`.

### Anti-Patterns to Avoid
- **Modifying cashflow_job table for final funding:** Adds mode namespace collision risk, pollutes cashflow job history, couples unrelated job types in one table. Use a separate `final_funding_job` table.
- **Synchronous script execution in the route handler:** Final Funding scripts can take several minutes; keeping the HTTP connection open until completion will hit the ALB 60-second timeout. Always run in a background thread.
- **Permanent file copies for the bridge:** Copying cashflow outputs into the inputs area permanently causes confusion about which files are "real" inputs vs derived. Copy only into the ephemeral temp dir.
- **Failing the run when cashflow bridge files are absent:** The bridge is optional convenience. The script should fail on its own terms if it needs a file that is not present.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job state DB access | Custom ORM layer | Same raw psycopg pattern as cashflow_job | Already works; psycopg v3 row dicts are sufficient |
| Script execution isolation | Custom sandbox | subprocess with FOLDER env + temp dir | final_funding_runner._run_workbook_script already does this |
| Storage reads/writes | Direct boto3/pathlib calls | `get_storage_backend(area=...)` | Handles local/S3 transparently; already tested in prod |
| Orphan job detection | Custom heartbeat system | Same _reconcile_orphaned_job pattern | cashflow_job implementation handles ECS task ARN, PID, heartbeat age |
| Output file listing | Custom file browser | Existing `/api/files/list` + ProgramRuns file manager | Already works for `final_funding_sg/` and `final_funding_cibc/` prefixes |

**Key insight:** The hardest part of this phase — the file convention glue, temp dir lifecycle, S3 sync, and output upload — is already implemented and tested in `final_funding_runner.py`. Phase 6 adds job tracking around it, not a new runner.

---

## Common Pitfalls

### Pitfall 1: Legacy Scripts Use Hardcoded Folder Paths
**What goes wrong:** The real scripts at `loan_engine/inputs/93rd_buy/bin/final_funding_sg.py` and `final_funding_cibc.py` open with `folder = Path(r'C:\Users\omack\Intrepid\pythonFramework\loan_engine\inputs\93rd_buy')` — a hardcoded absolute Windows path. If bundled as-is, they will always read from that path and ignore the `FOLDER` env var.
**Why it happens:** The legacy scripts were Jupyter notebook exports run interactively on the developer's machine.
**How to avoid:** Before copying into `backend/scripts/`, patch the first few lines to `folder = Path(os.environ.get("FOLDER", ".")).resolve()` and remove the hardcoded IRR/date variables (`pdate`, `curr_date`, `last_end`, `fd`, `yestarday`). These variables are derived from filenames already present in `files_required/` — the scripts discover filenames by iterating the directory, not by using these date vars directly for I/O (they use them for DataFrame filtering). Verify that removing the hardcoded date initialization does not break file-loading logic.
**Warning signs:** Script runs and produces output at the wrong path, or raises FileNotFoundError pointing at a non-existent Windows path.

### Pitfall 2: Script Uses `folder` Variable for Both Path and Date Context
**What goes wrong:** The real scripts use `pdate`, `curr_date`, `last_end`, `fd`, `yestarday` as both file-discovery variables and DataFrame filtering values. If you only patch `folder` and leave these hardcoded, the script will read the right files but apply filtering based on the 93rd buy's dates.
**Why it happens:** Legacy scripts were written for a specific buy cycle and committed with specific dates.
**How to avoid:** The scripts load files by constructing paths from `folder` plus hardcoded filename patterns that include the date strings. The filenames in `files_required/` must match those patterns, so these date variables are essentially filename aliases. Keep them as-is OR make the runner detect filenames dynamically. The simplest fix: keep the date variables in the script as-is for the 93rd buy; when the 94th buy script is needed, update them. The planner should flag this as a known limitation.
**Warning signs:** Script loads wrong files (e.g. loading 93rd buy exhibit from files_required/ that actually contains 94th buy exhibits).

### Pitfall 3: Two Concurrent Runs of Same Mode
**What goes wrong:** Ops clicks "Final Funding SG" twice quickly; two jobs start, both writing to `final_funding_sg/` prefix, files interleave.
**Why it happens:** No concurrency guard in the current synchronous handler.
**How to avoid:** On job creation, query for any existing job with `status IN ('QUEUED', 'RUNNING') AND mode = 'sg'` and return 409 if one exists. Mirror the `pg_advisory_xact_lock` pattern used in `cashflow_job` creation.
**Warning signs:** Partial/corrupt output Excel files in the file manager.

### Pitfall 4: The Current `create_program_run` Endpoint Is Synchronous and Will Timeout
**What goes wrong:** Real Final Funding scripts run for several minutes (heavy pandas computation, multiple Excel files, underwriting loops). The current handler blocks the HTTP connection until the script finishes. ALB timeout is 60 seconds — anything longer returns a 504 to the browser.
**Why it happens:** The stub scripts finish in milliseconds; the synchronous approach was invisible before. The real scripts take minutes.
**How to avoid:** Move to background threading before landing the real scripts. Return 202 immediately with job_id, let the frontend poll for status.
**Warning signs:** Requests that succeed locally but return 504 in AWS staging.

### Pitfall 5: Cashflow Output Key Paths May Not Match What Final Funding Expects
**What goes wrong:** The bridge copies `current_assets.csv` from the outputs area, but the outputs area may contain it at a sub-prefix (e.g. `cashflow-abc123/current_assets.csv`) rather than at the root.
**Why it happens:** Cashflow job output files are stored under a job-specific key, not at the root of the outputs area.
**How to avoid:** The bridge should list all files in the outputs area and find the most-recently-modified file named `current_assets.csv` regardless of prefix depth. Use `storage.list_files("", recursive=True)` and filter by filename, sort by `last_modified` descending, take the first match.
**Warning signs:** Bridge copies nothing despite cashflow having run successfully; script fails with missing file.

---

## Code Examples

### Creating a Final Funding Job Row (psycopg pattern from cashflow_job)
```python
# Source: backend/cashflow/routes.py _ensure_cashflow_job_table and create_cashflow_job
from cashflow.db import db_conn
from psycopg.types.json import Json

def _ensure_final_funding_job_table() -> None:
    with db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS final_funding_job (
              job_id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              mode TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL,
              started_at TIMESTAMPTZ NULL,
              completed_at TIMESTAMPTZ NULL,
              output_prefix TEXT NULL,
              progress_message TEXT NULL,
              log_messages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
              error_detail TEXT NULL,
              owner_instance TEXT NULL,
              worker_pid INTEGER NULL,
              last_heartbeat TIMESTAMPTZ NULL
            )
        """)
```

### Detecting Orphaned Jobs (from cashflow_job pattern)
```python
# Source: backend/cashflow/routes.py _reconcile_orphaned_job
# Key check: if owner_instance is this instance and PID is dead → mark FAILED
# If last_heartbeat is > 1hr old from unknown instance → mark FAILED
# For final_funding_job: simpler because no ECS task ARN needed (runs in main process thread)
```

### Storage Backend Bridge Call
```python
# Source: backend/storage/factory.py get_storage_backend + backend/storage/local.py list_files
output_storage = get_storage_backend(area="outputs")
all_outputs = output_storage.list_files("", recursive=True)
# FileInfo has: path, size, is_directory, last_modified
candidates = [f for f in all_outputs if not f.is_directory and f.path.endswith("current_assets.csv")]
candidates.sort(key=lambda f: f.last_modified or "", reverse=True)
if candidates:
    content = output_storage.read_file(candidates[0].path)
    (files_required_path / "current_assets.csv").write_bytes(content)
```

### Frontend Status Polling Pattern (already in ProgramRuns.tsx)
```typescript
// Source: frontend/src/pages/ProgramRuns.tsx — stdoutRunId / fetchStdout useEffect
// Exact same pattern: useEffect on jobId state, 3-second setTimeout re-poll,
// clear jobId when status reaches terminal state (COMPLETED/FAILED)
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Browser alert on completion | Job status polling with DB-backed state | cashflow_job already does this; phase 6 extends the pattern |
| Synchronous HTTP request blocking until script done | Return 202 + job_id immediately; frontend polls | Required to survive ALB 60-second timeout |
| Manual download/re-upload of cashflow outputs | Storage-layer bridge copies on run start | Keeps inputs and outputs storage areas logically separate |

---

## Open Questions

1. **Which files do the real scripts actually require that could come from cashflow outputs?**
   - What we know: Both scripts read `current_assets.csv` from `files_required/`. This is produced by the cashflow `current_assets` mode.
   - What's unclear: Whether any other cashflow outputs (e.g. the cashflow Excel workbooks) feed into final funding scripts. From reading the real scripts, they do not appear to — they only need `current_assets.csv` from prior cashflow runs.
   - Recommendation: Bridge only `current_assets.csv`. If other files are needed, Ops can upload them manually via the existing file manager.

2. **Do the hardcoded date variables (`pdate`, `curr_date`, etc.) in the real scripts cause runtime failures, or are they only used for DataFrame filtering?**
   - What we know: The scripts load files using `folder / "files_required" / f"FX3_{curr_date}_ExhibitAtoFormofSaleNotice_sg.xlsx"` — so the date variables are embedded in file paths. If files_required contains differently-dated files, the script will raise FileNotFoundError.
   - What's unclear: Whether Ops always uses the same buy cycle's files_required/ or switches between buys.
   - Recommendation: The script replacement task must document that the date variables in the bundled scripts are set to 93rd buy dates and must be updated manually for each new buy cycle (or made configurable). Flag this as a known limitation in the plan.

3. **Should `final_funding_job` reuse `cashflow.db.db_conn` or use the SQLAlchemy session from `db.connection`?**
   - What we know: `cashflow_job` uses raw psycopg via `cashflow.db.db_conn`. `PipelineRun` uses SQLAlchemy via `db.connection`. Both connect to the same Postgres database.
   - Recommendation: Use the same `cashflow.db.db_conn` approach — it is already in the codebase and avoids mixing ORM and raw SQL for job state tables. The job table does not need SQLAlchemy relationships.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini in backend/) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_final_funding_jobs.py -x -v` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FF-01 | Real SG script executes against files_required/ and produces Excel output in output/ | unit/integration | `pytest tests/test_final_funding_runner.py::test_sg_script_executes -x` | ❌ Wave 0 |
| FF-02 | Real CIBC script executes against files_required/ and produces Excel output in output/ | unit/integration | `pytest tests/test_final_funding_runner.py::test_cibc_script_executes -x` | ❌ Wave 0 |
| FF-03 | Job creation returns 202 with job_id; job row inserted in DB with status=QUEUED | unit | `pytest tests/test_final_funding_jobs.py::test_create_job_returns_queued -x` | ❌ Wave 0 |
| FF-04 | Job transitions QUEUED → RUNNING → COMPLETED when script succeeds | unit | `pytest tests/test_final_funding_jobs.py::test_job_lifecycle_success -x` | ❌ Wave 0 |
| FF-05 | Job transitions to FAILED when script raises exception | unit | `pytest tests/test_final_funding_jobs.py::test_job_lifecycle_failure -x` | ❌ Wave 0 |
| FF-06 | GET /api/program-run/jobs/{job_id} returns correct status | unit | `pytest tests/test_final_funding_jobs.py::test_poll_endpoint -x` | ❌ Wave 0 |
| FF-07 | Cashflow bridge copies current_assets.csv from outputs area into temp files_required/ | unit | `pytest tests/test_final_funding_runner.py::test_cashflow_bridge_copies_file -x` | ❌ Wave 0 |
| FF-08 | Bridge is a no-op when current_assets.csv is not in outputs area (no error) | unit | `pytest tests/test_final_funding_runner.py::test_cashflow_bridge_absent_is_noop -x` | ❌ Wave 0 |
| FF-09 | Concurrent job creation for same mode returns 409 | unit | `pytest tests/test_final_funding_jobs.py::test_concurrent_job_409 -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_final_funding_jobs.py tests/test_final_funding_runner.py -x -v`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_final_funding_jobs.py` — covers FF-03, FF-04, FF-05, FF-06, FF-09
- [ ] `backend/tests/test_final_funding_runner.py` — covers FF-01, FF-02, FF-07, FF-08
- [ ] Existing `backend/tests/conftest.py` should be extended with fixtures for DB connection and temp input dirs

Note: FF-01 and FF-02 (real script execution) require a minimal `files_required/` directory with at least placeholder Excel files. These are integration-style tests that may need to be marked `@pytest.mark.slow` or `@pytest.mark.integration` and skipped in CI without sample data.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `backend/orchestration/final_funding_runner.py` — runner implementation confirmed, storage conventions verified
- Direct code inspection: `backend/cashflow/routes.py` — cashflow_job table schema, job lifecycle, polling endpoints, orphan detection, full implementation
- Direct code inspection: `backend/api/routes.py` — current program-run endpoint, synchronous execution pattern, threading pattern for pipeline
- Direct code inspection: `frontend/src/pages/ProgramRuns.tsx` — existing button/alert pattern, polling pattern (stdoutRunId), file manager
- Direct code inspection: `backend/storage/factory.py` + `local.py` — storage abstraction, area-based routing
- Direct code inspection: `backend/config/settings.py` — FINAL_FUNDING_SG_SCRIPT_PATH, FINAL_FUNDING_CIBC_SCRIPT_PATH settings
- Direct code inspection: `loan_engine/inputs/93rd_buy/bin/final_funding_sg.py` and `final_funding_cibc.py` — confirmed hardcoded paths, confirmed FOLDER env var is NOT read (stubs are), confirmed file dependencies

### Secondary (MEDIUM confidence)
- `backend/scripts/final_funding_sg.py` and `final_funding_cibc.py` — confirmed these are stubs; the runner already searches for bundled scripts here via `_BUNDLED_SG` / `_BUNDLED_CIBC`

### Tertiary (LOW confidence)
- None — all findings are from direct codebase inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code verified by direct inspection, no new libraries
- Architecture patterns: HIGH — job table and threading patterns copied from existing cashflow_job; bridge design is new but simple
- Pitfalls: HIGH — hardcoded paths confirmed by reading the real scripts; ALB timeout pitfall confirmed by architecture review; concurrency gap confirmed by reading current route handler
- Script content: HIGH — read both real scripts completely; identified hardcoded `folder` variable as the sole blocker for bundling

**Research date:** 2026-03-09
**Valid until:** 2026-06-09 (stable internal codebase; no external dependencies to expire)
