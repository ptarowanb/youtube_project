terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "runner"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  common_tags = {
    Project = "youtube_project"
    Managed = "terraform"
  }

  n8n_service_name          = "n8n"
  automation_service_name   = "automation"
  n8n_task_family           = "n8n"
  automation_task_family    = "project1"
  n8n_container_port        = 5678
  automation_container_port = 8080
  n8n_public_protocol       = var.certificate_arn != "" ? "https" : "http"
}
