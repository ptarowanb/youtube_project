resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "n8n.local"
  description = "Private namespace for ECS internal services"
  vpc         = var.vpc_id

  tags = local.common_tags
}

resource "aws_service_discovery_service" "automation" {
  name = local.automation_service_name

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}
