# Project Research Summary

**Project:** Intrepid Loan Purchase Operations Platform
**Domain:** Internal Financial Operations Dashboard — Loan Purchase Workflow
**Researched:** 2026-03-04
**Confidence:** HIGH

## Executive Summary

This project is a web-based operations dashboard that wraps an existing Python loan processing engine. The core workflow is: Ops team uploads loan tape spreadsheets, triggers a multi-phase Python pipeline that evaluates loan suitability against counterparty rules, reviews exceptions and counterparty tagging, calculates cashflows, generates wire instruction PDFs, and delivers them to counterparties via email. The system runs approximately twice per week at roughly 1,000 loans per run, serving two counterparties (prime/SG and SFY/CIBC). The platform is substantially built — most table-stakes features are already implemented. What remains is completing Stage 5 (wire instruction PDF generation, in-UI preview, and email delivery), polish on several high-value differentiators, and hardening the operational controls that a financial workflow demands.

The critical architectural correction from codebase analysis: the actual stack is React 19 + Python FastAPI, not the React + Node.js + Python arrangement described in greenfield planning. Python FastAPI is both the API/orchestration layer and the business logic host. There is no Node.js service. The ORM is SQLAlchemy 2.0 + Alembic migrations (not Drizzle). Pandas DataFrames are the in-memory data structure for loan processing (not openpyxl-only parsing). All new work should build on this established architecture — introducing a Node.js layer now would be a costly and unnecessary disruption.

The dominant risks for the remaining build are concentrated in three areas: (1) financial data accuracy — floating-point must be replaced with Decimal throughout cashflow calculations before Stage 4 outputs are trusted; (2) operational safety controls — the email send step needs idempotency, production/staging separation, and a mandatory human review gate before any wire instruction leaves the system; and (3) audit completeness — the audit schema exists in the database but several key events (who triggered each step, sent PDF archived permanently, git SHA recorded per run) are not yet captured. These must be addressed during the remaining phases, not deferred to post-launch.

---

## Key Findings

### Recommended Stack

The existing stack is well-suited to this use case and should not be changed. Python FastAPI is both the API layer and the pipeline orchestration layer. React 19 (Vite, TypeScript, Tailwind) is the frontend. PostgreSQL via SQLAlchemy is the database. AWS ECS Fargate runs a single container (FastAPI serves both the API and the React static build). S3 stores uploaded tapes, exception reports, and will store generated PDFs. AWS SES handles email delivery.

The greenfield STACK.md recommendations for Node.js, Drizzle ORM, and the Node-to-Python sidecar pattern are superseded by the actual codebase. Within the Python layer, the established patterns to continue using are: pandas DataFrames for in-process loan data, Pydantic v2 for validation, background threads (not subprocesses) for new business logic, subprocess only for the legacy tagging and final funding scripts, and WeasyPrint + Jinja2 for PDF generation (preferred over ReportLab for maintainability). For email, use AWS SES via boto3 (wire instruction PDFs must not transit third-party email servers). Cashflow computation already supports both local subprocess and ECS task launch — continue using the ECS task launch path for production-scale runs.

**Core technologies (confirmed via codebase):**
- **React 19 + TypeScript + Vite:** Frontend SPA — serves as static files from the FastAPI container in production
- **Python FastAPI + Uvicorn:** API layer and pipeline orchestration — single process, background threads for long jobs
- **SQLAlchemy 2.0 + Alembic:** Database ORM and migrations — schema-as-code, auditable migration files
- **pandas DataFrames:** In-process loan data structure — passes through all pipeline stages without serialization
- **Pydantic v2:** API input validation and loan record modeling
- **WeasyPrint + Jinja2:** Wire instruction PDF generation — HTML-templated, maintainable layout
- **AWS SES via boto3:** Email delivery — stays within AWS perimeter for financial data
- **AWS S3 via StorageBackend abstraction:** All file I/O — same code works in dev (local) and production (S3)
- **PostgreSQL 16 via RDS:** Primary data store — NUMERIC(18,6) for all monetary values, UUIDs as PKs, soft deletes
- **AWS ECS Fargate + ALB + CloudFront:** Infrastructure — single container, Terraform-managed

**Critical version rules:**
- All monetary values: `decimal.Decimal` in Python, `NUMERIC(18,6)` in PostgreSQL — never `float`
- Loan IDs: always `str`, never `int` or `float`
- Python 3.12 (not 3.13 — ecosystem still catching up)

### Expected Features

The FEATURES.md research, grounded in codebase analysis, reveals 28 table-stakes features spanning file ingestion, pipeline control, rules processing, counterparty management, output generation, audit trail, auth, and business date management. The majority are already implemented. What is not yet built concentrates in two areas:

**Must have (table stakes — not yet complete):**
- **TS-19: Wire instruction PDF generation** — the end product of the workflow; final funding scripts exist but PDF pipeline needs to be wired to the UI
- **TS-20: PDF delivery to counterparties** — currently a fully manual process (download + email); needs integration into the dashboard
- Stage 5 UI (wire instruction review and send screen) — the guided workflow has no completion step

**Should have (differentiators that prevent wasted runs):**
- **D-1: Pre-flight file validation** — catches missing required files before the run starts, not after a mid-run crash
- **D-2: File format and column validation on upload** — surface column mismatches immediately, before processing
- **D-6: Structured real-time log panel** — log data is stored in `run.errors` but not displayed in real time on the run detail page
- **D-8: Exception drill-down with loan attributes** — loan_data JSON is stored per exception but not surfaced in the UI
- **D-11: IRR target override as a visible field** — currently silently defaults; ops should see and confirm it
- **D-13: Cashflow progress message** — `progress_message` field exists but compute layer does not populate it meaningfully

**Defer (v2+):**
- D-7: Run-over-run exception delta (requires sufficient run history)
- D-10: Side-by-side run comparison
- D-17 to D-21: Email delivery tracking, template admin UI, run history analytics, rejection trend charts, balance-weighted exception summaries
- All anti-features (AF-1 through AF-9): automated email ingestion, banking API integration, counterparty portal, mobile UI, automated scheduling, ML scoring, bulk exception workflows, multi-currency, streaming ingestion

### Architecture Approach

The architecture is a single-container deployment pattern: React SPA + FastAPI API + Python business logic all live in one ECS Fargate task. The frontend calls FastAPI REST endpoints with JWT authentication. Pipeline logic runs in background threads (not subprocesses) for new code; legacy tagging and final funding scripts run via `subprocess.run`. The database is the single source of truth for all run state — the frontend never reads files directly. S3/local filesystem is accessed exclusively through the `StorageBackend` abstraction. The one exception to single-container is cashflow computation, which already supports launching as a separate ECS task for CPU-intensive production runs.

**Major components:**
1. **React SPA (frontend/src/)** — 9 implemented pages; missing: Stage 5 wire instruction review/send UI
2. **FastAPI API (backend/api/, backend/orchestration/)** — runs, files, cashflow, auth routers; background thread for main pipeline
3. **PipelineExecutor (backend/orchestration/pipeline.py)** — coordinates all suitability analysis stages in sequence
4. **StorageBackend abstraction (backend/storage/)** — local or S3, transparent to all pipeline code
5. **SQLAlchemy models (backend/db/models.py)** — pipeline_runs, loan_exceptions, loan_facts, users, holidays, cashflow_jobs
6. **External script runners (backend/orchestration/tagging_runner.py, final_funding_runner.py)** — subprocess isolation for legacy scripts
7. **Cashflow engine (backend/cashflow/)** — in-process compute or ECS task launch; Final Funding workbooks

### Critical Pitfalls

The 16 identified pitfalls sort into three must-address-before-launch categories:

**Foundation-level (must be correct before any new phase delivers value):**

1. **Floating-point in cashflow calculations (Critical)** — Any `float` used for monetary values in the Python cashflow engine will accumulate rounding errors across 1,000 loans. Replace with `decimal.Decimal` using a single canonical rounding function at output boundaries. Add regression tests against known loan tapes with pre-calculated expected outputs. Treat any cent-level discrepancy as a blocking bug.

2. **Non-idempotent processing runs (Critical)** — A retry or double-click must not produce duplicate database records, duplicate cashflow entries, or duplicate emails. Enforce via `INSERT ... ON CONFLICT DO NOTHING` throughout, UUID-keyed run records, and a state machine (`created → uploaded → validated → analyzed → tagged → cashflows_calculated → pdfs_generated → emails_sent`) that gates UI actions on completed prior states.

3. **No full audit trail (Critical)** — The schema exists but key events are missing: authenticated user ID per step transition, git SHA per run, sent PDFs archived permanently (never regenerated). Treat the run database as an append-only ledger. Store original uploaded spreadsheets by run_id in S3 permanently.

**Integration-level (must be correct when Stage 5 is built):**

4. **Duplicate wire instructions from email retry (Critical)** — Track email delivery state per `(run_id, counterparty)`. Use SES message IDs for delivery confirmation. Require explicit "you are about to send a real email" confirmation with two-step UI. Log every resend attempt.

5. **No test/production separation (High)** — Before any end-to-end testing, enforce that all non-production environments override counterparty email addresses to an internal mailbox. Add an unmissable environment banner to the UI. Never rely on developer discipline for this.

**Core-build-level (must be addressed during feature implementation):**

6. **Silent data truncation from spreadsheet parsing (High)** — Implement a strict validation layer that runs immediately after parse: expected columns present, types correct, value ranges sane, row count matches expectations. Reject the file entirely on any failure. Parse loan IDs as strings always.

7. **PDF content errors not caught before sending (High)** — Build a mandatory in-UI PDF preview step. Add automated assertions on PDF content after generation (counterparty name, total wire amount, account number, routing number all non-empty). Do not allow "Send" button to activate without preview confirmation.

---

## Implications for Roadmap

Based on combined research, the project's substantially-built state means the roadmap is not starting from zero. The sequencing follows two principles: (1) do not let incomplete foundational safety controls accumulate across phases, and (2) complete the workflow end-to-end before adding polish features. The suggested phase structure is:

### Phase 1: Foundation Hardening
**Rationale:** Three critical pitfalls are in "Foundation" phase — floating-point, idempotency, and audit trail. These must be correct before any new feature is trusted to produce accurate financial results. This phase is primarily defensive work on the existing codebase, not new features.
**Delivers:** A trustworthy processing foundation — correct monetary arithmetic, run state machine with full transitions, complete audit log schema, environment separation (staging banner, email override)
**Addresses:** TS-21 through TS-24 (audit trail), TS-7 (sequential job enforcement), TS-26/27 (auth completeness)
**Avoids:** Pitfalls 1.1 (float arithmetic), 2.1 (idempotency), 2.2 (audit trail), 5.1 (test/prod separation)
**Research flag:** Standard patterns — no phase research needed. Decimal replacement and idempotent upserts are well-understood.

### Phase 2: Upload and Pre-Run Validation
**Rationale:** File discovery and validation are the gate to every run. Pre-flight checks (D-1, D-2) are the highest-value differentiators because they prevent wasted runs. Schema drift (pitfall 4.1) and silent data truncation (pitfall 1.2) must be caught here, not mid-pipeline.
**Delivers:** Pre-flight checklist UI, column validation on upload, duplicate file detection, schema mismatch errors surfaced immediately
**Addresses:** TS-1, TS-2, TS-3 (file ingestion — hardening), D-1, D-2, D-3 (pre-run validation)
**Avoids:** Pitfalls 1.2 (data truncation), 4.1 (schema drift), 4.2 (upload corruption)
**Research flag:** Standard patterns — no phase research needed. Validation schemas and file checksums are established.

### Phase 3: Pipeline Visibility and Run Experience
**Rationale:** The core processing pipeline is working, but the operator experience during a run is weak. Real-time log panel, per-phase timing, and exception drill-down give Ops confidence that the run is progressing correctly and help diagnose failures quickly. This phase completes the gap between "it runs" and "we trust what it's doing."
**Delivers:** Structured real-time log panel (D-6), exception drill-down with loan attributes (D-8), IRR target visible on run start (D-11), cashflow progress messages (D-13), per-phase timing (D-5), estimated run duration (D-4)
**Addresses:** TS-5 (real-time status hardening), TS-6 (failure feedback improvement)
**Avoids:** Pitfall 5.2 (processing state lost on refresh — DB-backed state), 5.3 (API layer validation), 5.4 (reconciliation reporting)
**Research flag:** Standard patterns — polling, SSE, and log streaming are well-documented.

### Phase 4: Counterparty Tagging Integration
**Rationale:** Tagging is currently a stub. The real tagging script must be integrated before Stage 5 can produce correct wire instructions. The UI needs a tagging review step — not just a trigger button — because counterparty assignment errors produce misdirected wire instructions, the most serious operational error.
**Delivers:** Real tagging script integrated, tagging results UI with per-loan counterparty assignments visible, explicit Ops confirmation gate before cashflow calculation proceeds
**Addresses:** TS-14 (dual-counterparty tagging), TS-15 (per-counterparty output generation)
**Avoids:** Pitfall 1.3 (tagging logic errors — mandatory review step is the control)
**Research flag:** May need phase research for the tagging script API contract. The subprocess pattern is established, but the specific input/output format for the real script needs confirmation.

### Phase 5: Wire Instructions and Email Delivery
**Rationale:** This is the only unbuilt major workflow stage. It depends on correct loan data (Phase 1), correct tagging (Phase 4), and correct cashflows (already built). Because this stage sends real financial documents to external counterparties, it has the highest concentration of operational safety requirements.
**Delivers:** Wire instruction PDF generation (WeasyPrint + Jinja2), in-UI PDF preview with mandatory review gate, AWS SES email delivery with idempotency, per-(run_id, counterparty) delivery state tracking, run completion reconciliation summary
**Addresses:** TS-19 (PDF generation), TS-20 (PDF delivery), D-16 (in-UI preview), D-17 (email delivery tracking)
**Avoids:** Pitfalls 2.3 (duplicate wire emails), 3.1 (PDF content errors), 3.2 (PDF environment failures), 5.4 (reconciliation reporting)
**Research flag:** Needs phase research. WeasyPrint PDF generation in ECS Fargate containers requires system font and library verification. SES raw email with PDF attachments has specific configuration requirements. Confirm the exact counterparty wire instruction format before designing the template.

### Phase 6: Audit and Operational Hardening
**Rationale:** With the full workflow running end-to-end, complete the audit trail, production alerting, and run history features. This phase makes the system defensible to auditors and reduces operational risk from silent failures.
**Delivers:** Complete audit event table with all step transitions and user IDs, git SHA per run result, permanent PDF storage policy enforced, CloudWatch alarms on failed runs, failed run dashboard surfacing, run notes field (D-12), run archive browsing
**Addresses:** TS-21 through TS-25 (audit trail completion), D-12 (run notes)
**Avoids:** Pitfall 2.2 (audit trail gaps), 6.2 (no alerting on production failures)
**Research flag:** Standard patterns — CloudWatch alarms and append-only event logging are well-documented.

### Phase Ordering Rationale

- Phase 1 before everything: floating-point errors and idempotency gaps silently corrupt all downstream results. No other phase should deliver value on top of a broken foundation.
- Phase 2 before Phase 3: pre-run validation prevents wasted runs that Phase 3 monitoring would otherwise surface after the fact.
- Phase 4 before Phase 5: Stage 5 PDF generation reads counterparty-tagged loan data from Postgres. A tagging stub produces placeholder outputs that would generate incorrect wire instructions.
- Phase 5 as the integration milestone: it is the only unbuilt mandatory workflow stage and has the highest operational stakes — concentrated safety controls should only be built once, in one phase, not spread across multiple phases.
- Phase 6 after end-to-end delivery: operational hardening is most useful once the full workflow is running and real usage patterns are observable.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 4 (Tagging Integration):** The tagging script API contract (input dir layout, output file format, environment variable interface) needs confirmation before the integration work is estimated. If the real script is unavailable, a more complete stub that produces realistic output format is needed.
- **Phase 5 (Wire Instructions + Email):** WeasyPrint system dependency behavior in the ECS Fargate container image needs verification before implementation. The exact wire instruction document format (fields, layout, counterparty-specific variations) needs business sign-off before templating.

**Phases with standard patterns (skip phase research):**
- **Phase 1 (Foundation Hardening):** Decimal replacement, idempotent upserts, and audit schemas are textbook patterns.
- **Phase 2 (Upload Validation):** Schema validation, column presence checks, and file checksums are well-established.
- **Phase 3 (Pipeline Visibility):** DB-backed polling, log streaming, and SSE patterns are standard.
- **Phase 6 (Audit Hardening):** CloudWatch alarms and event logging are AWS standard practices.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Architecture.md is grounded in direct codebase analysis of all key files. The stack is confirmed, not inferred. The STACK.md greenfield recommendations are informative for library choices within the Python layer but are superseded by what exists. |
| Features | HIGH | FEATURES.md is grounded in codebase analysis of all implemented routes, pages, and database tables. The table-stakes/differentiator/anti-feature classification is based on direct observation of what is and is not built. |
| Architecture | HIGH | ARCHITECTURE.md cites specific files and line numbers. The integration patterns (background threads, subprocess for legacy scripts, StorageBackend abstraction, ECS task for cashflow) are confirmed by code review. |
| Pitfalls | HIGH | Pitfalls are grounded in both codebase observation and financial operations domain knowledge. Specific warning signs (float usage, INSERT without ON CONFLICT, missing email idempotency) are verifiable in the existing code. |

**Overall confidence:** HIGH

### Gaps to Address

- **Tagging script API contract:** The real counterparty tagging script is not present in the codebase (only a stub). The environment variable interface (`INPUT_DIR`, `OUTPUT_DIR`) is established, but the exact output file format and column schema is unknown. Validate with the business team before Phase 4.
- **Wire instruction document format:** The exact layout, fields, and counterparty-specific content of wire instruction PDFs has not been specified. This must be confirmed before Phase 5 template design. Existing output from `final_funding_sg.py` and `final_funding_cibc.py` scripts should be reviewed as the format baseline.
- **Decimal audit of existing cashflow code:** The cashflow engine (`backend/cashflow/compute/`) needs a targeted audit for float usage before Phase 1 closes. The scope of Decimal replacement depends on how widely float is used in the existing calculation code.
- **Concurrent user requirements:** The current architecture assumes one run at a time (TS-7). If multiple ops users will submit runs simultaneously in the future, a job queue (SQS or BullMQ) is required. Confirm expected concurrent usage before finalizing the Phase 1 run state machine design.
- **Counterparty rules changeability:** The research flagged whether prime/SFY routing rules are static (hardcoded Python) or dynamic (need a `counterparty_rules` admin table). This determines whether Phase 4 needs an admin UI component. Confirm with the business owner.

---

## Sources

### Primary (HIGH confidence — direct codebase analysis)
- `backend/api/routes.py` — pipeline endpoint, threading pattern
- `backend/orchestration/pipeline.py` — PipelineExecutor, all stage sequence
- `backend/orchestration/tagging_runner.py`, `final_funding_runner.py` — subprocess patterns
- `backend/cashflow/routes.py` — local subprocess vs ECS task launch
- `backend/db/models.py` — all database tables and relationships
- `backend/storage/__init__.py`, `backend/storage/base.py` — StorageBackend abstraction
- `backend/requirements.txt` — confirmed Python dependency versions
- `frontend/src/App.tsx` — all implemented frontend routes
- `frontend/package.json` — confirmed frontend dependency versions
- `deploy/terraform/qa/ecs.tf`, `deploy/terraform/qa/s3.tf` — infrastructure configuration
- `.planning/PROJECT.md` — requirements and constraints

### Secondary (MEDIUM confidence — domain research with general applicability)
- STACK.md — greenfield library recommendations (informative for choices within the Python layer; architecture superseded by codebase)
- PITFALLS.md — financial operations domain pitfalls (pattern-matched to codebase observations)

### Tertiary (LOW confidence — needs validation during implementation)
- WeasyPrint ECS Fargate compatibility — system font and GTK library behavior in the container environment needs smoke testing before Phase 5
- Tagging script output format — inferred from the stub; actual format depends on the real script

---

*Research completed: 2026-03-04*
*Ready for roadmap: yes*
