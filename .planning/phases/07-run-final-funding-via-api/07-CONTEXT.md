# Phase 7: Application Hardening - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the deployed application across seven security and engineering-discipline areas:
AWS networking/TLS, default secrets and bootstrap passwords, frontend auth token storage,
file/error endpoint information leakage, CI security and quality gates, durable audit
logging, and repository hygiene. All seven areas are in scope.

This phase does not add new product features. It hardens what already exists.

</domain>

<decisions>
## Implementation Decisions

### 1. AWS Networking / TLS
- RDS must move to private subnets — remove `publicly_accessible = true` from `deploy/terraform/qa/rds.tf`
- ALB HTTPS: add TLS listener with ACM cert ARN as a Terraform variable (leave cert ARN to be filled in — not blocking the PR)
- Add HTTP → HTTPS redirect (port 80 → 443) in ALB listener rules
- Tighten security group egress: replace default `0.0.0.0/0` open egress in `deploy/terraform/qa/security-groups.tf:31` with minimal required rules

### 2. Default Secrets / Bootstrap Passwords
- App must fail startup (outside explicit local-dev mode) when `SECRET_KEY` is the hardcoded fallback (`backend/config/settings.py:52`)
- Remove default `admin123` password and other known analyst default passwords from `backend/scripts/seed_admin.py` and `README.md`
- Seed/reset scripts should generate a one-time random password and print it once — never a fixed known value
- Password policy at registration and reset: minimum 12 characters, at least one uppercase, one lowercase, one digit

### 3. Frontend Auth (localStorage replacement)
- Replace `localStorage` token handling in `frontend/src/contexts/AuthContext.tsx` with HttpOnly/Secure/SameSite=Strict cookies
- Backend login endpoint sets the cookie; frontend never stores the token in JS-accessible storage
- Add CSP header to backend responses
- Add rate limiting and failed-login monitoring to `backend/auth/routes.py` login endpoint (no current throttling/lockout)

### 4. File / Error Endpoint Leakage
- Never return `file://` URIs to clients — remove from `backend/api/files.py` and `backend/storage/local.py`
- Replace all `str(e)` / raw exception text in HTTP responses with generic client-facing messages plus a server-side correlation ID in logs
- Affects: `backend/api/files.py:44`, `backend/api/files.py:97`, `backend/api/files.py:165`
- All file area endpoints (inputs, outputs, output_share) must require authenticated user — no anonymous access

### 5. CI Security / Quality Gates
- Add a required CI job that runs before deploy in `deploy-test.yml`
- Tools: ruff (Python lint/format), mypy (type checks), pip-audit (Python dependency CVEs), npm audit (frontend), Terraform validate
- Job must be blocking — deploy cannot proceed if any gate fails

### 6. Durable Audit Logging
- Persist security-relevant events to a new `audit_log` Postgres table (not just application log output)
- Current `backend/auth/audit.py` only writes to the logger — upgrade to DB persistence
- Events to persist: login success/failure, file access, run start/cancel, admin actions, auth failures
- Table should include: event_type, user_id, timestamp, source_ip, resource, outcome, detail_json

### 7. Repository Hygiene
- Remove `loan-engine-qa.pem` (private key) from the workspace and ensure it is gitignored
- Remove generated deploy bundles (`deploy/aws/eb/app-bundle.zip`) from source control
- Confirm sample datasets under `backend/data/sample` are sanitized (no real PII)
- Enable secret scanning in GitHub CI (e.g. `git-secrets` or GitHub's built-in secret scanning)

### Claude's Discretion
- Specific ruff rule set and mypy strictness level — use sensible defaults for an existing codebase (not maximally strict)
- Correlation ID implementation detail (UUID header vs structured log field)
- Exact SG egress rules (allow only what ECS tasks need: RDS port, S3 endpoint, SES, ECR)
- CSP header specifics (allow same-origin, deny inline scripts except Vite dev build)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/auth/security.py`: `get_current_user`, `require_role` — existing auth middleware, will need cookie extraction added
- `backend/auth/audit.py`: existing audit functions (logger-only today) — add DB write here
- `backend/auth/routes.py:55`: login endpoint — add rate limiting and cookie-set response here
- `backend/config/settings.py`: settings model — add startup validation for SECRET_KEY here
- `deploy/terraform/qa/`: all existing Terraform files for networking changes

### Established Patterns
- Auth middleware: Bearer token from Authorization header (needs to add cookie fallback or replacement)
- Error handling: currently returns `str(e)` directly in multiple places — pattern to fix throughout `backend/api/files.py`
- Alembic migrations: existing migration workflow — new `audit_log` table goes through a migration

### Integration Points
- `frontend/src/contexts/AuthContext.tsx`: token read/write in localStorage (lines 34, 70, 107) — replace with cookie-based flow
- `backend/api/files.py`: file:// URL and raw exception leakage — fix here
- `backend/storage/local.py:100`: generates file:// URLs — remove
- `deploy-test.yml:27`: CI pipeline — add gates job before deploy step
- `deploy/terraform/qa/rds.tf:4,29`: public accessibility — remove
- `deploy/terraform/qa/alb.tf:16,36`: HTTP listener — add HTTPS + redirect
- `deploy/terraform/qa/security-groups.tf:31`: open egress — tighten

</code_context>

<specifics>
## Specific Ideas

- ALB HTTPS: cert ARN left as Terraform variable — plan should include the variable definition and instructions for filling it in, but not block on having a real cert
- Seed script one-time password: generate with `secrets.token_urlsafe(16)`, print once to stdout, never store in code
- CI gate job should be named `security-quality-gate` and listed as a `needs:` dependency of the deploy job
- Audit log table: use `TIMESTAMPTZ` for timestamp, `JSONB` for detail — consistent with existing `final_funding_job` pattern

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-run-final-funding-via-api*
*Context gathered: 2026-03-10*
