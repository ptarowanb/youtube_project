resource "aws_security_group" "alb" {
  name        = "${var.cluster_name}-alb-sg"
  description = "Security group for the public n8n ALB"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-alb-sg"
  })
}

resource "aws_security_group" "n8n" {
  name        = "${local.n8n_service_name}-sg"
  description = "Security group for the private n8n ECS service"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow ALB traffic to n8n"
    from_port       = local.n8n_container_port
    to_port         = local.n8n_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.n8n_service_name}-sg"
  })
}

resource "aws_security_group" "automation" {
  name        = "${local.automation_service_name}-sg"
  description = "Security group for the private automation render service"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow only n8n to reach automation"
    from_port       = local.automation_container_port
    to_port         = local.automation_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.n8n.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.automation_service_name}-sg"
  })
}

resource "aws_security_group_rule" "n8n_to_rds" {
  count                    = var.rds_security_group_id == "" ? 0 : 1
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.n8n.id
  description              = "Allow n8n ECS service to reach the existing PostgreSQL RDS instance"
}
