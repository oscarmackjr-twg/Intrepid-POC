# Phase 8: Fix Staging Auth & Complete Smoke Test - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Apply the `LOCAL_DEV_MODE=true` ECS environment variable (already present in ecs.tf from Phase 7), run `terraform apply` to register a new task definition revision, push to main to trigger the CI/CD pipeline, and run the full STAGE-01/02/03 smoke test to formally close Phase 5's staging verification gap. Also add `LOCAL_DEV_MODE=true` explicitly to docker-compose.yml to fix MISS-01 startup guard fragility.

</domain>

<decisions>
## Implementation Decisions

### Terraform Apply Process (Plan 08-01)
- Include a `terraform plan` preview step before `terraform apply` — confirm the diff before committing to changes
- Use manual PowerShell commands (not deploy-qa.ps1 script) — consistent with how Phases 3-7 handled infra
- Generate a fresh plan at runtime (`terraform plan -out=tfplan`) — ignore the stale `deploy/terraform/qa/tfplan` file
- Include post-apply verification: run `terraform output` to confirm the new task def ARN, then describe the ECS service to confirm the new revision registered

### docker-compose MISS-01 Fix (Plan 08-01)
- Fix = add `LOCAL_DEV_MODE=true` explicitly to the `app` service environment block in `deploy/docker-compose.yml`
- Do NOT change the `sh -c` startup command — the current `alembic upgrade head && exec uvicorn` pattern is acceptable
- After adding the env var, run a quick local compose smoke test (`docker compose up -d`, hit `/health/ready`, `docker compose down`) to confirm the change doesn't break anything before pushing

### CI/CD Deploy Trigger (Plan 08-02)
- Trigger deploy by pushing to main — GitHub Actions `deploy-test.yml` builds a fresh image, runs migrations, and deploys to ECS
- Trust the CI/CD workflow for Alembic migrations — no separate migration fallback instructions needed
- Skip seed script re-run — staging admin user already exists from Phase 5; `seed_staging_user.py` is idempotent but unnecessary

### Smoke Test Protocol (Plan 08-02)
- Embed the full browser verification checklist directly in 08-02 — self-contained, no need to reference 05-03-PLAN.md
- VERIFICATION.md lives in `.planning/phases/05-staging-deployment/` — with the phase it verifies
- After smoke test passes: update REQUIREMENTS.md to mark STAGE-01, STAGE-02, STAGE-03 as `[x]` and update the traceability table

### Claude's Discretion
- Exact PowerShell command syntax for terraform steps (consistent with existing deploy scripts)
- CloudWatch log troubleshooting steps if CI/CD fails
- VERIFICATION.md format and structure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/terraform/qa/ecs.tf`: `LOCAL_DEV_MODE=true` already present in container_definitions environment block — terraform apply is the only remaining step
- `deploy/docker-compose.yml`: `app` service environment block needs `LOCAL_DEV_MODE: "true"` added
- `backend/auth/routes.py`: `secure=not settings.LOCAL_DEV_MODE` — this is the cookie behavior being fixed
- `.github/workflows/deploy-test.yml`: Full CI/CD pipeline already configured with OIDC auth, migration gate, and ECS deploy
- `deploy/terraform/qa/tfplan`: Stale saved plan file — ignore, generate fresh

### Established Patterns
- Manual PowerShell commands for AWS infra operations (Phases 3, 5, 7)
- `terraform plan -out=tfplan && terraform apply tfplan` pattern
- ECS service verification via `aws ecs describe-services` after deploy
- Human checkpoint gate for staging verification (was used in 05-03-PLAN.md)

### Integration Points
- `deploy/terraform/qa/ecs.tf` → ECS task definition → cookie `secure` flag behavior
- `deploy/docker-compose.yml` → local dev consistency with staging behavior
- `.planning/phases/05-staging-deployment/` → VERIFICATION.md destination
- REQUIREMENTS.md traceability table → STAGE-01/02/03 need `[x]` after smoke test

</code_context>

<specifics>
## Specific Ideas

- The ALB URL for smoke testing: `http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com`
- Admin credentials for staging: `admin` / `IntrepidStaging2024!`
- STAGE-03 banner check: amber/yellow "STAGING — Not Production" banner must be visible on Login page and all authenticated pages, sticky on scroll
- Phase 5 smoke test checklist (from 05-03-PLAN.md) covers: login page loads, banner visible, admin logs in, file upload succeeds, banner appears on Dashboard, Program Runs, Pipeline Runs, Exceptions, Rejected Loans, File Manager, Cash Flow, Holiday Maintenance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-fix-staging-auth*
*Context gathered: 2026-03-10*
