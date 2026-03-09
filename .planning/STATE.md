---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Completed 06-final-funding-cashflow-integration/06-01-PLAN.md — 9 FF test stubs scaffolded (Wave 0 RED state)
last_updated: "2026-03-09T13:49:20.560Z"
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 19
  completed_plans: 14
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Completed 05-staging-deployment/05-01-PLAN.md — StagingBanner + Dockerfile/CI build-arg wiring complete
last_updated: "2026-03-06T21:02:42.136Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 14
  completed_plans: 13
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Completed 03-aws-infrastructure/03-02-PLAN.md — Phase 3 complete, all INFRA requirements verified
last_updated: "2026-03-06T16:27:04.501Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
  percent: 100
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: "Completed 03-aws-infrastructure/03-01-PLAN.md"
last_updated: "2026-03-06T04:45:00.000Z"
progress:
  [██████████] 100%
  completed_phases: 2
  total_plans: 8
  completed_plans: 7
  percent: 100
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Completed 02-docker-local-dev/02-01-PLAN.md
last_updated: "2026-03-06T02:31:55.651Z"
progress:
  [██████████] 100%
  completed_phases: 1
  total_plans: 6
  completed_plans: 5
---

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in-progress
stopped_at: Completed Phase 1 — Local Dev (all 4 plans, all 6 LOCAL requirements verified)
last_updated: "2026-03-06T01:30:00Z"
last_activity: 2026-03-06 — Phase 1 complete (human smoke test approved, pipeline runs end-to-end)
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-05)

**Core value:** Ops can take a loan tape from email to executed wire instructions in one controlled, visible process — replacing ad hoc scripts
**Current focus:** Phase 4 — CI/CD

## Current Position

Phase: 3 of 5 (AWS Infrastructure) — COMPLETE
Plan: 2 of 2 complete in current phase
Status: Phase 3 complete — all four INFRA requirements verified (Secrets Manager readable, ECR push confirmed, RDS psql returning PostgreSQL 16.8)

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Phase 1 total: 4 plans

**By Phase:**

| Phase | Plans | Status |
|-------|-------|--------|
| 01-local-dev | 4/4 | Complete |
| 02-docker | TBD | Not started |
| 03-infra | 1/2 | In Progress |
| 04-cicd | TBD | Not started |
| 05-staging | TBD | Not started |
| Phase 02-docker-local-dev P01 | 2 | 3 tasks | 1 files |
| Phase 02-docker-local-dev P02 | 10 | 2 tasks | 1 files |
| Phase 03-aws-infrastructure P02 | 158min | 2 tasks | 0 files |
| Phase 04-cicd-pipeline P03 | 1 | 1 tasks | 1 files |
| Phase 04-cicd-pipeline P02 | 1min | 1 tasks | 1 files |
| Phase 05-staging-deployment P02 | 15 | 2 tasks | 2 files |
| Phase 05-staging-deployment P01 | 2 | 2 tasks | 5 files |
| Phase 06-final-funding-cashflow-integration P01 | 15 | 2 tasks | 3 files |

## Accumulated Context

### Roadmap Evolution

- Phase 6 added: Final Funding & Cashflow Integration

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stack confirmed: React 19 + Python FastAPI (no Node.js layer)
- Single container image (FastAPI serves React static files in production) — simplifies ECS deployment
- Decimal audit, wire instructions, counterparty tagging deferred to v1.1
- [01-01] STORAGE_TYPE=local set as active default in backend/.env; all S3 vars commented out
- [01-01] DEV_INPUT kept commented in .env (users set own paths); active in .env.example pointing at sample data
- [01-01] DATABASE_URL reset to generic local credentials; real password removed
- [01-02] Root .gitignore requires negation rules for backend/data/sample/ — git cannot re-include files in an excluded parent directory from child .gitignore
- [01-02] backend/.gitignore data/ replaced with specific subdirs (data/inputs/, data/outputs/, data/archive/) to allow sample/ exception
- [01-02] Postgres user password unknown on this machine; migration generated via pg_hba.conf trust auth (temporarily); restored to scram-sha-256 after; user must update DATABASE_URL in .env
- [01-04] Pipeline had 4 bugs fixed during smoke test (promo_term, Purchase Price, int overflow on NaN, ChainedAssignmentError)
- [Phase 02-docker-local-dev]: Volume paths relative to deploy/ (../backend, ../frontend) — eliminates Windows path blocker DOCKER-02
- [Phase 02-docker-local-dev]: exec uvicorn pattern ensures PID 1 signal handling; alembic upgrade head runs inline before start
- [Phase 02-docker-local-dev]: First `docker compose up` after DB name change requires `down -v` to wipe stale pgdata volume (Postgres ignores POSTGRES_DB if data dir already exists)
- [Phase 02-docker-local-dev]: App image must be rebuilt after requirements.txt changes — use `up --build app`; cached image pre-dates psycopg[binary] addition
- [Phase 02-docker-local-dev]: VITE_API_TARGET nullish coalescing (??): frontend proxy target reads env var in Docker, falls back to localhost:8000 for host-native dev
- [Phase 03-aws-infrastructure]: deploy-qa.ps1 ECS update-service uses terraform output -raw instead of hardcoded cluster/service names — handles any app_name change automatically
- [Phase 03-aws-infrastructure]: RDS psql connection requires AWS global CA bundle (sslmode=verify-ca + sslrootcert) and % password chars URL-encoded as %25
- [Phase 03-aws-infrastructure]: Temporary SG ingress pattern for RDS testing: authorize /32 from local IP, test, revoke immediately — keeps RDS not publicly reachable
- [Phase 04-cicd-pipeline]: docs/CICD.md created as self-contained runbook — any developer can configure CI/CD from scratch using only this document
- [Phase 04-cicd-pipeline]: Variables table sourced from Terraform outputs (not hardcoded) — keeps IDs in sync with infrastructure
- [Phase 04-cicd-pipeline]: GitHub repo owner confirmed as oscarmackjr-twg (from git remote -v); OIDC provider created as new resource; trust policy uses StringEquals locked to refs/heads/main
- [Phase 04-cicd-pipeline]: IAM role github-actions-intrepid-poc-qa applied via terraform apply — OIDC auth foundation complete, GitHub repo variables AWS_ROLE_ARN, ECS_SUBNET_IDS, ECS_SECURITY_GROUP configured
- [Phase 04-cicd-pipeline]: deploy-test.yml rewritten: OIDC auth, migration gate (run-task + exit code check), services-stable wait, all resource names corrected to intrepid-poc-qa
- [Phase 05-staging-deployment]: Seed script uses explicit upsert (query-then-update-or-insert) not SQLAlchemy merge() for staging admin — simpler and predictable for one-off ops use
- [Phase 05-staging-deployment]: ECS one-off task pattern documented in CICD.md First Deploy Checklist with PowerShell syntax — covers seed script execution, wait, exit code check, and Ops login verification
- [Phase 05-staging-deployment]: StagingBanner renders when VITE_APP_ENV \!== 'production' — undefined (no build arg) also shows banner, safe default for local dev
- [Phase 05-staging-deployment]: VITE_APP_ENV baked into Docker image at build time via ARG/ENV — no runtime secret injection needed, Vite inlines value at npm run build
- [Phase 06-final-funding-cashflow-integration]: pytestmark skipif at module level: entire jobs test file skips when api.program_run_jobs missing
- [Phase 06-final-funding-cashflow-integration]: Wave 0 scaffold: 9 test stubs created before any FF implementation, gating Plans 02-04

### Pending Todos

None.

### Blockers/Concerns

- docker-compose.yml volume mount is hardcoded Windows path — blocks cross-platform Docker use (Phase 2, primary work item)
- deploy-test.yml GitHub Actions workflow needs migration step and secret config added (Phase 4)
- Existing Terraform in deploy/terraform/qa/ needs audit before applying (Phase 3)
- Postgres user password on this machine is not "postgres" — user must update backend/.env DATABASE_URL with actual password for alembic commands

## Session Continuity

Last session: 2026-03-09T13:49:10.043Z
Stopped at: Completed 06-final-funding-cashflow-integration/06-01-PLAN.md — 9 FF test stubs scaffolded (Wave 0 RED state)
Resume file: None
