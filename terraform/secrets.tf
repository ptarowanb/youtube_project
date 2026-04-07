resource "random_password" "n8n_encryption_key" {
  length  = 48
  special = false
}

resource "random_password" "automation_shared_token" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "runtime" {
  name = "project1/runtime"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id = aws_secretsmanager_secret.runtime.id
  secret_string = jsonencode({
    n8n_db_host                    = var.n8n_db_host
    n8n_db_port                    = "5432"
    n8n_db_name                    = var.n8n_db_name
    n8n_db_user                    = var.n8n_db_user
    n8n_db_password                = var.n8n_db_password
    n8n_db_schema                  = var.n8n_db_schema
    n8n_db_ssl_enabled             = "true"
    n8n_encryption_key             = random_password.n8n_encryption_key.result
    automation_shared_token        = random_password.automation_shared_token.result
  })
}
