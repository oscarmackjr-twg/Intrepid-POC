# Intrepid Loan Purchase Platform

## What This Is

An internal operations dashboard for processing loan purchase opportunities. The Ops team uses it to ingest loan spreadsheets, run suitability analysis, tag loans to counterparties, calculate cashflows, and generate wire instruction PDFs — all through a controlled, step-by-step UI backed by Python processing logic.

## Core Value

Ops can take a loan tape from email to executed wire instructions in a single, auditable workflow — replacing ad hoc scripts with a controlled, visible process.

## Current Milestone: v2.0 Real Estate Loan Dashboard POC

**Goal:** Build a comprehensive RE loan portfolio dashboard POC inside the existing React + FastAPI platform, powered by a seeded Postgres dataset.

**Target features:**
- Executive Summary page — KPI cards (UPB, WAC, WAM, LTV, DSCR, active loans, delinquency buckets, yield/spread)
- Portfolio Composition — property type pie chart, US geo heatmap by state/MSA, loan size histogram, maturity profile, top-10 exposures table, concentration limit indicators
- Credit Quality & Risk — LTV/DSCR color-band histograms, watchlist table with risk ratings + trend arrows, delinquency waterfall, risk rating migration matrix, interest rate sensitivity
- Cash Flow & Performance — P&I actual vs projected, NOI trends, yield analysis, CPR tracking, loss/recovery tracking
- Origination Pipeline — new origination volume by month, payoffs/paydowns, pipeline funnel, vintage analysis
- Market Context — stubbed static values (10Y Treasury, SOFR, cap rates, vacancy rates) with real-feed hook markers
- Global filter sidebar — date/as-of, property type, geography, loan size, risk rating, vintage, borrower, rate type
- Drill-down interactivity — chart segment click filters dashboard; loan row click opens detail card
- Export — PDF dashboard snapshot, CSV export of any filtered table
- Role-based view stub — PM (full portfolio) vs advisor (their book only)

## Requirements

### Validated

- ✓ File upload and S3 storage — existing
- ✓ Suitability pipeline execution (PipelineExecutor, background thread) — existing
- ✓ LoanFact and LoanException persistence in PostgreSQL — existing
- ✓ Cashflow computation (subprocess/ECS mode) — existing
- ✓ Dashboard, RunDetail, ProgramRuns, CashFlow, Exceptions, FileManager UI pages — existing

### Active

- [ ] Developer can start the full stack locally with a single command
- [ ] FastAPI server runs locally with Postgres database connected
- [ ] React frontend runs locally with hot reload
- [ ] Pipeline executes end-to-end locally
- [ ] Environment config managed via .env files (no hardcoded values)
- [ ] Local file storage works without S3 (dev mode)
- [ ] `docker compose up` starts all services (FastAPI, Postgres, React dev server)
- [ ] Postgres data persists across container restarts (volume)
- [ ] Production Dockerfile builds React static files into FastAPI container
- [ ] Production image runs via environment variables for config
- [ ] Terraform defines ECS Fargate cluster and task definition
- [ ] Terraform defines RDS Postgres (staging)
- [ ] Terraform defines ALB with HTTPS termination
- [ ] Terraform defines S3 buckets and ECR repository
- [ ] VPC and networking configured (public/private subnets, security groups)
- [ ] IAM roles and policies for ECS task execution
- [ ] SES configured for email delivery
- [ ] GitHub Actions workflow builds and pushes Docker image to ECR on push
- [ ] CI/CD deploys to staging ECS on push to main branch
- [ ] Database migrations run automatically on deploy
- [ ] Staging environment is deployed and accessible via URL
- [ ] Staging email delivery routes to internal mailbox only
- [ ] End-to-end smoke test passes in staging

### Out of Scope

- Automated email ingestion (Ops manually downloads and uploads spreadsheets)
- Direct integration with banking APIs for wire execution (PDFs are the output)
- Counterparty portal / external user access — internal Ops tool only
- Wire instruction PDF generation and SES email delivery — v1.1
- Counterparty tagging integration (real script) — v1.1
- Foundation hardening (Decimal precision, idempotency) — v1.1

## Context

- **Existing work:** Substantial codebase already built — React SPA + Python FastAPI + PostgreSQL + S3. Core pipeline stages (upload, suitability, cashflow) are implemented. No local or Docker dev environment currently exists.
- **Actual stack (corrected from initial brief):** React 19 + Python FastAPI (no Node.js layer) + PostgreSQL via SQLAlchemy + S3 + ECS Fargate
- **Frequency:** Runs approximately twice per working week when loan tapes arrive via email
- **Volume:** ~1,000 loans per processing run (two spreadsheets of ~500 each)
- **Counterparties:** Two — "prime" and "SFY" — loans may be tagged to one or both
- **Current state:** Codebase exists but nothing runs locally. Goal: local dev → Docker → AWS staging by end of next week.

## Constraints

- **Tech Stack:** React 19 + Python FastAPI + PostgreSQL (SQLAlchemy/Alembic) + S3 — no Node.js layer
- **Infrastructure:** AWS ECS Fargate + RDS + ALB via Terraform — established pattern
- **Container:** Single container image (FastAPI serves React static files in production)
- **Financial accuracy:** All monetary values must use `decimal.Decimal` / `NUMERIC(18,6)` — never float
- **Users:** Internal Ops team only — no external access required for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React 19 + Python FastAPI (no Node) | Actual scaffolding discovered in codebase | ✓ Confirmed |
| AWS ECS Fargate + Terraform | Established infra approach | ✓ Confirmed |
| Single container (React built into FastAPI) | Simplifies ECS deployment; no separate CDN needed for v1 | — Pending |
| Docker Compose for local dev | Standard pattern; mirrors production topology locally | — Pending |
| GitHub Actions for CI/CD | Standard, integrates with ECR/ECS natively | — Pending |
| Cashflow as subprocess / ECS task | CPU-heavy computation supports horizontal scaling | ✓ Confirmed |
| Decimal arithmetic throughout | Float accumulates error across 1,000 loans | — Pending (verify in existing code) |

---
## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 — Phase 24 complete: Origination Pipeline + Market Context page live (all 6 RE dashboard tabs now implemented)*
