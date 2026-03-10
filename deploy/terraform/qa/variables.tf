variable "aws_region" {
  description = "AWS region for QA resources"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name (used in resource names)"
  type        = string
  default     = "intrepid-poc"
}

variable "environment" {
  description = "Environment name (qa)"
  type        = string
  default     = "qa"
}

# --- S3 ---
variable "s3_bucket_name" {
  description = "S3 bucket name for QA (inputs/outputs/archive)"
  type        = string
  default     = "intrepid-poc-qa"
}

# --- RDS ---
variable "db_instance_identifier" {
  description = "RDS instance identifier"
  type        = string
  default     = "intrepid-poc-qa"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "intrepid_poc"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "RDS master password (e.g. Intrepid456$%)"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# --- ECS / Compute ---
variable "ecs_cluster_name" {
  description = "ECS cluster name (referred to as EC2/compute for QA)"
  type        = string
  default     = "intrepid-poc-qa"
}

variable "ecs_service_name" {
  description = "ECS service name"
  type        = string
  default     = "intrepid-poc-qa"
}

variable "ecr_repository_name" {
  description = "ECR repository name for QA images"
  type        = string
  default     = "intrepid-poc-qa"
}

variable "ecs_cpu" {
  description = "ECS task CPU units"
  type        = string
  default     = "1024"
}

variable "ecs_memory" {
  description = "ECS task memory (MB)"
  type        = string
  default     = "2048"
}

variable "ecs_desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 1
}

variable "cashflow_worker_cpu" {
  description = "CPU units for dedicated cashflow worker tasks"
  type        = string
  default     = "4096"
}

variable "cashflow_worker_memory" {
  description = "Memory (MB) for dedicated cashflow worker tasks"
  type        = string
  default     = "16384"
}

variable "cashflow_worker_max_workers" {
  description = "Max worker-process count for current-assets cashflow runs on AWS"
  type        = number
  default     = 4
}

# --- Optional: build/push image as part of apply (leave empty to skip) ---
variable "docker_image_tag" {
  description = "Docker image tag to use (e.g. latest or qa-1.0). Set in CI or deploy script."
  type        = string
  default     = "latest"
}

# --- Optional: EC2 key pair (for bastion or future EC2; QA app runs on ECS Fargate) ---
variable "ec2_key_pair_public_key" {
  description = "Public key for EC2 key pair 'loan-engine-qa' (e.g. from: ssh-keygen -y -f loan-engine-qa.pem). Leave empty to skip."
  type        = string
  default     = ""
  sensitive   = true
}

# --- TLS / HTTPS ---
variable "acm_certificate_arn" {
  description = "ACM certificate ARN for ALB HTTPS listener. Leave empty string to skip HTTPS listener (QA without a cert). When set, HTTP port 80 redirects to HTTPS 443."
  type        = string
  default     = ""
}
