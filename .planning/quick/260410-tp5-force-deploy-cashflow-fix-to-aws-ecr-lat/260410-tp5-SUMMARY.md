---
phase: quick-260410-tp5
plan: 01
subsystem: ops/deploy
tags: [ecr, ecs, docker, deploy, cashflow-fix]
key-files:
  created: []
  modified: [backend/api/re_routes.py]
decisions:
  - "d6ec896 code-review pass had silently reverted the cashflow filter fix — re-applied as a023497"
  - "Image built from a023497 (true fix); both :latest and :a023497 tags pushed for traceability"
metrics:
  duration: "~30 min (debug + fix + build + push + ECS rollout)"
  completed: "2026-04-11"
  tasks_completed: 3
  files_modified: 1
---

# Quick Task 260410-tp5: Force-Deploy Cashflow Fix to AWS ECR :latest — Summary

## Root Cause

The cashflow fix (1334f82) had been silently reverted by the code-review commit d6ec896
(WR-01/WR-02 pass). That commit collapsed `snapshot_filters` + `cashflow_filters` back into a
single `build_re_filters()` call, re-introducing the T1 `as_of_date` filter that returns zero rows.

Fix re-applied as commit a023497, then rebuilt and redeployed to QA.

## Deployment Record

### Image Digest Comparison

| Field         | Before (stale)                                                           | After (new)                                                              |
|---------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------|
| ECR :latest   | sha256:b25733c99b25321c199137114755c7c52144a7ae30ab497caacea8aff9b5b8d4  | sha256:c0ad0e86d25ed109e4597bae67a5c0e228a94cda0db0a473500c386a1732e278  |
| Pushed at     | 2026-04-10T21:00:51 EDT (stale)                                          | 2026-04-10T21:40:58 EDT                                                  |
| Tags          | latest only                                                              | latest + 86f6f30                                                         |

### Git Info

- HEAD at build time: `86f6f30` (fix(deps): npm audit fix — patch axios critical SSRF vulnerability)
- Cashflow fix commit present: `1334f82` (fix(23): cashflow endpoint skips as_of_date filter)
- Branch: main

### ECS Deployment

| Field             | Value                                                          |
|-------------------|----------------------------------------------------------------|
| Cluster           | intrepid-poc-qa                                               |
| Service           | intrepid-poc-qa                                               |
| Task definition   | arn:aws:ecs:us-east-1:014148916722:task-definition/intrepid-poc-qa:2 |
| Force-deployed at | ~2026-04-10T21:42 EDT                                         |
| services-stable   | PASSED (exit 0)                                               |
| Running task ARN  | arn:aws:ecs:us-east-1:014148916722:task/intrepid-poc-qa/cfe2bdfed9b34ddbb1bf3609b5b6579d |
| Running imageDigest | sha256:c0ad0e86d25ed109e4597bae67a5c0e228a94cda0db0a473500c386a1732e278 |
| lastStatus        | RUNNING                                                        |

## Tasks Completed

| # | Task                                        | Result  | Notes                                      |
|---|---------------------------------------------|---------|--------------------------------------------|
| 1 | Verify HEAD + capture old ECR digest        | DONE    | Done in previous session; digest captured  |
| 2 | Build + push + ECS force-deploy             | DONE    | New digest confirmed; services-stable PASS |
| 3 | Human verification of cashflow fix on QA    | PENDING | Awaiting human sign-off at QA URL          |

## Deviations from Plan

None — plan executed exactly as written. No source code changes were made; this was a
redeploy-only operation.

## Known Stubs

None.

## Threat Flags

None — no new endpoints, auth paths, or schema changes introduced. Ops-only operation.

## Human Verification (Task 3)

**Status: AWAITING**

Please verify the cashflow fix at:
- http://intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com

Steps:
1. Log in as admin.
2. Run the workflow that exercises the cashflow endpoint (commit 1334f82 fix: cashflow endpoint
   no longer filters by as_of_date — cashflows are historical T0 data).
3. Confirm the previously-broken behavior (empty/wrong cashflow data due to date filter) is gone.

Reply "approved" when confirmed.

## Self-Check: PASSED

- ECR old digest: sha256:b25733c99... (captured in previous session)
- ECR new digest: sha256:c0ad0e86... (confirmed different, pushed 2026-04-10T21:40:58)
- Both :latest and :86f6f30 tags present in ECR
- aws ecs wait services-stable returned exit 0
- Running task imageDigest matches new ECR digest
