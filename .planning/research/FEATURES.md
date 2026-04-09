# Features Research: Loan Purchase Operations Platform

**Research type:** Project Research — Features dimension
**Date:** 2026-03-04
**Question:** What features do internal loan purchase operations platforms need? What's table stakes vs differentiating?

---

## Summary

This platform wraps an existing Python loan processing engine in a controlled, auditable web UI. The Ops team downloads loan tape files from email, uploads them, triggers each processing phase manually, reviews outputs, and receives wire instruction PDFs. The workflow runs approximately twice per week at ~1,000 loans per run, serving two counterparties: prime and SFY.

The codebase already implements the full processing pipeline, file management, and a multi-phase workflow UI. Feature decisions here focus on what must be complete for the workflow to be reliable vs. what would materially improve Ops efficiency beyond the current baseline.

---

## Table Stakes — Must Have or the Workflow Breaks

Features in this category are non-negotiable. If any of them are absent or unreliable, Ops cannot complete the loan purchase workflow.

### File Ingestion

**TS-1: Multi-file upload to managed input area**
Ops downloads two spreadsheet files per run from email and must upload them to the platform. The platform must accept both files, store them in a named input directory (`files_required/`), and make them available to the Python pipeline. Already implemented via the File Manager and S3/local storage abstraction.

**TS-2: Reference file management**
The pipeline depends on stable reference files: `MASTER_SHEET.xlsx`, `MASTER_SHEET - Notes.xlsx`, `Underwriting_Grids_COMAP.xlsx`, and `current_assets.csv`. These must be manageable through the UI — viewable, replaceable, downloadable — without requiring server access. Already implemented.

**TS-3: File discovery by date convention**
Input loan tape files follow a date-based naming convention. The platform must correctly discover the right files for a given run date (pdate, yesterday, last month-end) without requiring the Ops user to manually specify file paths. Already implemented via `file_discovery.py` and the `tday` parameter.

**Dependency:** TS-1 and TS-2 must be complete before TS-3 can function correctly. TS-3 must work correctly before any pipeline phase can run.

---

### Processing Pipeline Visibility

**TS-4: Manual step-by-step trigger control**
Ops must be able to manually trigger each pipeline phase (Pre-Funding, Tagging, Final Funding SG, Final Funding CIBC) from the UI. Steps must not run automatically or chain without user action. This is the core safety mechanism. Already implemented via Program Runs page.

**TS-5: Real-time run status with phase-level progress**
When a pipeline run is in progress, Ops must see the current phase (e.g., "Running CoMAP checks", "Saving to database") updated in near-real-time (polling). When a run fails, the last phase reached must be surfaced so the Ops team can diagnose the problem. Already implemented: `last_phase` field, polling on Dashboard and Program Runs.

**TS-6: Run completion and failure feedback**
A completed run must surface: total loans processed, total balance, exception count, and status (completed / failed / cancelled). A failed run must surface the error message. Currently implemented. Note: error messages are stored in the `errors` JSON array on the run record, which doubles as the log output panel.

**TS-7: Sequential job enforcement**
Only one pipeline run may execute at a time. A second run must be blocked with a clear message if one is already running. Already implemented via the 409 conflict response and the `RUNNING` status check.

**TS-8: Run cancellation**
Ops must be able to cancel a running pipeline run from the UI. The system must gracefully stop execution and set the run to CANCELLED so a new run can be started. Already implemented.

**Dependency:** TS-5 and TS-6 depend on TS-4 (runs must be triggerable before status matters). TS-7 depends on having persistent run state (database).

---

### Suitability and Rules Processing

**TS-9: Purchase price check**
Every loan in the tape must be checked for purchase price validity. Mismatches must be flagged and exported as `purchase_price_mismatch.xlsx`. Already implemented.

**TS-10: Underwriting grid checks (SFY, Prime, Notes)**
Loans must be evaluated against underwriting grids for all three program types. Flagged loans must be exported as `flagged_loans.xlsx` and `notes_flagged_loans.xlsx`. Already implemented.

**TS-11: CoMAP grid validation**
Each loan's program must exist in the applicable CoMAP grid (Prime, SFY, Notes). Loans not in any CoMAP grid must be flagged and exported as `comap_not_passed.xlsx`. Already implemented.

**TS-12: Eligibility checks per counterparty**
Portfolio-level eligibility checks must run against both the prime and SFY counterparty criteria and produce a pass/fail result for each check. Results must be shown on the run detail page. Already implemented.

**TS-13: Loan disposition classification**
Each loan must be classified as `to_purchase`, `projected`, or `rejected`, with a canonical rejection criteria key attached to each rejected loan. This is required for downstream reporting and audit. Already implemented.

**Dependency:** TS-9, TS-10, TS-11 all run against the same `buy_df` and must complete before TS-13. TS-12 runs against the combined `final_df_all`. All depend on TS-3 (file discovery) working correctly.

---

### Counterparty Management

**TS-14: Dual-counterparty tagging (prime / SFY)**
Loans are tagged to one or both counterparties (prime, SFY) based on loan program and eligibility. The tagging step must run as an explicit, Ops-controlled phase after Pre-Funding. Already implemented via the Tagging phase and `tagging_runner.py`.

**TS-15: Per-counterparty output generation**
Final Funding outputs must be generated separately for SG (prime) and CIBC counterparties. These are distinct pipeline phases, each producing separate output files. Already implemented as Final Funding SG and Final Funding CIBC phases.

---

### Output and Document Generation

**TS-16: Exception report exports (Excel)**
The pipeline must produce downloadable Excel files for each exception category (flagged loans, purchase price mismatch, CoMAP not passed, notes flagged loans, special asset prime, special asset SFY). These are the primary deliverables from Pre-Funding. Already implemented as notebook replacement outputs.

**TS-17: Eligibility summary export**
An eligibility checks summary must be exported as both JSON (`eligibility_checks.json`) and Excel (`eligibility_checks_summary.xlsx`) and made available for download from the run detail page. Already implemented.

**TS-18: Output file browsing and download**
All output files produced by any pipeline phase must be browsable and downloadable from the UI, organized by phase and run. Already implemented via the Program Runs output file manager and run archive.

**Dependency:** TS-16 and TS-17 depend on TS-9 through TS-12 completing successfully. TS-18 is a UI wrapper around the storage abstraction (S3 or local).

---

### Wire Instruction and Document Delivery

**TS-19: Wire instruction PDF generation**
Final Funding phases (SG and CIBC) must produce wire instruction PDFs as outputs. These are the end product of the full workflow. Implemented via the bundled `final_funding_sg.py` and `final_funding_cibc.py` scripts, which run as sub-processes.

**TS-20: PDF delivery to counterparties**
Generated PDFs must be emailed to the appropriate counterparty (SG or CIBC). This step is currently outside the dashboard — PDFs are downloaded from the output file manager and emailed manually, which is the established process.

**Dependency:** TS-19 depends on TS-14 and TS-15 completing first. TS-20 is a manual step that depends on TS-19 producing correct files.

---

### Audit Trail

**TS-21: Immutable run history with timestamps**
Every pipeline run must be recorded with: run ID, triggering user, start/end timestamps, phase reached, status, loan counts, balances, and exception counts. Records must persist and be queryable. Already implemented in `pipeline_runs` table.

**TS-22: Per-loan exception records**
Each exception (purchase price mismatch, underwriting flag, CoMAP fail) must be persisted at the loan level with: loan number, exception type, category, severity, message, and rejection criteria key. Already implemented in `loan_exceptions` table.

**TS-23: Per-loan fact records with disposition**
Each processed loan must be persisted with its key attributes and final disposition (`to_purchase`, `projected`, `rejected`) plus the canonical rejection criteria if rejected. Already implemented in `loan_facts` table.

**TS-24: Input and output file archiving per run**
Input files and output reports must be archived under a per-run key (`archive/{run_id}/input`, `archive/{run_id}/output`) so any run can be reconstructed. Already implemented in `archive_run.py`.

**TS-25: Exception browsing and export**
Exceptions must be browsable in the UI with filters by run, type, severity, and rejection criteria. They must be exportable to CSV or Excel. Already implemented.

---

### Authentication and Access Control

**TS-26: Username/password authentication with JWT**
All UI access must require authentication. Sessions must be managed via JWT tokens. Already implemented with bcrypt hashing, role-based access, and session expiry handling.

**TS-27: Role-based access (Admin, Analyst, Sales Team)**
Admins see and can manage all runs. Analysts see all runs. Sales team users see only their team's runs. Admin-only routes (cancel-all, clear-history, holiday management) must be protected. Already implemented.

---

### Business Date Management

**TS-28: Holiday calendar for posting date calculation**
The pipeline posting date (pdate) is the next Tuesday that is a US business day. If that Tuesday is a US holiday, the system must advance to the following business day. The holiday calendar must be admin-manageable and cover US, UK, India, and Singapore calendars. Already implemented.

---

## Differentiators — Improves Ops Efficiency, Not Workflow-Breaking if Absent

Features in this category reduce manual effort, catch errors earlier, or improve the quality of the run experience. They are high value but the workflow can complete without them.

### Ingestion and Pre-Run

**D-1: Pre-flight file validation before run starts**
Before triggering a run, surface a checklist of which required files are present in `files_required/` and which are missing. Currently, a missing file causes the pipeline to fail mid-run with a Python error. A pre-flight check surfaces this immediately, saving time and preventing wasted runs. Not currently implemented.

*Dependency: Requires knowing the expected file manifest for the current run date, which depends on the `file_discovery` logic.*

**D-2: File format and column validation on upload**
When a loan tape is uploaded, immediately validate that expected columns are present (e.g., `SELLER Loan #`, `Orig. Balance`, `Platform`). Surface column mismatches as warnings before the run starts. Not currently implemented.

**D-3: Duplicate file detection**
Warn Ops if a file with the same name already exists in the input area and would be overwritten. Prevents accidental replacement of reference files with tape files. Not currently implemented.

---

### Processing Pipeline Visibility

**D-4: Estimated run duration indicator**
Based on historical run durations stored in the database (elapsed time between `started_at` and `completed_at`), show an estimated time remaining during an active run. Reduces anxiety during the 5-15 minute processing window. Not currently implemented.

**D-5: Per-phase timing breakdown**
Record and display how long each pipeline phase took (reference data load, normalize, underwriting, CoMAP, eligibility, export). Identifies which phase is slow when runs take longer than expected. Not currently implemented.

**D-6: Structured log panel during run**
The current `errors` JSON array doubles as the log output, which is surfaced as a flat list. A structured, scrollable, real-time log panel on the run detail page — showing messages like "Loaded 1,043 loans", "CoMAP checks: 3 loans not in grid" — would give Ops meaningful progress without navigating to CloudWatch. Partially implemented (log messages appended to `run.errors`), but not displayed in real-time on the run detail page.

---

### Exception and Rejection Review

**D-7: Run-over-run exception delta**
When viewing a completed run, show how the exception count and composition changed relative to the previous run (e.g., "+12 CoMAP failures, -3 purchase price mismatches"). Helps Ops quickly assess whether the new tape introduced new problems. Not currently implemented.

**D-8: Exception drill-down with loan attributes**
On the exceptions page, allow Ops to expand a row and see the key loan attributes (FICO, DTI, balance, program, state) alongside the rejection reason — without needing to cross-reference the Excel download. Currently, `loan_data` is stored as JSON on each exception record but is not surfaced in the UI. Partially implemented (data is stored); UI drill-down not built.

**D-9: Exception acknowledge and note**
Allow Ops to mark an exception as "reviewed" with a free-text note (e.g., "Discussed with counterparty — OK to proceed"). Provides a lightweight exception management layer without requiring a full exception workflow. Not currently implemented.

---

### Counterparty and Run Management

**D-10: Run comparison view (side-by-side runs)**
Display two runs side by side: total loans, balance, exception counts, eligibility check results. Useful when Ops wants to confirm that re-running with corrected files produced the expected improvement. Not currently implemented.

**D-11: IRR target override per run**
The IRR target defaults to 8.05% but is parameterizable. Surfacing this as an explicit, labeled field in the run start form (rather than accepting the default silently) ensures Ops is aware when a non-default target is used. Currently implemented in the API as `irr_target` but the Dashboard UI uses the default without displaying it prominently.

**D-12: Run notes / memo field**
Allow Ops to attach a free-text memo to a completed run (e.g., "93rd buy, corrected SFY file"). Makes the run history table useful as a lightweight log of what happened on each run day. Not currently implemented.

---

### Cashflow Calculation

**D-13: Cashflow job status polling with progress bar**
The cashflow computation (current assets, SG, CIBC modes) can be long-running. The current UI polls job status every 5 seconds and shows a progress percentage. Surfacing a more meaningful progress message (e.g., "Processing loan 450 of 1,043") would improve the experience. Partially implemented; `progress_message` field exists but content depends on the compute layer populating it.

**D-14: Cashflow parameter validation before job submission**
Before submitting a cashflow job, validate that the referenced input files (prime workbook, SFY workbook, master sheet) exist in the inputs area. Currently, a missing file causes the job to fail after it starts. Not currently implemented.

**D-15: Cashflow output summary in UI**
After a cashflow job completes, show a summary of key computed values (e.g., aggregate IRR, total balance, number of loans modeled) in the UI before the user downloads the full output file. Currently, output is only available as file download. Not currently implemented.

---

### Document Generation and Delivery

**D-16: In-UI PDF preview of wire instructions**
Allow Ops to preview the generated wire instruction PDF in the browser before downloading and emailing it. Catches formatting issues or wrong counterparty data before the document is sent. Not currently implemented.

**D-17: Email delivery tracking**
Record when a wire instruction PDF was downloaded and by whom, providing a lightweight record that the document was retrieved for sending. Not currently implemented (download events are not logged beyond the HTTP response).

**D-18: Templated wire instruction generation**
Allow the wire instruction template (counterparty name, bank details, amounts) to be managed via an admin UI rather than hardcoded in the Python script. Makes it possible to update counterparty banking details without a code deployment. Not currently implemented.

---

### Reporting and Analytics

**D-19: Run history analytics dashboard**
Aggregate metrics across all completed runs: loans processed per week, exception rate trend, average processing time. Useful for reporting to management and identifying patterns (e.g., consistent CoMAP failures on Tuesdays). Not currently implemented.

**D-20: Rejected loan trend by criteria**
Show a chart or table of the most common rejection criteria over the last N runs, grouped by exception type. Helps Ops identify systemic tape quality issues with the seller. Not currently implemented.

**D-21: Balance-weighted exception summary**
In addition to loan count, show the aggregate original balance of rejected loans per exception type. A high-balance rejection is more operationally significant than many small-balance rejections. Not currently implemented.

---

## Anti-Features — Deliberately Out of Scope for v1

These features are technically possible but should not be built in v1. Building them would add scope risk without proportional value for an internal tool at this scale and frequency.

**AF-1: Automated email ingestion**
Automatically watching an email inbox, parsing loan tape attachments, and triggering runs without Ops action. The manual download-and-upload step is a deliberate control point. Automating it removes Ops judgment about which tape to process and when. Explicitly excluded per project scope.

**AF-2: Direct banking API integration for wire execution**
Connecting to banking APIs (e.g., SWIFT, ACH) to execute wires programmatically. The current PDF + email process is the established counterparty workflow. An API integration would require counterparty buy-in, compliance review, and security controls well beyond v1 scope.

**AF-3: Counterparty portal / external user access**
A separate login for counterparty (SG, CIBC) users to view their eligible loans, download documents, or receive notifications. This is an internal ops tool only. External access would require a fundamentally different security posture, data filtering, and UX.

**AF-4: Mobile-optimized UI**
The dashboard is used by Ops at desktops during normal business hours. Responsive mobile design adds layout complexity for no practical gain.

**AF-5: Automated run scheduling**
Scheduling runs to trigger automatically at a set time on run days. The manual trigger is intentional — Ops must confirm files are ready and review any late-arriving corrections before processing. Automation would require pre-flight checks (AF-1 territory) and could process stale or incorrect files.

**AF-6: Machine learning-based suitability scoring**
Replacing or augmenting the rule-based suitability engine with ML models. The rules-based engine is the business logic that has been validated against counterparty agreements. Changing it requires counterparty negotiation, not an engineering decision.

**AF-7: Bulk exception override / manual approval workflow**
A formal workflow where exceptions can be escalated, assigned, approved, or overridden by multiple parties with sign-off tracking. For a two-person ops team running twice per week, a formal exception management workflow adds overhead without commensurate value. D-9 (acknowledge + note) is sufficient for v1.

**AF-8: Multi-currency support**
All loans are denominated in USD. Multi-currency adds data model complexity across the cashflow, eligibility, and wire instruction layers for a non-existent use case.

**AF-9: Real-time loan tape streaming**
Processing loans as they stream in rather than as a batch file upload. The workflow is inherently batch — a loan tape arrives once per run as a complete file. Streaming is architecturally inappropriate for this use case.

---

## Feature Dependencies Summary

```
File Ingestion (TS-1, TS-2)
    └── File Discovery (TS-3)
            └── Pipeline Execution (TS-4, TS-5, TS-6, TS-7, TS-8)
                    ├── Rules Processing (TS-9, TS-10, TS-11)
                    │       └── Loan Disposition (TS-13)
                    ├── Eligibility Checks (TS-12)
                    └── Output Generation (TS-16, TS-17)
                            └── Output File Access (TS-18)

Counterparty Tagging (TS-14)
    └── Final Funding per Counterparty (TS-15)
            └── Wire Instruction PDFs (TS-19)
                    └── PDF Delivery [manual step] (TS-20)

Run Execution (any run)
    └── Audit Trail (TS-21, TS-22, TS-23, TS-24)

Authentication (TS-26, TS-27) — gates all of the above

Business Dates (TS-28) — gates run start (pdate calculation)
```

**Differentiator dependencies worth noting:**
- D-1 (pre-flight check) depends on TS-3 logic being extractable as a standalone validation step
- D-4 (estimated duration) depends on having a sufficient history of completed runs with timestamps
- D-7 (exception delta) depends on having at least two completed runs to compare
- D-13 (cashflow progress) depends on the cashflow compute layer emitting progress signals

---

## Implementation Priority

Given the project is greenfield wrapping an existing Python engine, the sequencing that minimizes risk is:

1. **TS-26, TS-27** (auth) — nothing else is accessible without this
2. **TS-1, TS-2, TS-3** (file ingestion and discovery) — pipeline cannot run without inputs
3. **TS-4 through TS-8** (pipeline control and visibility) — core workflow loop
4. **TS-9 through TS-13** (rules processing) — suitability engine integration
5. **TS-14, TS-15** (counterparty tagging and final funding) — second-phase workflow
6. **TS-16 through TS-18** (output access) — deliverables
7. **TS-19, TS-20** (wire instructions) — end product
8. **TS-21 through TS-25** (audit trail) — compliance and traceability
9. **TS-28** (holiday calendar) — date calculation correctness
10. **D-1, D-2** (pre-flight validation) — highest-value differentiators; prevent wasted runs
11. **D-6, D-8** (log panel, exception drill-down) — operational visibility improvements

---

*Research completed: 2026-03-04*
*Based on: codebase analysis of intrepid-poc (backend pipeline, API routes, frontend pages, data models), PROJECT.md context, and loan purchase operations workflow requirements*
