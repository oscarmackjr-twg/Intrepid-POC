# Deferred Items - Phase 07

## Out-of-Scope Issues Found During Execution

### 07-03: test_api_routes.py::TestAuthentication::test_login_success

**Found during:** Task 2 full-suite run
**Issue:** `test_api_routes.py` asserts `"access_token" in response.json()` but the
login endpoint was changed in Plan 05 (cookie-based auth) to return `{"user": {...}}`
without exposing the token in the body. The test has been stale since that change.
**Status:** Pre-existing failure — not caused by 07-03 changes
**Fix needed:** Update test to check for `"user" in response.json()` (matching the
new `LoginResponse` model) instead of `"access_token" in response.json()`
