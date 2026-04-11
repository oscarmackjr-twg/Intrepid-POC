variable "location" {
  description = "Azure region for DR resources."
  type        = string
  default     = "eastus2"
}

variable "app_name" {
  description = "Application name used in resource names."
  type        = string
  default     = "intrepid-poc"
}

variable "environment" {
  description = "Environment name for the Azure DR stack."
  type        = string
  default     = "dr"
}

variable "resource_group_name" {
  description = "Resource group name for the Azure DR stack."
  type        = string
  default     = "RG-Intrepid-POC"
}

variable "container_image" {
  description = "Full container image name. Leave empty to use a placeholder image for the first apply."
  type        = string
  default     = ""
}

variable "container_image_tag" {
  description = "Container image tag used with the ACR repository name when container_image is empty."
  type        = string
  default     = "latest"
}

variable "acr_repository_name" {
  description = "Repository name in Azure Container Registry."
  type        = string
  default     = "intrepid-poc"
}

variable "container_cpu" {
  description = "Container App CPU allocation."
  type        = number
  default     = 1
}

variable "container_memory" {
  description = "Container App memory allocation."
  type        = string
  default     = "2Gi"
}

variable "min_replicas" {
  description = "Minimum warm replicas for the DR app."
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum replicas for the DR app."
  type        = number
  default     = 2
}

variable "db_name" {
  description = "Application database name."
  type        = string
  default     = "intrepid_poc"
}

variable "db_admin_username" {
  description = "Azure PostgreSQL administrator login."
  type        = string
  default     = "intrepid_admin"
}

variable "db_admin_password" {
  description = "Azure PostgreSQL administrator password."
  type        = string
  sensitive   = true
}

variable "db_sku_name" {
  description = "Azure PostgreSQL Flexible Server SKU."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  description = "Storage size for Azure PostgreSQL Flexible Server."
  type        = number
  default     = 32768
}

variable "db_backup_retention_days" {
  description = "Backup retention days for Azure PostgreSQL."
  type        = number
  default     = 7
}

variable "secret_key" {
  description = "Application secret key."
  type        = string
  sensitive   = true
}

variable "public_hostname" {
  description = "Optional public hostname for browser CORS and manual DNS cutover."
  type        = string
  default     = ""
}

variable "enable_scheduler" {
  description = "Enable the in-app scheduler in Azure DR."
  type        = bool
  default     = true
}

variable "app_file_share_name" {
  description = "Azure Files share mounted into the container app."
  type        = string
  default     = "appdata"
}

variable "artifact_blob_container_name" {
  description = "Blob container for DR package uploads."
  type        = string
  default     = "dr-packages"
}

variable "db_dump_blob_container_name" {
  description = "Blob container for PostgreSQL dump uploads."
  type        = string
  default     = "db-dumps"
}
