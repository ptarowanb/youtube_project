variable "aws_region" {
  description = "AWS region used for the single-environment stack."
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
  default     = "project1"
}

variable "cluster_name" {
  description = "ECS cluster name."
  type        = string
  default     = "n8n"
}

variable "vpc_id" {
  description = "Existing VPC ID for the stack."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS services."
  type        = list(string)
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN for HTTPS on the public ALB."
  type        = string
  default     = ""

  validation {
    condition     = var.certificate_arn == "" || var.n8n_domain_name != ""
    error_message = "n8n_domain_name must be set when certificate_arn is provided."
  }
}

variable "n8n_domain_name" {
  description = "Optional public domain name for the n8n UI and webhooks."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Optional public Route53 hosted zone ID used to create an alias record for n8n."
  type        = string
  default     = ""
}

variable "n8n_db_host" {
  description = "Existing PostgreSQL RDS host used by n8n."
  type        = string
  default     = "runnerpoker-test.cmhs16pmizic.ap-northeast-2.rds.amazonaws.com"
}

variable "n8n_db_name" {
  description = "Database name used by n8n."
  type        = string
  default     = "n8n"
}

variable "n8n_db_user" {
  description = "Database user used by n8n."
  type        = string
  default     = "runner_dev"
}

variable "n8n_db_schema" {
  description = "Database schema used by n8n."
  type        = string
  default     = "public"
}

variable "n8n_db_password" {
  description = "Database password used by n8n. Terraform stores it in Secrets Manager."
  type        = string
  sensitive   = true
}

variable "render_bucket_name" {
  description = "Shared S3 bucket for intermediate and final render assets."
  type        = string
}

variable "rds_security_group_id" {
  description = "Optional existing RDS security group ID to allow inbound access from the n8n service."
  type        = string
  default     = ""
}

variable "automation_image" {
  description = "Pinned container image URI for the private automation render service."
  type        = string
}

variable "n8n_image" {
  description = "Pinned container image URI for the public n8n service."
  type        = string
}

variable "n8n_cpu" {
  description = "CPU units for the n8n task definition."
  type        = number
  default     = 1024
}

variable "n8n_memory" {
  description = "Memory (MiB) for the n8n task definition."
  type        = number
  default     = 2048
}

variable "n8n_desired_count" {
  description = "Desired task count for the n8n ECS service."
  type        = number
  default     = 1
}
