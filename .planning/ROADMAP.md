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
| 7. Application Hardening | 2/6 | In Progress|  |

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
**Plans:** 2/6 plans executed

Plans:
- [ ] 07-01-PLAN.md — Wave 0 test scaffolds: failing tests for HARD-02, HARD-03, HARD-04, HARD-06 (HARD-02, HARD-03, HARD-04, HARD-06)
- [ ] 07-02-PLAN.md — Repository hygiene + Terraform networking/TLS (HARD-07, HARD-01)
- [ ] 07-03-PLAN.md — Default secrets guard, seed script one-time passwords, password policy validator (HARD-02)
- [ ] 07-04-PLAN.md — File/error leakage sanitization + AuditLog DB model and migration (HARD-04, HARD-06)
- [ ] 07-05-PLAN.md — HttpOnly cookie auth, rate limiting, CSP header, frontend localStorage removal (HARD-03)
- [ ] 07-06-PLAN.md — CI security-quality-gate job blocking deploy + human checkpoint (HARD-05)
