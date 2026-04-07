# Terraform

Single-environment Terraform root for the `n8n` and `automation` deployment.

This stack is intended to run with the AWS profile `runner` and a single shared environment. It is not split into `dev` / `test` / `prod`.

## Architecture

- `n8n` is the public workflow engine behind the ALB.
- `automation` is a private ECS service that only performs final Python/ffmpeg rendering.
- `n8n` owns AI/API orchestration such as OpenAI, image generation, and TTS.
- Shared intermediate and final assets are stored in a single S3 bucket.
- `n8n` stores workflows and executions in the existing PostgreSQL RDS database.

## Usage

```powershell
$env:AWS_PROFILE='runner'
terraform -chdir=terraform init
terraform -chdir=terraform fmt -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform plan "-var-file=terraform.tfvars"
terraform -chdir=terraform apply "-var-file=terraform.tfvars"
```

## GitHub Actions deployment

- The repository includes `.github/workflows/deploy-automation.yml`.
- On every push to `main`, GitHub Actions builds the root `Dockerfile`, pushes the image to ECR repository `project1` with the commit SHA tag, and deploys the updated image to ECS service `automation`.
- `aws_ecs_service.automation` ignores `task_definition` drift so a later `terraform apply` does not roll back the image deployed by GitHub Actions.
- Required GitHub repository secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
- Terraform still owns the infrastructure. GitHub Actions only updates the running `automation` application image after the baseline stack exists.

## State

This root currently uses Terraform's default local state. That is acceptable for a single operator bootstrap, but the state file will contain references to generated runtime secrets and should be protected accordingly.

Before multiple operators or CI/CD start applying this stack, move the root to a remote backend such as S3 with locking.

## Inputs

Copy `terraform.tfvars.example` to `terraform.tfvars` and fill in at least these values:

- `vpc_id`
- `public_subnet_ids`
- `private_subnet_ids`
- `render_bucket_name`
- `n8n_db_password`
- `n8n_image` with a pinned tag or digest
- `automation_image` with a pinned tag or digest
- `certificate_arn` if HTTPS is required
- `n8n_domain_name` if using a custom domain, and it is required when `certificate_arn` is set
- `route53_zone_id` if Terraform should create the public alias record for `n8n_domain_name`
- `rds_security_group_id` if Terraform should open PostgreSQL access for `n8n`

You can use the `automation_ecr_repository_url` output after the first apply to build and push the renderer image with an immutable tag.

## Secrets

Terraform creates these Secrets Manager entries during apply:

- `project1/runtime`

Only `n8n_db_password` needs to be provided as input. Terraform writes a single JSON secret containing the n8n database connection values, the generated n8n encryption key, and the internal `automation` shared token.

AI/API credentials such as OpenAI, image generation, and TTS credentials are expected to live in `n8n` credentials storage rather than Terraform-managed ECS secrets by default.

## automation API shape

`n8n` uploads intermediate assets to S3 first, then calls the private `automation` service with S3 references rather than raw files.

Example payload:

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

## Post-deploy checks

- Open the public n8n URL from the ALB output.
- Confirm `n8n` target health on `/healthz/readiness`.
- From inside the VPC, confirm `http://automation.n8n.local:8080/health` returns `200`.
- Create an n8n workflow that can call `POST /render-jobs` and then poll `GET /render-jobs/{id}`.
- Confirm `automation` can read assets from S3 and write the final mp4 back to S3.
