---
phase: 17
name: Data Foundation
status: context-complete
date: 2026-04-08
---

# Phase 17 Context: Data Foundation

## Phase Goal
The `re_loans` and `re_loan_cashflows` tables exist with correct schema and are seeded with realistic CRE portfolio data, making the database the single source of truth for all subsequent dashboard development.

## Canonical Refs
- `.planning/REQUIREMENTS.md` — DATA-01, DATA-02, DATA-03, DATA-04
- `backend/db/models.py` — existing SQLAlchemy model patterns to follow
- `backend/migrations/versions/efe3898fdf4b_add_audit_log_table.py` — current Alembic head; new migrations chain from here
- `backend/scripts/seed_staging_user.py` — seed script pattern to follow

## Decisions

### Schema: API-Driven Minimum (~25–30 columns)
`re_loans` includes only columns needed to power the 11 `/api/re/*` endpoints. No Phase 25 side-panel fields (appraisal history, covenant notes) — those can be added in a later migration when needed.

Required columns derived from endpoint requirements:
- **Identity/admin:** `id`, `loan_number`, `borrower_name`, `sales_team_id` (FK → sales_teams), `as_of_date`
- **Financials:** `upb` (NUMERIC(18,6)), `original_balance` (NUMERIC(18,6)), `interest_rate` (NUMERIC(10,6)), `wam_months` (Integer), `ltv` (NUMERIC(10,6)), `dscr` (NUMERIC(10,6))
- **Classification:** `property_type` (String), `state` (String(2)), `msa` (String), `risk_rating` (String), `prior_risk_rating` (String), `rate_type` (String — fixed/floating/hybrid)
- **Dates:** `origination_date` (Date), `maturity_date` (Date)
- **Delinquency:** `days_past_due` (Integer, default 0), `delinquency_status` (String — current/30/60/90/default)
- **Pipeline:** `pipeline_stage` (String — underwriting/approved/closing/funded), `vintage_year` (Integer)
- **Audit:** `created_at` (DateTime)

**Constraint:** All monetary columns use `NUMERIC(18,6)`. All rate columns use `NUMERIC(10,6)`. No `Float` for financial values (project-wide constraint from PROJECT.md).

`re_loan_cashflows` columns:
- `id`, `loan_id` (FK → re_loans), `period_date` (Date), `scheduled_principal` (NUMERIC(18,6)), `actual_principal` (NUMERIC(18,6)), `scheduled_interest` (NUMERIC(18,6)), `actual_interest` (NUMERIC(18,6)), `noi` (NUMERIC(18,6)), `created_at` (DateTime)

### Seed Data: Statistically Realistic Distributions
- **500–600 loans** total (across both as_of_date snapshots — see below)
- LTV normally distributed ~N(0.67, 0.08) — clipped to [0.40, 0.95]
- DSCR inversely correlated with LTV: base ~N(1.35, 0.25), clipped to [0.70, 2.80]
- Property type distribution: multifamily 35%, office 20%, retail 15%, industrial 15%, hospitality 10%, mixed-use 5%
- Geographic spread: ≥20 states, ≥8 MSAs (concentrate in NY, CA, TX, FL, IL to feel realistic)
- Risk ratings: AAA/AA/A/BBB/BB/B/CCC — bell-curved around BBB
- Rate type: ~60% fixed, 30% floating, 10% hybrid
- `days_past_due` / `delinquency_status`: ~85% current, ~8% 30-day, ~5% 60-day, ~2% 90+

### Two as_of_date Snapshots
- **T0:** `2025-09-30` — base snapshot (~500 loans)
- **T1:** `2025-12-31` — updated snapshot (same loan population, with ~10–15% showing risk rating changes)
  - Migrations: ~8% downgraded one notch (BBB→BB, BB→B), ~5% upgraded one notch
  - The `prior_risk_rating` column on each row stores the T0 rating; `risk_rating` stores the T1 rating
  - This powers the Phase 22 risk rating migration matrix using the two snapshots
- Cashflow history: 12 monthly records per loan (Oct 2024 – Sep 2025), linked to T0 loan records
  - T1 snapshot rows do not duplicate cashflow records — cashflows belong to the loan, not the snapshot

### Seed Script Location
- File: `backend/scripts/seed_re_loans.py`
- Invocation: `python scripts/seed_re_loans.py` from `backend/` directory
- Behavior: idempotent — truncates `re_loan_cashflows` then `re_loans` before re-seeding so it can be re-run safely
- Pattern: follows `backend/scripts/seed_staging_user.py` — direct SQLAlchemy session, not via ORM relationships for bulk inserts

### Alembic Migration Chain
- Two new migration files chaining from `efe3898fdf4b`:
  1. `add_re_loans_table` — creates `re_loans` with all columns and indexes (`as_of_date`, `property_type`, `state`, `sales_team_id`)
  2. `add_re_loan_cashflows_table` — creates `re_loan_cashflows` with FK to `re_loans` and index on `(loan_id, period_date)`
- SQLAlchemy model classes added to `backend/db/models.py` following existing patterns

## Out of Scope (Deferred)
- Phase 25 side-panel fields (appraisal history, collateral description, covenant notes) — add in a later migration
- Live data ingestion or real loan data — this is seeded/synthetic only
- Seed wired into CI or Alembic — manual run only for now

## Success Criteria (from ROADMAP.md)
1. `alembic upgrade head` with no errors; `SELECT COUNT(*) FROM re_loans` ≥ 500 rows
2. All monetary columns are `NUMERIC(18,6)`, rate columns `NUMERIC(10,6)` — confirmed via `\d re_loans`
3. `SELECT COUNT(*) FROM re_loan_cashflows` returns 12 records per loan
4. Seeded data spans ≥5 property types, ≥20 states, ≥8 MSAs, two distinct `as_of_date` snapshots
5. `alembic upgrade head` runs in CI without conflicts with existing migration chain
