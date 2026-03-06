resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  # AWS ignores this thumbprint for github.com (uses its own CA store), but field is required
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

locals {
  github_oidc_provider_arn = aws_iam_openid_connect_provider.github.arn
}

resource "aws_iam_role" "github_actions" {
  name = "github-actions-intrepid-poc-qa"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          # Lock to main branch only — no PRs, no feature branches
          "token.actions.githubusercontent.com:sub" = "repo:oscarmackjr-twg/Intrepid-POC:ref:refs/heads/main"
        }
      }
    }]
  })

  tags = { Name = "github-actions-intrepid-poc-qa" }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "deploy-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR auth token (account-level — cannot be resource-scoped)
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      # ECR image push (scoped to QA repo)
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
      # ECS — run migration task, describe tasks, deploy service
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
          "arn:aws:ecs:us-east-1:014148916722:service/intrepid-poc-qa/*",
          "arn:aws:ecs:us-east-1:014148916722:task-definition/intrepid-poc-qa:*",
          "arn:aws:ecs:us-east-1:014148916722:task/intrepid-poc-qa/*"
        ]
      },
      # IAM PassRole — required for aws ecs run-task (passes execution + task roles)
      # name_prefix generates random suffix, so wildcard is required
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [
          "arn:aws:iam::014148916722:role/ecsTaskExecution-intrepid-poc-qa-*",
          "arn:aws:iam::014148916722:role/ecsTaskRole-intrepid-poc-qa-*"
        ]
      },
      # Secrets Manager — read QA secrets (migration task inherits via task role;
      # included here in case CI needs direct reads in future)
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:us-east-1:014148916722:secret:intrepid-poc/qa/*"
      }
    ]
  })
}

output "github_actions_role_arn" {
  description = "GitHub Actions OIDC role ARN — set as GitHub repo variable AWS_ROLE_ARN"
  value       = aws_iam_role.github_actions.arn
}
