data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  lower   = true
  numeric = true
  special = false
}

locals {
  name_prefix          = "${var.app_name}-${var.environment}"
  clean_name_prefix    = lower(replace(local.name_prefix, "-", ""))
  storage_account_name = substr("${local.clean_name_prefix}${random_string.suffix.result}sa", 0, 24)
  acr_name             = substr("${local.clean_name_prefix}${random_string.suffix.result}acr", 0, 50)
  postgres_server_name = substr("${local.clean_name_prefix}${random_string.suffix.result}pg", 0, 63)
  key_vault_name       = substr("${local.clean_name_prefix}${random_string.suffix.result}kv", 0, 24)
  app_identity_name    = "${local.name_prefix}-app-id"
  aca_env_name         = "${local.name_prefix}-env"
  aca_name             = "${local.name_prefix}-app"
  log_analytics_name   = "${local.name_prefix}-logs"
  direct_fqdn          = ""
  app_url              = ""
  cors_origins_json    = var.public_hostname != "" ? jsonencode(["https://${var.public_hostname}"]) : "[]"
  container_image      = var.container_image != "" ? var.container_image : "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
  database_url         = "postgresql://${var.db_admin_username}:${var.db_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.db_name}?sslmode=require"

  tags = {
    Environment = var.environment
    Project     = var.app_name
    ManagedBy   = "terraform"
    Recovery    = "level1"
  }
}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}
