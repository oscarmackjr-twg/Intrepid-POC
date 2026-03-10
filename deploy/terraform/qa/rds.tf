# DB subnet group
# HARD-01: RDS moved to private subnets — requires VPC private subnet routing to ECS
resource "aws_db_subnet_group" "main" {
  name_prefix = "${local.name_prefix}-db-"
  # HARD-01: RDS moved to private subnets — requires VPC private subnet routing to ECS
  subnet_ids  = aws_subnet.private[*].id
  description = "DB subnet group for ${var.app_name} QA"
  tags        = { Name = "${local.name_prefix}-db-subnet" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "main" {
  identifier     = var.db_instance_identifier
  engine         = "postgres"
  engine_version = "16.8"
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  allocated_storage       = 20
  storage_type            = "gp2"
  backup_retention_period = 7

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  # HARD-01: RDS moved to private subnets — requires VPC private subnet routing to ECS
  publicly_accessible    = false

  skip_final_snapshot = true
  tags               = { Name = var.db_instance_identifier }
}
