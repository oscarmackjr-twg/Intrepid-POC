# PITFALLS — Loan Purchase Operations Platform

**Project:** Intrepid Loan Purchase Platform
**Research type:** Project Pitfalls — Financial Operations Workflow
**Date:** 2026-03-04
**Scope:** Greenfield internal ops dashboard; spreadsheet upload → Python analysis → counterparty tagging → cashflow calculation → wire instruction PDFs → email delivery

---

## How to Use This Document

Each pitfall entry follows this structure:

- **What goes wrong** — the failure mode
- **Warning signs** — how to detect it early, before it costs you
- **Prevention strategy** — concrete steps to avoid it
- **Phase** — when to address it (Foundation / Core Build / Integration / Pre-Launch / Operations)

Pitfalls are grouped by domain. Read all of them before planning; the worst ones compound each other.

---

## 1. Financial Data Accuracy

### 1.1 Floating-Point Arithmetic in Cashflow Calculations

**What goes wrong:** Python's native `float` type uses IEEE 754 binary floating-point. Addition and multiplication of dollar amounts accumulate rounding error. A run of 1,000 loans compounding tiny errors can produce wire amounts that are off by cents — or, if intermediate results are rounded at the wrong stage, by dollars. Counterparties will notice. Auditors will notice. The ops team will not notice until a discrepancy surfaces downstream.

**Warning signs:**
- Cashflow totals that differ by $0.01–$0.05 from manual spreadsheet recalculations
- Test cases that pass at the unit level but fail at the aggregate level
- The Python scripts using `float` types for any monetary value
- `round()` calls scattered ad hoc through calculation code rather than at defined output boundaries

**Prevention strategy:**
- Replace every monetary value in Python with `decimal.Decimal` using `ROUND_HALF_UP` or `ROUND_HALF_EVEN` as appropriate for your business rules. Do this before wrapping existing scripts, not after.
- Define a single canonical rounding function that is called once, at output time, not during intermediate calculations.
- Write regression tests with known loan tapes and pre-calculated expected outputs. Treat any cent-level discrepancy as a blocking bug.
- Store monetary values in PostgreSQL as `NUMERIC(18, 6)` — never `FLOAT` or `DOUBLE PRECISION`. Use six decimal places internally; round to two for display and PDF output.
- Document the rounding rules (e.g., "round to nearest cent at final cashflow aggregation, not at per-loan level") so they survive developer turnover.

**Phase:** Foundation — fix before any cashflow logic is wrapped into the application.

---

### 1.2 Silent Data Truncation from Spreadsheet Parsing

**What goes wrong:** Excel/CSV files are not clean. Loan IDs get coerced to scientific notation (`1.23E+12`), leading zeros are stripped from zip codes and loan numbers, numeric fields contain embedded currency symbols (`$1,234.56`), date fields are stored as Excel serial numbers, and cells that look empty contain spaces or non-breaking whitespace. The parser accepts the file without error, but the data is wrong. Downstream calculations silently produce wrong answers.

**Warning signs:**
- Loan counts from parsed data don't match the row count in the original spreadsheet
- Loan IDs that should be 10-digit numbers appearing as 10-character floats or truncated strings
- Interest rates parsed as `0.065` in some rows and `6.5` in others (percent vs. decimal inconsistency)
- Date parsing succeeding on some files and silently producing NaT or epoch dates on others
- Fields with trailing whitespace that break exact-match comparisons to suitability criteria

**Prevention strategy:**
- Write a strict validation layer that runs immediately after parse and before any processing. It should check: expected column presence, type conformance per column, value range sanity (e.g., interest rate between 0.001 and 0.30), no-null constraints on required fields, and row count against a declared expected count.
- Reject the entire file with a human-readable error report if any validation rule fails. Do not partially process.
- Read loan IDs as strings, never as integers or floats. Apply this rule in the schema definition, not as a post-hoc conversion.
- Parse dates with an explicit format string. Reject ambiguous formats (e.g., `01/02/03`) rather than guessing.
- Log the raw parsed value alongside the interpreted value for every field in the first N rows of each run, so discrepancies are detectable without re-running.
- Test with real historical spreadsheets, including malformed ones. Edge cases in financial data are not edge cases — they are regular occurrences.

**Phase:** Foundation / Core Build — validation schema must be defined before processing logic is written.

---

### 1.3 Counterparty Tagging Logic Producing Wrong Assignments

**What goes wrong:** The tagging rules (which loans go to "prime," which to "SFY," which to both) are encoded as business logic in Python. When requirements are ambiguous or change, the code drifts from actual business intent without anyone noticing. A loan tagged to the wrong counterparty means a wire instruction sent to the wrong party, which is a serious operational error.

**Warning signs:**
- Tagging rules described verbally in tickets with no formal spec document
- Tests that verify "it runs without error" rather than "it produces the correct assignment for these specific loan attributes"
- No reconciliation step where the ops team reviews assignments before cashflows are calculated
- Rule changes deployed without a corresponding test that would have failed before the change

**Prevention strategy:**
- Produce a written business rule specification for tagging logic, signed off by the business owner, before implementation. Store it in the repo.
- Implement tagging rules as data-driven configuration (e.g., a rules table in PostgreSQL or a YAML config file) rather than hardcoded conditionals where possible. This makes changes auditable via version control.
- Build a tagging review step into the UI workflow — the ops team must explicitly confirm counterparty assignments before cashflow calculation proceeds. This is not a UX nicety; it is an operational control.
- Write property-based tests that verify tagging rules against a representative synthetic loan tape. Include boundary cases (loans that exactly meet or miss eligibility thresholds).

**Phase:** Core Build — the review step must be in the UI design from day one, not added later.

---

## 2. Processing Run Integrity

### 2.1 Non-Idempotent Processing Runs

**What goes wrong:** A processing run is triggered, fails partway through (Python subprocess crash, database write error, network timeout), and is retried. The retry re-processes loans that were already processed, doubles cashflow entries, or creates duplicate wire instructions. The ops team doesn't notice because the UI shows "completed." Two PDFs go out for the same loans.

**Warning signs:**
- No unique run identifier tracked in the database
- Processing steps that `INSERT` rather than `UPSERT`
- No status field distinguishing "in progress," "completed," and "failed" for each processing step
- Retry logic that restarts from step 1 instead of from the failed step
- No test for "what happens if I click Run twice quickly"

**Prevention strategy:**
- Assign a globally unique `run_id` (UUID) to every processing run at the moment it is created. All database writes for that run are keyed to the `run_id`.
- Make every processing step idempotent: running it twice with the same `run_id` must produce the same state, not doubled entries. Use `INSERT ... ON CONFLICT DO NOTHING` or `UPSERT` patterns throughout.
- Store a state machine for each run: `created → uploaded → validated → analyzed → tagged → cashflows_calculated → pdfs_generated → emails_sent`. Each transition is recorded with a timestamp and the user who triggered it.
- The UI should prevent re-triggering a step that has already completed for a given run. "Re-run from this step" should be an explicit action with a confirmation dialog, not the default behavior of a page refresh.
- Test partial failure scenarios: what happens if the Python process is killed mid-run? The database should reflect "in progress," not "completed," and the next run should be able to start clean.

**Phase:** Foundation — the state machine schema must exist before any processing code is written.

---

### 2.2 No Audit Trail for Financial Operations

**What goes wrong:** A wire goes out, a counterparty disputes an amount, and the ops team cannot reconstruct exactly which loans were in that run, which rules were applied, which version of the Python logic was active, and who triggered which steps. Regulators or auditors ask for records and the team has to piece together the answer from log files and email threads.

**Warning signs:**
- Processing steps that overwrite rather than append database records
- No record of who triggered each step (authentication present but not logged)
- Python script version not recorded alongside run results
- PDF not stored after sending — only the email delivery record exists
- No way to reproduce a historical run against the same input data

**Prevention strategy:**
- Treat the run database as an append-only ledger for financial data. Loan analysis results, tagging decisions, and cashflow calculations are never updated in place — they are versioned by `run_id`.
- Store every uploaded spreadsheet as a binary blob (S3) keyed to the `run_id`. The original input must be reproducible years later.
- Record the authenticated user ID and timestamp for every workflow step transition (upload, validate, analyze, approve tagging, calculate, generate PDF, send email).
- Store generated PDFs in S3 with a stable, permanent URL keyed to `run_id` and counterparty. Never regenerate a sent PDF — it is a historical record.
- Record the git commit SHA of the Python processing code alongside every run result. This enables exact reproduction of any historical run.
- Write an audit log table: `(run_id, step, user_id, timestamp, outcome, metadata_json)`. This is separate from application logs, which are ephemeral.

**Phase:** Foundation — audit schema must be designed before any processing steps are built.

---

### 2.3 Duplicate Wire Instructions from Email Retries

**What goes wrong:** The email sending step fails (SMTP timeout, SES throttle). The ops team retries. Two emails go to the counterparty with the same wire instructions, or worse, two emails with different amounts if any data changed between attempts. The counterparty executes the wire twice.

**Warning signs:**
- Email sending step has no idempotency check
- No record of which emails have already been successfully delivered for a given run
- Retry is handled by the UI "resend" button with no guard against prior successful sends
- No acknowledgment from the counterparty required before the run is marked complete

**Prevention strategy:**
- Track email delivery state per `(run_id, counterparty)` in the database: `pending → sent → delivery_confirmed → failed`. Only allow sending if the state is `pending` or `failed`.
- Use AWS SES message IDs to confirm delivery, and store them against the run record. A "sent" email without a delivery confirmation should trigger an alert, not a silent pass.
- The "resend" action in the UI must require explicit confirmation ("A PDF has already been sent for this run to [counterparty]. Send again?") and must log the reason for the resend.
- Consider including a unique run identifier in the email subject line and PDF filename so the counterparty can detect and flag duplicates on their end.

**Phase:** Integration — when the email sending step is built, not retrofitted later.

---

## 3. PDF Generation

### 3.1 PDF Content Errors That Are Not Caught Until After Sending

**What goes wrong:** The wire instruction PDF is generated with a formatting defect: a dollar amount that wraps to a second line and loses its context, a table that overflows and truncates values, a blank field where a routing number should appear, or a date formatted in a locale-ambiguous way (`03/04/26`). The PDF is sent. The counterparty misreads the wire amount or the account number.

**Warning signs:**
- PDF generation tested only with short, clean data — not with maximum-length loan tapes
- No visual review step before sending — PDFs are auto-attached to emails
- Template uses dynamic width containers that can reflow under long values
- No automated assertion on PDF content after generation (just "file was created")

**Prevention strategy:**
- Generate a PDF preview step in the UI workflow. The ops team must open and visually confirm the PDF before the "Send" button is available. This is a process control, not optional UX.
- Parse the generated PDF immediately after creation and assert that key fields (counterparty name, total wire amount, date, account number, routing number) are present and non-empty. Treat a failed assertion as a failed run.
- Test PDF generation with edge cases: maximum loan counts, long counterparty names, amounts in the billions, dates at year boundaries.
- Use explicit fixed-width layouts for financial tables. Avoid CSS flexbox or auto-sizing containers in PDF templates. Wire instruction PDFs must look identical regardless of data volume.
- Version the PDF template. If the template changes, existing sent PDFs must not be regenerated with the new template — they are historical records.

**Phase:** Core Build — the review step and content assertion must be designed before the PDF generation step is built.

---

### 3.2 PDF Generation Failures Caused by Dependency or Environment Drift

**What goes wrong:** PDF generation works in development and breaks in production because a system font is missing, a headless browser (Puppeteer/wkhtmltopdf) is not installed, a library version differs, or the Lambda/container environment lacks a required native dependency. The run fails silently or with a cryptic error after cashflows have already been calculated.

**Warning signs:**
- PDF generation uses a headless browser that is not explicitly pinned in the container image
- No PDF generation test in the CI/CD pipeline that runs against the production environment image
- PDF generation works via `localhost` in dev but the production environment is a Lambda with a 512MB ephemeral disk
- Error messages from PDF generation are swallowed and logged as "PDF generation failed" with no detail

**Prevention strategy:**
- Run PDF generation in a Docker container with explicitly pinned dependencies. The same image runs in dev, CI, and production.
- Add a smoke test to the deployment pipeline: generate a single-loan PDF and assert the output file is non-zero bytes and parses correctly.
- If using a headless browser (Puppeteer, wkhtmltopdf, Playwright), use a Lambda layer or container layer that is explicitly versioned and tested. Do not rely on system-installed binaries.
- Capture full stderr/stdout from the PDF generation process and store it against the run record for diagnostics.

**Phase:** Foundation / Infrastructure — containerization and environment parity must be established before PDF generation is implemented.

---

## 4. Spreadsheet Ingestion

### 4.1 Schema Drift Between Counterparty File Formats

**What goes wrong:** The two input spreadsheets (one per counterparty source) have column names or ordering that changes between weeks when the upstream sender modifies their export. The parser silently reads columns by position and assigns wrong data to wrong fields — or fails with a KeyError that the ops team cannot diagnose quickly.

**Warning signs:**
- Columns read by position index rather than by header name
- No header validation at parse time
- Ops team reports "the numbers look wrong this week" after a file format change
- No version tracking of input file schemas

**Prevention strategy:**
- Parse by header name, never by column position. On every file load, validate that all expected column headers are present (exact match or normalized match after stripping whitespace and lowercasing).
- Surface a clear, human-readable error for schema mismatches: "Expected column 'LoanOriginalBalance' but found 'OriginalBalance'. Please verify the file format."
- Maintain a schema definition file in the repo for each input format. When a new column is added or renamed, the schema file is updated and the change is reviewed.
- Consider adding a file format version identifier (either by filename convention or a header cell) so the parser can select the correct schema without guessing.

**Phase:** Core Build — schema validation is part of the file upload step, not a post-hoc addition.

---

### 4.2 Large File Uploads Timing Out or Corrupting

**What goes wrong:** A 500-row spreadsheet is small in row count but can be large in file size if it contains many columns or embedded formatting. Multipart upload through the Node API to S3 times out, the file is partially written, and the Python processor reads a truncated file without detecting the corruption.

**Warning signs:**
- Upload endpoint has a body size limit set at Express defaults (100kb) that hasn't been raised
- S3 upload uses a single PUT rather than multipart upload for files over 5MB
- No file checksum (MD5/SHA256) verified after upload completes
- Python reads the uploaded file without checking for parse errors at the end of file

**Prevention strategy:**
- Upload files directly to S3 via pre-signed URLs from the browser, bypassing the Node API entirely for the file payload. The Node API handles metadata and triggers processing after the upload completes.
- Compute a SHA256 checksum of the file in the browser before upload and verify it on the server after S3 confirms the upload. Reject any run where the checksums don't match.
- Store the file size and checksum alongside the S3 key in the database. Log them with every run for forensic use.
- Test with files at realistic sizes, not toy examples. Use production-scale test data.

**Phase:** Core Build — the upload architecture decision must be made before the upload UI is built.

---

## 5. Operational and Process Risks

### 5.1 No Separation Between Test Runs and Production Runs

**What goes wrong:** The ops team runs a test with real loan data against a staging environment and accidentally triggers a wire instruction email to a real counterparty. Or a developer tests the email step in production and sends a garbled PDF. Because the workflow is manual and step-by-step, the "Send Email" button is always one click away from production counterparties.

**Warning signs:**
- The same counterparty email addresses are configured in all environments
- No visual distinction between staging and production in the UI
- Test runs stored in the same database tables as production runs without a flag distinguishing them
- Developers have access to the production "Send Email" action

**Prevention strategy:**
- In all non-production environments, override counterparty email addresses to an internal ops mailbox. This override must be enforced by the application, not by relying on developers to configure it correctly.
- Add an environment banner to the UI ("STAGING" / "PRODUCTION") that is impossible to miss. In staging, make the banner red and prominent.
- Add a `is_test_run` flag to the runs table. Test runs never trigger real email sends — they produce a preview only.
- Require a two-step confirmation for the email send action in production: "You are about to send wire instructions to [counterparty name] for $[total amount]. This will send a real email. Confirm?"

**Phase:** Foundation / Infrastructure — environment separation must be established before any end-to-end testing.

---

### 5.2 Processing State Lost on Browser Refresh or Session Expiry

**What goes wrong:** The ops user is midway through a processing run. They refresh the browser, their session expires, or they switch tabs. The UI loses track of where the run is, and the user cannot determine whether the Python processing completed, failed, or is still running. They trigger a second run.

**Warning signs:**
- Processing state stored only in React component state or localStorage, not in the database
- Long-running Python jobs with no polling or websocket status updates
- No way to view "runs in progress" from the main dashboard
- Session timeout shorter than the longest expected processing run

**Prevention strategy:**
- All processing state lives in the database (the run state machine described in section 2.1). The UI reads state from the API on load — refreshing the page restores the current state.
- Use server-sent events (SSE) or WebSocket for real-time status updates during long Python runs. If neither is available, a simple polling endpoint with a 2-second interval is acceptable for this volume.
- The main dashboard must show all active, recent, and historical runs with their current state. The user should never need to "know" what step they were on — the system knows.
- Extend session TTL to cover the longest expected end-to-end run time, or implement a "run lock" that persists even after session expiry, releasable by any authenticated ops user.

**Phase:** Core Build — the runs dashboard and status API must be built before any processing steps.

---

### 5.3 Failure to Validate Business Rules at the Application Layer

**What goes wrong:** The Python suitability analysis scripts contain the business rules. When those scripts are wrapped by the Node API, the assumption is "Python handles all validation." But the application layer also receives direct API calls (from tests, from future integrations) that bypass the Python checks. Business rules are enforced only on the happy path.

**Warning signs:**
- No API-level input validation — validation is entirely delegated to Python subprocess
- Tests call the API directly without going through the full Python pipeline
- The Node API accepts a file and triggers Python without any pre-check
- A future developer adds a "bulk import" endpoint that skips the Python step

**Prevention strategy:**
- Define a validation contract at the API layer: required fields, type constraints, size limits. This is not a replacement for Python-level business rules; it is a first line of defence.
- Any endpoint that accepts loan data must validate structure before dispatching to Python. Malformed input must be rejected with a clear error at the API layer, never passed to Python and allowed to fail silently.
- Document explicitly which validations live in the API layer vs. the Python layer vs. the database constraints. Overlap is intentional and acceptable for financial data.

**Phase:** Core Build — API validation schema defined alongside the endpoint design.

---

### 5.4 Lack of Reconciliation Reporting

**What goes wrong:** At the end of a run, the ops team has sent two PDFs but has no summary view showing: how many loans were processed, how many were eligible, how many went to each counterparty, what the total wire amounts were, and how those compare to the raw input. Without this, data errors go undetected until the counterparty flags them.

**Warning signs:**
- The workflow ends at "email sent" with no summary screen
- Ops team performs manual reconciliation in a separate Excel sheet after each run
- No database query that can reproduce the full summary for a historical run
- Total loan counts and dollar amounts not surfaced anywhere in the UI

**Prevention strategy:**
- Build a run summary screen as part of the workflow completion step (not a separate report). It must show: input loan count, eligible loan count per counterparty, total cashflow per counterparty, PDF generation status, email delivery status.
- Store these summary statistics in the database at run completion. They must be queryable for any historical run.
- The ops team should sign off on the reconciliation summary before the run is marked "complete." This is the final human control before the run is closed.

**Phase:** Core Build — summary data model designed alongside the run state machine.

---

## 6. Infrastructure and Reliability

### 6.1 Long-Running Python Jobs Blocking the API

**What goes wrong:** Processing 1,000 loans through the Python suitability engine takes minutes. If this runs synchronously in the Node API request-response cycle, the HTTP connection times out, the client thinks the job failed, and the Python process continues running in the background with no way to track or cancel it.

**Warning signs:**
- Python called via `child_process.execSync` or equivalent blocking call
- No job queue or background worker — processing happens inline in the API handler
- API gateway or load balancer timeout shorter than the processing duration
- No mechanism to poll for job completion after the initial request

**Prevention strategy:**
- All Python processing jobs are dispatched asynchronously. The API responds immediately with a `run_id` and `status: "processing"`. The client polls for status updates.
- Use a job queue (AWS SQS, BullMQ, or similar) to dispatch Python jobs. This decouples the API from processing time and enables retries on failure.
- Set the Python job timeout explicitly and handle it as a failure state in the run state machine, not as an uncaught exception.
- The Node API should never wait more than 5 seconds for a Python response. Anything longer is a background job.

**Phase:** Foundation — the async job architecture must be decided before any processing integration.

---

### 6.2 No Alerting on Processing Failures in Production

**What goes wrong:** A processing run fails in production at 4pm on a Friday. The Python job throws an exception, the run state is set to "failed," and nothing else happens. The ops team doesn't check the dashboard until Monday morning. The counterparty is waiting on a wire that never arrived.

**Warning signs:**
- Failed runs produce no notification outside the UI
- No CloudWatch alarm on failed job count
- Ops team has no on-call or escalation path for processing failures
- "Failed" run state is visible only if you navigate to the specific run

**Prevention strategy:**
- Send an internal alert (email or Slack/Teams webhook) whenever a run transitions to "failed" state. Include the run ID, the step that failed, and a link to the run detail page.
- Set up a CloudWatch alarm on the SQS dead-letter queue depth — failed jobs that exhaust retries land there.
- The runs dashboard must prominently surface any run in "failed" state, not bury it in a list.
- Define an SLA for run completion and add a CloudWatch alarm for runs that have been in "processing" state longer than the SLA (e.g., 30 minutes).

**Phase:** Integration / Pre-Launch — alerting configured before go-live, not after the first production failure.

---

## Priority Summary

| # | Pitfall | Severity | Phase |
|---|---------|----------|-------|
| 1.1 | Floating-point in cashflow calculations | Critical | Foundation |
| 2.1 | Non-idempotent processing runs | Critical | Foundation |
| 2.2 | No audit trail | Critical | Foundation |
| 2.3 | Duplicate wire instructions from email retry | Critical | Integration |
| 1.2 | Silent data truncation from spreadsheet parsing | High | Foundation / Core Build |
| 3.1 | PDF content errors not caught before sending | High | Core Build |
| 5.1 | No separation between test and production runs | High | Foundation |
| 1.3 | Counterparty tagging logic errors | High | Core Build |
| 6.1 | Long-running Python jobs blocking the API | High | Foundation |
| 4.1 | Spreadsheet schema drift | Medium | Core Build |
| 5.4 | No reconciliation reporting | Medium | Core Build |
| 5.2 | Processing state lost on browser refresh | Medium | Core Build |
| 3.2 | PDF generation environment failures | Medium | Foundation |
| 4.2 | Large file upload corruption | Medium | Core Build |
| 5.3 | Business rules not validated at API layer | Medium | Core Build |
| 6.2 | No alerting on production failures | Medium | Pre-Launch |

---

*Generated by gsd-project-researcher — 2026-03-04*
*Covers: financial data accuracy, floating point, idempotency, audit trails, PDF generation, email delivery, spreadsheet parsing, operational controls*
