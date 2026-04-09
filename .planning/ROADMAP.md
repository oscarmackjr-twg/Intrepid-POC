# Roadmap: Intrepid Loan Purchase Platform

## Overview

This milestone (v1.0 â Local to Cloud) takes the existing codebase from nothing-runs to a fully deployed staging environment. The work progresses in strict dependency order: get the app running locally, containerize it, provision AWS infrastructure, wire up CI/CD, and verify the staging deployment end-to-end. Each phase builds directly on the previous and cannot proceed without it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Local Dev** - App runs locally with clean config, no hardcoded paths or Windows artifacts
- [x] **Phase 2: Docker Local Dev** - Single-command Docker Compose startup with auto-migrations and hot reload (completed 2026-03-06)
- [x] **Phase 3: AWS Infrastructure** - Terraform qa environment applies cleanly with secrets, ECR, and RDS live (completed 2026-03-06)
- [x] **Phase 4: CI/CD Pipeline** - GitHub Actions builds, pushes to ECR, and deploys to ECS with migrations (completed 2026-03-06)
- [x] **Phase 5: Staging Deployment** - Live staging URL, Ops can log in and upload, environment banner visible (completed 2026-03-22)

## Phase Details

### Phase 1: Local Dev
**Goal**: A developer can run the full stack locally â backend, frontend, database, and pipeline â using only documented env config with no hardcoded paths or Windows artifacts
**Depends on**: Nothing (first phase)
**Requirements**: LOCAL-01, LOCAL-02, LOCAL-03, LOCAL-04, LOCAL-05, LOCAL-06
**Success Criteria** (what must be TRUE):
  1. `uvicorn` starts the FastAPI backend and connects to local Postgres without error
  2. `npm run dev` starts the React frontend with hot reload at the expected local port
  3. `backend/.env` contains no hardcoded Windows paths and clearly separates local-storage vs S3 modes
  4. A new developer can onboard using `.env.example` alone â no undocumented env vars required
  5. Alembic migrations apply cleanly and the core pipeline completes an upload-to-cashflow run locally
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md â Clean backend/.env and create backend/.env.example (LOCAL-03, LOCAL-04)
- [ ] 01-02-PLAN.md â Synthetic sample data and initial Alembic migration (LOCAL-05, LOCAL-06)
- [ ] 01-03-PLAN.md â Makefile and DEVELOPMENT.md onboarding guide (LOCAL-01, LOCAL-02, LOCAL-04)
- [ ] 01-04-PLAN.md â Human smoke test: full stack end-to-end verification (all LOCAL requirements)

### Phase 2: Docker Local Dev
**Goal**: `docker compose up` starts the full local stack â app, Postgres, React dev server â with data persisting across restarts and migrations running automatically
**Depends on**: Phase 1
**Requirements**: DOCKER-01, DOCKER-02, DOCKER-03, DOCKER-04
**Success Criteria** (what must be TRUE):
  1. `docker compose -f deploy/docker-compose.yml up` starts all services with no manual steps after the first run
  2. The app is accessible at `localhost:8000` in the browser immediately after compose up
  3. The Postgres volume mount uses a relative or env-var path â no hardcoded Windows absolute paths in docker-compose.yml
  4. Alembic migrations run automatically on container start without manual intervention
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md â Overhaul docker-compose.yml: fix DB name, remove Windows path, add migrations entrypoint, add frontend service (DOCKER-01, DOCKER-02, DOCKER-04)
- [ ] 02-02-PLAN.md â Update vite.config.ts proxy target + human smoke test of full Docker stack (DOCKER-01, DOCKER-03)

### Phase 3: AWS Infrastructure
**Goal**: Terraform qa environment applies cleanly, leaving a provisioned ECR repository, running RDS instance, and Secrets Manager entries that ECS tasks can consume
**Depends on**: Phase 2
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. `terraform init && terraform apply` completes with no errors in the qa workspace
  2. Secrets Manager contains entries for `DATABASE_URL` and `SECRET_KEY` readable by the ECS task role
  3. ECR repository is provisioned and a test `docker push` to it succeeds with valid AWS credentials
  4. RDS Postgres instance is running and reachable on its private endpoint from within the VPC
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md â Fix loan-engine naming remnants, create terraform.tfvars, destroy+apply infrastructure (INFRA-01)
- [x] 03-02-PLAN.md â Verify Secrets Manager entries, ECR push test, and RDS psql connectivity (INFRA-02, INFRA-03, INFRA-04)

### Phase 4: CI/CD Pipeline
**Goal**: A push to main triggers GitHub Actions to build the Docker image, push it to ECR, run Alembic migrations, and deploy the updated task to ECS â all without manual steps
**Depends on**: Phase 3
**Requirements**: CICD-01, CICD-02, CICD-03
**Success Criteria** (what must be TRUE):
  1. A push to main triggers the GitHub Actions workflow, which builds the image and pushes it to ECR successfully
  2. The workflow runs Alembic migrations against the staging RDS instance as part of the deploy sequence
  3. All required GitHub secrets and variables are documented (in README or CICD runbook) and confirmed configured in the repo
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md â Terraform OIDC IAM role, subnet/SG outputs, terraform apply + GitHub repo variable setup (CICD-01)
- [ ] 04-02-PLAN.md â Rewrite GitHub Actions workflow: OIDC auth, correct ECR/ECS names, migration step, stability wait (CICD-01, CICD-02)
- [ ] 04-03-PLAN.md â Create docs/CICD.md runbook: secrets/variables inventory, OIDC setup steps, deploy sequence (CICD-03)

### Phase 5: Staging Deployment
**Goal**: The staging environment is live at a real URL, Ops can log in and upload a file, and the environment is clearly identified as non-production
**Depends on**: Phase 4
**Requirements**: STAGE-01, STAGE-02, STAGE-03
**Success Criteria** (what must be TRUE):
  1. The staging URL loads the application in a browser after a CI/CD deploy completes
  2. An Ops team member can log in, upload a loan spreadsheet, and see it accepted by the application
  3. A clearly visible, unmissable banner identifies the environment as staging (not production) on every page
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md â StagingBanner component (Layout + Login), VITE_APP_ENV build arg in Dockerfile and GitHub Actions (STAGE-03)
- [x] 05-02-PLAN.md â Seed script for staging admin user, First Deploy Checklist in CICD.md (STAGE-02)
- [x] 05-03-PLAN.md â Trigger deploy, run seed script, human verification of all three STAGE requirements (STAGE-01, STAGE-02, STAGE-03)

## Progress

**Execution Order:**
Phases execute sequentially: 1 â 2 â 3 â 4 â 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Local Dev | 4/4 | Complete | 2026-03-06 |
| 2. Docker Local Dev | 2/2 | Complete   | 2026-03-06 |
| 3. AWS Infrastructure | 2/2 | Complete | 2026-03-06 |
| 4. CI/CD Pipeline | 3/3 | Complete   | 2026-03-06 |
| 5. Staging Deployment | 3/3 | Complete   | 2026-03-22 |
| 6. Final Funding & Cashflow | 3/5 | In Progress|  |
| 7. Application Hardening | 7/7 | Complete   | 2026-03-11 |
| 8. Fix Staging Auth & Smoke Test | 2/2 | Complete   | 2026-03-22 |
| 9. Write Missing Verification Records | 3/3 | Complete   | 2026-03-22 |
| 10. Revamp User Interface | 3/3 | Complete    | 2026-03-22 |
| 11. Refing UI for Regression Testing | 5/5 | Complete   | 2026-03-14 |
| 12. Unit Testing Build Out | 3/3 | Complete   | 2026-03-22 |
| 13. Final Documentation Cleanup | 3/3 | Complete    | 2026-03-22 |
| 14. Alembic Migration & Seed Automation | 0/2 | Pending | |
| 15. Integrate Updated Tagging Logic | 2/2 | Complete   | 2026-04-09 |

### Phase 6: Final Funding & Cashflow Integration

**Goal:** Replace stub Final Funding SG and CIBC scripts with real workbook implementations, add async job tracking so Ops can see RUNNING/COMPLETED/FAILED status in the UI, and bridge cashflow outputs automatically into Final Funding inputs.
**Requirements**: FF-01, FF-02, FF-03, FF-04, FF-05, FF-06, FF-07, FF-08, FF-09
**Depends on:** Phase 5
**Plans:** 3/3 plans complete

Plans:
- [ ] 06-01-PLAN.md â Test scaffolds (Wave 0): test_final_funding_jobs.py and test_final_funding_runner.py (FF-03..FF-09)
- [ ] 06-02-PLAN.md â Real script replacement: copy and patch SG + CIBC scripts from legacy repo (FF-01, FF-02)
- [ ] 06-03-PLAN.md â Backend job tracking: final_funding_job table, background thread runner, GET/POST API endpoints, cashflow bridge (FF-03..FF-09)
- [ ] 06-04-PLAN.md â Frontend polling: replace alert() in ProgramRuns.tsx with job-id status display (FF-03, FF-06)
- [ ] 06-05-PLAN.md â Full test suite verification + human smoke test checkpoint (FF-01..FF-09)

### Phase 7: Application Hardening

**Goal:** Harden the deployed application across seven areas: AWS networking/TLS (RDS to private subnets, ALB HTTPS), default secrets and bootstrap passwords, frontend auth token storage (localStorage â HttpOnly cookies), file/error endpoint information leakage, CI security and quality gates, durable audit logging, and repository hygiene.
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05, HARD-06, HARD-07
**Depends on:** Phase 6
**Plans:** 7/7 plans complete

Plans:
- [ ] 07-01-PLAN.md â Wave 0 test scaffolds: failing tests for HARD-02, HARD-03, HARD-04, HARD-06 (HARD-02, HARD-03, HARD-04, HARD-06)
- [ ] 07-02-PLAN.md â Repository hygiene + Terraform networking/TLS (HARD-07, HARD-01)
- [ ] 07-03-PLAN.md â Default secrets guard, seed script one-time passwords, password policy validator (HARD-02)
- [ ] 07-04-PLAN.md â File/error leakage sanitization + AuditLog DB model and migration (HARD-04, HARD-06)
- [ ] 07-05-PLAN.md â HttpOnly cookie auth, rate limiting, CSP header, frontend localStorage removal (HARD-03)
- [ ] 07-06-PLAN.md â CI security-quality-gate job blocking deploy + human checkpoint (HARD-05)
- [ ] 07-07-PLAN.md â Wire db session to login audit calls + README credential cleanup (HARD-06, HARD-02)

### Phase 8: Fix Staging Auth & Complete Smoke Test

**Goal:** Unblock staging by adding `LOCAL_DEV_MODE=true` to the ECS task definition (fixing Secure cookie failure over HTTP ALB), apply the Terraform change, and run the Phase 05-03 smoke test to formally verify all three STAGE requirements end-to-end.
**Requirements:** STAGE-01, STAGE-02, STAGE-03
**Gap Closure:** Closes MISS-02 (High â Secure cookie breaks HTTP staging), MISS-01 (Medium â docker-compose.yml startup guard fragility), and satisfies STAGE-01 (unsatisfied) + formally verifies STAGE-02/STAGE-03 (partial)
**Depends on:** Phase 7

Plans:
- [x] 08-01-PLAN.md â Add LOCAL_DEV_MODE=true to ecs.tf + docker-compose.yml; terraform plan + apply (STAGE-01, MISS-01, MISS-02)
- [x] 08-02-PLAN.md â Trigger ECS deploy, run 05-03 smoke test, write Phase 5 VERIFICATION.md (STAGE-01, STAGE-02, STAGE-03)

### Phase 9: Write Missing Verification Records

**Goal:** Produce the VERIFICATION.md files absent from Phases 1 and 6, formalising evidence already confirmed by the integration checker and plan SUMMARYs. No code changes â documentation gap only.
**Requirements:** LOCAL-01, LOCAL-02, LOCAL-03, LOCAL-04, LOCAL-05, LOCAL-06
**Gap Closure:** Closes the verification record gap for LOCAL-01â06 (Phase 1) and the Final Funding integration (Phase 6)
**Depends on:** Phase 8

Plans:
- [x] 09-01-PLAN.md â Write Phase 1 VERIFICATION.md (evidence: integration checker, SUMMARYs, MEMORY.md sample run 9 loans E2E) (LOCAL-01âLOCAL-06)
- [x] 09-02-PLAN.md â Write Phase 6 VERIFICATION.md (evidence: 4 plan SUMMARYs, API confirmed working) (FF-01âFF-09)
- [x] 09-03-PLAN.md â Update REQUIREMENTS.md traceability to reflect gap closure and mark all LOCAL/STAGE reqs Complete

### Phase 10: Revamp User Interface - Phase 10

**Goal:** Redesign the ops dashboard look, feel, and navigation to align with TWG Global brand guidelines â replace horizontal nav with a fixed left sidebar, apply navy brand color throughout, rename app to "Intrepid Loan Platform", add TWG logo, and restructure nav with SG/CIBC group labels. Visual and structural changes only; no new data features.
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Depends on:** Phase 9
**Plans:** 3/3 plans complete

Plans:
- [ ] 10-01-PLAN.md â Brand globals (index.html title, index.css Gotham font + CSS vars, logo asset copy) + Login page rebrand (UI-01, UI-02)
- [ ] 10-02-PLAN.md â Layout.tsx full sidebar rewrite: TWG navy sidebar, logo, SG/CIBC nav groups, admin gate, user footer (UI-03, UI-04, UI-05)
- [ ] 10-03-PLAN.md â Human visual verification of all pages: sidebar, branding, active states, StagingBanner (UI-01âUI-05)

### Phase 11: Refing UI for Regression Testing

**Goal:** Fix nav active-state bugs from Phase 10, apply spacing/typography polish and structural layout improvements to Program Runs and File Manager, create a manual regression test checklist (docs/REGRESSION_TEST.md), and build a data regression script that runs the pipeline CLI against local test cases and diffs outputs byte-for-byte.
**Requirements**: UI-06, UI-07, REG-01, REG-02
**Depends on:** Phase 10
**Plans:** 5/5 plans complete

Plans:
- [ ] 11-01-PLAN.md â Fix nav active-state bugs in Layout.tsx + typography polish in index.css (UI-06)
- [ ] 11-02-PLAN.md â Layout restructure: max-w-5xl + section reordering for ProgramRuns.tsx and FileManager.tsx (UI-07)
- [ ] 11-03-PLAN.md â Create docs/REGRESSION_TEST.md manual checklist covering all pages and core ops workflow (REG-01)
- [ ] 11-04-PLAN.md â Create backend/scripts/regression_test.py data regression harness (REG-02)
- [ ] 11-05-PLAN.md â Claude dry-run of REGRESSION_TEST.md + human visual verification checkpoint (UI-06, UI-07, REG-01, REG-02)

### Phase 12: Unit Testing Build Out

**Goal:** Fix the 8 currently-failing tests to get the suite fully green, extend coverage into cashflow compute (amortization, waterfall, prepayment), rules/comap.py, and orchestration/archive_run.py, wire pytest into CI as a blocking deploy gate with coverage reporting, and update test documentation.
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07
**Depends on:** Phase 11
**Plans:** 3/3 plans complete

Plans:
- [x] 12-01-PLAN.md â Fix all 10 failing/erroring tests across 4 test files (TEST-01)
- [x] 12-02-PLAN.md â New coverage: cashflow compute, CoMAP rules, archive run (TEST-02, TEST-03, TEST-04)
- [x] 12-03-PLAN.md â CI unit-tests gate, pytest-cov, tests/README.md update (TEST-05, TEST-06, TEST-07)

### Phase 13: Final Documentation Cleanup

**Goal:** Write the VERIFICATION.md files still missing after Phase 9 â specifically Phase 11 (all 5 SUMMARYs complete, verification never written) â fix the 03-02-SUMMARY.md frontmatter gaps for INFRA-02/03/04, and formally document the Phase 12 CI human verification step as an accepted outstanding item.
**Requirements:** UI-06, UI-07, REG-01, REG-02 (Phase 11 coverage), INFRA-02, INFRA-03, INFRA-04 (frontmatter)
**Gap Closure:** Closes Phase 11 VERIFICATION.md gap; fixes INFRA-02/03/04 frontmatter; documents Phase 12 CI human step
**Depends on:** Phase 12

Plans:
- [x] 13-01-PLAN.md â Write Phase 11 VERIFICATION.md (evidence: all 5 plan SUMMARYs complete; UI/regression work confirmed by Phase 11 execution)
- [x] 13-02-PLAN.md â Fix 03-02-SUMMARY.md frontmatter: add INFRA-02, INFRA-03, INFRA-04 to requirements_completed
- [x] 13-03-PLAN.md â Document Phase 12 CI human verification as accepted outstanding item in VERIFICATION.md; update REQUIREMENTS.md traceability for Phase 13 closures (completed 2026-03-22)

### Phase 14: Alembic Migration & Seed Automation

**Goal:** Add a proper Alembic migration for the `final_funding_job` table (currently created via raw psycopg at module import) and automate or formally harden the staging admin seed step in the CI pipeline.
**Requirements:** (no formal v1.0 REQ-IDs â addresses MISS-03 and MISS-04 integration gaps)
**Gap Closure:** Closes MISS-04 (final_funding_job outside Alembic migration chain); closes MISS-03 (seed_staging_user.py not wired into deploy-test.yml)
**Depends on:** Phase 13

Plans:
- [ ] 14-01-PLAN.md â Add Alembic migration for final_funding_job table; remove raw CREATE TABLE from program_run_jobs.py (MISS-04)
- [ ] 14-02-PLAN.md â Add conditional seed step to deploy-test.yml (runs only when admin user does not exist) or document as formally accepted manual step with runbook (MISS-03)

### Phase 15: Integrate Updated Tagging Logic

**Goal:** Update tagging.py allocation ratios (p=0.325, s=0.5), extract allocation logic into a testable function, replace hardcoded 12-key SG dict with a dynamic loop over grouped_sum keys, fix KeyError guard with .get(), add unit tests, run regression tests and re-baseline golden files, and update developer reference docs.
**Requirements**: TAG-01, TAG-02, TAG-03, TAG-04, TAG-05, TAG-06
**Depends on:** Phase 14
**Plans:** 2/2 plans complete

Plans:
- [x] 15-01-PLAN.md â Extract allocate_sg function, update ratios (p=0.325, s=0.5), dynamic SG dict loop, KeyError guard, unit tests (TAG-01, TAG-02, TAG-03, TAG-04, TAG-05)
- [x] 15-02-PLAN.md â Run regression tests, re-baseline golden files, update developer reference docs and tests README (TAG-06)

### Phase 16: Linting

**Goal:** Establish working, enforced linting across the full project -- ESLint v9 flat config for frontend, fix the single ruff violation in backend, wire ESLint into CI as a blocking gate, and add husky + lint-staged pre-commit hooks for both frontend and backend lint enforcement.
**Requirements**: LINT-01, LINT-02, LINT-03, LINT-04
**Depends on:** Phase 15
**Plans:** 2/2 plans complete

Plans:
- [x] 16-01-PLAN.md â Create ESLint v9 flat config, fix ruff violation, add ESLint CI gate (LINT-01, LINT-02, LINT-03)
- [x] 16-02-PLAN.md â Install husky + lint-staged, configure pre-commit hooks for ESLint and ruff (LINT-04)

---

## Milestone v2.0: Real Estate Loan Dashboard POC

**Goal:** Build a comprehensive RE loan portfolio dashboard POC inside the existing React + FastAPI platform, powered by a seeded Postgres dataset â covering Executive Summary, Portfolio Composition, Credit Quality, Cash Flow, Origination Pipeline, and Market Context pages with global filtering, drill-down interactivity, export, and role-based view scoping.

**Phase Numbering:** Continues from v1.0. Phases 17â27.

### v2.0 Phases

- [x] **Phase 17: Data Foundation** - re_loans + re_loan_cashflows schema locked, Alembic migrations applied, seed script populates 500+ loans
- [ ] **Phase 18: Core API Layer** - All 11 /api/re/* endpoints return correct data with filter param support
- [x] **Phase 19: Filter Hook + TypeScript Foundation** - Filter sidebar, URL param sync, Zustand store, and TanStack Query keys wired before any chart component is built (completed 2026-04-09)
- [ ] **Phase 20: Executive Summary Page** - KPI cards populated from real seeded data; chart click-to-filter wired
- [ ] **Phase 21: Portfolio Composition Page** - Property type chart, geo map/bar fallback, loan size histogram, maturity profile, top-10 table, concentration limits; click-to-filter wired
- [ ] **Phase 22: Credit Quality Page** - LTV/DSCR histograms, watchlist table, delinquency waterfall, migration matrix, rate sensitivity; click-to-filter wired
- [ ] **Phase 23: Cash Flow & Performance Page** - P&I line chart, NOI trend, yield analysis, CPR, loss/recovery; click-to-filter wired
- [ ] **Phase 24: Origination Pipeline + Market Context** - Origination volume, payoffs, pipeline funnel, vintage analysis, market context stub panel; click-to-filter wired
- [ ] **Phase 25: Loan Detail Side-Panel** - Read-only loan detail slide-in panel, closes without page navigation
- [ ] **Phase 26: Export** - CSV download per filterable table, PDF dashboard snapshot
- [ ] **Phase 27: Role Scope Validation** - admin/analyst see full portfolio, sales_team sees only their book, enforced server-side

### v2.0 Phase Details

### Phase 17: Data Foundation
**Goal**: The re_loans and re_loan_cashflows tables exist with correct schema and are seeded with realistic CRE portfolio data, making the database the single source of truth for all subsequent development
**Depends on**: Phase 16
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. Developer runs `alembic upgrade head` with no errors and `SELECT COUNT(*) FROM re_loans` returns 500 or more rows
  2. All monetary columns in re_loans are NUMERIC(18,6) and all rate columns are NUMERIC(10,6) â confirmed via `\d re_loans` in psql
  3. `SELECT COUNT(*) FROM re_loan_cashflows` returns 12 records per loan (12 months of cashflow history for each seeded loan)
  4. Seeded data spans at least 5 property types, 20 states, 8 MSAs, and includes two distinct as_of_date snapshots
  5. `alembic upgrade head` runs to completion in CI without conflicts with the existing migration chain
**Plans**: 2 plans

Plans:
- [x] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [x] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)

### Phase 18: Core API Layer
**Goal**: All eleven /api/re/* endpoints are implemented, return correctly shaped JSON for their respective panels, and respect filter query params â verified via Swagger UI before any frontend work begins
**Depends on**: Phase 17
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09, API-10, API-11
**Success Criteria** (what must be TRUE):
  1. GET /api/re/kpis with no filter params returns total UPB, WAC, WAM, WA LTV, WA DSCR, active loan count, and delinquency buckets populated with non-zero values from seeded data
  2. GET /api/re/loans?property_type=multifamily returns only multifamily loans â confirming filter enforcement works across all endpoints
  3. GET /api/re/loans/{id} for a known seeded loan returns full detail including terms, collateral, and payment history summary
  4. A sales_team role JWT passed to any /api/re/* endpoint returns only loans matching that user's sales_team_id â not the full portfolio
  5. All endpoints respond under 500ms for the full seeded dataset with no active filters
**Plans**: 2 plans

Plans:
- [x] 18-01-PLAN.md — Foundation + aggregation endpoints: re_schemas.py, FilterParams, build_re_filters, KPIs, concentration, distributions, maturity-profile (API-01, API-02, API-03, API-04, API-11)
- [ ] 18-02-PLAN.md — Loans + remaining endpoints: paginated loans, loan detail, cashflow-performance, origination-pipeline, market-context, sensitivity, scoping tests, Swagger verification (API-05, API-06, API-07, API-08, API-09, API-10, API-11)


### Phase 19: Filter Hook + TypeScript Foundation
**Goal**: The global filter sidebar component, useReLoanFilters hook, Zustand store, and all TypeScript response types are in place so that every subsequent chart component can import them directly without retrofitting
**Depends on**: Phase 18
**Requirements**: FILTER-01, FILTER-02, FILTER-03, FILTER-04
**Success Criteria** (what must be TRUE):
  1. The filter sidebar renders on the /re-dashboard route with all documented controls: as-of date, property type, state/MSA, loan size range, risk rating, vintage, borrower, rate type
  2. Selecting a property type filter updates the browser URL query params and the Zustand store simultaneously without page reload
  3. Clicking "Clear all filters" resets all URL params and store state to defaults in a single action
  4. Changing any filter causes all TanStack Query keys to invalidate â confirmed by watching network requests in browser DevTools
**Plans**: 2 plans

Plans:
- [x] 19-01-PLAN.md — Install Zustand, TypeScript types, filter store, useReLoanFilters hook (FILTER-01, FILTER-02, FILTER-03, FILTER-04)
- [x] 19-02-PLAN.md — ReDashboard page, filter sidebar component, route + nav link wiring (FILTER-01, FILTER-02, FILTER-03, FILTER-04)
**UI hint**: yes

### Phase 20: Executive Summary Page
**Goal**: Users can open /re-dashboard and immediately see KPI cards populated with real portfolio data, with loading and no-data states handled, and clicking any metric initiates a filter
**Depends on**: Phase 19
**Requirements**: EXEC-01, EXEC-02, UX-01
**Success Criteria** (what must be TRUE):
  1. Visiting /re-dashboard shows KPI cards for total UPB, WAC, WAM, WA LTV, WA DSCR, active loan count, delinquency buckets, and portfolio yield â all populated with non-zero values from seeded data
  2. Applying a property type filter from the sidebar updates all KPI card values without page reload
  3. Filtering to a combination that returns zero matching loans shows a visible no-data state on each card â not zeros or blank space
  4. A KPI card in a loading state shows a visible loading indicator â not a flash of empty content
**Plans**: 1 plan

Plans:
- [ ] 20-01-PLAN.md — Install TanStack Query, KPI card component + formatting, wire ReDashboard grid with loading/no-data/click states (EXEC-01, EXEC-02, UX-01)
**UI hint**: yes

### Phase 21: Portfolio Composition Page
**Goal**: Users can see the full portfolio broken down by property type, geography, loan size, maturity, and top exposures â and can click any chart segment to filter the entire dashboard
**Depends on**: Phase 20
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, UX-01
**Success Criteria** (what must be TRUE):
  1. The Portfolio Composition page shows a pie/donut chart of loans by property type, a loan size histogram, and a maturity profile stacked bar chart â all populated from seeded data
  2. The geographic view shows either a US state choropleth or a ranked bar chart of top states by UPB â at least one is present and populated
  3. The top-10 exposures table shows the 10 largest loans by UPB with LTV, DSCR, property type, and location columns
  4. Clicking a pie slice or histogram bar applies that dimension as a filter â confirmed by URL param change and updated KPI cards
  5. Concentration limit indicators are visible and show proximity to policy limits for borrower, geography, and property type concentrations
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)
**UI hint**: yes

### Phase 22: Credit Quality Page
**Goal**: Users can assess portfolio credit risk through color-coded LTV and DSCR distributions, a watchlist of criticized loans, delinquency flow, risk rating migration, and rate sensitivity analysis
**Depends on**: Phase 21
**Requirements**: CREDIT-01, CREDIT-02, CREDIT-03, CREDIT-04, CREDIT-05, CREDIT-06, UX-01
**Success Criteria** (what must be TRUE):
  1. The Credit Quality page shows an LTV histogram with green bars below 65%, yellow bars 65â75%, and red bars above 75%, populated from seeded data
  2. The DSCR histogram shows color-banded bars (above 1.4x green, 1.0â1.4x yellow, below 1.0x red)
  3. The watchlist table shows criticized loans with risk rating and trend arrow columns, and is filterable by risk rating
  4. The delinquency waterfall displays loan flow from current to 30, 60, 90, and default buckets
  5. The risk rating migration matrix shows movement between current and prior period ratings using the two seeded as_of_date snapshots
  6. The interest rate sensitivity table shows portfolio impact under +/â100, 200, and 300 bps scenarios
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)
**UI hint**: yes

### Phase 23: Cash Flow & Performance Page
**Goal**: Users can evaluate portfolio cash flow health through actual vs projected P&I, NOI trends, yield analysis, CPR tracking, and loss/recovery history â all drawn from the re_loan_cashflows time-series data
**Depends on**: Phase 22
**Requirements**: CASHFLOW-01, CASHFLOW-02, CASHFLOW-03, CASHFLOW-04, CASHFLOW-05, UX-01
**Success Criteria** (what must be TRUE):
  1. The Cash Flow page shows a monthly P&I line chart with separate actual and projected series and a variance indicator, populated from re_loan_cashflows seeded data
  2. The NOI trend chart shows aggregated net operating income over the 12 seeded months
  3. The yield analysis section shows gross yield, net yield after losses, and spread to SOFR and Treasury
  4. The CPR trend line and loss/recovery tracking section (realized losses, recoveries, net loss rate) are both visible and populated
  5. Applying a filter from the sidebar updates all Cash Flow charts without page reload
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)
**UI hint**: yes

### Phase 24: Origination Pipeline + Market Context
**Goal**: Users can track new origination activity, portfolio growth, and pipeline stage progression, and can view stubbed market benchmark rates clearly labeled as indicative â completing all six dashboard sections
**Depends on**: Phase 23
**Requirements**: ORIGIN-01, ORIGIN-02, ORIGIN-03, ORIGIN-04, MARKET-01, MARKET-02, UX-01
**Success Criteria** (what must be TRUE):
  1. The Origination Pipeline page shows a monthly origination volume bar chart broken down by property type
  2. Net portfolio growth (originations minus payoffs) is visible as a trend or summary metric
  3. The pipeline funnel shows stage counts for underwriting, approved, closing, and funded
  4. The vintage analysis section shows performance metrics grouped by origination year
  5. The Market Context panel shows 10Y Treasury and SOFR stub values with trend shapes and cap rates/vacancy rates by property type, each clearly labeled as indicative with live-feed hook markers in the code
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)
**UI hint**: yes

### Phase 25: Loan Detail Side-Panel
**Goal**: Users can click any loan row in any table across the dashboard and see a read-only detail panel with full loan information, without leaving the current page
**Depends on**: Phase 24
**Requirements**: UX-02, UX-03
**Success Criteria** (what must be TRUE):
  1. Clicking a loan row in any table (top-10 exposures, watchlist, loan list) opens a slide-in side-panel showing full terms, collateral, borrower, payment history summary, and appraisal history
  2. The side-panel closes when the user clicks a close button or presses Escape â the underlying dashboard page remains in place with active filters unchanged
  3. Opening the side-panel does not trigger a page navigation or modify any URL query params
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)
**UI hint**: yes

### Phase 26: Export
**Goal**: Users can download the current filtered view of any table as CSV and can capture the current dashboard page as a labeled PDF snapshot
**Depends on**: Phase 25
**Requirements**: EXPORT-01, EXPORT-02
**Success Criteria** (what must be TRUE):
  1. Each filterable table (top-10 exposures, watchlist, loan list, pipeline) has a "Download CSV" button that downloads a CSV file containing exactly the rows and columns currently visible with active filters applied
  2. A "Download PDF" button on each dashboard page triggers a rasterized PDF download labeled "Dashboard Snapshot" containing all visible charts and tables from that page
  3. The PDF export does not show blank charts â all Recharts visualizations are fully rendered in the captured output
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)
**UI hint**: yes

### Phase 27: Role Scope Validation
**Goal**: Role-based view scoping is verified end-to-end â admin and analyst users see the full portfolio, sales_team users see only their assigned loans enforced at the API layer, and all authenticated users can navigate to the RE dashboard
**Depends on**: Phase 26
**Requirements**: ROLES-01, ROLES-02, ROLES-03
**Success Criteria** (what must be TRUE):
  1. Logging in as an admin or analyst user and visiting /re-dashboard shows KPI cards and charts for the full seeded portfolio
  2. Logging in as a sales_team user and visiting /re-dashboard shows only the loans assigned to that user's sales_team_id â confirmed by checking total UPB against the expected subset
  3. A sales_team user calling GET /api/re/loans directly (bypassing the UI) still receives only their scoped loans â server-side enforcement confirmed
  4. The RE dashboard nav link is visible in the sidebar for all authenticated users regardless of role
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — SQLAlchemy models + Alembic migrations for re_loans and re_loan_cashflows (DATA-01, DATA-02, DATA-04)
- [ ] 17-02-PLAN.md — Seed script + integration tests for realistic CRE portfolio data (DATA-03, DATA-04)

### v2.0 Progress

**Execution Order:**
Phases execute sequentially: 17 â 18 â 19 â 20 â 21 â 22 â 23 â 24 â 25 â 26 â 27

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. Data Foundation | 0/2 | Not started | - |
| 18. Core API Layer | 1/2 | In Progress|  |
| 19. Filter Hook + TypeScript Foundation | 2/2 | Complete   | 2026-04-09 |
| 20. Executive Summary Page | 0/TBD | Not started | - |
| 21. Portfolio Composition Page | 0/TBD | Not started | - |
| 22. Credit Quality Page | 0/TBD | Not started | - |
| 23. Cash Flow & Performance Page | 0/TBD | Not started | - |
| 24. Origination Pipeline + Market Context | 0/TBD | Not started | - |
| 25. Loan Detail Side-Panel | 0/TBD | Not started | - |
| 26. Export | 0/TBD | Not started | - |
| 27. Role Scope Validation | 0/TBD | Not started | - |
