resource "random_password" "n8n_encryption_key" {
  length  = 48
  special = false
}

resource "random_password" "automation_shared_token" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "n8n_db_password" {
  name = "n8n/db-password"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "n8n_db_password" {
  secret_id     = aws_secretsmanager_secret.n8n_db_password.id
  secret_string = var.n8n_db_password
}

resource "aws_secretsmanager_secret" "n8n_encryption_key" {
  name = "n8n/encryption-key"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "n8n_encryption_key" {
  secret_id     = aws_secretsmanager_secret.n8n_encryption_key.id
  secret_string = random_password.n8n_encryption_key.result
}

resource "aws_secretsmanager_secret" "automation_shared_token" {
  name = "automation/shared-token"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "automation_shared_token" {
  secret_id     = aws_secretsmanager_secret.automation_shared_token.id
  secret_string = random_password.automation_shared_token.result
}
