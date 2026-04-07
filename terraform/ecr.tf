resource "aws_ecr_repository" "automation" {
  name                 = local.automation_task_family
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_lifecycle_policy" "automation" {
  repository = aws_ecr_repository.automation.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged automation images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
