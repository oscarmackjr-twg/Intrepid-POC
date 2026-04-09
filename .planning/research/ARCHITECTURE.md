# Architecture Research
**Project:** Intrepid Loan Purchase Operations Platform
**Dimension:** Architecture
**Date:** 2026-03-04
**Status:** Research complete

---

## Question

How should a React/Node/Python/Postgres loan purchase operations platform be architected? What are the major components and how do they connect?

---

## Key Findings

### The stack is not actually React + Node + Python + Postgres

**Important correction from the codebase:** The existing scaffolding uses React (Vite/TypeScript) talking directly to a Python FastAPI backend. There is no Node.js layer. The "Node orchestrates Python" mental model does not match what has been built.

The actual stack, as confirmed by the code:
- **Frontend:** React 19 + TypeScript, Vite build tooling, React Router, Axios, Tailwind CSS
- **Backend/API:** Python FastAPI (uvicorn), served on port 8000
- **Business Logic:** Python — pandas, numpy, scipy, numpy-financial (all in-process with the API)
- **Database:** PostgreSQL via SQLAlchemy ORM + Alembic migrations
- **File Storage:** AWS S3 (abstracted behind a `StorageBackend` interface; local filesystem for dev)
- **Infrastructure:** AWS ECS Fargate + ALB + RDS + S3, managed by Terraform

The roadmap should plan around Python FastAPI as the orchestration and API layer, not a separate Node.js service.

---

## Component Architecture

### Layer 1: React Frontend

**Location:** `frontend/src/`

The frontend is a React SPA served as static files. In production it is built and embedded into the Docker image, then served by FastAPI's `StaticFiles` mount and SPA fallback route. In development, Vite dev server proxies API calls to the FastAPI backend.

**Pages currently implemented:**
- `Dashboard` — run status overview
- `Runs` / `RunDetail` — pipeline run list and per-run detail
- `Exceptions` — loan-level exceptions viewer
- `RejectedLoans` — rejected loan list with rejection criteria
- `FileManager` — upload and browse input files (S3 or local)
- `CashFlow` — cashflow job submission and results
- `ProgramRuns` — final funding workbook outputs
- `HolidayMaintenance` — admin-managed holiday calendar
- `Login` — JWT-based auth

**Authentication pattern:** JWT tokens stored in browser, sent as `Authorization: Bearer` on every API call. `AuthContext` provides user state; `ProtectedRoute` wraps all routes. Role-based: `admin`, `analyst`, `sales_team`.

**React → FastAPI boundary:** All communication is REST over HTTP. The frontend has no direct database access and no Python process access. Axios is the HTTP client.

**Missing for the full workflow:**
- No wire instruction PDF viewer or send-to-email UI (Stage 5 of the workflow)
- No step-by-step workflow stepper UI (each workflow stage is a separate manual API call, but there is no guided wizard)

---

### Layer 2: FastAPI Backend (the "orchestration" layer)

**Location:** `backend/api/` + `backend/orchestration/`

FastAPI is the single backend process. It serves both the REST API and (in production) the static frontend build. There is no separate Node.js service.

**Routers:**
| Module | Prefix | Purpose |
|---|---|---|
| `api/routes.py` | `/api` | Pipeline runs, loan data, exceptions, downloads |
| `api/files.py` | `/api/files` | File upload/browse/download |
| `cashflow/routes.py` | `/api/cashflow` | Cashflow job submission and status |
| `auth/routes.py` | `/auth` | Login, token refresh |

**How the API triggers Python business logic:**

The API does NOT call Python as a subprocess in the main pipeline path. Pipeline logic runs in-process in a background thread:

```python
# backend/api/routes.py line 446
thread = threading.Thread(target=_run_pipeline_background, args=(context, run_data))
thread.start()
# Returns 202 Accepted immediately
```

`_run_pipeline_background` calls `PipelineExecutor.execute()` directly — same Python process, different thread. The run's status (`PENDING` → `RUNNING` → `COMPLETED`/`FAILED`) is written to Postgres, and the frontend polls `GET /api/runs/{run_id}` to show progress.

**Exception: the tagging and final funding scripts use subprocess.** When an external Python script path is configured (`TAGGING_SCRIPT_PATH`), `tagging_runner.py` and `final_funding_runner.py` launch it via `subprocess.run()` with environment variables as the interface:

```python
# backend/orchestration/tagging_runner.py
result = subprocess.run(
    [os.environ.get("PYTHON", "python"), script_path],
    env=env,   # INPUT_DIR, OUTPUT_DIR injected
    capture_output=True,
    text=True,
    timeout=3600,
)
```

**Cashflow computation also uses subprocess** for local execution and AWS ECS task launch for production-scale runs:

```python
# backend/cashflow/routes.py
_LOCAL_JOB_PROCS: dict[str, subprocess.Popen[str]] = {}
# or: launch ECS task via boto3
```

**Summary of integration patterns by component:**

| Component | Integration Pattern | Rationale |
|---|---|---|
| Main suitability pipeline | In-process, background thread | Low latency, shares models/DB session |
| Tagging script (external) | `subprocess.run`, env vars | Legacy script isolation |
| Final funding workbooks | `subprocess.run`, env vars | Legacy script isolation |
| Cashflow (local) | `subprocess.Popen`, long-running | CPU-heavy, needs cancellation support |
| Cashflow (production) | AWS ECS task launch via boto3 | Horizontal scale, separate container |

**Recommended pattern for new workflow stages:** Keep new logic in-process (Python functions called directly), run in a background thread. Use subprocess only when integrating external scripts that cannot be refactored. Avoid message queues at this scale (2x/week, ~1000 loans).

---

### Layer 3: Python Business Logic

**Location:** `backend/` subpackages

All computation is Python. The key modules:

| Package | Role |
|---|---|
| `orchestration/pipeline.py` | `PipelineExecutor` — coordinates all stages in sequence |
| `orchestration/run_context.py` | `RunContext` dataclass — parameters for one run (run_id, pdate, irr_target, sales_team_id) |
| `transforms/normalize.py` | Column normalization, header standardization for loan tapes |
| `transforms/enrichment.py` | Tag loans by group, add seller loan numbers, mark repurchased loans |
| `rules/purchase_price.py` | Purchase price validation against master sheet |
| `rules/underwriting.py` | FICO, DTI, PTI, income checks against underwriting grids |
| `rules/comap.py` | CoMAP grid checks for Prime and SFY |
| `rules/eligibility.py` | Eligibility checks (A through L) for Prime and SFY |
| `cashflow/compute/` | Amortization, prepayment, default model, ARM reset, waterfall |
| `outputs/excel_exports.py` | Exception report Excel generation |
| `outputs/eligibility_reports.py` | Eligibility report generation |
| `storage/` | `StorageBackend` abstraction (local filesystem or S3) |
| `scheduler/job_scheduler.py` | APScheduler-based automated daily runs |

**Key dependency: pandas DataFrames as the in-memory data structure.** Loan data flows through the pipeline as `pd.DataFrame` objects, passed between functions. There is no serialization overhead within a single run.

---

### Layer 4: PostgreSQL Database

**Location:** `backend/db/models.py`, `backend/db/connection.py`, `backend/migrations/`

**Tables:**

| Table | Purpose |
|---|---|
| `users` | Auth — email, hashed password, role, sales_team_id |
| `sales_teams` | Multi-tenancy — each sales team sees only their runs |
| `pipeline_runs` | One row per run — status, pdate, irr_target, summary counts, last_phase |
| `loan_exceptions` | One row per loan-level exception — type, category, severity, rejection_criteria, loan_data JSON |
| `loan_facts` | One row per processed loan — validation flags, disposition, rejection_criteria |
| `holidays` | Admin-managed business calendar by country |
| `cashflow_jobs` | (in cashflow/db.py) Cashflow job tracking |

**ORM:** SQLAlchemy 2.0 with synchronous sessions (not async). Background thread pipeline work uses a dedicated `SessionLocal()` session, closed when the thread finishes.

**Migrations:** Alembic manages schema evolution. Ad-hoc SQL migration files also exist in `backend/db/migrations/`.

**The database is the source of truth for run state.** The frontend never reads files directly — it reads run status and loan data from Postgres via the API. Files (inputs, outputs) live in S3/filesystem; Postgres holds metadata and processing results.

---

### Layer 5: AWS Infrastructure

**Location:** `deploy/terraform/qa/`

| Resource | Service | Notes |
|---|---|---|
| Application | ECS Fargate | Single container task definition, 1 task |
| Load balancer | ALB | Terminates HTTP, forwards to container port 8000 |
| Database | RDS PostgreSQL | Private subnet, credentials in AWS Secrets Manager |
| File storage | S3 | Versioning + server-side encryption, bucket policy blocks public |
| Container registry | ECR | Docker image pushed on deploy |
| Secrets | AWS Secrets Manager | DB credentials, JWT secret key, S3 credentials |
| Logs | CloudWatch Logs | 14-day retention |

**Storage abstraction:** `backend/storage/factory.py` creates either a `LocalStorageBackend` or `S3StorageBackend` based on the `STORAGE_TYPE` environment variable. This means the same pipeline code runs in both local dev (filesystem) and production (S3) without changes.

---

## Data Flow Through the 5 Workflow Stages

### Stage 1: Upload

```
Ops user → React FileManager page
  → POST /api/files/upload (multipart form)
    → FastAPI files.py router
      → StorageBackend.upload_file()
        → S3 (production) or local filesystem (dev)
          → File stored at: {input_prefix}/files_required/{filename}
```

Files required per run:
- `MASTER_SHEET.xlsx` (prime loan tape)
- `MASTER_SHEET - Notes.xlsx` (notes tape)
- `current_assets.csv` (existing portfolio)
- `Underwriting_Grids_COMAP.xlsx` (rule grids — all sheets)
- Tape file (pattern-matched, date-based filename)

After upload, the Ops user triggers Stage 2 manually via the dashboard.

---

### Stage 2: Suitability Analysis (Pipeline Run)

```
Ops user → React Dashboard → "Start Run" button
  → POST /api/pipeline/run (body: {pdate, irr_target, folder})
    → FastAPI routes.py
      → Creates PipelineRun record (status=PENDING) in Postgres
      → Returns 202 Accepted with run_id
      → Spawns background thread: _run_pipeline_background()
        → PipelineExecutor.execute()
          → load_reference_data() — reads all files from storage
          → normalize_loans_df() — standardize columns
          → tag_loans_by_group() — enrich with tape data
          → check_purchase_price() → LoanException records written
          → check_underwriting() → LoanException records written
          → check_comap_prime/sfy() → LoanException records written
          → check_eligibility_prime/sfy() → LoanException records written
          → export_exception_reports() → Excel files written to storage
          → export_eligibility_report() → Excel files written to storage
          → LoanFact records bulk-inserted to Postgres
          → PipelineRun status → COMPLETED

React frontend polls GET /api/runs/{run_id} every N seconds
  → Shows PENDING → RUNNING → COMPLETED
  → Ops reviews exceptions in Exceptions page
```

Disposition outcome per loan: `to_purchase`, `projected`, or `rejected`.

---

### Stage 3: Counterparty Tagging

```
Ops user → React UI (counterparty tagging trigger — currently stub)
  → POST /api/pipeline/tagging (or similar endpoint)
    → FastAPI routes.py
      → execute_tagging()
        → tagging_runner.run_tagging()
          → If TAGGING_SCRIPT_PATH set:
              subprocess.run([python, script_path], env={INPUT_DIR, OUTPUT_DIR})
          → Else: stub writes placeholder output
          → Output written to storage: {output_dir}/tagging/
```

Tagging assigns eligible loans to counterparties: "prime", "SFY", or both. The tagging script is a pluggable external Python script — the current implementation is a stub pending the real script.

---

### Stage 4: Cashflow Calculation

```
Ops user → React CashFlow page → submit job
  → POST /api/cashflow/run (body: {mode, buy_num, purchase_date, target, ...})
    → FastAPI cashflow/routes.py
      → If CASHFLOW_EXECUTION_MODE == "local":
          subprocess.Popen([python, run_cashflows.py], env=job_params)
          _LOCAL_JOB_PROCS[job_id] = proc
      → If CASHFLOW_EXECUTION_MODE == "ecs_task":
          boto3 ECS run_task() → launches separate Fargate task
          Job tracked in cashflow_jobs table

React polls GET /api/cashflow/jobs/{job_id} for status
  → Output: Excel/CSV files written to S3 under cashflow/{job_id}/
  → Also: Final Funding workbooks (SG, CIBC) via execute_final_funding_sg/cibc()
      → subprocess.run() with FOLDER env var pointing to temp input dir
```

---

### Stage 5: PDF Generation and Email (Not Yet Built)

This stage is defined in requirements but not implemented in the codebase. Based on what exists:

**What needs to be built:**
- Wire instruction PDF generation (Python — reportlab or weasyprint is appropriate; xlsxwriter if Excel-to-PDF)
- An API endpoint to trigger PDF generation per counterparty
- Email delivery via SMTP or AWS SES
- A React UI step to review and approve before sending

**Where it fits architecturally:**
```
Ops user → React "Generate Wire Instructions" button
  → POST /api/pipeline/wire-instructions/{run_id}/{counterparty}
    → FastAPI routes
      → Python: reads LoanFact records for run + counterparty from Postgres
      → Python: generates PDF (in-process, background thread)
      → Python: uploads PDF to S3 at outputs/{run_id}/wire_{counterparty}.pdf
      → Returns PDF S3 key to frontend

Ops user → React "Send to Counterparty" button
  → POST /api/pipeline/send-wire/{run_id}/{counterparty}
    → FastAPI routes
      → Python: retrieves PDF from S3
      → Python: sends email via SES (boto3) with PDF attachment
      → Audit log entry written to Postgres
```

**Recommended library:** `reportlab` for PDF generation (pure Python, no external process needed). AWS SES for email (already using boto3 for S3).

---

## File Storage Approach

The `StorageBackend` abstraction (`backend/storage/`) is the key decision already made. All file I/O goes through this interface:

```python
class StorageBackend:
    def upload_file(self, local_path, remote_path) -> None
    def download_file(self, remote_path, local_path) -> None
    def list_files(self, prefix, recursive) -> List[FileInfo]
    def get_file_content(self, remote_path) -> bytes
    def put_file_content(self, remote_path, content) -> None
    def delete_file(self, remote_path) -> None
```

**S3 bucket layout (production):**
```
{bucket}/
  input/                          ← uploaded loan tapes (files_required/)
    {sales_team_N}/               ← per-team isolation
      files_required/
        MASTER_SHEET.xlsx
        Underwriting_Grids_COMAP.xlsx
        ...
  runs/{run_id}/                  ← pipeline outputs
    exception_reports.xlsx
    eligibility_report.xlsx
    tagging/                      ← tagging script outputs
    cashflow/{job_id}/            ← cashflow outputs
    wire_{counterparty}.pdf       ← TO BUILD: wire instruction PDFs
  archive/{run_id}/               ← archived previous run outputs
```

**Dev local layout mirrors the S3 layout** using filesystem paths. `STORAGE_TYPE=local` in `.env`.

---

## Suggested Build Order

Dependencies flow from data ingest → processing → output. Build in this sequence:

### Phase 1: Foundation (already substantially done)
- PostgreSQL schema and SQLAlchemy models
- FastAPI app with auth (JWT, roles)
- StorageBackend abstraction (S3 + local)
- React SPA shell with auth, routing, layout

**Build first because:** Everything else depends on auth, DB, and file storage.

### Phase 2: Upload + Run (substantially done)
- File upload UI and API (`FileManager`, `/api/files`)
- Pipeline run trigger and status polling (`Dashboard`, `Runs`, `/api/pipeline/run`)
- Main suitability analysis pipeline (normalize → rules → exceptions → LoanFact inserts)
- Exception and rejected loan viewers (`Exceptions`, `RejectedLoans`)

**Build second because:** This is the core of the workflow. Nothing downstream is meaningful without suitability analysis results.

### Phase 3: Cashflow (substantially done)
- Cashflow computation engine (`cashflow/compute/`)
- Cashflow job management API and UI (`CashFlow`, `/api/cashflow`)
- Final funding workbooks (SG, CIBC)

**Build third because:** Cashflow needs the eligible loan set from Stage 2. Can be developed in parallel once Stage 2 loan data is in Postgres.

### Phase 4: Counterparty Tagging (stub exists, real logic needed)
- Real tagging script (currently a stub)
- Tagging results UI (currently no dedicated viewer)

**Build fourth because:** Tagging is logically between suitability analysis and cashflow, but the stub lets later stages proceed in development. Integrate the real script when available.

### Phase 5: Wire Instructions + Email (not yet built)
- PDF generation (reportlab, in-process)
- PDF storage to S3
- Email delivery via AWS SES
- React UI for review-and-send

**Build last because:** Requires correct loan data, counterparty assignments, and cashflow results. Also requires SES configuration and email template design.

### Phase 6: Audit + Polish
- Full audit trail surfacing in UI
- Run archive/history with output file access
- Scheduler improvements (APScheduler already integrated)
- Notification emails on run completion/failure

---

## Decisions and Tradeoffs

### Node.js is not in this stack

The project documentation specifies Node.js, but the actual implementation uses Python FastAPI for everything the API layer does. The correct framing is:

- **FastAPI** = the API/orchestration layer (plays the role described as "Node")
- **Python business logic** = in-process functions and modules (not a separate service)

If Node.js is later required (e.g., for a separate BFF layer), it would sit between React and FastAPI as a thin proxy — but there is no current benefit at this scale that justifies adding it.

### In-process threads vs subprocess for Python logic

The main pipeline uses in-process background threads. This is correct for:
- ~1000 loans, 2x/week — not a throughput problem
- Shared SQLAlchemy connection pool
- Simpler deployment (single Docker image)

Subprocess is used only for legacy external scripts (tagging, final funding) that cannot be refactored into the main codebase. This is the right tradeoff.

### No message queue needed

At 2 runs/week and ~1000 loans, a message queue (Celery, SQS worker, etc.) adds operational complexity with no benefit. The current pattern of HTTP 202 + background thread + DB status polling is correct for this scale. Revisit if:
- Run frequency increases substantially (daily or higher), or
- Run duration exceeds the ECS task timeout

### Single container vs separate services

The current architecture runs FastAPI + static frontend in a single ECS Fargate task. This is correct for:
- Low-traffic internal tool
- Simplified deployment
- No per-service scaling needed

Cashflow computation is the one exception — the code already supports launching it as a separate ECS task (`CASHFLOW_EXECUTION_MODE=ecs_task`) when CPU demands require it.

---

## Sources

Research grounded in direct codebase analysis:
- `backend/api/main.py` — FastAPI app structure, routers, lifespan
- `backend/api/routes.py` — Pipeline run endpoint, threading pattern
- `backend/orchestration/pipeline.py` — PipelineExecutor, stage sequence
- `backend/orchestration/tagging_runner.py` — subprocess pattern for external scripts
- `backend/orchestration/final_funding_runner.py` — subprocess pattern for workbooks
- `backend/cashflow/routes.py` — local subprocess vs ECS task launch
- `backend/db/models.py` — all database tables and relationships
- `backend/storage/__init__.py`, `backend/storage/base.py` — storage abstraction
- `backend/scheduler/job_scheduler.py` — APScheduler integration
- `backend/requirements.txt` — full Python dependency set
- `frontend/src/App.tsx` — all frontend routes
- `frontend/package.json` — frontend dependency set (React 19, Vite, Axios, Tailwind)
- `deploy/terraform/qa/ecs.tf` — ECS Fargate task definition
- `deploy/terraform/qa/s3.tf` — S3 bucket configuration
- `.planning/PROJECT.md` — requirements and constraints
