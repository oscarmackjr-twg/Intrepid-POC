# Phase 5: Staging Deployment — Verification

**Verified:** 2026-03-22
**Verifier:** Human smoke test (Phase 8, Plan 08-02)
**Status:** PASSED

## Requirements Verified

| Requirement | Description | Result | Evidence |
|-------------|-------------|--------|----------|
| STAGE-01 | Staging URL is accessible and app loads after CI/CD deploy | PASS | Login page loaded at http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com |
| STAGE-02 | Ops team can log in and upload a file in staging | PASS | Admin logged in with admin/IntrepidStaging2024!; sample .xlsx upload accepted |
| STAGE-03 | Staging environment has an unmissable banner (not production) | PASS | Amber "STAGING — Not Production" banner visible on Login page and all 8 authenticated pages; banner sticky on scroll |

## Gap Closure

This verification closes the gap created when Phase 5 Plan 03 stalled due to the Secure cookie
failure over HTTP ALB (MISS-02). The root cause was LOCAL_DEV_MODE=false in the ECS task
definition, causing FastAPI to set secure=True on the login cookie. HTTP ALB silently drops
secure cookies; the session was never stored.

**Fix applied in Phase 8:**
- Plan 08-01: Added LOCAL_DEV_MODE=true to deploy/docker-compose.yml (MISS-01); terraform
  applied to register new ECS task definition revision with LOCAL_DEV_MODE=true (MISS-02)
- Plan 08-02: CI/CD triggered via push to main; ECS force-new-deployment picked up new task
  def; smoke test confirmed login, upload, and banner functional

## Verification Notes

- StagingBanner was implemented in Phase 5 Plan 01 (VITE_APP_ENV=staging baked into Docker image
  at build time via ARG/ENV in Dockerfile + --build-arg in deploy-test.yml)
- Staging admin user was seeded in Phase 5 Plan 02 (seed_staging_user.py); user persists in RDS
- ALB URL: http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com
- ECS cluster: intrepid-poc-qa, service: intrepid-poc-qa, region: us-east-1
