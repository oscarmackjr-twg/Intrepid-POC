# ALB security group
resource "aws_security_group" "alb" {
  name_prefix = "${local.name_prefix}-alb-sg-"
  description = "ALB for ${var.app_name} QA"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name_prefix}-alb-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  tags              = { Name = "allow-80" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  tags              = { Name = "allow-443" }
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ECS security group
resource "aws_security_group" "ecs" {
  name_prefix = "${local.name_prefix}-ecs-sg-"
  description = "ECS tasks for ${var.app_name} QA"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name_prefix}-ecs-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id  = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  tags                         = { Name = "from-alb-8000" }
}

# HARD-01: Tightened ECS egress — replaces open 0.0.0.0/0 egress
resource "aws_vpc_security_group_egress_rule" "ecs_to_rds" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.rds.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "ECS to RDS Postgres"
}

resource "aws_vpc_security_group_egress_rule" "ecs_https_out" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "ECS outbound HTTPS (S3, ECR, Secrets Manager)"
}

resource "aws_vpc_security_group_egress_rule" "ecs_dns_out" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
  description       = "ECS DNS resolution"
}

# RDS security group
resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-sg-"
  description = "RDS for ${var.app_name} QA"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name_prefix}-rds-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id  = aws_security_group.ecs.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  tags                         = { Name = "from-ecs-5432" }
}

# HARD-01: RDS has no outbound networking needs — rds_all 0.0.0.0/0 egress removed intentionally
