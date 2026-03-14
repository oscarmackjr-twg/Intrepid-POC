# Roadmap: Intrepid Loan Purchase Platform

## Overview

This milestone (v1.0 — Local to Cloud) takes the existing codebase from nothing-runs to a fully deployed staging environment. The work progresses in strict dependency order: get the app running locally, containerize it, provision AWS infrastructure, wire up CI/CD, and verify the staging deployment end-to-end. Each phase builds directly on the previous and cannot proceed without it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Local Dev** - App runs locally with clean config, no hardcoded paths or Windows artifacts
- [x] **Phase 2: Docker Local Dev** - Single-command Docker Compose startup with auto-migrations and hot reload (completed 2026-03-06)
- [x] **Phase 3: AWS Infrastructure** - Terraform qa environment applies cleanly with secrets, ECR, and RDS live (completed 2026-03-06)
- [x] **Phase 4: CI/CD Pipeline** - GitHub Actions builds, pushes to ECR, and deploys to ECS with migrations (completed 2026-03-06)
- [ ] **Phase 5: Staging Deployment** - Live staging URL, Ops can log in and upload, environment banner visible

## Phase Details

### Phase 1: Local Dev
**Goal**: A developer can run the full stack locally — backend, frontend, database, and pipeline — using only documented env config with no hardcoded paths or Windows artifacts
**Depends on**: Nothing (first phase)
**Requirements**: LOCAL-01, LOCAL-02, LOCAL-03, LOCAL-04, LOCAL-05, LOCAL-06
**Success Criteria** (what must be TRUE):
  1. `uvicorn` starts the FastAPI backend and connects to local Postgres without error
  2. `npm run dev` starts the React frontend with hot reload at the expected local port
  3. `backend/.env` contains no hardcoded Windows paths and clearly separates local-storage vs S3 modes
  4. A new developer can onboard using `.env.example` alone — no undocumented env vars required
  5. Alembic migrations apply cleanly and the core pipeline completes an upload-to-cashflow run locally
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Clean backend/.env and create backend/.env.example (LOCAL-03, LOCAL-04)
- [ ] 01-02-PLAN.md — Synthetic sample data and initial Alembic migration (LOCAL-05, LOCAL-06)
- [ ] 01-03-PLAN.md — Makefile and DEVELOPMENT.md onboarding guide (LOCAL-01, LOCAL-02, LOCAL-04)
- [ ] 01-04-PLAN.md — Human smoke test: full stack end-to-end verification (all LOCAL requirements)

### Phase 2: Docker Local Dev
**Goal**: `docker compose up` starts the full local stack — app, Postgres, React dev server — with data persisting across restarts and migrations running automatically
**Depends on**: Phase 1
**Requirements**: DOCKER-01, DOCKER-02, DOCKER-03, DOCKER-04
**Success Criteria** (what must be TRUE):
  1. `docker compose -f deploy/docker-compose.yml up` starts all services with no manual steps after the first run
  2. The app is accessible at `localhost:8000` in the browser immediately after compose up
  3. The Postgres volume mount uses a relative or env-var path — no hardcoded Windows absolute paths in docker-compose.yml
  4. Alembic migrations run automatically on container start without manual intervention
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Overhaul docker-compose.yml: fix DB name, remove Windows path, add migrations entrypoint, add frontend service (DOCKER-01, DOCKER-02, DOCKER-04)
- [ ] 02-02-PLAN.md — Update vite.config.ts proxy target + human smoke test of full Docker stack (DOCKER-01, DOCKER-03)

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
- [x] 03-01-PLAN.md — Fix loan-engine naming remnants, create terraform.tfvars, destroy+apply infrastructure (INFRA-01)
- [x] 03-02-PLAN.md — Verify Secrets Manager entries, ECR push test, and RDS psql connectivity (INFRA-02, INFRA-03, INFRA-04)

### Phase 4: CI/CD Pipeline
**Goal**: A push to main triggers GitHub Actions to build the Docker image, push it to ECR, run Alembic migrations, and deploy the updated task to ECS — all without manual steps
**Depends on**: Phase 3
**Requirements**: CICD-01, CICD-02, CICD-03
**Success Criteria** (what must be TRUE):
  1. A push to main triggers the GitHub Actions workflow, which builds the image and pushes it to ECR successfully
  2. The workflow runs Alembic migrations against the staging RDS instance as part of the deploy sequence
  3. All required GitHub secrets and variables are documented (in README or CICD runbook) and confirmed configured in the repo
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — Terraform OIDC IAM role, subnet/SG outputs, terraform apply + GitHub repo variable setup (CICD-01)
- [ ] 04-02-PLAN.md — Rewrite GitHub Actions workflow: OIDC auth, correct ECR/ECS names, migration step, stability wait (CICD-01, CICD-02)
- [ ] 04-03-PLAN.md — Create docs/CICD.md runbook: secrets/variables inventory, OIDC setup steps, deploy sequence (CICD-03)

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
- [ ] 05-01-PLAN.md — StagingBanner component (Layout + Login), VITE_APP_ENV build arg in Dockerfile and GitHub Actions (STAGE-03)
- [ ] 05-02-PLAN.md — Seed script for staging admin user, First Deploy Checklist in CICD.md (STAGE-02)
- [ ] 05-03-PLAN.md — Trigger deploy, run seed script, human verification of all three STAGE requirements (STAGE-01, STAGE-02, STAGE-03)

## Progress

**Execution Order:**
Phases execute sequentially: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Local Dev | 4/4 | Complete | 2026-03-06 |
| 2. Docker Local Dev | 2/2 | Complete   | 2026-03-06 |
| 3. AWS Infrastructure | 2/2 | Complete | 2026-03-06 |
| 4. CI/CD Pipeline | 3/3 | Complete   | 2026-03-06 |
| 5. Staging Deployment | 2/3 | In Progress|  |
| 6. Final Funding & Cashflow | 3/5 | In Progress|  |
| 7. Application Hardening | 7/7 | Complete   | 2026-03-11 |
| 8. Fix Staging Auth & Smoke Test | 0/2 | Pending | |
| 9. Write Missing Verification Records | 0/3 | Pending | |
| 10. Revamp User Interface | 3/3 | Complete    | 2026-03-13 |
| 11. Refing UI for Regression Testing | 5/5 | Complete   | 2026-03-14 |

### Phase 6: Final Funding & Cashflow Integration

**Goal:** Replace stub Final Funding SG and CIBC scripts with real workbook implementations, add async job tracking so Ops can see RUNNING/COMPLETED/FAILED status in the UI, and bridge cashflow outputs automatically into Final Funding inputs.
**Requirements**: FF-01, FF-02, FF-03, FF-04, FF-05, FF-06, FF-07, FF-08, FF-09
**Depends on:** Phase 5
**Plans:** 3/5 plans executed

Plans:
- [ ] 06-01-PLAN.md — Test scaffolds (Wave 0): test_final_funding_jobs.py and test_final_funding_runner.py (FF-03..FF-09)
- [ ] 06-02-PLAN.md — Real script replacement: copy and patch SG + CIBC scripts from legacy repo (FF-01, FF-02)
- [ ] 06-03-PLAN.md — Backend job tracking: final_funding_job table, background thread runner, GET/POST API endpoints, cashflow bridge (FF-03..FF-09)
- [ ] 06-04-PLAN.md — Frontend polling: replace alert() in ProgramRuns.tsx with job-id status display (FF-03, FF-06)
- [ ] 06-05-PLAN.md — Full test suite verification + human smoke test checkpoint (FF-01..FF-09)

### Phase 7: Application Hardening

**Goal:** Harden the deployed application across seven areas: AWS networking/TLS (RDS to private subnets, ALB HTTPS), default secrets and bootstrap passwords, frontend auth token storage (localStorage → HttpOnly cookies), file/error endpoint information leakage, CI security and quality gates, durable audit logging, and repository hygiene.
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05, HARD-06, HARD-07
**Depends on:** Phase 6
**Plans:** 7/7 plans complete

Plans:
- [ ] 07-01-PLAN.md — Wave 0 test scaffolds: failing tests for HARD-02, HARD-03, HARD-04, HARD-06 (HARD-02, HARD-03, HARD-04, HARD-06)
- [ ] 07-02-PLAN.md — Repository hygiene + Terraform networking/TLS (HARD-07, HARD-01)
- [ ] 07-03-PLAN.md — Default secrets guard, seed script one-time passwords, password policy validator (HARD-02)
- [ ] 07-04-PLAN.md — File/error leakage sanitization + AuditLog DB model and migration (HARD-04, HARD-06)
- [ ] 07-05-PLAN.md — HttpOnly cookie auth, rate limiting, CSP header, frontend localStorage removal (HARD-03)
- [ ] 07-06-PLAN.md — CI security-quality-gate job blocking deploy + human checkpoint (HARD-05)
- [ ] 07-07-PLAN.md — Wire db session to login audit calls + README credential cleanup (HARD-06, HARD-02)

### Phase 8: Fix Staging Auth & Complete Smoke Test

**Goal:** Unblock staging by adding `LOCAL_DEV_MODE=true` to the ECS task definition (fixing Secure cookie failure over HTTP ALB), apply the Terraform change, and run the Phase 05-03 smoke test to formally verify all three STAGE requirements end-to-end.
**Requirements:** STAGE-01, STAGE-02, STAGE-03
**Gap Closure:** Closes MISS-02 (High — Secure cookie breaks HTTP staging), MISS-01 (Medium — docker-compose.yml startup guard fragility), and satisfies STAGE-01 (unsatisfied) + formally verifies STAGE-02/STAGE-03 (partial)
**Depends on:** Phase 7

Plans:
- [ ] 08-01-PLAN.md — Add LOCAL_DEV_MODE=true to ecs.tf + docker-compose.yml; terraform plan + apply (STAGE-01, MISS-01, MISS-02)
- [ ] 08-02-PLAN.md — Trigger ECS deploy, run 05-03 smoke test, write Phase 5 VERIFICATION.md (STAGE-01, STAGE-02, STAGE-03)

### Phase 9: Write Missing Verification Records

**Goal:** Produce the VERIFICATION.md files absent from Phases 1 and 6, formalising evidence already confirmed by the integration checker and plan SUMMARYs. No code changes — documentation gap only.
**Requirements:** LOCAL-01, LOCAL-02, LOCAL-03, LOCAL-04, LOCAL-05, LOCAL-06
**Gap Closure:** Closes the verification record gap for LOCAL-01–06 (Phase 1) and the Final Funding integration (Phase 6)
**Depends on:** Phase 8

Plans:
- [ ] 09-01-PLAN.md — Write Phase 1 VERIFICATION.md (evidence: integration checker, SUMMARYs, MEMORY.md sample run 9 loans E2E) (LOCAL-01–LOCAL-06)
- [ ] 09-02-PLAN.md — Write Phase 6 VERIFICATION.md (evidence: 4 plan SUMMARYs, API confirmed working) (FF-01–FF-09)
- [ ] 09-03-PLAN.md — Update REQUIREMENTS.md traceability to reflect gap closure and mark all LOCAL/STAGE reqs Complete

### Phase 10: Revamp User Interface - Phase 10

**Goal:** Redesign the ops dashboard look, feel, and navigation to align with TWG Global brand guidelines — replace horizontal nav with a fixed left sidebar, apply navy brand color throughout, rename app to "Intrepid Loan Platform", add TWG logo, and restructure nav with SG/CIBC group labels. Visual and structural changes only; no new data features.
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Depends on:** Phase 9
**Plans:** 3/3 plans complete

Plans:
- [ ] 10-01-PLAN.md — Brand globals (index.html title, index.css Gotham font + CSS vars, logo asset copy) + Login page rebrand (UI-01, UI-02)
- [ ] 10-02-PLAN.md — Layout.tsx full sidebar rewrite: TWG navy sidebar, logo, SG/CIBC nav groups, admin gate, user footer (UI-03, UI-04, UI-05)
- [ ] 10-03-PLAN.md — Human visual verification of all pages: sidebar, branding, active states, StagingBanner (UI-01–UI-05)

### Phase 11: Refing UI for Regression Testing

**Goal:** Fix nav active-state bugs from Phase 10, apply spacing/typography polish and structural layout improvements to Program Runs and File Manager, create a manual regression test checklist (docs/REGRESSION_TEST.md), and build a data regression script that runs the pipeline CLI against local test cases and diffs outputs byte-for-byte.
**Requirements**: UI-06, UI-07, REG-01, REG-02
**Depends on:** Phase 10
**Plans:** 5/5 plans complete

Plans:
- [ ] 11-01-PLAN.md — Fix nav active-state bugs in Layout.tsx + typography polish in index.css (UI-06)
- [ ] 11-02-PLAN.md — Layout restructure: max-w-5xl + section reordering for ProgramRuns.tsx and FileManager.tsx (UI-07)
- [ ] 11-03-PLAN.md — Create docs/REGRESSION_TEST.md manual checklist covering all pages and core ops workflow (REG-01)
- [ ] 11-04-PLAN.md — Create backend/scripts/regression_test.py data regression harness (REG-02)
- [ ] 11-05-PLAN.md — Claude dry-run of REGRESSION_TEST.md + human visual verification checkpoint (UI-06, UI-07, REG-01, REG-02)
