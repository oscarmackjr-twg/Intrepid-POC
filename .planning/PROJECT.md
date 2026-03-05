# Intrepid Loan Purchase Platform

## What This Is

An internal operations dashboard for processing loan purchase opportunities. The Ops team uses it to ingest loan spreadsheets, run suitability analysis, tag loans to counterparties, calculate cashflows, and generate wire instruction PDFs — all through a controlled, step-by-step UI backed by Python processing logic.

## Core Value

Ops can take a loan tape from email to executed wire instructions in a single, auditable workflow — replacing ad hoc scripts with a controlled, visible process.

## Requirements

### Validated

- ✓ File upload and S3 storage — existing
- ✓ Suitability pipeline execution (PipelineExecutor, background thread) — existing
- ✓ LoanFact and LoanException persistence in PostgreSQL — existing
- ✓ Cashflow computation (subprocess/ECS mode) — existing
- ✓ Dashboard, RunDetail, ProgramRuns, CashFlow, Exceptions, FileManager UI pages — existing

### Active

- [ ] Ops team can upload loan spreadsheets (2 files, ~500 loans each) downloaded from email
- [ ] Python workflow processes loans against rule-based suitability criteria
- [ ] Loans are tagged to up to two counterparties (prime and SFY)
- [ ] Cashflows are calculated per counterparty for eligible loans
- [ ] Wire instructions are generated as PDF documents
- [ ] PDFs are sent via email to the appropriate counterparty
- [ ] Ops team triggers each workflow step manually through the dashboard
- [ ] Full visibility into processing status at each stage
- [ ] All monetary values use Decimal (not float) throughout the pipeline
- [ ] Processing runs are idempotent (safe to retry without duplicate side effects)
- [ ] Full audit trail: user, timestamp, and Python version recorded per run step

### Out of Scope

- Automated email ingestion (Ops manually downloads and uploads spreadsheets)
- Direct integration with banking APIs for wire execution (PDFs are the output)
- Counterparty portal / external user access — internal Ops tool only

## Context

- **Existing work:** Substantial codebase already built — React SPA + Python FastAPI + PostgreSQL + S3. Core pipeline stages (upload, suitability, cashflow) are implemented. Remaining: wire instruction PDFs, email delivery, tagging integration, and hardening.
- **Actual stack (corrected from initial brief):** React 19 + Python FastAPI (no Node.js layer) + PostgreSQL via SQLAlchemy + S3 + ECS Fargate
- **Frequency:** Runs approximately twice per working week when loan tapes arrive via email
- **Volume:** ~1,000 loans per processing run (two spreadsheets of ~500 each)
- **Counterparties:** Two — "prime" and "SFY" — loans may be tagged to one or both
- **Current state:** Dashboard exists but Stage 5 (wire instructions + email) is not yet built; tagging script is a stub awaiting integration

## Constraints

- **Tech Stack:** React 19 + Python FastAPI + PostgreSQL (SQLAlchemy/Alembic) + S3 — no Node.js layer
- **Infrastructure:** AWS ECS Fargate + RDS + ALB via Terraform — established
- **Processing:** Python FastAPI handles both API and business logic orchestration
- **Financial accuracy:** All monetary values must use `decimal.Decimal` / `NUMERIC(18,6)` — never float
- **Users:** Internal Ops team only — no external access required for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React 19 + Python FastAPI (no Node) | Actual scaffolding discovered in codebase | ✓ Confirmed |
| AWS ECS Fargate + Terraform | Established infra approach | ✓ Confirmed |
| Manual step-by-step UI control | Ops needs to review and approve at each stage | — Pending |
| PDF wire instructions via email (AWS SES) | Existing counterparty process; financial data stays inside AWS perimeter | — Pending |
| Cashflow as subprocess / ECS task | CPU-heavy computation supports horizontal scaling | ✓ Confirmed |
| Decimal arithmetic throughout | Float accumulates error across 1,000 loans | — Pending (verify in existing code) |

---
*Last updated: 2026-03-04 after research — stack corrected (React + Python FastAPI, no Node.js)*
