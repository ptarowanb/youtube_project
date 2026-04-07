# AWS ECS n8n Terraform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a single-environment Terraform stack that deploys self-hosted `n8n` and the internal Python/ffmpeg `automation` render service on ECS Fargate, stores both intermediate and final render assets in S3, and uses the existing PostgreSQL RDS instance for n8n metadata.

**Architecture:** A public ALB exposes only the `n8n` service. The `automation` service runs privately in the same ECS cluster and is reachable from `n8n` through Cloud Map service discovery. `n8n` handles AI/API orchestration and uploads intermediate assets to S3, while `automation` downloads those assets, assembles the final video with Python and ffmpeg, and writes the result back to S3.

**Tech Stack:** Terraform 1.x, AWS provider 5.x, ECS Fargate, ALB, Cloud Map, S3, CloudWatch Logs, Secrets Manager, existing PostgreSQL RDS, official `n8n` container image, Python render container with `ffmpeg`.

---

### Task 1: Scaffold the Terraform root

**Files:**
- Create: `terraform/main.tf`
- Create: `terraform/variables.tf`
- Create: `terraform/outputs.tf`
- Create: `terraform/terraform.tfvars.example`
- Create: `terraform/README.md`

**Step 1: Create the Terraform root and provider configuration**

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "runner"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
```

**Step 2: Define the first-pass variables**

```hcl
variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "project_name" {
  type    = string
  default = "project1"
}

variable "cluster_name" {
  type    = string
  default = "n8n"
}
```

**Step 3: Add the base outputs and example tfvars placeholders**

```hcl
output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}
```

```hcl
aws_region         = "ap-northeast-2"
vpc_id             = "vpc-xxxxxxxx"
public_subnet_ids  = ["subnet-aaaa", "subnet-bbbb"]
private_subnet_ids = ["subnet-cccc", "subnet-dddd"]
```

**Step 4: Run formatting**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
```

Expected: every file is formatted, with exit code `0`.

**Step 5: Run validation to confirm the root is wired**

Run:

```powershell
$env:AWS_PROFILE='runner'
terraform -chdir=terraform init
terraform -chdir=terraform validate
```

Expected: validation passes for the minimal scaffold.

**Step 6: Commit**

```bash
git add terraform/main.tf terraform/variables.tf terraform/outputs.tf terraform/terraform.tfvars.example terraform/README.md
git commit -m "chore: scaffold terraform root"
```

### Task 2: Define shared locals, naming, and required inputs

**Files:**
- Modify: `terraform/main.tf`
- Modify: `terraform/variables.tf`
- Modify: `terraform/terraform.tfvars.example`

**Step 1: Add shared locals for names and ports**

```hcl
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
}
```

**Step 2: Add networking and DNS-related inputs**

```hcl
variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "certificate_arn" {
  type    = string
  default = ""
}

variable "n8n_domain_name" {
  type    = string
  default = ""
}
```

**Step 3: Add existing RDS and S3-related inputs**

```hcl
variable "n8n_db_host" {
  type    = string
  default = "runnerpoker-test.cmhs16pmizic.ap-northeast-2.rds.amazonaws.com"
}

variable "n8n_db_name" {
  type    = string
  default = "n8n"
}

variable "n8n_db_user" {
  type    = string
  default = "runner_dev"
}

variable "n8n_db_schema" {
  type    = string
  default = "public"
}

variable "render_bucket_name" {
  type = string
}

variable "rds_security_group_id" {
  type    = string
  default = ""
}
```

**Step 4: Document the new inputs in `terraform.tfvars.example`**

```hcl
certificate_arn       = ""
n8n_domain_name       = ""
render_bucket_name    = "youtube-project-render-bucket"
rds_security_group_id = ""
```

**Step 5: Re-run validation**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
```

Expected: syntax remains valid.

**Step 6: Commit**

```bash
git add terraform/main.tf terraform/variables.tf terraform/terraform.tfvars.example
git commit -m "chore: add terraform naming and input variables"
```

### Task 3: Add shared infrastructure resources

**Files:**
- Create: `terraform/ecr.tf`
- Create: `terraform/s3.tf`
- Create: `terraform/cloudwatch.tf`
- Create: `terraform/secrets.tf`
- Create: `terraform/iam.tf`
- Modify: `terraform/variables.tf`

**Step 1: Create the ECR repository for the render image**

```hcl
resource "aws_ecr_repository" "automation" {
  name                 = local.automation_task_family
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}
```

**Step 2: Create the S3 bucket for intermediate and final outputs**

```hcl
resource "aws_s3_bucket" "render_outputs" {
  bucket = var.render_bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "render_outputs" {
  bucket = aws_s3_bucket.render_outputs.id

  versioning_configuration {
    status = "Enabled"
  }
}
```

**Step 3: Create log groups for both ECS services**

```hcl
resource "aws_cloudwatch_log_group" "n8n" {
  name              = "/ecs/${local.n8n_service_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "automation" {
  name              = "/ecs/${local.automation_service_name}"
  retention_in_days = 14
}
```

**Step 4: Create Secrets Manager secrets for runtime values**

```hcl
resource "aws_secretsmanager_secret" "n8n_db_password" {
  name = "n8n/db-password"
}

resource "aws_secretsmanager_secret" "n8n_encryption_key" {
  name = "n8n/encryption-key"
}

resource "aws_secretsmanager_secret" "automation_shared_token" {
  name = "automation/shared-token"
}
```

**Step 5: Create ECS task execution and task roles**

```hcl
resource "aws_iam_role" "ecs_task_execution" {
  name               = "ecs-task-execution-n8n"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

resource "aws_iam_role" "ecs_task" {
  name               = "ecs-task-runtime-n8n"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}
```

The runtime task role must allow:

- `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the render bucket
- `secretsmanager:GetSecretValue` on required secrets
- `logs:CreateLogStream`, `logs:PutLogEvents` through the execution role

**Step 6: Validate**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
```

Expected: syntax is valid; any remaining failures should come from resources not yet added.

**Step 7: Commit**

```bash
git add terraform/ecr.tf terraform/s3.tf terraform/cloudwatch.tf terraform/secrets.tf terraform/iam.tf terraform/variables.tf
git commit -m "feat: add shared AWS resources for n8n stack"
```

### Task 4: Define networking, service discovery, and security groups

**Files:**
- Create: `terraform/networking.tf`
- Create: `terraform/service-discovery.tf`
- Modify: `terraform/variables.tf`

**Step 1: Create security groups for ALB, n8n, and automation**

```hcl
resource "aws_security_group" "alb" {
  name   = "${var.cluster_name}-alb-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

**Step 2: Restrict `n8n` and `automation` ingress correctly**

```hcl
resource "aws_security_group" "n8n" {
  name   = "${local.n8n_service_name}-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = local.n8n_container_port
    to_port         = local.n8n_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
}

resource "aws_security_group" "automation" {
  name   = "${local.automation_service_name}-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = local.automation_container_port
    to_port         = local.automation_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.n8n.id]
  }
}
```

**Step 3: Allow optional database ingress from the n8n security group**

```hcl
resource "aws_security_group_rule" "n8n_to_rds" {
  count                    = var.rds_security_group_id == "" ? 0 : 1
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = var.rds_security_group_id
  source_security_group_id = aws_security_group.n8n.id
}
```

**Step 4: Create the Cloud Map namespace and automation service registration**

```hcl
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "n8n.local"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "automation" {
  name = local.automation_service_name

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}
```

**Step 5: Validate networking**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
```

Expected: validation should now only fail on ECS and ALB resources not yet created.

**Step 6: Commit**

```bash
git add terraform/networking.tf terraform/service-discovery.tf terraform/variables.tf
git commit -m "feat: add networking and service discovery"
```

### Task 5: Add the public ALB and the n8n ECS service

**Files:**
- Create: `terraform/alb.tf`
- Create: `terraform/ecs.tf`
- Modify: `terraform/variables.tf`
- Modify: `terraform/outputs.tf`

**Step 1: Create the ALB, target group, and listeners**

```hcl
resource "aws_lb" "main" {
  name               = "${var.cluster_name}-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "n8n" {
  name        = "${local.n8n_service_name}-tg"
  port        = local.n8n_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path = "/healthz/readiness"
  }
}
```

Create:

- HTTP listener always
- HTTPS listener only when `certificate_arn != ""`

**Step 2: Create the ECS cluster**

```hcl
resource "aws_ecs_cluster" "main" {
  name = var.cluster_name
}
```

**Step 3: Create the n8n task definition using the official image**

Use the official image:

```hcl
image = "docker.n8n.io/n8nio/n8n:stable"
```

Set these core environment values:

```hcl
{ name = "N8N_PORT", value = tostring(local.n8n_container_port) }
{ name = "N8N_HOST", value = var.n8n_domain_name != "" ? var.n8n_domain_name : aws_lb.main.dns_name }
{ name = "N8N_PROTOCOL", value = var.certificate_arn != "" ? "https" : "http" }
{ name = "WEBHOOK_URL", value = var.n8n_domain_name != "" ? "https://${var.n8n_domain_name}/" : "http://${aws_lb.main.dns_name}/" }
{ name = "N8N_PROXY_HOPS", value = "1" }
{ name = "DB_TYPE", value = "postgresdb" }
{ name = "DB_POSTGRESDB_HOST", value = var.n8n_db_host }
{ name = "DB_POSTGRESDB_DATABASE", value = var.n8n_db_name }
{ name = "DB_POSTGRESDB_USER", value = var.n8n_db_user }
{ name = "DB_POSTGRESDB_SCHEMA", value = var.n8n_db_schema }
```

Inject these secrets:

- `DB_POSTGRESDB_PASSWORD`
- `N8N_ENCRYPTION_KEY`

**Step 4: Create the n8n ECS service**

- Name: `n8n`
- Desired count: `1`
- Subnets: `private_subnet_ids`
- Security group: `aws_security_group.n8n.id`
- Load balancer target group: `aws_lb_target_group.n8n`

**Step 5: Validate with a real plan**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=terraform.tfvars
```

Expected: n8n ALB, target group, cluster, task definition, and service appear in the plan.

**Step 6: Commit**

```bash
git add terraform/alb.tf terraform/ecs.tf terraform/variables.tf terraform/outputs.tf
git commit -m "feat: add public n8n ECS service"
```

### Task 6: Add the private automation ECS service

**Files:**
- Modify: `terraform/ecs.tf`
- Modify: `terraform/iam.tf`
- Modify: `terraform/outputs.tf`
- Modify: `terraform/variables.tf`
- Modify: `terraform/README.md`

**Step 1: Add automation image and runtime variables**

```hcl
variable "automation_image" {
  type    = string
  default = ""
}
```

Task definition must include:

```hcl
{ name = "PORT", value = tostring(local.automation_container_port) }
{ name = "AWS_REGION", value = var.aws_region }
{ name = "RENDER_BUCKET", value = aws_s3_bucket.render_outputs.bucket }
{ name = "FFMPEG_LOGLEVEL", value = "warning" }
```

Inject:

- `AUTOMATION_SHARED_TOKEN`

**Step 2: Add container health check**

```hcl
healthCheck = {
  command     = ["CMD-SHELL", "curl -fsS http://127.0.0.1:8080/health || exit 1"]
  interval    = 30
  timeout     = 5
  retries     = 3
  startPeriod = 20
}
```

**Step 3: Add the automation ECS service with Cloud Map registration**

- Name: `automation`
- Desired count: `1`
- No public load balancer
- Service registry: `aws_service_discovery_service.automation`
- Security group: `aws_security_group.automation.id`

**Step 4: Grant runtime S3 access to the automation task role**

Add an IAM policy that allows:

```json
{
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Effect": "Allow"
}
```

Scope it only to the render bucket and its objects.

**Step 5: Export the internal automation URL**

```hcl
output "automation_internal_base_url" {
  value = "http://${local.automation_service_name}.n8n.local:${local.automation_container_port}"
}
```

**Step 6: Document the automation API shape in `terraform/README.md`**

Document that `automation` receives references to assets already uploaded by `n8n`, for example:

```json
{
  "job_id": "job_123",
  "audio_keys": ["jobs/job_123/audio/01.mp3"],
  "image_keys": ["jobs/job_123/images/01.png"],
  "subtitle_key": "jobs/job_123/subtitles/output.srt",
  "bgm_key": "shared/bgm/default.mp3",
  "output_prefix": "jobs/job_123/output/"
}
```

**Step 7: Validate**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=terraform.tfvars
```

Expected: the plan now includes both ECS services and the private Cloud Map registration for `automation`.

**Step 8: Commit**

```bash
git add terraform/ecs.tf terraform/iam.tf terraform/outputs.tf terraform/variables.tf terraform/README.md
git commit -m "feat: add private automation render service"
```

### Task 7: Document deployment, secrets bootstrap, and first-run checks

**Files:**
- Modify: `terraform/README.md`
- Modify: `terraform/terraform.tfvars.example`

**Step 1: Document all required inputs**

Document at minimum:

- `vpc_id`
- `public_subnet_ids`
- `private_subnet_ids`
- `render_bucket_name`
- `certificate_arn`
- `n8n_domain_name`
- `automation_image`
- `rds_security_group_id`

**Step 2: Document the required secret creation order**

Include exact secret names:

- `n8n/db-password`
- `n8n/encryption-key`
- `automation/shared-token`

Also document that AI/API credentials such as OpenAI, image generation, and TTS credentials are owned by `n8n` credentials storage rather than Terraform-managed ECS secrets by default.

**Step 3: Document the first deployment commands**

```powershell
$env:AWS_PROFILE='runner'
terraform -chdir=terraform init
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=terraform.tfvars
terraform -chdir=terraform apply -var-file=terraform.tfvars
```

**Step 4: Document post-deploy checks**

Add checks for:

- `n8n` ALB URL opens successfully
- `/healthz/readiness` returns `200`
- `automation` responds inside the VPC at `http://automation.n8n.local:8080/health`
- `n8n` workflow can call `POST /render-jobs`
- `automation` can read inputs from `S3` and write the final result back to `S3`

**Step 5: Run a final validation**

Run:

```powershell
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=terraform.tfvars
```

Expected: no Terraform validation errors; the plan shows only the intended AWS resources.

**Step 6: Commit**

```bash
git add terraform/README.md terraform/terraform.tfvars.example
git commit -m "docs: add terraform deployment guide"
```

### Task 8: Verify the finished stack definition before claiming completion

**Files:**
- Review: `terraform/main.tf`
- Review: `terraform/variables.tf`
- Review: `terraform/networking.tf`
- Review: `terraform/alb.tf`
- Review: `terraform/ecr.tf`
- Review: `terraform/iam.tf`
- Review: `terraform/ecs.tf`
- Review: `terraform/service-discovery.tf`
- Review: `terraform/s3.tf`
- Review: `terraform/secrets.tf`
- Review: `terraform/cloudwatch.tf`
- Review: `terraform/outputs.tf`
- Review: `terraform/README.md`

**Step 1: Re-read the approved design doc**

Read:

```text
docs/plans/2026-04-03-aws-ecs-n8n-terraform-design.md
```

Create a checklist from it:

- `n8n` public via ALB
- `automation` private only
- `n8n` owns AI/API orchestration
- `automation` only performs final render assembly
- RDS PostgreSQL for `n8n`
- S3 render outputs
- Secrets Manager for secrets
- CloudWatch logs
- single environment only

**Step 2: Run the final Terraform commands fresh**

Run:

```powershell
$env:AWS_PROFILE='runner'
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=terraform.tfvars
```

Expected: all commands succeed, and the plan reflects the approved architecture.

**Step 3: Verify naming explicitly**

Check that the generated names match:

- ECS cluster: `n8n`
- ECS service: `n8n`
- ECS service: `automation`
- Task family: `n8n`
- Task family: `project1`

**Step 4: Verify database settings explicitly**

Check that n8n runtime config resolves to:

- host: `runnerpoker-test.cmhs16pmizic.ap-northeast-2.rds.amazonaws.com`
- database: `n8n`
- user: `runner_dev`
- schema: `public`

**Step 5: Commit**

```bash
git add terraform
git commit -m "feat: add n8n and automation ECS infrastructure"
```

Plan complete and saved to `docs/plans/2026-04-03-aws-ecs-n8n-terraform.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
