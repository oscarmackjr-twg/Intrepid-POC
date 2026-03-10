---
phase: 07-run-final-funding-via-api
plan: 03
subsystem: auth
tags: [pydantic, password-policy, secrets, settings, seed-script]

requires:
  - phase: 07-01
    provides: Wave 0 RED test scaffolds for HARD-02 (test_settings_guard.py, test_seed_admin.py)

provides:
  - Settings startup guard rejecting default SECRET_KEY unless LOCAL_DEV_MODE=true
  - generate_password() function in seed_admin.py using secrets.token_urlsafe(18)
  - Password policy validator on UserCreate enforcing 12-char, upper, lower, digit
  - All test_settings_guard.py and test_seed_admin.py tests GREEN

affects: [07-04, 07-05, 07-06, deploy]

tech-stack:
  added: [slowapi>=0.1.9 (already present from prior plan)]
  patterns:
    - "Settings model_validator raises ValueError when sentinel SECRET_KEY used outside LOCAL_DEV_MODE"
    - "secrets.token_urlsafe(18) generates 24-char URL-safe passwords for seed scripts"
    - "pydantic field_validator on password field enforces strength policy at schema level"

key-files:
  created: []
  modified:
    - backend/config/settings.py
    - backend/scripts/seed_admin.py
    - backend/auth/routes.py
    - backend/tests/test_auth_routes.py
    - backend/.env.example

key-decisions:
  - "LOCAL_DEV_MODE: bool = False field serves dual purpose — bypasses SECRET_KEY sentinel guard AND controls cookie secure flag (consolidated from two separate additions by parallel agents)"
  - "generate_password() extracted as importable function in seed_admin.py so test_seed_admin.py can call it directly without DB connection"
  - "Existing test_auth_routes.py register tests updated from 'testpass' to 'TestPass123!' to comply with new password policy validator"
  - "test_api_routes.py::TestAuthentication::test_login_success pre-existing failure deferred — broken by Plan 05 cookie-auth change, not by Plan 03"

patterns-established:
  - "Password policy: min 12 chars, at least one uppercase, one lowercase, one digit — enforced at Pydantic schema level, returns 422 automatically"
  - "Seed script never stores or prints hardcoded passwords — generate_password() called per-user"

requirements-completed: [HARD-02]

duration: 25min
completed: 2026-03-10
---

# Phase 07 Plan 03: Application Secret Guard and Password Policy Summary

**Pydantic model_validator blocks startup with default SECRET_KEY, seed_admin generates random passwords via secrets.token_urlsafe, and UserCreate field_validator enforces 12-char password strength policy**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-10T19:56:18Z
- **Completed:** 2026-03-10T20:21:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Settings.validate_secret_key model_validator raises ValueError when SECRET_KEY equals sentinel and LOCAL_DEV_MODE is False — prevents accidental production deployment with default credentials
- seed_admin.py generate_password() uses secrets.token_urlsafe(18) producing 24-char URL-safe passwords; all hardcoded "admin123" and "twg123" references removed
- UserCreate.validate_password_strength field_validator enforces minimum 12 chars, uppercase, lowercase, and digit — returns 422 automatically via Pydantic
- All 27 tests across test_settings_guard.py, test_seed_admin.py, and test_auth_routes.py pass GREEN

## Task Commits

1. **Task 1: SECRET_KEY startup guard and LOCAL_DEV_MODE escape hatch** - `6bcdf7b` (feat)
   - Consolidated duplicate LOCAL_DEV_MODE field (parallel agents had added it in two places with conflicting defaults)
   - Added validate_secret_key model_validator
   - Added LOCAL_DEV_MODE=true to .env, LOCAL_DEV_MODE=false to .env.example

2. **Task 2: Seed script one-time passwords and schema password policy validator** - Already committed by parallel agents in prior plan runs (commits `93f3148`, `56a1bf7`)
   - seed_admin.py: generate_password() function, removed hardcoded passwords
   - auth/routes.py: validate_password_strength field_validator on UserCreate
   - test_auth_routes.py: TestPasswordPolicy class added, existing passwords updated to TestPass123!

## Files Created/Modified

- `backend/config/settings.py` - Added LOCAL_DEV_MODE: bool = False field and validate_secret_key model_validator; fixed duplicate field from parallel agent runs
- `backend/scripts/seed_admin.py` - Added generate_password() using secrets.token_urlsafe(18); removed "admin123" and "twg123" defaults; create_admin_user no longer accepts password as positional arg
- `backend/auth/routes.py` - Added validate_password_strength field_validator to UserCreate (12-char, upper, lower, digit policy)
- `backend/tests/test_auth_routes.py` - Added TestPasswordPolicy class with 5 tests; updated existing register test passwords from "testpass" to "TestPass123!"
- `backend/.env.example` - Added LOCAL_DEV_MODE=false comment line

## Decisions Made

- LOCAL_DEV_MODE field consolidated: parallel agents had added it in two separate locations (one for SECRET_KEY guard with `False` default, one for cookie security with `True` default). Resolved by keeping a single field after the Security section with `False` default, serving both purposes.
- generate_password() extracted as public function to enable direct unit testing without database dependencies.
- Existing TestUserRegistration tests updated to use policy-compliant passwords — necessary correctness fix per Rule 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed duplicate LOCAL_DEV_MODE field in Settings**
- **Found during:** Task 1 (Settings startup guard)
- **Issue:** settings.py had LOCAL_DEV_MODE defined twice — first with `bool = False` (for SECRET_KEY guard) and second with `bool = True` (added by prior parallel plan for cookie security). Python resolves duplicate class attributes to the last definition, so the guard was effectively disabled by default.
- **Fix:** Removed the first definition (before validate_secret_key), kept the single field after CORS_ORIGINS with `bool = False` default
- **Files modified:** backend/config/settings.py
- **Verification:** pytest tests/test_settings_guard.py passes — both tests GREEN
- **Committed in:** `6bcdf7b`

**2. [Rule 1 - Bug] Updated existing test passwords to comply with new policy**
- **Found during:** Task 2 (password policy validation)
- **Issue:** TestUserRegistration tests use "testpass" which now fails the 12-char/uppercase/digit validator — causing 4 pre-existing tests to fail with 422
- **Fix:** Replaced "testpass" with "TestPass123!" in all register-endpoint tests
- **Files modified:** backend/tests/test_auth_routes.py
- **Verification:** All 23 auth route tests pass
- **Committed in:** `56a1bf7` (already committed by parallel agent)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- Parallel agents had already committed most of this plan's implementation in prior runs (seed_admin.py, auth/routes.py, test_auth_routes.py changes were in commits `93f3148` and `56a1bf7`). Only settings.py needed a new commit to fix the duplicate field.
- `test_api_routes.py::TestAuthentication::test_login_success` is a pre-existing failure (checks for `access_token` in body but Plan 05 changed login to use HttpOnly cookies). Logged to deferred-items.md.

## Self-Check

All 27 tests pass across the three relevant test files.

## Next Phase Readiness

- HARD-02 requirements complete: startup guard, one-time passwords, password policy all implemented
- Plan 04 (error sanitization and audit logging) has its SUMMARY already committed — all Phase 7 implementation appears complete from parallel agent execution
- Requirements ready for Plan 04/05/06 which depend on HARD-02 foundation

---
*Phase: 07-run-final-funding-via-api*
*Completed: 2026-03-10*
