# Phase 6: Final Funding & Cashflow Integration - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the stub Final Funding SG and CIBC scripts with the real workbook implementations from the legacy loan_engine repo. Ops should be able to run Final Funding SG and CIBC from Program Runs and see job status without relying on browser alerts. Cashflow computation outputs (from the CashFlow page) should be automatically available as inputs to Final Funding runs without manual download/re-upload.

Tagging, wire instruction PDFs, SES email, and counterparty tagging are NOT part of this phase.

</domain>

<decisions>
## Implementation Decisions

### Script replacement
- Real `final_funding_sg.py` and `final_funding_cibc.py` scripts exist in the legacy loan_engine repo (local folder) and already follow the FOLDER env var convention (input from `files_required/`, output to `output/` and `output_share/`)
- Bundle them directly into `backend/scripts/` — replace the stubs, no env var config required for deployment
- No wrapper or adapter needed — scripts are convention-compatible with the existing runner

### Cashflow → Final Funding input bridging
- Cashflow outputs (from the CashFlow page, stored in the `outputs` S3 prefix / local outputs dir) must be automatically available as Final Funding inputs without Ops manually downloading and re-uploading
- Ops triggers cashflow and final funding runs independently — no automatic chaining
- Claude's Discretion: how to bridge (copy/move on demand, runner reads from both areas, or UI provides a "use cashflow output as input" action)

### Run status tracking
- Final Funding SG and CIBC runs should show status in the UI (RUNNING, COMPLETED, FAILED) — not just a completion alert
- Pattern: similar to the CashFlow job queue (cashflow_job table pattern) — add a program_run tracking table or reuse existing run tracking
- Claude's Discretion: whether to add a dedicated `final_funding_job` table or reuse the existing `cashflow_job` table pattern with a different `mode` field

### Output expectations
- Real scripts produce Excel workbooks in `output/` and `output_share/`
- Output browsing via the existing ProgramRuns file manager is sufficient — no dedicated output panel needed for Phase 6
- Runner already copies `output/` → outputs storage area under `final_funding_sg/` or `final_funding_cibc/` prefix

### Claude's Discretion
- Exact DB schema for run tracking (new table vs extending cashflow_job)
- Implementation of cashflow → final funding input bridge mechanism
- UI layout for run status display within Program Runs page

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/orchestration/final_funding_runner.py`: Fully implemented — handles local/S3, temp dirs, script execution, output upload. No changes needed unless adding run tracking hooks.
- `backend/cashflow/routes.py` + `cashflow_job` table: Full job queue pattern (QUEUED/RUNNING/COMPLETED/FAILED, progress percent, log messages, cancel). Template for Final Funding run tracking.
- `frontend/src/pages/ProgramRuns.tsx`: Final Funding SG/CIBC buttons already exist, call `/api/program-run`. Add status display alongside existing buttons.
- Storage backends (`backend/storage/`): `local.py` and `s3.py` — abstraction for reading/writing files across areas (inputs, outputs, output_share).

### Established Patterns
- Job queue: `cashflow_job` table with `mode` discriminator — same pattern should work for final funding runs
- Runner convention: FOLDER env var, files_required/ in, output/ + output_share/ out — real scripts already follow this
- API routes: `/api/program-run` with `phase` discriminator already dispatches to tagging and final funding runners

### Integration Points
- `backend/api/routes.py`: `/api/program-run` endpoint dispatches to `execute_final_funding_sg()` and `execute_final_funding_cibc()` — add run tracking here
- Cashflow outputs area: stored under `outputs/` prefix (S3) or `settings.OUTPUT_DIR` (local) — final funding inputs area is `inputs/files_required/`; bridge must route between them
- `frontend/src/pages/ProgramRuns.tsx`: Status display for Final Funding needs to poll a new or extended API endpoint

</code_context>

<specifics>
## Specific Ideas

- The CashFlow job queue pattern (cashflow_job table, QUEUED→RUNNING→COMPLETED/FAILED states, polling) is the right model for Final Funding run tracking
- The cashflow→final funding input bridge should be as lightweight as possible — a "make available" step rather than a permanent copy if S3 mode can support it

</specifics>

<deferred>
## Deferred Ideas

- Wire instruction PDF generation (WeasyPrint + Jinja2) — v2.0 / BIZ-01
- SES email delivery to counterparties — v2.0 / BIZ-02
- Counterparty tagging stub replacement — separate phase or v2.0
- In-UI PDF preview — v2.0 / BIZ-04

</deferred>

---

*Phase: 06-final-funding-cashflow-integration*
*Context gathered: 2026-03-08*
