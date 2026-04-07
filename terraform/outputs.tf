output "aws_account_id" {
  description = "Current AWS account ID."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region_name" {
  description = "Resolved AWS region."
  value       = data.aws_region.current.name
}

output "n8n_alb_dns_name" {
  description = "DNS name of the public ALB serving n8n."
  value       = aws_lb.main.dns_name
}

output "n8n_public_base_url" {
  description = "Base URL for the n8n service."
  value       = "${local.n8n_public_protocol}://${var.n8n_domain_name != "" ? var.n8n_domain_name : aws_lb.main.dns_name}"
}

output "n8n_route53_record_name" {
  description = "Route53 record name created for the public n8n endpoint, when enabled."
  value       = var.route53_zone_id != "" && var.n8n_domain_name != "" ? aws_route53_record.n8n_ipv4[0].fqdn : null
}

output "automation_ecr_repository_url" {
  description = "ECR repository URL for the private automation renderer image."
  value       = aws_ecr_repository.automation.repository_url
}

output "automation_internal_base_url" {
  description = "Private Cloud Map base URL for the automation render service."
  value       = "http://${local.automation_service_name}.n8n.local:${local.automation_container_port}"
}
