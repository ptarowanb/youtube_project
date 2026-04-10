resource "aws_ecs_cluster" "main" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = var.cluster_name
  })
}

resource "aws_ecs_task_definition" "n8n" {
  family                   = local.n8n_task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.n8n_cpu
  memory                   = var.n8n_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = local.n8n_service_name
      image = var.n8n_image

      essential = true

      portMappings = [
        {
          containerPort = local.n8n_container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "N8N_PORT"
          value = tostring(local.n8n_container_port)
        },
        {
          name  = "N8N_HOST"
          value = var.n8n_domain_name != "" ? var.n8n_domain_name : aws_lb.main.dns_name
        },
        {
          name  = "N8N_PROTOCOL"
          value = local.n8n_public_protocol
        },
        {
          name  = "WEBHOOK_URL"
          value = "${local.n8n_public_protocol}://${var.n8n_domain_name != "" ? var.n8n_domain_name : aws_lb.main.dns_name}/"
        },
        {
          name  = "N8N_PROXY_HOPS"
          value = "1"
        },
        {
          name  = "N8N_BLOCK_ENV_ACCESS_IN_NODE"
          value = "false"
        },
        {
          name  = "DB_TYPE"
          value = "postgresdb"
        },
        {
          name  = "DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED"
          value = "false"
        },
        {
          name  = "RENDER_BUCKET_NAME"
          value = aws_s3_bucket.render_outputs.bucket
        },
        {
          name  = "TELEGRAM_REVIEW_CHAT_ID"
          value = var.telegram_review_chat_id
        }
      ]

      secrets = [
        {
          name      = "DB_POSTGRESDB_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_password::"
        },
        {
          name      = "N8N_ENCRYPTION_KEY"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_encryption_key::"
        },
        {
          name      = "AUTOMATION_SHARED_TOKEN"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:automation_shared_token::"
        },
        {
          name      = "TYPECAST_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:typecast_api_key::"
        },
        {
          name      = "DB_POSTGRESDB_HOST"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_host::"
        },
        {
          name      = "DB_POSTGRESDB_PORT"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_port::"
        },
        {
          name      = "DB_POSTGRESDB_DATABASE"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_name::"
        },
        {
          name      = "DB_POSTGRESDB_USER"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_user::"
        },
        {
          name      = "DB_POSTGRESDB_SCHEMA"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_schema::"
        },
        {
          name      = "DB_POSTGRESDB_SSL_ENABLED"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:n8n_db_ssl_enabled::"
        }
      ]

      healthCheck = {
        command = [
          "CMD-SHELL",
          "node -e \"require('http').get('http://127.0.0.1:5678/healthz/readiness', (response) => process.exit(response.statusCode >= 200 && response.statusCode < 400 ? 0 : 1)).on('error', () => process.exit(1))\" || exit 1",
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.n8n.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = local.n8n_task_family
  })
}

resource "aws_ecs_service" "n8n" {
  name            = local.n8n_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.n8n.arn
  desired_count   = var.n8n_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.n8n.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.n8n.arn
    container_name   = local.n8n_service_name
    container_port   = local.n8n_container_port
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  enable_execute_command = true

  tags = merge(local.common_tags, {
    Name = local.n8n_service_name
  })

  depends_on = [
    aws_lb_listener.http,
    aws_lb_target_group.n8n,
  ]
}

resource "aws_ecs_task_definition" "automation" {
  family                   = local.automation_task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 2048
  memory                   = 4096
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = local.automation_service_name
      image     = var.automation_image
      essential = true

      portMappings = [
        {
          containerPort = local.automation_container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "PORT"
          value = tostring(local.automation_container_port)
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "RENDER_BUCKET"
          value = aws_s3_bucket.render_outputs.bucket
        },
        {
          name  = "FFMPEG_LOGLEVEL"
          value = "warning"
        }
      ]

      secrets = [
        {
          name      = "AUTOMATION_SHARED_TOKEN"
          valueFrom = "${aws_secretsmanager_secret.runtime.arn}:automation_shared_token::"
        }
      ]

      healthCheck = {
        command = [
          "CMD-SHELL",
          "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')\" || exit 1",
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 20
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.automation.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = local.automation_task_family
  })
}

resource "aws_ecs_service" "automation" {
  name            = local.automation_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.automation.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.automation.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.automation.arn
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  enable_execute_command = true

  tags = merge(local.common_tags, {
    Name = local.automation_service_name
  })

  lifecycle {
    ignore_changes = [task_definition]
  }
}
