# Phase 5: Staging Deployment - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

The staging environment is live at the ALB URL, Ops can log in and upload a file, and the environment is clearly identified as non-production on every screen. This phase ends when all three STAGE requirements are manually verified: URL loads (STAGE-01), admin user can log in and upload (STAGE-02), staging banner is visible everywhere (STAGE-03).

</domain>

<decisions>
## Implementation Decisions

### Staging banner
- Bold, high-contrast bar (amber/yellow background, dark text) — unmissable, not subtle
- Positioned above the nav bar, full-width, sticky — appears before the nav on every authenticated page
- Also appears on the Login page — Login.tsx gets the same banner component
- Implementation: shared `StagingBanner` component rendered in both `Layout.tsx` (above `<nav>`) and `Login.tsx` (above the login form)
- Environment detection: `VITE_APP_ENV` build arg injected at Docker build time via GitHub Actions (`--build-arg VITE_APP_ENV=staging`). Banner renders when `import.meta.env.VITE_APP_ENV !== 'production'`. Baked into the static bundle — zero runtime overhead.
- Text: "STAGING — Not Production" (or similar unmissable phrasing — Claude's discretion on exact wording)

### First-user setup
- Manual seed script: `backend/scripts/seed_staging_user.py` — creates an admin user with a known staging password
- Run once after first successful deploy via `aws ecs run-task` with CMD override (same pattern as migration runs)
- User: `admin`, role: `admin` — full access for smoke testing including Holiday Maintenance
- Password: hardcoded in the script — staging is internal-only and RDS is not publicly accessible
- Documented in `docs/CICD.md` runbook under a new "First Deploy Checklist" section (alongside CICD setup steps from Phase 4)
- Script should be idempotent: if the admin user already exists, update password rather than fail

### ECS env config
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/Layout.tsx`: Single shared layout for all authenticated routes — add `StagingBanner` above the `<nav>` element here to cover all post-login pages
- `frontend/src/pages/Login.tsx`: Standalone page outside `Layout.tsx` — needs `StagingBanner` added separately (at top of the form container)
- `frontend/src/App.tsx`: Route structure is clean — no new routes needed for Phase 5
- `backend/config/settings.py`: `CORS_ORIGINS: list[str]` already defined — env var injection works natively with pydantic-settings
- `backend/auth/`: Existing auth module — seed script should reuse whatever password hashing utility exists here

### Established Patterns
- ECS one-off task pattern (from Phase 4): `aws ecs run-task --cluster intrepid-poc-qa --task-definition intrepid-poc-qa-app --overrides '{"containerOverrides":[{"name":"app","command":[...]}]}'` — seed script runs the same way as migrations
- `STORAGE_TYPE=local` active in local dev, `=s3` for staging — the switch is already wired in settings.py and storage factory
- IAM task role already grants S3 access to `intrepid-poc-qa` bucket (provisioned in Phase 3) — no new IAM changes needed for S3 storage
- `VITE_APP_ENV` follows the Vite convention for custom env vars (`import.meta.env.VITE_APP_ENV`) — no vite.config.ts changes needed

### Integration Points
- `ecs.tf` `environment` block on the app container: add CORS_ORIGINS, STORAGE_TYPE, S3_BUCKET_NAME, S3_REGION, LOG_LEVEL
- GitHub Actions workflow: add `--build-arg VITE_APP_ENV=staging` to the `docker build` step
- `Layout.tsx` and `Login.tsx`: import and render `StagingBanner` component
- `docs/CICD.md`: extend with "First Deploy Checklist" section

</code_context>

<specifics>
## Specific Ideas

- Banner positioning: above the nav (not inside it) so it doesn't shift nav layout — a separate full-width `<div>` as the first element in the page, above `<nav>`
- Seed script should use `aws ecs run-task` with the same subnet/security group pattern used for migration runs in Phase 4
- `CORS_ORIGINS` in Terraform should be a JSON array string matching pydantic-settings list format: `["http://alb-url", "http://localhost:5173"]`

</specifics>

<deferred>
## Deferred Ideas

- Smoke test automation (scripted API test hitting staging) — not required for v1.0 STAGE-02; manual verification is sufficient
- Private RDS endpoint (remove public accessibility) — v2.0 hardening
- Production environment setup — separate milestone

</deferred>

---

*Phase: 05-staging-deployment*
*Context gathered: 2026-03-06*
