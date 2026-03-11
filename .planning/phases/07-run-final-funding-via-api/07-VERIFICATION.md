---
phase: 07-run-final-funding-via-api
verified: 2026-03-10T22:00:00Z
status: human_needed
score: 15/15 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 14/15
  gaps_closed:
    - "Login success/failure events are persisted to the audit_log DB table"
    - "README no longer shows admin123 as a login credential"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Verify HTTPS redirect works once ACM cert ARN is configured"
    expected: "HTTP requests to ALB on port 80 receive 301 redirect to HTTPS on port 443"
    why_human: "ALB HTTPS listener is count-gated on acm_certificate_arn — cert ARN not set in QA yet; cannot test redirect end-to-end without a live cert"
  - test: "Verify rate limiting triggers on 11th login within 1 minute"
    expected: "11th POST /api/auth/login within 60 seconds returns 429 Too Many Requests"
    why_human: "Rate limiting verified in unit tests with slowapi; production ALB/ECS behavior with real IP may differ due to X-Forwarded-For header handling"
  - test: "Confirm TruffleHog CI step passes on a real push"
    expected: "TruffleHog secret scan passes with --only-verified flag"
    why_human: "CI workflow validated for syntax and structure; actual secret scan run requires GitHub Actions environment"
  - test: "Confirm RDS is unreachable from public internet after terraform apply"
    expected: "Attempting TCP connection to RDS endpoint from outside VPC fails"
    why_human: "Terraform validated but not applied — RDS publicly_accessible=false not yet active in QA"
---

# Phase 7: Application Hardening Verification Report

**Phase Goal:** Harden the deployed application across seven areas: AWS networking/TLS, default secrets and bootstrap passwords, frontend auth token storage (localStorage to HttpOnly cookies), file/error endpoint information leakage, CI security and quality gates, durable audit logging, and repository hygiene.
**Verified:** 2026-03-10T22:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (07-07-PLAN.md)

## Re-Verification Summary

| Item | Previous Status | Current Status |
|------|----------------|----------------|
| Login success event persisted to audit_log | FAILED | VERIFIED |
| Login failure event persisted to audit_log | FAILED | VERIFIED |
| README no longer shows admin123 | Warning | VERIFIED |
| All 14 other previously-passing truths | VERIFIED | VERIFIED (regression check passed) |

**Gap closure commits verified:**
- `e3585ca` — feat(07-07): wire db session to login audit calls + assert DB rows in tests
- `3b6e87c` — docs(07-07): remove hardcoded admin123 from README credential section

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | App fails startup with fallback SECRET_KEY unless LOCAL_DEV_MODE=true | VERIFIED | settings.py model_validator raises ValueError; .env has LOCAL_DEV_MODE=true; test_settings_guard.py GREEN |
| 2 | Seed script generates one-time random passwords — no hardcoded defaults | VERIFIED | seed_admin.py uses secrets.token_urlsafe(18); no "admin123" in file; test_seed_admin.py GREEN |
| 3 | Passwords shorter than 12 chars or lacking uppercase/digit rejected with 422 | VERIFIED | validate_password_strength field_validator in routes.py; TestPasswordPolicy GREEN |
| 4 | Login sets HttpOnly/SameSite=Strict cookie, no token in JSON body | VERIFIED | routes.py: httponly=True at line 105, samesite="strict" at line 107; TestCookieLogin GREEN |
| 5 | get_current_user accepts cookie before Authorization header | VERIFIED | security.py Cookie(default=None) + header fallback; test_auth_security.py GREEN |
| 6 | Login rate-limited to 10/minute; CSP header on all responses; CORS has allow_credentials | VERIFIED | @limiter.limit("10/minute"); CSPMiddleware in main.py; allow_credentials=True |
| 7 | Frontend uses withCredentials, no localStorage token storage | VERIFIED | axios.defaults.withCredentials=true at AuthContext.tsx line 31; no localStorage token write |
| 8 | File list/upload/URL/delete errors return correlation ID messages, not raw exceptions | VERIFIED | files.py: 6 exception handlers all use uuid.uuid4() correlation_id; no str(e) in responses |
| 9 | local.py returns /api/files/download/ paths, not file:// URIs | VERIFIED | local.py returns f"/api/files/download/{path}"; test_storage_local.py GREEN |
| 10 | AuditLog DB table exists with correct schema; log_user_action writes rows to DB | VERIFIED | db/models.py AuditLog class; migration efe3898fdf4b; audit.py db.add(entry) at line 73 |
| 11 | Login success event persisted to audit_log DB table | VERIFIED | routes.py line 112: log_user_action('login', user, db=db, outcome='success') — confirmed in codebase |
| 12 | Login failure event persisted to audit_log DB table | VERIFIED | routes.py line 85: log_user_action('login_failed', user, db=db, outcome='failure', details=...) — confirmed in codebase |
| 13 | security-quality-gate CI job exists and blocks deploy | VERIFIED | deploy-test.yml: security-quality-gate job at line 21; deploy job has needs: [security-quality-gate] at line 72 |
| 14 | security-quality-gate runs: ruff, mypy, pip-audit, npm audit, terraform validate, TruffleHog | VERIFIED | All 8 steps present in deploy-test.yml |
| 15 | app-bundle.zip removed from git tracking; .gitignore blocks future bundles | VERIFIED | git ls-files returns empty for bundle; .gitignore line 8: deploy/aws/eb/*.zip |

**Score:** 15/15 truths verified

### Required Artifacts

| Artifact | Requirement | Status | Details |
|----------|------------|--------|---------|
| `backend/config/settings.py` | HARD-02 | VERIFIED | LOCAL_DEV_MODE field + validate_secret_key model_validator present |
| `backend/scripts/seed_admin.py` | HARD-02 | VERIFIED | generate_password() uses secrets.token_urlsafe(18); no hardcoded passwords |
| `backend/auth/routes.py` | HARD-02, HARD-03, HARD-06 | VERIFIED | validate_password_strength; set_cookie(httponly=True); @limiter.limit; log_user_action with db=db at both login call sites |
| `backend/auth/security.py` | HARD-03 | VERIFIED | Cookie(default=None, alias="access_token") + Authorization header fallback |
| `backend/auth/limiter.py` | HARD-03 | VERIFIED | Shared Limiter instance to avoid circular import |
| `backend/api/main.py` | HARD-03 | VERIFIED | app.state.limiter; CSPMiddleware; CORS with allow_credentials=True and explicit origins |
| `frontend/src/contexts/AuthContext.tsx` | HARD-03 | VERIFIED | withCredentials=true at line 31; zero localStorage token storage |
| `backend/api/files.py` | HARD-04 | VERIFIED | correlation_id pattern in all 6 exception handlers; no str(e) in HTTP detail |
| `backend/storage/local.py` | HARD-04 | VERIFIED | Returns /api/files/download/{path} — no file:// URI |
| `backend/db/models.py` | HARD-06 | VERIFIED | class AuditLog with id, event_type, user_id, timestamp, source_ip, resource, outcome, detail_json |
| `backend/auth/audit.py` | HARD-06 | VERIFIED | db.add(entry) + db.commit() when db session passed |
| `backend/migrations/versions/efe3898fdf4b_add_audit_log_table.py` | HARD-06 | VERIFIED | op.create_table('audit_log') with all columns + indexes |
| `backend/tests/test_auth_routes.py` | HARD-06 | VERIFIED | TestLoginAuditLog class at line 365 with 3 DB-persistence tests |
| `.github/workflows/deploy-test.yml` | HARD-05 | VERIFIED | security-quality-gate job; deploy needs: [security-quality-gate]; 8 tool steps |
| `deploy/terraform/qa/rds.tf` | HARD-01 | VERIFIED | publicly_accessible=false at line 32; aws_subnet.private[*].id |
| `deploy/terraform/qa/alb.tf` | HARD-01 | VERIFIED | HTTP redirect + count-gated HTTPS listener; var.acm_certificate_arn |
| `deploy/terraform/qa/security-groups.tf` | HARD-01 | VERIFIED | ecs_to_rds, ecs_https_out, ecs_dns_out rules |
| `deploy/terraform/qa/variables.tf` | HARD-01 | VERIFIED | acm_certificate_arn variable with default="" |
| `.gitignore` | HARD-07 | VERIFIED | deploy/aws/eb/*.zip at line 8; loan-engine-qa.pem at line 3 |
| `README.md` | HARD-02 | VERIFIED | admin123 removed — grep returns 0 matches; seed_admin.py instructions in place |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| backend/config/settings.py | backend/.env | LOCAL_DEV_MODE env var | WIRED | .env: LOCAL_DEV_MODE=true |
| backend/auth/routes.py | backend/auth/audit.py | log_user_action on login success | WIRED | Line 112: log_user_action('login', user, db=db, outcome='success') |
| backend/auth/routes.py | backend/auth/audit.py | log_user_action on login failure | WIRED | Line 85: log_user_action('login_failed', user, db=db, outcome='failure', ...) |
| backend/auth/security.py | cookie or header | Cookie(default=None) fallback | WIRED | security.py tries cookie first then Authorization header |
| frontend/src/contexts/AuthContext.tsx | backend/auth/routes.py | withCredentials POST /api/auth/login | WIRED | axios.defaults.withCredentials=true; login() posts without expecting token body |
| backend/api/main.py | backend/config/settings.py | settings.CORS_ORIGINS | WIRED | main.py allow_origins=settings.CORS_ORIGINS |
| backend/auth/audit.py | backend/db/models.py | AuditLog import | WIRED | audit.py: from db.models import User, AuditLog |
| deploy/terraform/qa/rds.tf | deploy/terraform/qa/main.tf | aws_subnet.private[*].id | WIRED | rds.tf line 6 references private subnets |
| deploy/terraform/qa/alb.tf | deploy/terraform/qa/variables.tf | var.acm_certificate_arn | WIRED | alb.tf count-gates HTTPS listener on var.acm_certificate_arn |
| .github/workflows/deploy-test.yml:security-quality-gate | .github/workflows/deploy-test.yml:deploy | needs: [security-quality-gate] | WIRED | deploy job line 72: needs: [security-quality-gate] |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|------------|-------------|-------------|--------|---------|
| HARD-01 | 07-02 | AWS networking/TLS: RDS private subnets, ALB HTTPS, SG egress tightening | SATISFIED | rds.tf publicly_accessible=false; alb.tf HTTPS listener; security-groups.tf tightened |
| HARD-02 | 07-01, 07-03, 07-07 | Default secrets guard, seed one-time passwords, password policy, README cleanup | SATISFIED | validate_secret_key; secrets.token_urlsafe(18); validate_password_strength; README admin123 removed |
| HARD-03 | 07-01, 07-05 | HttpOnly cookie auth, rate limiting, CSP, frontend localStorage removal | SATISFIED | set_cookie(httponly=True, samesite="strict"); @limiter.limit; CSPMiddleware; withCredentials; no localStorage |
| HARD-04 | 07-01, 07-04 | File/error leakage: no file:// URIs, sanitized errors with correlation IDs | SATISFIED | 6 handlers in files.py use correlation IDs; local.py returns /api/files/download/ |
| HARD-05 | 07-06 | CI security/quality gates blocking deploy | SATISFIED | security-quality-gate job with ruff, mypy, pip-audit, npm audit, terraform validate, TruffleHog; blocks deploy |
| HARD-06 | 07-01, 07-04, 07-05, 07-07 | Durable audit logging: AuditLog DB table, DB persistence for login events | SATISFIED | AuditLog model + migration + audit.py DB write + routes.py passes db=db at both login call sites + 3 TDD tests |
| HARD-07 | 07-02 | Repository hygiene: tracked secrets/bundles removed, gitignore, secret scanning | SATISFIED | app-bundle.zip untracked; .gitignore has *.zip rule; TruffleHog in CI |

### Anti-Patterns Found

None detected in gap-closure files. Previously noted anti-patterns resolved:

| File | Pattern | Previous Severity | Current Status |
|------|---------|-------------------|----------------|
| backend/auth/routes.py lines 85, 112 | log_user_action without db= | Warning | RESOLVED — db=db now passed at both call sites |
| README.md lines 81, 93 | admin123 hardcoded credential | Warning | RESOLVED — admin123 removed; seed_admin.py instructions in place |

### Human Verification Required

#### 1. ALB HTTPS Redirect End-to-End

**Test:** Configure `acm_certificate_arn` in terraform.tfvars and run `terraform apply`, then attempt HTTP request to ALB on port 80.
**Expected:** HTTP 301 redirect to HTTPS on port 443.
**Why human:** ALB HTTPS listener is count-gated on the cert ARN variable, which is currently empty string. Cannot test the redirect path without a real ACM cert applied.

#### 2. Rate Limiting Under Real Load

**Test:** From outside localhost (or using a real IP), make 11 consecutive POST requests to `/api/auth/login` within 60 seconds.
**Expected:** The 11th request returns HTTP 429 Too Many Requests.
**Why human:** slowapi rate limiting uses `get_remote_address`. In unit tests, limiter state is reset between tests. Real behavior behind ECS/ALB with X-Forwarded-For header handling needs validation.

#### 3. TruffleHog CI Pass

**Test:** Push a branch and observe the security-quality-gate job in GitHub Actions.
**Expected:** TruffleHog step completes without flagging verified secrets.
**Why human:** YAML structure verified locally. Actual scan requires the GitHub Actions runner environment to execute trufflesecurity/trufflehog-actions-scan@main.

#### 4. RDS Public Accessibility After Apply

**Test:** After `terraform apply`, attempt a TCP connection to the RDS endpoint from outside the VPC.
**Expected:** Connection refused or times out (no public route).
**Why human:** Terraform validated but changes not applied to AWS. `publicly_accessible=false` and private subnets only take effect after apply.

## Test Suite Results

| Test File | Tests | Result |
|-----------|-------|--------|
| test_settings_guard.py | 2 | 2 GREEN |
| test_seed_admin.py | 2 | 2 GREEN |
| test_auth_security.py | 5 | 5 GREEN |
| test_api_files.py | 4 | 4 GREEN |
| test_storage_local.py | 4 | 4 GREEN |
| test_audit_log.py | 7 | 7 GREEN |
| test_auth_routes.py | 26 | 26 GREEN (23 original + 3 new TestLoginAuditLog) |
| **Total Phase 7** | **50** | **50 GREEN** |

## Goal Achievement Summary

All 7 HARD requirements are fully satisfied in code. All 15 observable truths verify. All 10 key links are wired. 50 automated tests pass.

Four items remain for human/environment verification (ALB HTTPS, real-IP rate limiting, GitHub Actions TruffleHog, and RDS post-apply network isolation). These are infrastructure-level confirmations that require the live AWS environment or the GitHub Actions runner — they cannot be verified programmatically against the repository alone.

---

_Verified: 2026-03-10T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: gap closed by 07-07 (commits e3585ca, 3b6e87c)_
