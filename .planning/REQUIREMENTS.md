# Requirements: Intrepid Loan Purchase Platform

**Defined:** 2026-03-05
**Milestone:** v1.0 — Local to Cloud
**Core Value:** Ops can take a loan tape from email to executed wire instructions in one controlled, visible process — replacing ad hoc scripts.

## v1.0 Requirements

Requirements for local dev → Docker → AWS staging deployment.

### Local Dev

- [x] **LOCAL-01**: Developer can run backend locally with `uvicorn` against local Postgres
- [x] **LOCAL-02**: React frontend runs locally with `npm run dev` (hot reload)
- [x] **LOCAL-03**: `backend/.env` config separates local vs S3 mode cleanly (no hardcoded Windows paths)
- [x] **LOCAL-04**: `.env.example` template exists so any developer can onboard
- [x] **LOCAL-05**: Alembic migrations run cleanly against local Postgres
- [x] **LOCAL-06**: Core loan pipeline executes end-to-end locally (upload → suitability → cashflow)

### Docker

- [ ] **DOCKER-01**: `docker compose -f deploy/docker-compose.yml up` starts app + Postgres successfully
- [ ] **DOCKER-02**: Docker Compose volume mount is configurable (not hardcoded Windows path)
- [ ] **DOCKER-03**: App is accessible at `localhost:8000` after compose up
- [ ] **DOCKER-04**: Migrations run automatically on container start

### AWS Infrastructure

- [ ] **INFRA-01**: Terraform `qa` environment applies cleanly (`terraform init && apply`)
- [ ] **INFRA-02**: Secrets Manager entries exist for `DATABASE_URL` and `SECRET_KEY`
- [ ] **INFRA-03**: ECR repository is provisioned and accessible
- [ ] **INFRA-04**: RDS Postgres instance is running and reachable from ECS tasks

### CI/CD

- [ ] **CICD-01**: GitHub Actions workflow builds Docker image and pushes to ECR on push to main
- [ ] **CICD-02**: Workflow runs Alembic migrations as part of deploy
- [ ] **CICD-03**: Required GitHub secrets/variables are documented and configured

### Staging

- [ ] **STAGE-01**: Staging URL is accessible and app loads after CI/CD deploy
- [ ] **STAGE-02**: Ops team can log in and upload a file in staging
- [ ] **STAGE-03**: Staging environment has an unmissable banner (not production)

## v2.0 Requirements (Deferred)

### Business Workflow Completion

- **BIZ-01**: Wire instruction PDF generation (WeasyPrint + Jinja2)
- **BIZ-02**: PDF delivery to counterparties via AWS SES
- **BIZ-03**: Counterparty tagging integration (real script, not stub)
- **BIZ-04**: In-UI PDF preview with mandatory review gate
- **BIZ-05**: Per-(run_id, counterparty) email delivery state tracking

### Foundation Hardening

- **HARD-01**: Decimal precision audit and replacement throughout cashflow engine
- **HARD-02**: Idempotent processing runs (INSERT ... ON CONFLICT DO NOTHING)
- **HARD-03**: Complete audit trail (user ID per step, git SHA per run)
- **HARD-04**: Pre-flight file validation before run starts
- **HARD-05**: Column validation on upload (surface schema mismatches immediately)

### Pipeline Visibility

- **VIS-01**: Structured real-time log panel on run detail page
- **VIS-02**: Exception drill-down with loan attributes (FICO, DTI, balance)
- **VIS-03**: IRR target displayed explicitly on run start form
- **VIS-04**: Cashflow progress messages (loan N of M)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated email ingestion | Manual upload is a deliberate control point |
| Banking API wire execution | PDF + email is the established counterparty process |
| Counterparty portal / external access | Internal ops tool only |
| Mobile-optimized UI | Desktop only; ops team works at desktops |
| Automated run scheduling | Manual trigger is intentional safety mechanism |
| ML-based suitability scoring | Rules engine is counterparty-contractual |
| Multi-currency | All loans USD only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LOCAL-01 | Phase 1 | Complete |
| LOCAL-02 | Phase 1 | Complete |
| LOCAL-03 | Phase 1 | Complete — 01-01 |
| LOCAL-04 | Phase 1 | Complete — 01-01 |
| LOCAL-05 | Phase 1 | Complete |
| LOCAL-06 | Phase 1 | Complete |
| DOCKER-01 | Phase 2 | Pending |
| DOCKER-02 | Phase 2 | Pending |
| DOCKER-03 | Phase 2 | Pending |
| DOCKER-04 | Phase 2 | Pending |
| INFRA-01 | Phase 3 | Pending |
| INFRA-02 | Phase 3 | Pending |
| INFRA-03 | Phase 3 | Pending |
| INFRA-04 | Phase 3 | Pending |
| CICD-01 | Phase 4 | Pending |
| CICD-02 | Phase 4 | Pending |
| CICD-03 | Phase 4 | Pending |
| STAGE-01 | Phase 5 | Pending |
| STAGE-02 | Phase 5 | Pending |
| STAGE-03 | Phase 5 | Pending |

**Coverage:**
- v1.0 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after initial definition*
