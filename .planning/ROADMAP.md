# Roadmap: Intrepid Loan Purchase Platform

## Overview

This milestone (v1.0 — Local to Cloud) takes the existing codebase from nothing-runs to a fully deployed staging environment. The work progresses in strict dependency order: get the app running locally, containerize it, provision AWS infrastructure, wire up CI/CD, and verify the staging deployment end-to-end. Each phase builds directly on the previous and cannot proceed without it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Local Dev** - App runs locally with clean config, no hardcoded paths or Windows artifacts
- [ ] **Phase 2: Docker Local Dev** - Single-command Docker Compose startup with auto-migrations and hot reload
- [ ] **Phase 3: AWS Infrastructure** - Terraform qa environment applies cleanly with secrets, ECR, and RDS live
- [ ] **Phase 4: CI/CD Pipeline** - GitHub Actions builds, pushes to ECR, and deploys to ECS with migrations
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
**Plans**: TBD

### Phase 3: AWS Infrastructure
**Goal**: Terraform qa environment applies cleanly, leaving a provisioned ECR repository, running RDS instance, and Secrets Manager entries that ECS tasks can consume
**Depends on**: Phase 2
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. `terraform init && terraform apply` completes with no errors in the qa workspace
  2. Secrets Manager contains entries for `DATABASE_URL` and `SECRET_KEY` readable by the ECS task role
  3. ECR repository is provisioned and a test `docker push` to it succeeds with valid AWS credentials
  4. RDS Postgres instance is running and reachable on its private endpoint from within the VPC
**Plans**: TBD

### Phase 4: CI/CD Pipeline
**Goal**: A push to main triggers GitHub Actions to build the Docker image, push it to ECR, run Alembic migrations, and deploy the updated task to ECS — all without manual steps
**Depends on**: Phase 3
**Requirements**: CICD-01, CICD-02, CICD-03
**Success Criteria** (what must be TRUE):
  1. A push to main triggers the GitHub Actions workflow, which builds the image and pushes it to ECR successfully
  2. The workflow runs Alembic migrations against the staging RDS instance as part of the deploy sequence
  3. All required GitHub secrets and variables are documented (in README or CICD runbook) and confirmed configured in the repo
**Plans**: TBD

### Phase 5: Staging Deployment
**Goal**: The staging environment is live at a real URL, Ops can log in and upload a file, and the environment is clearly identified as non-production
**Depends on**: Phase 4
**Requirements**: STAGE-01, STAGE-02, STAGE-03
**Success Criteria** (what must be TRUE):
  1. The staging URL loads the application in a browser after a CI/CD deploy completes
  2. An Ops team member can log in, upload a loan spreadsheet, and see it accepted by the application
  3. A clearly visible, unmissable banner identifies the environment as staging (not production) on every page
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute sequentially: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Local Dev | 2/4 | In Progress|  |
| 2. Docker Local Dev | 0/TBD | Not started | - |
| 3. AWS Infrastructure | 0/TBD | Not started | - |
| 4. CI/CD Pipeline | 0/TBD | Not started | - |
| 5. Staging Deployment | 0/TBD | Not started | - |
