# Intrepid POC Migration Plan (cursor_loan_engine + riskmvp)

## 1. Objectives
- Merge both applications into a single repository at `C:\Users\omack\Intrepid\pythonFramework\intrepid-poc`.
- Preserve all `cursor_loan_engine` frontend screens.
- Add only the `riskmvp` cashflow frontend screen and required backend support.
- Keep as much backend functionality as possible without destabilizing current loan-engine behavior.
- Standardize local + AWS deployment on a new database name/instance: `intrepid-poc`.
- Prepare structure for future platform expansion (including Azure).

## 2. Current State Summary
- `cursor_loan_engine`:
  - Monolithic FastAPI backend in `backend/` with auth, runs, files, holidays, scheduler.
  - React frontend in `frontend/` (login, dashboard, runs, exceptions, files, program-runs, holidays).
  - Terraform under `deploy/terraform/qa` for a simpler single-service ECS model and single Postgres RDS instance.
- `riskmvp`:
  - Microservice-oriented FastAPI code under `services/` plus compute workers under `compute/`.
  - React frontend in `frontend/` with multiple pages; only `/cashflow` is required for this merge.
  - Cashflow backend endpoints in `services/data_ingestion_svc/app/routes/cashflow.py`.
  - Terraform under `terraform/` for multi-service ECS, Aurora + RDS Proxy, and multi-image ECR setup.

## 3. Recommended Integration Strategy
- Use `cursor_loan_engine` as the base application skeleton (frontend shell, auth model, primary API).
- Import `riskmvp` cashflow capability as a bounded module inside the base backend.
- Do not merge full `riskmvp` frontend shell/routes now; port only cashflow UI + API client functions.
- Keep one DB (`intrepid-poc`) with clearly namespaced schema objects (table names prefixed where needed).
- Move toward modular infra in phases:
  - Phase 1: run merged app in current single-service style (fastest path).
  - Phase 2: extract high-load jobs (cashflow workers) into dedicated ECS task/service.
  - Phase 3: abstract cloud-specific infra for AWS/Azure dual-target.

## 4. Target Repository Layout
- `frontend/` (from `cursor_loan_engine` as primary UI)
  - keep all existing screens
  - add `pages/CashFlow.tsx` (ported from riskmvp `CashFlowPage.tsx`)
  - add/update API client methods for cashflow endpoints
- `backend/` (from `cursor_loan_engine` as primary API host)
  - `api/routes.py` retains existing loan-engine routes
  - new module:
    - `api/cashflow_routes.py` (port from `riskmvp` cashflow endpoints)
    - `cashflow/` (ported compute/helpers needed for current_assets/sg/cibc jobs)
  - storage integration:
    - align cashflow input/output paths with existing S3/local storage abstraction
  - migrations:
    - add migration for `cashflow_job` table and any supporting objects
- `infra/terraform/aws/` (new normalized location)
  - start from `cursor_loan_engine` terraform
  - selectively port cashflow worker/task patterns from `riskmvp`
- `docs/`
  - migration decisions and runbooks

## 5. Detailed Migration Phases

## Phase 0 - Inventory and Baseline (1-2 days)
- Freeze both source repos at known commit SHAs.
- Export API surface inventory:
  - loan-engine existing routes
  - riskmvp cashflow routes only
- Capture dependency lockfiles and Python package versions.
- Record baseline test results for both repos.

## Phase 1 - Repository Bootstrapping (1 day)
- Initialize `intrepid-poc` git repo.
- Import `cursor_loan_engine` code as initial baseline commit.
- Import selected `riskmvp` code via copy/cherry-pick:
  - cashflow route module
  - required compute modules
  - minimal shared utility modules required by cashflow path
- Keep commit history traceability with clear commit messages referencing source SHAs.

## Phase 2 - Backend Merge (3-5 days)
- Add cashflow API router into monolithic FastAPI app.
- Port required dependencies from `riskmvp` into a consolidated Python dependency file.
- Resolve DB driver mismatch:
  - base app uses `psycopg2-binary` + SQLAlchemy
  - riskmvp cashflow path uses `psycopg` v3
  - recommendation: standardize on one DB access path for merged code (prefer SQLAlchemy session for app tables, isolate raw SQL where required).
- Add migrations for cashflow tables.
- Normalize config/env names (single `.env` contract):
  - `DATABASE_URL` -> points to `intrepid-poc`
  - `CASHFLOW_S3_BUCKET`
  - `CASHFLOW_S3_PREFIX`
  - worker mode flags for local/AWS execution

## Phase 3 - Frontend Merge (2-3 days)
- Keep `cursor_loan_engine` router and layout as primary shell.
- Add a `Cash Flow` navigation item and route in loan-engine frontend.
- Port `riskmvp` `CashFlowPage.tsx` into loan-engine style system:
  - unify CSS classes/tokens to current app design
  - map API base paths to merged backend
- Add only API client methods needed for cashflow screen.
- Remove/avoid importing other riskmvp pages/components.

## Phase 4 - Data and Schema Consolidation (2-3 days)
- Provision new local DB and AWS DB with name `intrepid-poc`.
- Apply existing loan-engine migrations first.
- Apply new cashflow migration(s).
- Seed required reference/config data for login + cashflow defaults.
- Validate no table-name collisions; if collisions exist, rename with migration.

## Phase 5 - Deployment Merge (3-5 days)
- Build one Terraform root for AWS deployment in this repo.
- Start from loan-engine deploy path, then add:
  - cashflow execution config env vars
  - optional dedicated cashflow worker task definition/service
  - least-privilege S3 permissions for `inputs/` + `outputs/`
- Keep first cut simple (single app service + optional worker) before reintroducing full microservice topology.

## Phase 6 - Validation and Cutover (2-4 days)
- Local acceptance:
  - all original loan-engine screens function unchanged
  - cashflow screen works end-to-end (upload, run, status, download)
- AWS acceptance:
  - health endpoints green
  - DB migrations apply cleanly to `intrepid-poc`
  - run smoke test script post-deploy
- Cutover:
  - release candidate tag
  - rollback plan to previous independent deployments

## 6. Key Technical Decisions
- Frontend ownership: `cursor_loan_engine` UI architecture remains canonical.
- Backend ownership: monolithic API host remains canonical; risk cashflow is integrated as module.
- Database naming:
  - local DB name: `intrepid-poc`
  - AWS DB name: `intrepid-poc`
- Terraform direction:
  - immediate: AWS-focused merged stack
  - near-term: refactor into cloud-agnostic modules (`network`, `database`, `compute`, `storage`) to enable Azure parity.

## 7. Risks and Mitigations
- Dependency/version conflicts (React 19 vs React 18, Tailwind v4 vs v3, Vite 7 vs 5).
  - Mitigation: keep loan-engine frontend toolchain; adapt cashflow page to it.
- DB driver incompatibility (`psycopg2` vs `psycopg`).
  - Mitigation: avoid dual runtime drivers where possible; isolate one driver for specialized path if needed.
- Route/auth mismatch between apps.
  - Mitigation: enforce loan-engine auth flow; secure cashflow endpoints with same auth middleware.
- Terraform complexity creep.
  - Mitigation: stage infra merge; do not import full riskmvp infra on day 1.

## 8. Definition of Done (MVP Merge)
- Single repo in `intrepid-poc` builds locally.
- Single local DB named `intrepid-poc` supports all required features.
- Loan-engine frontend screens all available and unchanged in behavior.
- Cashflow screen available and functional.
- AWS terraform deploy succeeds for merged app using `intrepid-poc` DB.
- CI pipeline runs tests/builds for merged backend and frontend.

## 9. Information Needed Before Execution
- Canonical source of truth for backend auth/users:
  - keep `cursor_loan_engine` auth exactly as-is? (recommended)
- Cashflow execution in AWS:
  - run in-process in app task initially, or dedicated worker task from day 1? (recommended: dedicated worker if workloads are heavy)
- S3 bucket strategy:
  - reuse existing bucket naming or create new `intrepid-poc-*` bucket(s)?
- Preferred branch strategy for merge:
  - long-lived `merge/intrepid-poc` integration branch vs short-lived feature branches.
- CI/CD target:
  - keep current AWS-only pipeline initially, then add Azure pipeline later.

## 10. Suggested First Implementation Sprint
- Day 1:
  - bootstrap repo from loan-engine and set DB/env contract to `intrepid-poc`
- Day 2:
  - integrate backend cashflow routes + migrations
- Day 3:
  - add cashflow frontend page into loan-engine UI
- Day 4:
  - local end-to-end testing + bug fixes
- Day 5:
  - terraform merge for AWS + deploy smoke test
