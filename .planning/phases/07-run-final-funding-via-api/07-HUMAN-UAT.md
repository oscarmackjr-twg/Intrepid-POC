---
status: partial
phase: 07-run-final-funding-via-api
source: [07-VERIFICATION.md]
started: 2026-03-22T00:00:00Z
updated: 2026-03-22T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. ALB HTTPS Redirect End-to-End
expected: HTTP requests to ALB on port 80 receive 301 redirect to HTTPS on port 443
result: [pending]

### 2. Rate Limiting Under Real Load
expected: 11th POST /api/auth/login within 60 seconds returns 429 Too Many Requests
result: [pending]

### 3. TruffleHog CI Pass
expected: TruffleHog secret scan step in GitHub Actions security-quality-gate job completes without flagging verified secrets
result: [pending]

### 4. RDS Public Accessibility After Terraform Apply
expected: TCP connection to RDS endpoint from outside VPC fails (connection refused or times out)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
