# ALB HTTPS Setup — ACM Certificate & Terraform Apply

**Environment:** QA (`us-east-1`, account `014148916722`)
**ALB:** `intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com`

## Context

`deploy/terraform/qa/alb.tf` has the HTTPS listener fully coded (Phase 7), gated on `var.acm_certificate_arn`:

- HTTP listener (port 80): redirects all traffic → HTTPS 443 (`HTTP_301`)
- HTTPS listener (port 443): created only when `acm_certificate_arn != ""`

The HTTP→HTTPS redirect and HTTPS listener are **written but not yet applied to AWS**. Do not run `terraform apply` until the cert ARN is set — otherwise the HTTP listener switches to redirect mode and the app becomes unreachable.

---

## Step 1 — Prerequisites: a domain you control

ACM public certs require a domain name you own (e.g. `qa.intrepid.yourcompany.com`). You cannot get a cert for the raw ALB DNS name.

---

## Step 2 — Request the ACM Certificate

```powershell
aws acm request-certificate `
  --domain-name "qa.yourdomain.com" `
  --validation-method DNS `
  --region us-east-1
```

Returns a `CertificateArn`. Copy it — status will be `PENDING_VALIDATION` until DNS validation completes.

---

## Step 3 — Get the DNS Validation Record

```powershell
aws acm describe-certificate `
  --certificate-arn "arn:aws:acm:us-east-1:014148916722:certificate/YOUR-ID" `
  --region us-east-1 `
  --query "Certificate.DomainValidationOptions[0].ResourceRecord"
```

Returns a CNAME record like:

```json
{
  "Name": "_abc123.qa.yourdomain.com.",
  "Type": "CNAME",
  "Value": "_xyz456.acm-validations.aws."
}
```

Add that CNAME to your DNS provider (Route 53, Cloudflare, etc.).

---

## Step 4 — Wait for ISSUED Status

```powershell
aws acm describe-certificate `
  --certificate-arn "arn:aws:acm:us-east-1:014148916722:certificate/YOUR-ID" `
  --region us-east-1 `
  --query "Certificate.Status"
```

Flips from `PENDING_VALIDATION` → `ISSUED` in 2–10 minutes after DNS propagates.

---

## Step 5 — Add ARN to terraform.tfvars

Edit `deploy/terraform/qa/terraform.tfvars`:

```hcl
acm_certificate_arn = "arn:aws:acm:us-east-1:014148916722:certificate/YOUR-ID"
```

---

## Step 6 — Point Your Domain at the ALB

In your DNS provider, add:

| Type  | Name                   | Value                                                              |
|-------|------------------------|--------------------------------------------------------------------|
| CNAME | `qa.yourdomain.com`    | `intrepid-poc-qa-alb-1332245107.us-east-1.elb.amazonaws.com`      |

(Use an ALIAS record instead of CNAME if your DNS provider is Route 53 — avoids the CNAME-at-apex restriction.)

---

## Step 7 — Terraform Plan (review before applying)

```powershell
cd deploy/terraform/qa
terraform plan -out=tfplan
```

**Expected changes in the diff** (all Phase 7 unapplied changes apply together):

| Resource | Change | Notes |
|----------|--------|-------|
| `aws_lb_listener.http` | `forward` → `redirect to HTTPS 443` | HTTPS fix |
| `aws_lb_listener.https` | created (new) | Requires cert ARN |
| `aws_db_instance.main` | `publicly_accessible = true → false` | Moves RDS to private subnets — verify ECS can still reach it |
| `aws_security_group` | Egress tightened to ports 5432/443/53 | Review before applying |

The **RDS private subnet change** is the highest risk. Confirm ECS tasks and the migration task are in the same VPC and can route to the private RDS subnet before applying.

---

## Step 8 — Terraform Apply

```powershell
terraform apply tfplan
```

---

## Step 9 — Post-Apply Verification

```powershell
# Confirm new ECS task definition revision registered
terraform output

# Confirm ECS service is running
aws ecs describe-services `
  --cluster intrepid-poc-qa `
  --services intrepid-poc-qa `
  --region us-east-1 `
  --query "services[0].{taskDef:taskDefinition,running:runningCount,desired:desiredCount}"

# Confirm HTTPS listener exists on the ALB
aws elbv2 describe-listeners `
  --load-balancer-arn (aws elbv2 describe-load-balancers `
    --names intrepid-poc-qa-alb `
    --query "LoadBalancers[0].LoadBalancerArn" `
    --output text `
    --region us-east-1) `
  --region us-east-1 `
  --query "Listeners[*].{Port:Port,Protocol:Protocol}"
```

Expected output: listeners on port 80 (HTTP) and port 443 (HTTPS).

---

## Terraform File Reference

| File | Key variable |
|------|-------------|
| `deploy/terraform/qa/alb.tf` | HTTPS listener (count-gated on `acm_certificate_arn`) |
| `deploy/terraform/qa/variables.tf` | `acm_certificate_arn` variable definition |
| `deploy/terraform/qa/terraform.tfvars` | Set `acm_certificate_arn` here (gitignored) |
