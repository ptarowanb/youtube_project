resource "aws_cloudwatch_log_group" "n8n" {
  name              = "/ecs/${local.n8n_service_name}"
  retention_in_days = 14
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "automation" {
  name              = "/ecs/${local.automation_service_name}"
  retention_in_days = 14
  tags              = local.common_tags
}
