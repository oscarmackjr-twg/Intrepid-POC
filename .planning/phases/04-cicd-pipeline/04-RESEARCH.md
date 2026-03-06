# Phase 4: CI/CD Pipeline - Research

**Researched:** 2026-03-06
**Domain:** GitHub Actions, AWS OIDC, ECS Fargate one-off tasks, Terraform IAM
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **AWS Authentication:** GitHub OIDC + IAM role — no static long-lived credentials stored in GitHub
- **OIDC IAM role created via Terraform** — new `github-oidc.tf` in `deploy/terraform/qa/`
- **Trust policy restricted** to repo + `refs/heads/main` only (no other branches or PRs)
- **Workflow uses** `aws-actions/configure-aws-credentials@v4` with `role-to-assume` (not access keys)
- **No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` secrets needed** — replace with `AWS_ROLE_ARN` repo variable
- **Migration execution:** Run `alembic upgrade head` as an explicit ECS one-off task **before** `update-service`
- **Reuse existing app task definition** with CMD override (`alembic upgrade head`) — no separate task definition
- **If migration task exits non-zero: abort the workflow**, do not proceed to `update-service`
- **Container entrypoint still runs migrations on startup** (belt-and-suspenders) — this is not removed
- **Post-Deploy Validation:** After `update-service`, add `aws ecs wait services-stable` — timeout = failure
- **Default wait timeout (~10 min)** — if exceeded, workflow step fails; no "warn and continue"
- **Documentation:** Create `docs/CICD.md` as dedicated runbook covering all GitHub secrets/variables and step-by-step OIDC setup

### Claude's Discretion

- Exact IAM policy permissions on the OIDC role (least-privilege: ECR push, ECS run-task/update-service/describe, Secrets Manager read for `intrepid-poc/qa/*` path)
- Whether to rename `deploy-test.yml` to `deploy.yml` or keep the existing filename
- `aws ecs wait` timeout override if 10 min proves too short

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CICD-01 | GitHub Actions workflow builds Docker image and pushes to ECR on push to main | OIDC auth pattern, ECR login action, build/push shell steps verified |
| CICD-02 | Workflow runs Alembic migrations as part of deploy | ECS run-task with command override, aws ecs wait tasks-stopped, exit code verification pattern |
| CICD-03 | Required GitHub secrets/variables are documented and configured | Secrets inventory table, OIDC setup steps, `docs/CICD.md` runbook structure |
</phase_requirements>

---

## Summary

This phase updates the existing `.github/workflows/deploy-test.yml` to make the full deploy pipeline work against the `intrepid-poc-qa` infrastructure provisioned in Phase 3. Three changes are needed: (1) swap static AWS credentials for GitHub OIDC with a Terraform-managed IAM role, (2) add an explicit Alembic migration step (ECS one-off task with command override) that runs before `update-service` and aborts if it fails, and (3) add `aws ecs wait services-stable` after `update-service` to block until the new task is healthy.

The existing workflow already has the correct action versions (`aws-actions/configure-aws-credentials@v4`, `aws-actions/amazon-ecr-login@v2`). OIDC support requires only swapping the auth inputs (remove `aws-access-key-id`/`aws-secret-access-key`, add `role-to-assume`) plus adding `permissions: id-token: write` to the job. The ECR repo name and ECS cluster/service name corrections are straightforward constant swaps. The migration step requires capturing the task ARN from `aws ecs run-task`, waiting with `aws ecs wait tasks-stopped`, then querying the container's exit code via `aws ecs describe-tasks` and failing explicitly if non-zero.

The Terraform OIDC resources require adding `aws_iam_openid_connect_provider` (one-time per AWS account) and `aws_iam_role` with a trust policy scoped to `repo:OWNER/intrepid-poc:ref:refs/heads/main`. The OIDC provider may already exist in the account if another project created it — Terraform will error on duplicate; use `terraform import` or `data` source in that case.

**Primary recommendation:** Write all three changes as three discrete tasks: (1) Terraform `github-oidc.tf` + apply, (2) workflow YAML rewrite, (3) `docs/CICD.md` runbook. This allows clean verification at each step.

---

## Standard Stack

### Core

| Tool / Action | Version | Purpose | Why Standard |
|---|---|---|---|
| `aws-actions/configure-aws-credentials` | v4 | Exchange OIDC JWT for AWS temporary credentials | Official AWS-maintained action; already in workflow |
| `aws-actions/amazon-ecr-login` | v2 | ECR authentication, outputs `registry` URL | Official AWS-maintained action; already in workflow |
| `actions/checkout` | v4 | Checkout source for Docker build | Standard; already in workflow |
| GitHub OIDC (`token.actions.githubusercontent.com`) | — | Keyless AWS auth via federated identity | Eliminates long-lived secrets; AWS/GitHub jointly documented |
| `aws_iam_openid_connect_provider` (Terraform) | AWS provider ~5.0 | Register GitHub as trusted OIDC issuer in AWS | Required once per account; already using provider ~5.0 |
| `aws ecs run-task` (AWS CLI) | CLI v2 | Launch migration as Fargate one-off task | No separate action needed; CLI available on ubuntu-latest |
| `aws ecs wait tasks-stopped` (AWS CLI) | CLI v2 | Block until migration task reaches STOPPED | Built-in waiter; 6s poll, 100 attempts (~10 min max) |
| `aws ecs wait services-stable` (AWS CLI) | CLI v2 | Block until new app task is healthy post-deploy | Built-in waiter; 15s poll, 40 attempts (~10 min max) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| AWS CLI `run-task` + `wait` | Third-party GH action (geekcell/github-action-aws-ecs-run-task) | CLI approach has no additional supply-chain risk, already available |
| Custom Terraform OIDC resources | `unfunco/terraform-aws-oidc-github` module | Custom is 15 lines; module adds external dependency for minimal benefit |
| Keeping `deploy-test.yml` name | Renaming to `deploy.yml` | Rename is cleaner long-term; either works functionally |

**Installation:** No new packages. All tools (AWS CLI v2, Docker) are pre-installed on `ubuntu-latest` runners.

---

## Architecture Patterns

### Workflow Deploy Sequence

```
push to main
  └─ job: deploy (ubuntu-latest)
       ├─ permissions: id-token: write, contents: read
       ├─ checkout
       ├─ configure-aws-credentials (OIDC: role-to-assume)
       ├─ ecr-login  → outputs: registry
       ├─ build & push image (SHA tag + latest tag)
       ├─ run migration task (aws ecs run-task → capture ARN)
       ├─ wait migration stopped (aws ecs wait tasks-stopped)
       ├─ check migration exit code (aws ecs describe-tasks → fail if non-zero)
       ├─ update-service (aws ecs update-service --force-new-deployment)
       ├─ wait services-stable (aws ecs wait services-stable)
       └─ summary (echo image, cluster, service)
```

### Pattern 1: GitHub OIDC Authentication

**What:** The workflow requests a short-lived JWT from GitHub's OIDC provider; AWS validates it against a pre-configured IAM trust policy and issues temporary credentials.

**When to use:** Always — replaces static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` secrets.

**Required workflow permissions block** (job level):
```yaml
# Source: https://github.com/aws-actions/configure-aws-credentials
permissions:
  id-token: write   # required for OIDC token request
  contents: read    # required for actions/checkout
```

**Workflow configure step (replaces current static-credential block):**
```yaml
- name: Configure AWS
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ vars.AWS_ROLE_ARN }}
    aws-region: ${{ env.AWS_REGION }}
```

Note: Remove `aws-access-key-id` and `aws-secret-access-key` inputs entirely. The action detects OIDC automatically when only `role-to-assume` is present.

### Pattern 2: Terraform OIDC Resources (`github-oidc.tf`)

**What:** Two Terraform resources: the OIDC identity provider (once per AWS account) and the assumable IAM role with trust policy.

```hcl
# Source: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  # AWS ignores the thumbprint for this provider (uses its own CA store),
  # but the field is required by the resource schema.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "github-actions-intrepid-poc-qa"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringEquals = {
          # Lock to main branch only — no PRs, no feature branches
          # OWNER must be substituted with actual GitHub org/user
          "token.actions.githubusercontent.com:sub" = "repo:OWNER/intrepid-poc:ref:refs/heads/main"
        }
      }
    }]
  })

  tags = { Name = "github-actions-intrepid-poc-qa" }
}

output "github_actions_role_arn" {
  description = "ARN of GitHub Actions OIDC role — set as GitHub repo variable AWS_ROLE_ARN"
  value       = aws_iam_role.github_actions.arn
}
```

**Important:** `OWNER` is the GitHub org/username. The context notes "repo owner TBD (no git remote configured locally)" — the planner must include a step to determine this before writing the trust policy.

### Pattern 3: IAM Policy on the OIDC Role (Least Privilege)

The OIDC role needs exactly these permissions:

```hcl
resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "deploy-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR — auth token (account-level, cannot be resource-scoped)
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      # ECR — image push operations (scoped to QA repo)
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Resource = "arn:aws:ecr:us-east-1:014148916722:repository/intrepid-poc-qa"
      },
      # ECS — run migration task and deploy
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:DescribeTasks",
          "ecs:DescribeServices",
          "ecs:UpdateService"
        ]
        Resource = [
          "arn:aws:ecs:us-east-1:014148916722:cluster/intrepid-poc-qa",
          "arn:aws:ecs:us-east-1:014148916722:service/intrepid-poc-qa/intrepid-poc-qa",
          "arn:aws:ecs:us-east-1:014148916722:task-definition/intrepid-poc-qa:*",
          "arn:aws:ecs:us-east-1:014148916722:task/intrepid-poc-qa/*"
        ]
      },
      # IAM PassRole — required so run-task can assign the existing ECS task/execution roles
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [
          "arn:aws:iam::014148916722:role/ecsTaskExecution-intrepid-poc-qa-*",
          "arn:aws:iam::014148916722:role/ecsTaskRole-intrepid-poc-qa-*"
        ]
      },
      # Secrets Manager — read QA secrets (needed if CI ever calls secrets directly;
      # migration task inherits these via task role, not CI role)
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:us-east-1:014148916722:secret:intrepid-poc/qa/*"
      }
    ]
  })
}
```

**Critical note on `iam:PassRole`:** `aws ecs run-task` must pass the existing execution role and task role to the migration task. Without `iam:PassRole` on these role ARNs, the CLI call will fail with `AccessDeniedException`. The role ARNs use `name_prefix` in Terraform (e.g., `ecsTaskExecution-intrepid-poc-qa-RANDOM`), so wildcard suffix `*` is required.

**Critical note on `ecs:DescribeTasks`:** Needed to read the container exit code after `wait tasks-stopped`. Without it, the exit code check step will fail.

### Pattern 4: Migration Step — Run, Wait, Check Exit Code

**What:** ECS one-off task using the existing `intrepid-poc-qa` task definition with a `command` override. The task inherits `DATABASE_URL` from Secrets Manager via the existing execution role — no extra config needed.

```bash
# Source: https://docs.aws.amazon.com/cli/latest/reference/ecs/run-task.html

# Step 1: Launch migration task, capture ARN
TASK_ARN=$(aws ecs run-task \
  --cluster intrepid-poc-qa \
  --task-definition intrepid-poc-qa \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${{ vars.ECS_SUBNET_IDS }}],securityGroups=[${{ vars.ECS_SECURITY_GROUP }}],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}' \
  --query 'tasks[0].taskArn' \
  --output text)

echo "Migration task ARN: $TASK_ARN"

# Step 2: Wait until task reaches STOPPED (polls every 6s, max ~10 min)
aws ecs wait tasks-stopped \
  --cluster intrepid-poc-qa \
  --tasks "$TASK_ARN"

# Step 3: Check container exit code — fail workflow if non-zero
EXIT_CODE=$(aws ecs describe-tasks \
  --cluster intrepid-poc-qa \
  --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[?name==`app`].exitCode' \
  --output text)

echo "Migration container exit code: $EXIT_CODE"
if [ "$EXIT_CODE" != "0" ]; then
  echo "Migration failed with exit code $EXIT_CODE"
  exit 1
fi
```

**Why not skip the exit code check?** `aws ecs wait tasks-stopped` exits 0 as soon as the task is STOPPED — regardless of whether the container succeeded or crashed. A failing migration (exit code 1) would silently pass the wait step without the explicit check.

### Pattern 5: Post-Deploy Stability Wait

```bash
# Source: https://docs.aws.amazon.com/cli/latest/reference/ecs/wait/services-stable.html
# Polls every 15s, max 40 attempts (~10 min). Exits 255 on timeout (fails workflow step).
aws ecs wait services-stable \
  --cluster intrepid-poc-qa \
  --services intrepid-poc-qa
```

### Anti-Patterns to Avoid

- **Using `set -e` around `aws ecs wait`:** The waiter exits with code 255 on timeout, which `set -e` catches and terminates the shell before the error message prints. Use explicit `if` checks or temporarily disable `set -e`.
- **Skipping the exit code check after `wait tasks-stopped`:** The waiter exits 0 for any STOPPED task. A crashed migration looks identical to a successful one without the describe-tasks check.
- **Hardcoding subnet/security group IDs in the workflow:** These should be GitHub repo variables or derived from Terraform outputs. Hardcoding breaks if infrastructure is recreated.
- **Using `StringLike` with `*` in the sub condition:** A condition like `repo:OWNER/intrepid-poc:*` allows ALL branches and PR builds to assume the role. Use `StringEquals` with exact `ref:refs/heads/main`.
- **Creating a second OIDC provider if one already exists:** `aws_iam_openid_connect_provider` errors on duplicate URL. Check with `aws iam list-open-id-connect-providers` before applying; use `terraform import` if it exists.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| AWS credential management | Rotating stored secrets, IAM user keys | GitHub OIDC + IAM role | OIDC tokens are 1-hour TTL and per-workflow-scoped; no rotation needed |
| Migration wait loop | Custom polling while loop with sleep | `aws ecs wait tasks-stopped` | Built-in waiter handles retries, timeouts, and AWS transient errors |
| Service health check | Custom describe-services polling | `aws ecs wait services-stable` | Built-in waiter checks `deployments` + `runningCount == desiredCount` |
| Separate migration task definition | New Terraform task definition resource | `--overrides` on existing app task def | Overrides reuse all env vars, secrets, and role bindings; simpler to maintain |

**Key insight:** `aws ecs wait` commands handle all polling complexity correctly. The only required addition is the explicit exit code check after `tasks-stopped` — the waiter itself cannot distinguish success from crash.

---

## Common Pitfalls

### Pitfall 1: OIDC Provider Already Exists in the Account

**What goes wrong:** `terraform apply` fails: `EntityAlreadyExists: An OpenID Connect Provider already exists with the URL https://token.actions.githubusercontent.com`.

**Why it happens:** The OIDC provider is account-level (not region-specific). If any other project in account `014148916722` already configured GitHub OIDC, this resource already exists.

**How to avoid:** Before writing `github-oidc.tf`, check: `aws iam list-open-id-connect-providers`. If an entry for `token.actions.githubusercontent.com` exists, use a `data` source instead of a `resource`, or import the existing provider into state.

**Warning signs:** `terraform plan` shows the provider creation without error (Terraform doesn't pre-check for existing providers).

### Pitfall 2: Missing `iam:PassRole` on the OIDC Role

**What goes wrong:** `aws ecs run-task` fails with `AccessDeniedException: User ... is not authorized to perform: iam:PassRole on resource: arn:aws:iam::...`.

**Why it happens:** Fargate requires passing the task execution role and task role when launching a task. The caller (GitHub Actions CI role) must have `iam:PassRole` for these.

**How to avoid:** Include `iam:PassRole` explicitly on both `ecsTaskExecution-intrepid-poc-qa-*` and `ecsTaskRole-intrepid-poc-qa-*` in the OIDC role policy. The `*` suffix is required because `name_prefix` generates random suffixes.

**Warning signs:** Run-task fails immediately (not after waiting); error message explicitly mentions `iam:PassRole`.

### Pitfall 3: Network Configuration Required for Fargate run-task

**What goes wrong:** `aws ecs run-task` fails with `InvalidParameterException: Network Configuration must be provided when networkMode 'awsvpc' is utilized`.

**Why it happens:** The `app` task definition uses `awsvpc` network mode (required for Fargate). One-off tasks don't inherit network config from the service — it must be specified explicitly.

**How to avoid:** Pass `--network-configuration` with subnet IDs and security group ID. Store these as GitHub repo variables (e.g., `ECS_SUBNET_IDS`, `ECS_SECURITY_GROUP`) or derive from Terraform outputs.

**Warning signs:** Immediate failure on `run-task` call; error includes "NetworkConfiguration".

### Pitfall 4: GitHub Repo Owner Unknown (trust policy OWNER placeholder)

**What goes wrong:** The trust policy `sub` condition references `repo:OWNER/intrepid-poc:ref:refs/heads/main`. If OWNER is wrong, the workflow gets `AccessDenied` when assuming the role — no helpful error message.

**Why it happens:** The CONTEXT.md notes "repo owner TBD (no git remote configured locally)". The planner must add a step to confirm the GitHub org/username before writing the Terraform file.

**How to avoid:** Determine the repo owner first (`git remote -v` or check the GitHub repo URL). It appears in the format `github.com/OWNER/intrepid-poc`.

**Warning signs:** Workflow fails at "Configure AWS" step with `AccessDenied`; no other explanation.

### Pitfall 5: `aws ecs wait tasks-stopped` Masks Migration Failure

**What goes wrong:** Migration fails (Alembic exits 1), but the workflow continues to `update-service` because `wait tasks-stopped` exits 0 (task did reach STOPPED state).

**Why it happens:** The waiter only checks `lastStatus == STOPPED`, not the container's exit code.

**How to avoid:** Always follow `wait tasks-stopped` with a `describe-tasks` call to extract and check `containers[?name==\`app\`].exitCode`.

**Warning signs:** Deployment "succeeds" but new container immediately crashes on startup (same migration error hits on startup since entrypoint also runs alembic).

### Pitfall 6: ECR Repo Name Mismatch

**What goes wrong:** Current workflow uses `ECR_REPO_NAME: loan-engine`; actual ECR repo is `intrepid-poc-qa`. Image push succeeds to the wrong (nonexistent) repo or fails with 404.

**How to avoid:** Update `ECR_REPO_NAME` to `intrepid-poc-qa` or derive it from `steps.ecr.outputs.registry` + the Terraform output.

---

## Code Examples

### Complete Updated Workflow Skeleton

```yaml
# Source: based on aws-actions/configure-aws-credentials@v4 official docs
name: Deploy to AWS QA

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPO_NAME: intrepid-poc-qa
  ECS_CLUSTER: intrepid-poc-qa
  ECS_SERVICE: intrepid-poc-qa

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # required for OIDC
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push image
        id: build
        env:
          ECR_REGISTRY: ${{ steps.ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -f deploy/Dockerfile \
            -t $ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG \
            -t $ECR_REGISTRY/$ECR_REPO_NAME:latest .
          docker push $ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPO_NAME:latest
          echo "image=$ECR_REGISTRY/$ECR_REPO_NAME:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Run Alembic migration (ECS one-off task)
        run: |
          TASK_ARN=$(aws ecs run-task \
            --cluster ${{ env.ECS_CLUSTER }} \
            --task-definition ${{ env.ECS_CLUSTER }} \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[${{ vars.ECS_SUBNET_IDS }}],securityGroups=[${{ vars.ECS_SECURITY_GROUP }}],assignPublicIp=ENABLED}" \
            --overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}' \
            --query 'tasks[0].taskArn' \
            --output text)
          echo "TASK_ARN=$TASK_ARN" >> $GITHUB_ENV
          echo "Migration task started: $TASK_ARN"

      - name: Wait for migration to complete
        run: |
          aws ecs wait tasks-stopped \
            --cluster ${{ env.ECS_CLUSTER }} \
            --tasks "$TASK_ARN"

      - name: Check migration exit code
        run: |
          EXIT_CODE=$(aws ecs describe-tasks \
            --cluster ${{ env.ECS_CLUSTER }} \
            --tasks "$TASK_ARN" \
            --query 'tasks[0].containers[?name==`app`].exitCode' \
            --output text)
          echo "Migration exit code: $EXIT_CODE"
          if [ "$EXIT_CODE" != "0" ]; then
            echo "Migration FAILED (exit code $EXIT_CODE) — aborting deploy"
            exit 1
          fi
          echo "Migration succeeded"

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ${{ env.ECS_SERVICE }} \
            --force-new-deployment \
            --region ${{ env.AWS_REGION }}

      - name: Wait for service stability
        run: |
          aws ecs wait services-stable \
            --cluster ${{ env.ECS_CLUSTER }} \
            --services ${{ env.ECS_SERVICE }}

      - name: Deployment summary
        run: |
          echo "Image: ${{ steps.build.outputs.image }}"
          echo "ECS: ${{ env.ECS_CLUSTER }} / ${{ env.ECS_SERVICE }}"
          echo "Deploy complete"
```

### Checking for Existing OIDC Provider

```bash
# Run before writing github-oidc.tf
aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[*].Arn" \
  --output text | grep -i github
```

If output is non-empty, use a `data` source in Terraform:
```hcl
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}
# Then reference: data.aws_iam_openid_connect_provider.github.arn
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Static IAM user keys in GitHub Secrets | GitHub OIDC + IAM role | 2021 (GitHub added OIDC) | No secrets to rotate; credentials expire after 1 hour |
| `aws-actions/configure-aws-credentials@v1` (access-key-id inputs) | v4 with `role-to-assume` | 2023 (v3+) | Same action, different inputs |
| Separate migration task definition | `--overrides` on existing task def | — | Fewer resources to maintain; inherits all secrets/env vars |

**Deprecated/outdated in current workflow:**
- `aws-access-key-id` / `aws-secret-access-key` inputs on configure-aws-credentials: replaced by `role-to-assume`
- `ECR_REPO_NAME: loan-engine`: wrong name — must be `intrepid-poc-qa`
- `ECS_CLUSTER: test-cluster` / `ECS_SERVICE: loan-engine-test`: wrong names — must be `intrepid-poc-qa`

---

## Open Questions

1. **GitHub repo owner (OWNER in trust policy)**
   - What we know: repo is `intrepid-poc`; owner is unknown ("no git remote configured locally")
   - What's unclear: Is it a personal account or an org?
   - Recommendation: Planner must include a step: "determine GitHub remote owner" as prerequisite to writing `github-oidc.tf`

2. **OIDC provider already exists in account `014148916722`?**
   - What we know: Account has been active with ECS/ECR infrastructure
   - What's unclear: Was GitHub OIDC previously configured by any other project?
   - Recommendation: Planner should include a verification step before `terraform apply`

3. **Subnet IDs and Security Group ID for `run-task`**
   - What we know: ECS tasks use `aws_subnet.public[*].id` and `aws_security_group.ecs.id` from Terraform
   - What's unclear: Specific IDs — these are in `terraform.tfstate` but not surfaced as outputs
   - Recommendation: Add Terraform outputs for `ecs_subnet_ids` and `ecs_security_group_id`, or derive them from `terraform output` in a pre-deploy step; store as GitHub repo variables

4. **`alembic upgrade head` working directory in the container**
   - What we know: Container uses CMD override; Alembic config is at `backend/alembic.ini`
   - What's unclear: What is the container's working directory — does `alembic upgrade head` find `alembic.ini` without a `-c` flag?
   - Recommendation: Planner should include verification: check `deploy/Dockerfile` for `WORKDIR` and whether the CMD override needs `-c /app/alembic.ini`

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (existing, `backend/pytest.ini`) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/ -v --tb=short -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CICD-01 | GitHub Actions workflow builds and pushes image to ECR | manual-only | N/A — requires live GitHub Actions run | N/A |
| CICD-02 | Alembic migration runs as ECS task before update-service | manual-only | N/A — requires live ECS cluster | N/A |
| CICD-03 | Secrets/variables documented and configured in GitHub repo | manual-only | N/A — human verification of GitHub repo settings | N/A |

**Justification for manual-only:** All three requirements involve live cloud infrastructure (GitHub Actions runner, ECR, ECS Fargate, RDS). No unit or integration tests can validate cloud-side CI/CD behavior without the actual pipeline running. Validation is: push a commit to main and observe the full pipeline run green in the GitHub Actions UI.

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/ -v --tb=short -x -q` (smoke test that existing app tests still pass after any backend changes)
- **Per wave merge:** Full pipeline run via `git push origin main` and verify GitHub Actions green
- **Phase gate:** Full GitHub Actions run completes green before `/gsd:verify-work`

### Wave 0 Gaps

None — no new Python test files needed for this phase. Phase is infrastructure/config work only. Existing test suite should be kept green as a baseline.

---

## Sources

### Primary (HIGH confidence)

- `aws-actions/configure-aws-credentials` GitHub README — OIDC inputs, permissions block
- `https://docs.aws.amazon.com/cli/latest/reference/ecs/run-task.html` — `--overrides`, `--network-configuration`, `--query` for task ARN
- `https://docs.aws.amazon.com/cli/latest/reference/ecs/wait/tasks-stopped.html` — polling behavior (6s interval, 100 attempts, exit code 255 on timeout)
- `https://docs.aws.amazon.com/cli/latest/reference/ecs/wait/services-stable.html` — polling behavior (15s interval, 40 attempts, ~10 min max)
- Existing project files: `deploy/terraform/qa/iam.tf`, `ecs.tf`, `variables.tf`, `versions.tf`, `.github/workflows/deploy-test.yml`

### Secondary (MEDIUM confidence)

- `https://5pi.de/2024/aws-gh-actions/` — ECR IAM action list verified against official ECR docs
- `https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_openid_connect_provider` — thumbprint value (`6938fd4d98bab03faadb97b34396831e3780aea1`) confirmed by multiple sources; AWS ignores it for GitHub but field is required
- WebSearch: `iam:PassRole` requirement for ECS `run-task` — verified by multiple community sources and consistent with AWS IAM behavior for role passing

### Tertiary (LOW confidence)

- Trust policy subject format `repo:OWNER/intrepid-poc:ref:refs/heads/main` — sourced from multiple blog posts; consistent across sources but `StringEquals` vs `StringLike` nuance flagged: use `StringEquals` for exact main-branch lock per locked decision

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all tools already in use in the project or are official AWS actions
- Architecture: HIGH — workflow pattern verified against official AWS CLI docs and existing project structure
- IAM permissions: MEDIUM — ECR permissions list verified via official docs; ECS/PassRole permissions drawn from multiple consistent community sources and AWS IAM behavior documentation
- Pitfalls: HIGH — all pitfalls drawn from specific, verifiable technical behaviors (waiter exit codes, PassRole requirement, network-config requirement for awsvpc)

**Research date:** 2026-03-06
**Valid until:** 2026-09-06 (stable domain; GitHub Actions action versions should be re-verified if significantly later)
