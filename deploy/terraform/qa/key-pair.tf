# Optional: register EC2 key pair "intrepid-poc-qa" so you can use intrepid-poc-qa.pem for SSH
# (e.g. for a bastion host or future EC2). QA app runs on ECS Fargate and does not use EC2 by default.
resource "aws_key_pair" "qa" {
  count = length(var.ec2_key_pair_public_key) > 0 ? 1 : 0

  key_name   = "intrepid-poc-qa"
  public_key = var.ec2_key_pair_public_key
  tags       = { Name = "intrepid-poc-qa" }
}
