---
phase: 07-run-final-funding-via-api
plan: "05"
subsystem: auth
tags: [cookie-auth, rate-limiting, csp, security, frontend, HARD-03]
dependency_graph:
  requires: ["07-01", "07-03", "07-04"]
  provides: [cookie-based-auth-end-to-end, rate-limited-login, csp-header]
  affects: [backend/auth, backend/api/main.py, frontend/src/contexts/AuthContext.tsx]
tech_stack:
  added: [slowapi>=0.1.9]
  patterns: [HttpOnly cookie auth, SameSite=Strict, slowapi rate limiting, CSP middleware, password strength validation]
key_files:
  created:
    - backend/auth/limiter.py
    - backend/tests/test_auth_security.py
  modified:
    - backend/auth/routes.py
    - backend/auth/security.py
    - backend/api/main.py
    - backend/config/settings.py
    - backend/auth/validators.py
    - backend/tests/conftest.py
    - backend/tests/test_auth_routes.py
    - backend/tests/test_api_routes.py
    - frontend/src/contexts/AuthContext.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/pages/ProgramRuns.tsx
    - backend/requirements.txt
decisions:
  - "slowapi Limiter defined in auth/limiter.py (not api/main.py) to avoid circular import between routes and main"
  - "LOCAL_DEV_MODE=True in .env disables cookie secure flag for local HTTP dev; staging sets it False for HTTPS"
  - "Authorization header fallback kept in get_current_user for API clients and CI scripts"
  - "Password strength validator added to UserCreate (HARD-02 scope, implemented as part of linter enforcement)"
  - "DB isolation in tests switched to rollback-based (connection.begin() + transaction.rollback()) for true per-test isolation"
  - "limiter._storage.reset() called in client fixture to prevent rate limit state bleeding between tests"
metrics:
  duration: 45min
  completed_date: "2026-03-10"
  tasks_completed: 2
  files_modified: 12
---

# Phase 7 Plan 5: HttpOnly Cookie Auth, Rate Limiting, CSP Header Summary

**One-liner:** Cookie-based JWT auth replacing localStorage tokens — HttpOnly/SameSite=Strict cookie, slowapi 10/min rate limit on login, CSP middleware on all responses, frontend withCredentials.

## What Was Built

### Task 1: Backend (TDD RED then GREEN)

**`backend/auth/limiter.py`** (new)
Shared `slowapi.Limiter` instance defined in its own module to prevent circular import between `api/main.py` (app wiring) and `auth/routes.py` (decorator usage).

**`backend/auth/routes.py`**
- Login endpoint: adds `response: Response` parameter, calls `response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, secure=not LOCAL_DEV_MODE, samesite="strict")`. Token removed from JSON response body.
- New `POST /api/auth/logout` endpoint: calls `response.delete_cookie("access_token")`.
- `@limiter.limit("10/minute")` decorator on login.
- `UserCreate.validate_password_strength` field validator: min 12 chars, uppercase, lowercase, digit.

**`backend/auth/security.py`**
- `get_current_user` signature changed from `OAuth2PasswordBearer` to cookie+header dual-path.
- Cookie takes precedence (`Cookie(default=None, alias="access_token")`), then `Authorization` header fallback for API clients.

**`backend/api/main.py`**
- `app.state.limiter = limiter` + `RateLimitExceeded` exception handler wired.
- `CSPMiddleware` added (BaseHTTPMiddleware): sets `Content-Security-Policy` header on all responses.
- CORS already had `allow_credentials=True` and explicit origin list.

**`backend/config/settings.py`**
- `LOCAL_DEV_MODE: bool = False` field added; gating `secure=not LOCAL_DEV_MODE` on cookie.
- `KNOWN_FALLBACK_SECRET` validator: blocks startup in non-dev mode if SECRET_KEY is default.

**`backend/auth/validators.py`**
- Auto-fixed (Rule 1): "own role" check moved before `validate_sales_team_assignment` call. Previously a 400 pre-empted the intended 403 when admin tried to change own role to sales_team without sales_team_id.

**`backend/tests/conftest.py`**
- Auto-fixed (Rule 2): `test_db_session` switched to rollback-based isolation (`connection.begin()` + `transaction.rollback()`) — prevents UNIQUE constraint failures from user fixtures accumulating across tests.
- `client` fixture now calls `limiter._storage.reset()` before each test — prevents rate limit hits from one test bleeding into the next.
- Added shared `client`, `auth_headers_admin`, `auth_headers_sales` fixtures (previously only in `test_api_routes.py`).

### Task 2: Frontend

**`frontend/src/contexts/AuthContext.tsx`**
- All 6 `localStorage` references removed.
- `axios.defaults.withCredentials = true` set at module level.
- `useEffect` now calls `fetchUser()` unconditionally — if cookie present, `/api/auth/me` succeeds; if not, 401 is handled.
- `login()` no longer reads `access_token` from response body — extracts `user` field only.
- `logout()` now calls `POST /api/auth/logout` (server clears cookie) then navigates to `/login`.
- `token` state and `AuthContextType.token` field removed.

**`frontend/src/pages/Dashboard.tsx`** and **`ProgramRuns.tsx`**
- Removed `localStorage.getItem('token')` guards (5 total) — cookie is sent automatically by axios.

## Tests

| File | Tests | Result |
|------|-------|--------|
| test_auth_routes.py::TestCookieLogin | 5 | GREEN |
| test_auth_routes.py::TestRateLimit | 1 | GREEN |
| test_auth_security.py (all) | 5 | GREEN |
| test_auth_routes.py (all) | 23 | GREEN |
| test_api_routes.py (all) | 9 | GREEN |
| test_auth_validators.py (all) | 16 | GREEN |

**Total: 53 tests GREEN**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix own-role check order in `validate_user_update`**
- **Found during:** Task 1 full suite run
- **Issue:** `validate_sales_team_assignment` was called before "cannot change own role" check. Raised HTTP 400 instead of expected HTTP 403 when admin tried to change own role to sales_team without sales_team_id.
- **Fix:** Reordered checks — "own role" guard now runs first.
- **Files modified:** `backend/auth/validators.py`
- **Commit:** 82e2d44

**2. [Rule 2 - Missing critical functionality] DB isolation via rollback in test fixtures**
- **Found during:** Task 1 test runs — UNIQUE constraint errors across tests
- **Issue:** `test_db_session` used `session.close()` only; previous test data persisted in session-scoped in-memory SQLite engine.
- **Fix:** Switched to `connection.begin()` + `transaction.rollback()` pattern for true per-test isolation.
- **Files modified:** `backend/tests/conftest.py`
- **Commit:** 82e2d44

**3. [Rule 2 - Missing critical functionality] Rate limiter state reset between tests**
- **Found during:** Task 1 test runs — `TestRateLimit` exhausted rate limit causing subsequent login tests in same run to fail with 429
- **Fix:** `client` fixture calls `limiter._storage.reset()` before yielding `TestClient`
- **Files modified:** `backend/tests/conftest.py`
- **Commit:** 82e2d44

**4. [Rule 1 - Bug] Remove localStorage token guards in Dashboard.tsx and ProgramRuns.tsx**
- **Found during:** Task 2 grep for localStorage
- **Issue:** 5 locations reading `localStorage.getItem('token')` as auth guards — these will always return `null` after cookie migration
- **Fix:** Removed guards; cookie is sent automatically via `axios.defaults.withCredentials = true`
- **Files modified:** `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/ProgramRuns.tsx`
- **Commit:** 558f997

**5. [Rule 2 - Security] Password strength validation (HARD-02 scope)**
- **Found during:** Linter added `TestPasswordPolicy` tests to `test_auth_routes.py`
- **Note:** This is technically HARD-02 scope but the linter enforced it by adding tests. Implemented `UserCreate.validate_password_strength` field validator to satisfy the tests.
- **Files modified:** `backend/auth/routes.py`
- **Commit:** 82e2d44

## Out-of-Scope Failures (Pre-existing)

Failures in `test_rules_eligibility.py`, `test_rules_purchase_price.py`, `test_scheduler.py`, and `test_eligibility_complete.py` are pre-existing and not caused by this plan's changes. Logged in `deferred-items.md`.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| backend/auth/limiter.py | FOUND |
| backend/tests/test_auth_security.py | FOUND |
| 07-05-SUMMARY.md | FOUND |
| Commit 98a8794 (RED tests) | FOUND |
| Commit 82e2d44 (backend GREEN) | FOUND |
| Commit 558f997 (frontend) | FOUND |
| 53 auth tests GREEN | VERIFIED |
