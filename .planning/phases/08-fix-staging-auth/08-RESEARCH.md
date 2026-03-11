# Phase 8: Fix Staging Auth & Complete Smoke Test - Research

**Researched:** 2026-03-11
**Domain:** AWS ECS Terraform, Docker Compose env vars, FastAPI cookie auth, CI/CD pipeline, staging smoke test
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Terraform Apply Process (Plan 08-01)**
- Include a `terraform plan` preview step before `terraform apply` — confirm the diff before committing to changes
- Use manual PowerShell commands (not deploy-qa.ps1 script) — consistent with how Phases 3-7 handled infra
- Generate a fresh plan at runtime (`terraform plan -out=tfplan`) — ignore the stale `deploy/terraform/qa/tfplan` file
- Include post-apply verification: run `terraform output` to confirm the new task def ARN, then describe the ECS service to confirm the new revision registered

**docker-compose MISS-01 Fix (Plan 08-01)**
- Fix = add `LOCAL_DEV_MODE=true` explicitly to the `app` service environment block in `deploy/docker-compose.yml`
- Do NOT change the `sh -c` startup command — the current `alembic upgrade head && exec uvicorn` pattern is acceptable
- After adding the env var, run a quick local compose smoke test (`docker compose up -d`, hit `/health/ready`, `docker compose down`) to confirm the change doesn't break anything before pushing

**CI/CD Deploy Trigger (Plan 08-02)**
- Trigger deploy by pushing to main — GitHub Actions `deploy-test.yml` builds a fresh image, runs migrations, and deploys to ECS
- Trust the CI/CD workflow for Alembic migrations — no separate migration fallback instructions needed
- Skip seed script re-run — staging admin user already exists from Phase 5; `seed_staging_user.py` is idempotent but unnecessary

**Smoke Test Protocol (Plan 08-02)**
- Embed the full browser verification checklist directly in 08-02 — self-contained, no need to reference 05-03-PLAN.md
- VERIFICATION.md lives in `.planning/phases/05-staging-deployment/` — with the phase it verifies
- After smoke test passes: update REQUIREMENTS.md to mark STAGE-01, STAGE-02, STAGE-03 as `[x]` and update the traceability table

### Claude's Discretion
- Exact PowerShell command syntax for terraform steps (consistent with existing deploy scripts)
- CloudWatch log troubleshooting steps if CI/CD fails
- VERIFICATION.md format and structure

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STAGE-01 | Staging URL is accessible and app loads after CI/CD deploy | Blocked by `secure=True` cookie over HTTP ALB; fix is `LOCAL_DEV_MODE=true` in ecs.tf (already present) → terraform apply registers new task def → push to main triggers CI/CD deploy |
| STAGE-02 | Ops team can log in and upload a file in staging | Login cookie set with `secure=not settings.LOCAL_DEV_MODE`; when LOCAL_DEV_MODE=true cookie is sent over HTTP ALB; upload tests existing file manager endpoint |
| STAGE-03 | Staging environment has an unmissable banner (not production) | StagingBanner already implemented in Phase 5; baked via `VITE_APP_ENV=staging` build arg in deploy-test.yml; amber banner on Login + all authenticated pages, sticky on scroll |
</phase_requirements>

---

## Summary

Phase 8 is an operations and verification phase, not a feature development phase. The root cause of the staging authentication failure (MISS-02) is already understood and the fix is already in the codebase: `LOCAL_DEV_MODE=true` was added to `deploy/terraform/qa/ecs.tf` during Phase 7 but `terraform apply` was never run to register a new task definition revision with that env var active. The ECS service is still running a task definition revision that predates Phase 7's ecs.tf changes.

The fix path is deterministic and short: (1) run `terraform plan` to confirm the diff shows only the new env var, (2) run `terraform apply` to register a new task def revision, (3) add `LOCAL_DEV_MODE=true` to docker-compose.yml for local parity, (4) push to main to trigger the GitHub Actions CI/CD pipeline which rebuilds the image and force-deploys the service, and (5) run the Phase 5 smoke test checklist against the newly deployed staging URL.

No new code needs to be written for the auth fix itself — the change is purely operational (apply the Terraform that was already written). The docker-compose.yml change is a one-line environment variable addition. The smoke test is the same checklist that was blocked during Phase 5 Plan 03 when the Secure cookie prevented login.

**Primary recommendation:** Apply the existing ecs.tf Terraform change, add `LOCAL_DEV_MODE: "true"` to docker-compose.yml, push to main, and run the smoke test checklist. The entire phase is infrastructure operations and manual verification.

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Terraform AWS Provider | ~5.x (existing) | Register new ECS task def revision with env var change | Already in use for all QA infra; state is up to date |
| AWS CLI (PowerShell) | existing | Verify ECS service, describe task def, check CloudWatch | Used in all prior infra phases |
| GitHub Actions `deploy-test.yml` | existing | Build image + migrate + deploy to ECS | Already configured; push to main triggers it |
| Docker Compose | existing | Local dev smoke test of env var change | `deploy/docker-compose.yml` already wired to app service |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `gh run list / gh run watch` | Monitor GitHub Actions pipeline status | After push to main during Plan 08-02 |
| `aws ecs describe-services` | Confirm ECS service has picked up new task def revision | Post-apply verification and post-deploy verification |
| `aws logs get-log-events` | Diagnose container startup failures | If ECS tasks fail to reach RUNNING state |
| `aws ecs describe-task-definition` | Confirm new revision has LOCAL_DEV_MODE=true | Post-apply spot check |

---

## Architecture Patterns

### The LOCAL_DEV_MODE Cookie Pattern

`backend/auth/routes.py` line 106:
```python
secure=not settings.LOCAL_DEV_MODE,  # False over HTTP in local dev, True on HTTPS in staging
```

`backend/config/settings.py` line 118:
```python
LOCAL_DEV_MODE: bool = False
```

This means:
- `LOCAL_DEV_MODE=false` (default) → `secure=True` → cookie **only sent over HTTPS** — browser silently drops it on HTTP ALB, login appears to succeed but cookie is never stored, all subsequent requests fail with 401.
- `LOCAL_DEV_MODE=true` → `secure=False` → cookie sent over HTTP — this is the required state for HTTP-only staging (ALB has no ACM cert yet).

The env var is already in `deploy/terraform/qa/ecs.tf` at line 47:
```
{ name = "LOCAL_DEV_MODE", value = "true" },
```
It just hasn't been applied to AWS yet.

### Terraform ECS Task Def Apply Pattern

When `environment` block in `container_definitions` changes in `aws_ecs_task_definition`, Terraform creates a **new task definition revision** (task defs are immutable; Terraform registers revision N+1). The ECS service `aws_ecs_service.app` references `task_definition = aws_ecs_task_definition.app.arn` which resolves to the latest revision — but ECS services don't automatically redeploy when the task def changes; a force-new-deployment is needed.

The Phase 8 workflow handles this: terraform apply registers the new revision, then pushing to main triggers `deploy-test.yml` which calls `aws ecs update-service --force-new-deployment`.

**Pattern (PowerShell, consistent with Phases 3/5/7):**
```powershell
cd C:\Users\omack\Intrepid\pythonFramework\intrepid-poc\deploy\terraform\qa
terraform plan -out=tfplan
# Review diff — expect: change to aws_ecs_task_definition.app container_definitions
terraform apply tfplan

# Post-apply verify
terraform output
aws ecs describe-services `
  --cluster intrepid-poc-qa `
  --services intrepid-poc-qa `
  --query "services[0].{taskDef:taskDefinition,running:runningCount,pending:pendingCount}" `
  --region us-east-1
```

### docker-compose MISS-01 Fix Pattern

Current `deploy/docker-compose.yml` app service environment block (lines 16-21):
```yaml
environment:
  DATABASE_URL: postgresql://postgres:postgres@db:5432/intrepid_poc
  SECRET_KEY: change-me-in-production
  CORS_ORIGINS: '["http://localhost:8000","http://localhost:5173"]'
  STORAGE_TYPE: local
  DEV_INPUT: /data/sample/files_required
  DEV_OUTPUT: /tmp/dev_output
  DEV_OUTPUT_SHARED: /tmp/dev_output_share
```

Add one line:
```yaml
  LOCAL_DEV_MODE: "true"
```

This closes MISS-01: without this, `LOCAL_DEV_MODE` defaults to `False` in docker-compose, which causes the `validate_secret_key` model_validator to raise a `ValueError` at startup (because `SECRET_KEY: change-me-in-production` matches the `KNOWN_FALLBACK_SECRET`). This is the startup guard fragility referenced in MISS-01. The fix is the same env var, same value, different config file.

### CI/CD Deploy Trigger Pattern

Push to main triggers `deploy-test.yml`. The workflow:
1. `security-quality-gate` job — ruff, mypy, pip-audit, npm audit, terraform validate, TruffleHog (must pass before deploy)
2. Build Docker image with `--build-arg VITE_APP_ENV=staging` (bakes staging banner into frontend bundle)
3. Push image tagged with commit SHA and `:latest` to ECR
4. Run Alembic migration as ECS one-off task (same cluster, same task def)
5. Wait for migration to stop and check exit code (must be 0)
6. `aws ecs update-service --force-new-deployment` — picks up new task def revision registered by terraform apply
7. `aws ecs wait services-stable` — polls until service is stable (up to ~10 min)

**Note:** The migration task (step 4) uses `--task-definition intrepid-poc-qa` (the family name, not a specific ARN), which resolves to the latest active revision. After terraform apply, this will be the new revision with `LOCAL_DEV_MODE=true`.

### Phase 5 Smoke Test Checklist (embedded in 08-02)

The full checklist from `05-03-PLAN.md` must be reproduced verbatim in `08-02-PLAN.md` per the locked decision. Key items:

**STAGE-01:**
- [ ] Login page loads at `http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com`
- [ ] "Backend connected" visible (green health check)

**STAGE-02:**
- [ ] Log in as `admin` / `IntrepidStaging2024!`
- [ ] Upload a sample .xlsx loan tape — accepted without error

**STAGE-03:**
- [ ] Amber "STAGING — Not Production" banner on Login page
- [ ] Banner on every authenticated page: Dashboard, Program Runs, Pipeline Runs, Exceptions, Rejected Loans, File Manager, Cash Flow, Holiday Maintenance
- [ ] Banner is sticky (visible on scroll)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Force ECS to pick up new task def | Manual `aws ecs update-service` with hardcoded ARN | Push to main → CI/CD handles `--force-new-deployment` | CI/CD already wired; ensures image is rebuilt with latest code + VITE_APP_ENV=staging |
| Verify env var in running container | Manual docker exec / task exec | `aws ecs describe-task-definition` post-apply | Task def JSON is the source of truth before container starts; CloudWatch logs confirm at runtime |
| Re-create admin user | Run seed script again | Skip — admin user exists from Phase 5; `seed_staging_user.py` is idempotent but unnecessary overhead | State persists in RDS across deploys |

---

## Common Pitfalls

### Pitfall 1: Stale tfplan File
**What goes wrong:** Running `terraform apply tfplan` against the stale `deploy/terraform/qa/tfplan` saved in the repo — Terraform will reject it or apply wrong changes.
**Why it happens:** The tfplan binary was committed to the repo at some earlier phase; it is stale and targets a different state.
**How to avoid:** Always generate fresh: `terraform plan -out=tfplan` first, then `terraform apply tfplan`. The CONTEXT.md decision is explicit: ignore the stale saved plan file.
**Warning signs:** Terraform plan shows no changes or references resource versions inconsistent with the current state file.

### Pitfall 2: terraform apply Registers New Revision But ECS Doesn't Redeploy Automatically
**What goes wrong:** After `terraform apply`, the ECS service shows new task def ARN but the running task is still the old revision.
**Why it happens:** ECS services don't automatically roll when the task definition updates — they only redeploy on `update-service --force-new-deployment` or a new deployment trigger.
**How to avoid:** The CI/CD pipeline handles this via `--force-new-deployment`. Don't manually update the service — push to main and let the pipeline run.
**Warning signs:** `aws ecs describe-services` shows new `taskDefinition` ARN but `deployments[0].status` is still ACTIVE on the old revision.

### Pitfall 3: Security-Quality-Gate Fails and Blocks Deploy
**What goes wrong:** The `deploy` job has `needs: [security-quality-gate]` — if ruff/mypy/TruffleHog/npm-audit fails, the deploy never runs.
**Why it happens:** Any lint error, type error, CVE, or accidental secret in the diff will block CI/CD.
**How to avoid:** Run `ruff check backend/` and `ruff format --check backend/` locally before pushing. The docker-compose.yml change doesn't touch Python code, so ruff/mypy won't flag it. The only risk is if unrelated staged changes have issues.
**Warning signs:** GitHub Actions shows `security-quality-gate` job failed; `deploy` job shows "skipped".

### Pitfall 4: Migration Task Uses Old Task Def Revision
**What goes wrong:** The migration ECS one-off task step in deploy-test.yml uses `--task-definition ${{ env.ECS_CLUSTER }}` (family name `intrepid-poc-qa`) which AWS resolves to the latest ACTIVE revision. If terraform apply hasn't run yet, the migration runs against the old revision (still functionally fine since it's just `alembic upgrade head`).
**Why it happens:** ECS task family name resolves to latest active revision at time of `run-task` call.
**How to avoid:** Terraform apply must happen before the push that triggers CI/CD. In Phase 8, terraform apply is in Plan 08-01, CI/CD trigger is in Plan 08-02. As long as the plan sequence is followed, the migration task will use the new revision.
**Warning signs:** Not a real failure — migration is idempotent. Non-issue unless the new revision fails health check.

### Pitfall 5: LOCAL_DEV_MODE Disables SECRET_KEY Guard in Staging
**What goes wrong:** `LOCAL_DEV_MODE=true` also bypasses the `validate_secret_key` check. For staging, `SECRET_KEY` is loaded from Secrets Manager (not the fallback), so the guard would have passed anyway. The net effect is correct but the semantic intent is slightly overloaded.
**Why it happens:** A single `LOCAL_DEV_MODE` field serves two purposes: cookie `secure` flag and SECRET_KEY guard bypass.
**How to avoid:** This is an accepted design decision from Phase 7 (STATE.md: "LOCAL_DEV_MODE field consolidated... resolved to single field with False default serving both SECRET_KEY guard and cookie security"). Document in plan that this is intentional and acceptable until HTTPS is configured on the ALB.
**Warning signs:** None — this is by design. Only becomes a concern if the ACM cert is configured and HTTPS is enabled (at which point `LOCAL_DEV_MODE` should be removed from ecs.tf).

### Pitfall 6: CORS_ORIGINS Mismatch After Deploy
**What goes wrong:** The ECS task def has `CORS_ORIGINS: ["http://<ALB_DNS_NAME>"]` which is constructed at Terraform plan time using `aws_lb.main.dns_name`. If this value changes or the browser hits via a different origin (e.g., IP address), CORS will block API calls.
**Why it happens:** CORS is set to the exact ALB DNS name; any variation (HTTP vs HTTPS, trailing slash, IP) causes preflight failures.
**How to avoid:** Access staging only via the full ALB DNS name `http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com`. Don't use the IP address or add a trailing slash.
**Warning signs:** Browser shows CORS errors in console; API calls return 4xx with CORS headers missing.

---

## Code Examples

### Verify LOCAL_DEV_MODE in Current ECS Task Def (PowerShell)

```powershell
# Confirm the env var is in the Terraform-managed task def before apply
# Source: ecs.tf line 47 already has it; this is post-apply confirmation
aws ecs describe-task-definition `
  --task-definition intrepid-poc-qa `
  --query "taskDefinition.containerDefinitions[0].environment[?name=='LOCAL_DEV_MODE']" `
  --region us-east-1
# Expected: [{"name": "LOCAL_DEV_MODE", "value": "true"}]
```

### Check ECS Service Task Def After Apply (PowerShell)

```powershell
aws ecs describe-services `
  --cluster intrepid-poc-qa `
  --services intrepid-poc-qa `
  --query "services[0].{taskDef:taskDefinition,running:runningCount,desired:desiredCount}" `
  --region us-east-1
```

### Monitor CI/CD Pipeline (PowerShell-compatible gh CLI)

```powershell
gh run list --workflow=deploy-test.yml --limit=5
gh run watch  # live tail of active run
```

### CloudWatch Troubleshooting — Tail ECS App Logs (PowerShell)

```powershell
# Get recent log streams for the app container
aws logs describe-log-streams `
  --log-group-name /ecs/intrepid-poc-qa `
  --order-by LastEventTime `
  --descending `
  --max-items 5 `
  --region us-east-1

# Tail log stream (replace <stream-name> with actual stream from above)
aws logs get-log-events `
  --log-group-name /ecs/intrepid-poc-qa `
  --log-stream-name "ecs/app/<stream-name>" `
  --limit 50 `
  --region us-east-1
```

### ECS Wait Services Stable (PowerShell)

```powershell
aws ecs wait services-stable `
  --cluster intrepid-poc-qa `
  --services intrepid-poc-qa `
  --region us-east-1
# Returns when service deployment is complete; times out after ~10 min if unhealthy
```

---

## State of the Art

| Previous State | Current State (Phase 8 Goal) | Impact |
|----------------|------------------------------|--------|
| ecs.tf has LOCAL_DEV_MODE=true but terraform not applied | terraform apply registers new task def revision | ECS tasks pick up env var on next deploy |
| docker-compose.yml lacks LOCAL_DEV_MODE | Add `LOCAL_DEV_MODE: "true"` to app environment block | Closes MISS-01 — startup guard fragility resolved locally |
| Staging deploy was attempted in Phase 5 but stalled (secure cookie blocked login) | Phase 8 resolves root cause and re-runs the deploy + smoke test | STAGE-01 satisfied; STAGE-02/03 formally verified |
| STAGE-01 marked `[ ]` in REQUIREMENTS.md | Mark `[x]` after smoke test passes | Closes gap identified in milestone audit |

---

## Open Questions

1. **Is there currently a healthy ECS task running in staging?**
   - What we know: Phase 5 Plan 03 attempted a deploy; the `.continue-here.md` shows it stalled before the human checkpoint. The secure cookie issue would have prevented login but the container itself may have been running.
   - What's unclear: Whether the current running task (if any) is healthy or has been terminated. `aws ecs describe-services` will clarify.
   - Recommendation: Plan 08-02 should include a pre-push ECS service status check to baseline the state before triggering the new deploy.

2. **Does terraform state need to be refreshed before plan?**
   - What we know: Phase 7 made changes to ecs.tf (RDS private subnets, SG egress tightening, ALB HTTPS count-gated listener, LOCAL_DEV_MODE) but terraform was not applied for any of these — STATE.md confirms "Terraform validated but not applied — RDS publicly_accessible=false not yet active in QA" (Phase 7 VERIFICATION.md).
   - What's unclear: Whether the remote state is stale relative to the actual AWS resources (possible if someone applied manually, but unlikely given the workflow).
   - Recommendation: Run `terraform plan` (not just validate) and carefully review the diff. Expect changes beyond just LOCAL_DEV_MODE — the Phase 7 RDS/SG/ALB changes that were written but not applied will all show in the plan. The planner should note this clearly and have the executor review the full diff before applying.

3. **Phase 7 terraform changes scope: will applying ecs.tf also apply rds.tf/alb.tf/security-groups.tf?**
   - What we know: Terraform operates on the entire module in `deploy/terraform/qa/` — a single `terraform apply` applies ALL pending changes across all .tf files in scope, not just ecs.tf. Phase 7 VERIFICATION.md confirms: "RDS publicly_accessible=false not yet active in QA", "ALB HTTPS listener is count-gated on acm_certificate_arn — cert ARN not set" — these are all unapplied changes.
   - What's unclear: The exact diff magnitude. The Phase 7 RDS change (moving to private subnets) is potentially breaking — if RDS is moved to private subnets and ECS is still in public subnets, the migration task needs to reach RDS.
   - Recommendation: This is a HIGH-priority consideration for the planner. The plan should include explicit instruction to review the terraform plan output carefully, specifically checking rds.tf and networking changes. If the diff is large/risky, the executor may need to scope the apply or accept the full Phase 7 infra changes as part of Phase 8. The CONTEXT.md decisions don't mention this risk — flag it prominently.

---

## Validation Architecture

> `workflow.nyquist_validation` is absent from `.planning/config.json` — treated as enabled. However, this phase is infrastructure operations + manual browser verification. All phase requirements (STAGE-01, STAGE-02, STAGE-03) require human verification against a live staging environment and cannot be automated.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual verification (browser + AWS CLI) |
| Config file | n/a — no automated tests written in this phase |
| Quick run command | `aws ecs describe-services --cluster intrepid-poc-qa --services intrepid-poc-qa --query 'services[0].runningCount' --region us-east-1` |
| Full suite command | Browser smoke test checklist (human checkpoint gate) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAGE-01 | Staging URL loads and app renders | smoke (human) | `Invoke-WebRequest -Uri http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com -UseBasicParsing` returns 200 | ✅ (no file needed — AWS endpoint) |
| STAGE-02 | Admin can log in and upload a file | integration (human) | Manual browser — login form + file upload widget | ✅ (no file needed — human step) |
| STAGE-03 | Amber staging banner on all pages, sticky | visual (human) | Manual browser — visual inspection of each page | ✅ (no file needed — human step) |

### Sampling Rate
- **Per task commit:** `gh run list --workflow=deploy-test.yml --limit=1 --json conclusion --jq '.[0].conclusion'`
- **Per wave merge:** Full browser smoke test checklist from 08-02-PLAN.md
- **Phase gate:** Human approval of smoke test before REQUIREMENTS.md is updated to `[x]`

### Wave 0 Gaps
None — no new test files needed. This phase writes no new application code. The existing test suite (50 tests from Phase 7) continues to pass; the CI `security-quality-gate` job runs them on every push.

---

## Sources

### Primary (HIGH confidence)
- `deploy/terraform/qa/ecs.tf` — confirmed `LOCAL_DEV_MODE=true` at line 47, task def structure, ECS service wiring
- `backend/auth/routes.py` — confirmed `secure=not settings.LOCAL_DEV_MODE` at line 106, login cookie behavior
- `backend/config/settings.py` — confirmed `LOCAL_DEV_MODE: bool = False` at line 118, SECRET_KEY guard behavior
- `deploy/docker-compose.yml` — confirmed LOCAL_DEV_MODE absent from app environment block (lines 16-21)
- `.github/workflows/deploy-test.yml` — confirmed pipeline structure: security-quality-gate → build → migrate → deploy → wait
- `.planning/phases/05-staging-deployment/05-03-PLAN.md` — full smoke test checklist, ALB URL, admin creds
- `.planning/phases/07-run-final-funding-via-api/07-VERIFICATION.md` — confirmed Phase 7 infra changes are written but NOT applied to AWS
- `.planning/phases/08-fix-staging-auth/08-CONTEXT.md` — all locked decisions and specifics
- `deploy/terraform/qa/outputs.tf` — terraform output names for post-apply verification

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — project history and accumulated decisions, particularly "LOCAL_DEV_MODE field consolidated" decision from Phase 7

---

## Metadata

**Confidence breakdown:**
- Root cause of STAGE-01 failure: HIGH — `secure=not LOCAL_DEV_MODE` + `LOCAL_DEV_MODE` absent from running task def; confirmed in code
- Fix correctness: HIGH — `LOCAL_DEV_MODE=true` already in ecs.tf; terraform apply is the only remaining operation
- Terraform plan scope risk: MEDIUM — Phase 7 infra changes (RDS private subnets, SG egress, ALB HTTPS) are unapplied and will appear in plan; need careful review
- CI/CD pipeline behavior: HIGH — deploy-test.yml fully read and understood; behavior is deterministic
- Smoke test checklist: HIGH — reproduced verbatim from 05-03-PLAN.md with all page names, admin creds, and ALB URL

**Research date:** 2026-03-11
**Valid until:** 2026-04-10 (stable infrastructure; 30-day window appropriate)
