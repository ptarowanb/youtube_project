data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ecs_task_execution_secrets" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.runtime.arn,
    ]
  }
}

data "aws_iam_policy_document" "ecs_task_runtime" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.render_outputs.arn,
      "${aws_s3_bucket.render_outputs.arn}/*",
    ]
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "ecs-task-execution-n8n"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = local.common_tags
}

resource "aws_iam_role" "ecs_task" {
  name               = "ecs-task-runtime-n8n"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name   = "ecs-task-execution-secrets"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_task_execution_secrets.json
}

resource "aws_iam_role_policy" "ecs_task_runtime" {
  name   = "ecs-task-runtime-s3"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_runtime.json
}
