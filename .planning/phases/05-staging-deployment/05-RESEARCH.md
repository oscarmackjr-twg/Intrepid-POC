# Phase 5: Staging Deployment - Research

**Researched:** 2026-03-06
**Domain:** React/Vite frontend env vars, ECS task definition env config, Python seed scripts, CI/CD build args
**Confidence:** HIGH

## Summary

Phase 5 is a final integration and verification phase — not a greenfield build. All infrastructure is live (Phase 3), the CI/CD pipeline is operational (Phase 4), and the goal is to make the staging environment *usable* by real Ops users. The three requirements map to three distinct work items: STAGE-01 (service is reachable after a CI/CD deploy), STAGE-02 (admin user seeded so login + upload works), and STAGE-03 (visible staging banner on every page).

The codebase already has everything needed. `ecs.tf` already sets `STORAGE_TYPE=s3`, `S3_BUCKET_NAME`, `S3_REGION`, `CORS_ORIGINS`, and all S3 prefix vars. The GitHub Actions workflow already builds and deploys. `backend/auth/security.py` already exports `get_password_hash`. `backend/scripts/seed_admin.py` already provides a working `create_admin_user` function. The frontend uses Tailwind CSS throughout. The only new code is: a `StagingBanner` React component, two one-line imports in `Layout.tsx` and `Login.tsx`, a new `backend/scripts/seed_staging_user.py`, a `--build-arg VITE_APP_ENV=staging` in the Dockerfile `RUN npm run build` line and the GitHub Actions build step, and a new "First Deploy Checklist" section in `docs/CICD.md`.

**Primary recommendation:** Work in three focused tasks — (1) frontend banner + build arg wiring, (2) seed script + docs, (3) verify end-to-end. All three tasks are small and independently testable.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Staging banner:**
- Bold, high-contrast bar (amber/yellow background, dark text) — unmissable, not subtle
- Positioned above the nav bar, full-width, sticky — appears before the nav on every authenticated page
- Also appears on the Login page — Login.tsx gets the same banner component
- Implementation: shared `StagingBanner` component rendered in both `Layout.tsx` (above `<nav>`) and `Login.tsx` (above the login form)
- Environment detection: `VITE_APP_ENV` build arg injected at Docker build time via GitHub Actions (`--build-arg VITE_APP_ENV=staging`). Banner renders when `import.meta.env.VITE_APP_ENV !== 'production'`. Baked into the static bundle — zero runtime overhead.
- Text: "STAGING — Not Production" (or similar unmissable phrasing — Claude's discretion on exact wording)

**First-user setup:**
- Manual seed script: `backend/scripts/seed_staging_user.py` — creates an admin user with a known staging password
- Run once after first successful deploy via `aws ecs run-task` with CMD override (same pattern as migration runs)
- User: `admin`, role: `admin` — full access for smoke testing including Holiday Maintenance
- Password: hardcoded in the script — staging is internal-only and RDS is not publicly accessible
- Documented in `docs/CICD.md` runbook under a new "First Deploy Checklist" section (alongside CICD setup steps from Phase 4)
- Script should be idempotent: if the admin user already exists, update password rather than fail

**ECS env config:**
- All staging-specific env vars added to the ECS task definition via Terraform (`ecs.tf` environment block on the app container)
- `DATABASE_URL` and `SECRET_KEY` remain in Secrets Manager — no change to the secrets pattern
- New plain env vars to add in Terraform:
  - `CORS_ORIGINS` — set to the ALB URL (e.g., `["http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com"]`)
  - `STORAGE_TYPE=s3` — switches from local to S3 storage
  - `S3_BUCKET_NAME=intrepid-poc-qa` — existing S3 bucket from Phase 3
  - `S3_REGION=us-east-1` — ECS task IAM role already has S3 access; no credentials needed
  - `LOG_LEVEL=INFO` — explicit, matches default but makes it visible in task definition
- `VITE_APP_ENV=staging` is a Docker **build arg** (not ECS runtime env var) — passed in GitHub Actions workflow at image build time

### Claude's Discretion
- Exact banner wording and icon choice
- Whether `CORS_ORIGINS` also needs `http://localhost:5173` retained alongside the ALB URL (probably yes for future debugging)
- Whether the seed script uses `passlib`/`bcrypt` directly or calls an existing auth utility in `backend/auth/`
- Exact `aws ecs run-task` flags for the seed script execution (subnet, security group — same as migration task)

### Deferred Ideas (OUT OF SCOPE)
- Smoke test automation (scripted API test hitting staging) — not required for v1.0 STAGE-02; manual verification is sufficient
- Private RDS endpoint (remove public accessibility) — v2.0 hardening
- Production environment setup — separate milestone
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STAGE-01 | Staging URL is accessible and app loads after CI/CD deploy | GitHub Actions workflow is already wired; `ecs.tf` already has env vars; a successful `git push` to main should produce a working service — no new Terraform needed |
| STAGE-02 | Ops team can log in and upload a file in staging | `seed_staging_user.py` creates admin user; existing `seed_admin.py` + `auth/security.py` provide all reusable utilities; ECS run-task pattern already used by migration step |
| STAGE-03 | Staging environment has an unmissable banner (not production) | `StagingBanner` component with `VITE_APP_ENV` env var; Dockerfile needs `ARG`/`ENV` declaration; GitHub Actions build step needs `--build-arg` |
</phase_requirements>

---

## Standard Stack

### Core (what this phase touches)

| Library / Tool | Version | Purpose | Status |
|----------------|---------|---------|--------|
| React + TypeScript | 19 / 5 | Frontend — StagingBanner component | Already installed |
| Tailwind CSS | v4 (via `@tailwindcss/vite`) | Styling for banner | Already installed |
| Vite | Current | Build tool; `import.meta.env.VITE_*` convention | Already installed |
| passlib + bcrypt | Current | Password hashing in seed script | Already installed (`auth/security.py` uses it) |
| SQLAlchemy | Current | ORM for seed script DB access | Already installed |
| AWS ECS run-task | CLI | One-off task execution pattern | Already used by migration step |

### No New Dependencies

Phase 5 adds **zero new Python or npm packages**. All tools already exist.

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
frontend/src/components/
└── StagingBanner.tsx        # NEW — shared banner component

backend/scripts/
└── seed_staging_user.py     # NEW — idempotent admin seed for staging

docs/
└── CICD.md                  # MODIFIED — add "First Deploy Checklist" section

deploy/Dockerfile             # MODIFIED — add ARG VITE_APP_ENV, pass to npm build
.github/workflows/deploy-test.yml  # MODIFIED — add --build-arg VITE_APP_ENV=staging
```

### Pattern 1: Vite Build-Time Environment Variables

**What:** Vite bakes `import.meta.env.VITE_*` variables into the static JS bundle at build time. The value is determined by what is set in the environment when `npm run build` runs — not at runtime. Docker build args flow: `ARG` declaration → `ENV` assignment → available during `RUN npm run build`.

**When to use:** Any configuration that should be immutable per build artifact (environment name, feature flags, API base URL).

**Key finding:** The Dockerfile currently has no `ARG VITE_APP_ENV` declaration. The frontend build stage needs `ARG VITE_APP_ENV` declared and `ENV VITE_APP_ENV=$VITE_APP_ENV` before the `RUN npm run build` line. Without the `ARG` declaration, `--build-arg` is silently ignored.

**Dockerfile change (frontend build stage):**
```dockerfile
# After COPY frontend/ ./
ARG VITE_APP_ENV
ENV VITE_APP_ENV=$VITE_APP_ENV
RUN npm run build
```

**GitHub Actions build step change:**
```yaml
docker build -f deploy/Dockerfile \
  --build-arg VITE_APP_ENV=staging \
  -t $ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG \
  -t $ECR_REGISTRY/$ECR_REPO_NAME:latest .
```

**Banner component detection:**
```tsx
// StagingBanner.tsx — renders when NOT production
const isStaging = import.meta.env.VITE_APP_ENV !== 'production'
if (!isStaging) return null
```

**Important:** When `VITE_APP_ENV` is not passed as a build arg (e.g., local dev with `npm run build`), `import.meta.env.VITE_APP_ENV` is `undefined`. The condition `undefined !== 'production'` is `true`, so the banner renders unless you explicitly pass `production`. This is intentional per the CONTEXT.md: "renders when `import.meta.env.VITE_APP_ENV !== 'production'`" — banner shows in all non-production environments.

### Pattern 2: StagingBanner Component

**What:** A full-width sticky `<div>` rendered above `<nav>` in `Layout.tsx` and above the login form in `Login.tsx`. Uses Tailwind classes matching the project's existing utility-first style.

**Placement in Layout.tsx:** The outer `<div className="min-h-screen bg-gray-50">` currently has `<nav>` as its first child. `StagingBanner` becomes the first child, before `<nav>`.

**Placement in Login.tsx:** The `<div className="max-w-md w-full space-y-8">` is the form container. `StagingBanner` is inserted as the first element inside it, above the `<div>` containing the heading.

**Tailwind classes for high-visibility banner:**
```tsx
<div className="w-full bg-amber-400 text-gray-900 text-center text-sm font-bold py-2 px-4 sticky top-0 z-50">
  ⚠ STAGING — Not Production
</div>
```

Amber-400 (`#FBBF24`) is high-contrast against dark text, unmissable, and standard for warning indicators. Sticky + z-50 ensures it stays at top on scroll.

### Pattern 3: Idempotent Seed Script (ECS one-off task)

**What:** `backend/scripts/seed_staging_user.py` creates an admin user or updates the password if the user already exists. Uses `auth/security.py:get_password_hash` — same utility as the main app.

**Key difference from existing `seed_admin.py`:** The existing `seed_admin.py` `create_admin_user` function does NOT update an existing user — it prints "User already exists" and returns. CONTEXT.md requires idempotency with password update. The new seed script needs an upsert approach.

**Idempotent pattern:**
```python
# Check if user exists — if yes, update password; if no, create
existing = db.query(User).filter(User.username == "admin").first()
if existing:
    existing.hashed_password = get_password_hash(STAGING_PASSWORD)
    db.commit()
    print("Admin user password updated")
else:
    # create new User(...)
    db.add(user); db.commit()
    print("Admin user created")
```

**ECS run-task invocation (mirrors migration step exactly):**
```bash
aws ecs run-task \
  --cluster intrepid-poc-qa \
  --task-definition intrepid-poc-qa \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$ECS_SUBNET_IDS],securityGroups=[$ECS_SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"app","command":["python","scripts/seed_staging_user.py"]}]}'
```

Note: The ECS task runs from `/app` (the WORKDIR). The script does `sys.path.insert(0, str(Path(__file__).parent.parent))` — this pattern is already used in `seed_admin.py` and works correctly when invoked from `/app`.

### Pattern 4: ECS env var — CORS_ORIGINS

**What:** `settings.py` defines `CORS_ORIGINS: list[str]` parsed by pydantic-settings. Pydantic-settings parses a JSON array string from an env var into a Python list.

**Current state in ecs.tf:** `CORS_ORIGINS` is already set to `"[\"http://${aws_lb.main.dns_name}\"]"`. The CONTEXT.md decision says also include `localhost:5173`. The current Terraform value is already present — research confirms this specific env var is already configured.

**Confirmed:** All five env vars listed in the CONTEXT.md decisions (`CORS_ORIGINS`, `STORAGE_TYPE`, `S3_BUCKET_NAME`, `S3_REGION`, `LOG_LEVEL`) are **already present in `ecs.tf`**. The Terraform environment block also already has `S3_INPUT`, `S3_OUTPUT`, `S3_OUTPUT_SHARED`. No Terraform changes are needed for env vars.

### Anti-Patterns to Avoid

- **Runtime env var for VITE_APP_ENV:** VITE_ vars are build-time only. Setting them as ECS runtime env vars has no effect on the baked static bundle. The decision to use Docker build arg is correct.
- **`ARG` without `ENV` in Dockerfile:** `ARG VITE_APP_ENV` makes the variable available during the build step, but Vite reads it from the process environment. The `ENV VITE_APP_ENV=$VITE_APP_ENV` line is required to pass it into the environment that `npm run build` sees.
- **Passing `--build-arg` before the `ARG` declaration scope:** Docker `ARG` declarations are stage-scoped. The `ARG VITE_APP_ENV` must be in the `frontend` build stage (before `RUN npm run build`), not in the `backend` stage.
- **Non-idempotent seed script:** If the seed script fails with "user already exists" rather than updating, re-running it (e.g., after a failed first attempt) leaves no admin user with a known password.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt call | `auth/security.py:get_password_hash` | Already handles 72-byte truncation edge case, uses project's `pwd_context` |
| DB session for seed | Custom engine setup | `db.connection.SessionLocal` | Already configured with correct SSL, connection pooling for RDS |
| User model for seed | Raw SQL | `db.models.User, UserRole` | Keeps ORM layer consistent, enum values already defined |
| Banner env detection | Custom JS env file | `import.meta.env.VITE_APP_ENV` | Vite's standard convention, zero config needed |

**Key insight:** This phase is an integration task. Every primitive needed is already built and tested. The risk of hand-rolling alternatives is introducing subtle incompatibilities (e.g., different bcrypt context, different DB connection string handling).

---

## Common Pitfalls

### Pitfall 1: Docker ARG Scope (Silent Failure)

**What goes wrong:** `--build-arg VITE_APP_ENV=staging` is passed to `docker build`, but the banner does not appear. Build appears to succeed.

**Why it happens:** The `ARG` declaration is missing from the Dockerfile frontend stage (or is placed in the backend stage instead). Without `ARG VITE_APP_ENV` in the correct stage, Docker silently discards the build arg. `npm run build` sees `VITE_APP_ENV` as undefined.

**How to avoid:** After adding `ARG VITE_APP_ENV` + `ENV VITE_APP_ENV=$VITE_APP_ENV` to the Dockerfile, run a local test build: `docker build -f deploy/Dockerfile --build-arg VITE_APP_ENV=staging -t test-banner .` and inspect the built `index.js` for the string "staging" using `docker run --rm test-banner grep -r staging /app/static/assets/ 2>/dev/null | head -5`.

**Warning signs:** Banner renders locally (because `import.meta.env.VITE_APP_ENV` is undefined = not 'production') but not in a production-like environment where VITE_APP_ENV=production was intended.

### Pitfall 2: CORS Rejection Blocking Login

**What goes wrong:** The app loads (STAGE-01 passes) but the login form returns a network error in the browser.

**Why it happens:** The FastAPI CORS middleware rejects the preflight OPTIONS request if the `Origin` header (the ALB URL) is not in `CORS_ORIGINS`.

**How to avoid:** The current `ecs.tf` already sets `CORS_ORIGINS` to include the ALB URL via `"[\"http://${aws_lb.main.dns_name}\"]"`. Verify this renders correctly in the deployed task definition: `aws ecs describe-task-definition --task-definition intrepid-poc-qa --query 'taskDefinition.containerDefinitions[0].environment'`.

**Warning signs:** Browser console shows `CORS policy: No 'Access-Control-Allow-Origin' header` on `/api/auth/login`.

### Pitfall 3: ECS run-task for Seed Script — Wrong Working Directory

**What goes wrong:** Seed script fails with `ModuleNotFoundError: No module named 'auth'`.

**Why it happens:** The container `CMD` runs from `/app`. The seed script does `sys.path.insert(0, str(Path(__file__).parent.parent))` which adds `/app` to sys.path. This is correct when invoked as `python scripts/seed_staging_user.py` from the `/app` working directory. However, if the command override uses a different path format, the path calculation breaks.

**How to avoid:** Use the exact same invocation format as the migration step. The command in the container override should be `["python", "scripts/seed_staging_user.py"]`, not an absolute path.

**Warning signs:** CloudWatch Logs for the run-task show `ModuleNotFoundError` immediately after container start.

### Pitfall 4: Seed Script Not Idempotent — Password Not Updated

**What goes wrong:** Seed script is run a second time (e.g., after a password change or re-deploy), user already exists, but password was not updated. Ops can't log in with the expected credentials.

**Why it happens:** The existing `seed_admin.py:create_admin_user` function returns early without updating when the user exists: `print("User already exists") return existing`. The new `seed_staging_user.py` must explicitly set `existing.hashed_password` and commit.

**How to avoid:** Implement true upsert: query for user by username, if exists update `hashed_password` and `is_active`, commit. If not exists, create.

### Pitfall 5: S3 Upload Fails — Content-Type or Prefix Mismatch

**What goes wrong:** Login works, file upload UI accepts the file, but the backend returns a 500 error when writing to S3.

**Why it happens:** `S3_INPUT` env var controls which S3 prefix the app writes to. The current `ecs.tf` already sets `S3_INPUT=input`, `S3_OUTPUT=outputs`, `S3_OUTPUT_SHARED=output_share`. If these are wrong or the IAM task role lacks `s3:PutObject` on the correct prefix, uploads fail silently or with a generic 500.

**How to avoid:** Before STAGE-02 manual test, verify: `aws s3 ls s3://intrepid-poc-qa/input/` returns successfully from a local machine (IAM-authenticated), confirming the prefix exists and the bucket is accessible.

---

## Code Examples

### StagingBanner Component

```tsx
// frontend/src/components/StagingBanner.tsx
// Renders when VITE_APP_ENV is not 'production' (undefined = staging/local)

export default function StagingBanner() {
  if (import.meta.env.VITE_APP_ENV === 'production') return null

  return (
    <div className="w-full bg-amber-400 text-gray-900 text-center text-sm font-bold py-2 px-4 sticky top-0 z-50">
      STAGING — Not Production
    </div>
  )
}
```

### Layout.tsx Integration Point

```tsx
// Add import at top of Layout.tsx:
import StagingBanner from './StagingBanner'

// Change the return's outer div first child:
return (
  <div className="min-h-screen bg-gray-50">
    <StagingBanner />   {/* NEW — above nav */}
    <nav className="bg-white shadow-sm border-b">
      ...
```

### Login.tsx Integration Point

```tsx
// Add import at top of Login.tsx:
import StagingBanner from '../components/StagingBanner'

// Add as first element inside the centered container:
return (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <StagingBanner />   {/* NEW — fixed position, full width, above form */}
    <div className="max-w-md w-full space-y-8">
      ...
```

Note: In `Login.tsx`, `StagingBanner` with `sticky top-0` will stick to the viewport top, not inside the flex container. This is the correct behavior for a page-level banner.

### Dockerfile ARG/ENV Addition (frontend stage)

```dockerfile
# In the frontend build stage, after COPY frontend/ ./  and before RUN npm run build:
ARG VITE_APP_ENV
ENV VITE_APP_ENV=$VITE_APP_ENV
RUN npm run build
```

### seed_staging_user.py Core Logic

```python
# backend/scripts/seed_staging_user.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import User, UserRole
from auth.security import get_password_hash

STAGING_USERNAME = "admin"
STAGING_PASSWORD = "IntrepidStaging2024!"  # hardcoded — staging internal only
STAGING_EMAIL = "admin@staging.intrepid"

def seed_staging_user():
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == STAGING_USERNAME).first()
        if existing:
            existing.hashed_password = get_password_hash(STAGING_PASSWORD)
            existing.is_active = True
            db.commit()
            print(f"Admin user updated: {STAGING_USERNAME}")
        else:
            user = User(
                username=STAGING_USERNAME,
                email=STAGING_EMAIL,
                hashed_password=get_password_hash(STAGING_PASSWORD),
                full_name="Staging Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"Admin user created: {STAGING_USERNAME}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_staging_user()
```

### ECS run-task Command for Seed Script

```bash
aws ecs run-task \
  --cluster intrepid-poc-qa \
  --task-definition intrepid-poc-qa \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$ECS_SUBNET_IDS],securityGroups=[$ECS_SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"app","command":["python","scripts/seed_staging_user.py"]}]}' \
  --query 'tasks[0].taskArn' \
  --output text
```

Then wait and check exit code:
```bash
aws ecs wait tasks-stopped --cluster intrepid-poc-qa --tasks $TASK_ARN
aws ecs describe-tasks --cluster intrepid-poc-qa --tasks $TASK_ARN \
  --query 'tasks[0].containers[?name==`app`].exitCode' --output text
```

---

## State of the Art

| Old Approach | Current Approach | Status |
|--------------|-----------------|--------|
| Static AWS credentials in GitHub Secrets | OIDC token exchange (already Phase 4) | Done |
| Hardcoded env vars in Dockerfile | ECS task definition environment block | Done in ecs.tf |
| Runtime env var for frontend config | Vite build-arg baked into bundle | Phase 5 work item |
| Manual DB seed via SSH | ECS run-task CMD override | Phase 5 work item |

**Key observation:** The ECS environment configuration is already more complete than CONTEXT.md's "new plain env vars" list suggests. Reviewing `ecs.tf` confirms `CORS_ORIGINS`, `STORAGE_TYPE`, `S3_BUCKET_NAME`, `S3_REGION` are all already present. The only Terraform work item to verify is whether `LOG_LEVEL=INFO` is present (it is not in the current `ecs.tf`), though this is low-priority since it matches the default.

---

## Terraform: What Is Already Done vs. What Needs Work

This is a critical finding from reading the actual `ecs.tf`:

| CONTEXT.md "to-add" item | Status in current ecs.tf |
|--------------------------|--------------------------|
| `CORS_ORIGINS` = ALB URL | **ALREADY PRESENT** — `"[\"http://${aws_lb.main.dns_name}\"]"` |
| `STORAGE_TYPE=s3` | **ALREADY PRESENT** |
| `S3_BUCKET_NAME=intrepid-poc-qa` | **ALREADY PRESENT** (via `aws_s3_bucket.app.id`) |
| `S3_REGION=us-east-1` | **ALREADY PRESENT** (via `var.aws_region`) |
| `LOG_LEVEL=INFO` | **NOT PRESENT** — minor addition if desired |

Also already present: `S3_INPUT=input`, `S3_OUTPUT=outputs`, `S3_OUTPUT_SHARED=output_share`, `AWS_REGION`, `ENABLE_SCHEDULER=true`.

**Implication for planning:** There is no Terraform environment block work required for STAGE-01/STAGE-02. The only Terraform change (if any) is adding `LOG_LEVEL=INFO`, which is cosmetic and optional. CORS is covered, S3 is covered.

**However:** `CORS_ORIGINS` currently only contains the ALB URL. CONTEXT.md discretion item says "probably yes" to also including `localhost:5173`. If this is desired, the Terraform value needs updating to `"[\"http://${aws_lb.main.dns_name}\",\"http://localhost:5173\"]"` and `terraform apply` must run.

---

## Open Questions

1. **CORS_ORIGINS: include localhost:5173?**
   - What we know: Current `ecs.tf` sets CORS to ALB URL only. CONTEXT.md marks this as Claude's discretion: "probably yes for future debugging."
   - What's unclear: Whether any current use case requires localhost:5173 against the staging backend.
   - Recommendation: Include it — the cost is a one-line Terraform change + apply, and the debugging value is high.

2. **First CI/CD deploy: has it ever succeeded end-to-end?**
   - What we know: Phase 4 rewrote the workflow (`deploy-test.yml`). The workflow is committed and configured. Whether it has been triggered and produced a healthy ECS task is not confirmed in STATE.md.
   - What's unclear: Whether STAGE-01 is already partially satisfied (service is up) or whether the first successful deploy is still pending.
   - Recommendation: Plan for the first task to trigger a deploy (push to main) and verify the ALB URL loads before investing in the banner work. If the service is already up, banner work can proceed in parallel.

3. **ECS_SUBNET_IDS format for run-task**
   - What we know: The GitHub Actions migration step uses `vars.ECS_SUBNET_IDS` as a comma-separated list inside `awsvpcConfiguration={subnets=[...]}`. This works in the workflow context.
   - What's unclear: The exact format needed for the manual `aws ecs run-task` CLI command in the First Deploy Checklist — whether subnets need to be quoted individually or comma-separated.
   - Recommendation: Planner should note that the runbook command uses PowerShell; the subnet list format for PowerShell vs bash differs. Document both.

---

## Validation Architecture

Test framework: pytest (backend), no frontend test runner configured.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend only) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/ -v --tb=short -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAGE-01 | Staging URL loads app after deploy | manual-only | N/A — requires live AWS environment | N/A |
| STAGE-02 | Ops can log in and upload a file | manual-only | N/A — requires live staging environment | N/A |
| STAGE-03 | Banner renders on every page when VITE_APP_ENV != 'production' | manual-only (visual) | N/A — no frontend test runner | N/A |

**Manual verification notes:**
- STAGE-01: Open `http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com` in browser
- STAGE-02: Log in as `admin`, navigate to file upload, upload a sample loan spreadsheet, confirm accepted
- STAGE-03: Inspect each page (Login, Dashboard, Pipeline Runs, Exceptions, File Manager, Holiday Maintenance) for amber banner at top

### Sampling Rate
- **Per task commit:** Run `cd backend && python -m pytest tests/ -q --tb=short` to catch any accidental backend regression
- **Per wave merge:** Full suite green
- **Phase gate:** Manual verification of all three STAGE requirements before `/gsd:verify-work`

### Wave 0 Gaps
None — existing backend test infrastructure covers all backend code. No new backend logic is introduced by Phase 5 (seed script is a one-off utility, not part of the running application). Frontend has no test runner; visual verification is the acceptance mechanism per CONTEXT.md.

---

## Sources

### Primary (HIGH confidence)
- Direct file read: `deploy/terraform/qa/ecs.tf` — confirmed all env vars already present
- Direct file read: `backend/auth/security.py` — confirmed `get_password_hash` and `pwd_context`
- Direct file read: `backend/scripts/seed_admin.py` — confirmed existing pattern and non-idempotent limitation
- Direct file read: `deploy/Dockerfile` — confirmed no ARG VITE_APP_ENV declaration exists
- Direct file read: `.github/workflows/deploy-test.yml` — confirmed ECS run-task pattern for migration
- Direct file read: `frontend/src/components/Layout.tsx` — confirmed nav structure
- Direct file read: `frontend/src/pages/Login.tsx` — confirmed login form structure
- Direct file read: `backend/config/settings.py` — confirmed CORS_ORIGINS list[str] pydantic field
- Direct file read: `docs/CICD.md` — confirmed runbook structure for First Deploy Checklist placement
- Vite docs (knowledge): `import.meta.env.VITE_*` build-time convention, ARG/ENV Dockerfile pattern

### Secondary (MEDIUM confidence)
- Tailwind CSS amber-400 class: standard utility present in all Tailwind v3/v4 installations

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified by reading actual source files
- Architecture: HIGH — patterns derived from existing code (seed_admin.py, ecs.tf, Dockerfile) not from assumptions
- Pitfalls: HIGH — Docker ARG scoping and CORS pitfalls verified against actual file contents
- Terraform state: HIGH — ecs.tf read directly; env var presence confirmed

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable infrastructure, no moving dependencies)
