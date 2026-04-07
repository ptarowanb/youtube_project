# automation CI/CD Design

**Context**

- `n8n` runs as the public workflow engine on ECS.
- `automation` runs as the private Python/ffmpeg render service on ECS.
- Terraform owns the baseline infrastructure.
- GitHub Actions should own the `automation` application delivery path.

## Goal

Build and deploy the `automation` service automatically when code lands on `main`.

## Scope

- Add a minimal Python HTTP service for `automation` so ECS can start and health-check it.
- Build a Docker image for `automation`.
- Push the image to ECR repository `project1`.
- Update the ECS service `automation` in cluster `n8n` to the new image revision.
- Keep `n8n` deployment and Terraform apply outside this workflow.

## Architecture

1. Developer pushes to `main`.
2. GitHub Actions checks out the repository.
3. GitHub Actions authenticates to AWS with repository secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
4. Workflow builds the `automation` Docker image.
5. Workflow pushes the image to ECR `project1` using the commit SHA as the immutable tag.
6. Workflow reads the current ECS task definition for family `project1`.
7. Workflow replaces only the `automation` container image field.
8. Workflow registers a new task definition revision.
9. Workflow updates ECS service `automation` in cluster `n8n`.

## Health Checks

- Do not use Dockerfile `HEALTHCHECK`.
- Use ECS task-definition-level container health checks consistently.
- `automation` exposes `GET /health`.
- `n8n` keeps its ALB health check and also gets a task-definition-level health check.

## Security

- Use GitHub repository secrets for AWS credentials.
- Do not store AWS credentials in the repository.
- Keep permissions limited to ECR push and ECS deployment actions for the chosen IAM identity.

## Tradeoffs

### Option 1: Build only

- Simpler workflow.
- Manual ECS rollout still required.

### Option 2: Build + ECS deploy

- Faster path from `main` to running service.
- Slightly more workflow complexity.
- Recommended and chosen.

## Non-Goals

- No GitHub-driven `terraform apply`.
- No `n8n` image build/deploy in this workflow.
- No Dockerfile-level health check.
