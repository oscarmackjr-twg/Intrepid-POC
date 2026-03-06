---
phase: 04-cicd-pipeline
plan: 02
subsystem: infra
tags: [github-actions, ecs, ecr, oidc, alembic, fargate]

requires:
  - phase: 04-cicd-pipeline/04-01
    provides: IAM OIDC role, GitHub repo variables AWS_ROLE_ARN/ECS_SUBNET_IDS/ECS_SECURITY_GROUP configured

provides:
  - Full GitHub Actions deploy pipeline: OIDC auth, ECR build/push, Alembic migration gate, ECS deploy, stability wait
  - deploy-test.yml triggers on push to main — no manual steps required

affects:
  - 05-staging
  - Any future CI/CD changes

tech-stack:
  added: []
  patterns:
    - OIDC role assumption (no static credentials in GitHub Secrets)
    - ECS one-off run-task for database migrations before service deploy
    - Blocking stability wait (aws ecs wait services-stable) as hard failure gate

key-files:
  created: []
  modified:
    - .github/workflows/deploy-test.yml

key-decisions:
  - "deploy-test.yml retained as filename (no rename needed — workflow is now correctly scoped to QA)"
  - "Task definition name matches cluster name (intrepid-poc-qa) — this is the Terraform family = local.name_prefix pattern"
  - "TASK_ARN written to GITHUB_ENV so downstream steps (wait, exit-code-check) can reference it without shell subshell loss"

patterns-established:
  - "Migration gate pattern: run-task → wait tasks-stopped → describe-tasks exitCode check → abort on non-zero"
  - "OIDC pattern: permissions id-token: write at job level, role-to-assume: vars.AWS_ROLE_ARN (vars. not secrets.)"

requirements-completed: [CICD-01, CICD-02]

duration: 1min
completed: 2026-03-06
---

# Phase 4 Plan 02: CI/CD Workflow Rewrite Summary

**GitHub Actions deploy pipeline rewritten: OIDC auth replaces static credentials, Alembic migration runs as ECS one-off task before deploy, blocking services-stable wait added, all resource names corrected to intrepid-poc-qa**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-06T18:37:39Z
- **Completed:** 2026-03-06T18:38:51Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Replaced static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` inputs with OIDC `role-to-assume: ${{ vars.AWS_ROLE_ARN }}`
- Fixed all wrong resource names: `ECR_REPO_NAME`, `ECS_CLUSTER`, `ECS_SERVICE` all now reference `intrepid-poc-qa`
- Added Alembic migration step (ECS `run-task` + `wait tasks-stopped` + exit code check) that aborts deploy on non-zero exit
- Added `aws ecs wait services-stable` blocking wait after `update-service` — deploy fails hard on timeout

## Task Commits

1. **Task 1: Rewrite deploy-test.yml** - `521e45e` (feat)

**Plan metadata:** (following in this commit)

## Files Created/Modified

- `.github/workflows/deploy-test.yml` — Complete rewrite: OIDC auth, correct ECR/ECS names, migration gate, stability wait

## Decisions Made

- Filename kept as `deploy-test.yml` — no rename required; comment updated to reflect QA scope
- Task definition family name is `intrepid-poc-qa` (matches `ECS_CLUSTER` env var) — this follows the Terraform `local.name_prefix` pattern established in Phase 3
- `TASK_ARN` exported to `$GITHUB_ENV` (not captured inline) so all three migration steps (run-task, wait, check) share the same ARN without subshell scope issues

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - all GitHub repo variables (AWS_ROLE_ARN, ECS_SUBNET_IDS, ECS_SECURITY_GROUP) were configured in Plan 01. Push to main will trigger the full pipeline automatically.

## Next Phase Readiness

- CI/CD pipeline is complete end-to-end for QA environment
- First live run will validate OIDC handshake, ECR push, migration, and ECS deploy in sequence
- Phase 5 (staging) can reference this workflow pattern for promotion pipeline

---
*Phase: 04-cicd-pipeline*
*Completed: 2026-03-06*
